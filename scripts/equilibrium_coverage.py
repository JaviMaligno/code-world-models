"""Equilibrium-reach coverage: the Sec. 6.2 Leduc coverage statement, measured
against APPROXIMATE-EQUILIBRIUM reach instead of MCTS-self-play reach.

Fulfils the Sec. 7.4 promise ("run an equilibrium solver; measure the gap
against equilibrium reach rather than MCTS reach"): we run external-sampling
MCCFR / full-tree CFR+ (validated on Kuhn: game value -1/18;
tests/test_cfr.py) on the TRUE game, extract the average-strategy profile sigma-bar, report its
exploitability (certifying how close to equilibrium it is), compute each
info-set's EXACT reach probability under (sigma-bar, sigma-bar), and then ask
the coverage question of Sec. 6.2 for the equilibrium-relevant subset: what is
the union-bound probability that the N=8000 random gate misses any info-set
that equilibrium play relies on?

Run: PYTHONPATH=src python3.12 scripts/equilibrium_coverage.py
Writes results/equilibrium_coverage.json.
"""
import json
import math
from pathlib import Path

from cwm.groundtruth import kuhn_poker as K
from cwm.groundtruth import leduc_poker as L
from cwm.cfr import VanillaCFRPlus, expected_value, exploitability


def obs_key(model, state, player):
    """The gate's view of an info-set: (player, instantaneous observation).
    The solver runs on perfect-recall keys (observation + public history, see
    cwm.cfr); reach is PROJECTED onto these observation keys because they are
    what the inference gate actually samples."""
    return (player, tuple(model.observation(state, player)))

GATE_N = {"kuhn": 80, "leduc": 8000}     # deployed gate sizes from the paper
# Full-tree CFR+ (exact regrets, RM+, linear averaging): converges far tighter
# than sampling MCCFR on games this size. Kuhn validated against the analytic
# value in tests/test_cfr.py; external-sampling MCCFR (also in cwm.cfr) is the
# scalable variant but stalls at ~0.6 chips exploitability on Leduc within a
# CPU budget, so the solver of record here is CFR+.
ITERS = {"kuhn": 2_000, "leduc": 1_000}
CHECK_EVERY = {"kuhn": 2_000, "leduc": 250}   # exploitability checkpoints
THRESHOLDS = (1e-2, 1e-3, 1e-4)           # per-threshold subset reporting


def random_reach(model):
    """Exact pi^rho (uniform-random) reach probability per non-terminal info-set."""
    deals = model.initial_states()
    pc = 1.0 / len(deals)
    reach = {}
    def rec(s, prob):
        if model.is_terminal(s):
            return
        k = obs_key(model, s, s["current_player"])
        reach[k] = reach.get(k, 0.0) + prob
        legal = model.legal_actions(s)
        for a in legal:
            rec(model.apply_action(s, a), prob / len(legal))
    for d in deals:
        rec({"board": list(d["board"]), "current_player": d["current_player"]}, pc)
    return reach


def equilibrium_reach(model, strategy):
    """Exact reach per OBSERVATION key under (sigma,sigma): the profile is read
    with perfect-recall keys, the reach is accumulated projected onto the
    observation keys the gate samples."""
    from cwm.cfr import _profile_sigma
    deals = model.initial_states()
    pc = 1.0 / len(deals)
    reach = {}
    def rec(s, prob, hist):
        if model.is_terminal(s):
            return
        k = obs_key(model, s, s["current_player"])
        reach[k] = reach.get(k, 0.0) + prob
        actions = model.legal_actions(s)
        sig = _profile_sigma(model, strategy, s, len(actions), hist)
        for a, p in zip(actions, sig):
            if p > 0.0:
                rec(model.apply_action(s, a), prob * p, hist + (a,))
    for d in deals:
        rec({"board": list(d["board"]), "current_player": d["current_player"]},
            pc, ())
    return reach


def analyze(name, model):
    print(f"=== {name} ===", flush=True)
    solver = VanillaCFRPlus(model)
    done = 0
    expl = None
    while done < ITERS[name]:
        step = min(CHECK_EVERY[name], ITERS[name] - done)
        solver.iterate(step)
        done += step
        avg = solver.average_strategy()
        expl = exploitability(model, avg)
        print(f"  iters={done}: exploitability = {expl:.4f}", flush=True)
    avg = solver.average_strategy()
    v = expected_value(model, avg)
    print(f"CFR+ {done} iters: game value (P1) = {v:.4f}, "
          f"final exploitability = {expl:.4f}", flush=True)

    rho = random_reach(model)
    eq = equilibrium_reach(model, avg)
    N = GATE_N[name]

    # (i) The threshold-free headline: equilibrium-weighted uncovered mass.
    # Sum of eq-reach over info-sets, weighted by the gate's per-set miss
    # probability, normalized by total eq-reach: "of the decisions equilibrium
    # play makes, what expected fraction falls on info-sets a size-N random
    # gate never visited?"
    tot_mass = sum(eq.values())
    uncov_mass = sum(p * (1.0 - rho[k]) ** N for k, p in eq.items())
    frac_uncov = uncov_mass / tot_mass if tot_mass > 0 else 0.0
    print(f"equilibrium-weighted uncovered mass at N={N}: {frac_uncov:.4%} "
          f"(of all equilibrium decision mass)", flush=True)

    # (ii) Per-threshold subsets: the union-bound question on info-sets the
    # equilibrium actually relies on (reach >= t).
    per_threshold = []
    for t in THRESHOLDS:
        sub = {k: p for k, p in eq.items() if p >= t}
        if not sub:
            continue
        miss = sum((1.0 - rho[k]) ** N for k in sub)
        pi_min = min(rho[k] for k in sub)
        covered = miss < 0.05
        print(f"  eq-reach >= {t:g}: {len(sub)} info-sets, union-bound miss = "
              f"{miss:.4g} ({'covered' if covered else 'NOT covered'}), "
              f"pi_min = {pi_min:.4g}", flush=True)
        per_threshold.append({"threshold": t, "n_infosets": len(sub),
                              "union_bound_miss": miss, "pi_min_random": pi_min,
                              "covered": covered})
    return {"iters": done, "game_value_p1": v, "exploitability": expl,
            "reachable_infosets": len(rho), "gate_N": N,
            "eq_weighted_uncovered_mass_frac": frac_uncov,
            "per_threshold": per_threshold}


def main():
    out = {}
    out["kuhn"] = analyze("kuhn", K)
    out["leduc"] = analyze("leduc", L)
    Path("results").mkdir(exist_ok=True)
    Path("results/equilibrium_coverage.json").write_text(json.dumps(out, indent=2))
    print("wrote results/equilibrium_coverage.json", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()

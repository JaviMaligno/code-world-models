"""Diagnostic: does a coverage gap exist in Leduc between competent and random play?

Claim A needs an info-set region that competent play visits (so wrong inference
there costs play) but random sampling at the gate size misses (so the gate is
blind). This measures, model-free, whether such a region exists and what board
features characterize it — BEFORE committing to a _is_tail predicate.

Run: PYTHONPATH=src python scripts/leduc_coverage_diagnostic.py
"""
import random
from collections import Counter

from cwm.groundtruth import leduc_poker as L
from cwm.determinized import determinized_policy
from cwm.leduc_instrument import infoset_key

SIMS = 200
N_DET = 8


def n_consistent(obs_tuple, player):
    """How many opponent assignments are consistent (>1 => inference matters)."""
    return len(L.infer_states(list(obs_tuple), player))


def random_coverage_with_counts(n_games, seed):
    rng = random.Random(seed)
    deals = L.initial_states()
    counts = Counter()
    for _ in range(n_games):
        d = deals[rng.randrange(len(deals))]
        s = {"board": list(d["board"]), "current_player": d["current_player"]}
        while not L.is_terminal(s):
            counts[infoset_key(s["board"], s["current_player"])] += 1
            s = L.apply_action(s, rng.choice(L.legal_actions(s)))
    return counts


def competent_coverage_with_counts(n_games, seed):
    rng = random.Random(seed)
    deals = L.initial_states()
    counts = Counter()
    for i in range(n_games):
        d = deals[rng.randrange(len(deals))]
        s = {"board": list(d["board"]), "current_player": d["current_player"]}
        while not L.is_terminal(s):
            counts[infoset_key(s["board"], s["current_player"])] += 1
            a = determinized_policy(L, s, n_determinizations=N_DET,
                                    simulations=SIMS, seed=seed + i * 1000)
            if a not in L.legal_actions(s):
                a = L.legal_actions(s)[0]
            s = L.apply_action(s, a)
    return counts


def board_features(obs_tuple):
    """(round, max_committed, total_committed) — the structural signature."""
    b = obs_tuple
    return (b[3], max(b[4], b[5]), b[4] + b[5])


def main():
    # Random play at a generous gate size.
    rand = random_coverage_with_counts(n_games=8000, seed=0)
    # Competent play (expensive) at a modest size — we care about WHICH info-sets,
    # weighted by visit frequency, not precise rates.
    comp = competent_coverage_with_counts(n_games=300, seed=0)

    rand_set = set(rand)
    comp_total = sum(comp.values())

    # Info-sets competent play visits that random NEVER sampled, restricted to
    # those where inference is non-trivial (>1 consistent state).
    uncovered = {k: c for k, c in comp.items()
                 if k not in rand_set and n_consistent(k, _player_of(k)) > 1}

    print(f"random info-sets (4000 games): {len(rand_set)}")
    print(f"competent info-sets (120 games): {len(comp)}")
    covered = sum(c for k, c in comp.items() if k in rand_set)
    print(f"competent VISITS on random-covered info-sets: "
          f"{covered}/{comp_total} = {covered/comp_total:.3f}")
    unc_mass = sum(comp[k] for k in uncovered)
    print(f"competent VISITS on uncovered (inference-relevant) info-sets: "
          f"{unc_mass}/{comp_total} = {unc_mass/comp_total:.3f}")
    print(f"# distinct uncovered inference-relevant info-sets: {len(uncovered)}")

    # Characterize the uncovered region by board features.
    feat = Counter(board_features(k) for k in uncovered)
    print("\nuncovered region by (round, max_committed, total_committed) -> distinct infosets:")
    for f, n in sorted(feat.items(), key=lambda kv: -kv[1])[:15]:
        print(f"  round={f[0]} max_committed={f[1]} total={f[2]}: {n}")

    # For comparison: how often does random play reach each (round, max_committed)?
    rand_feat = Counter()
    for k, c in rand.items():
        rand_feat[board_features(k)] += c
    rand_visits = sum(rand.values())
    print("\nrandom-play visit fraction by (round, max_committed, total):")
    for f in sorted(rand_feat, key=lambda x: -rand_feat[x])[:15]:
        print(f"  round={f[0]} max_committed={f[1]} total={f[2]}: "
              f"{rand_feat[f]/rand_visits:.4f}")


def _player_of(obs_tuple):
    # current_player derivable from acted_round (index 7)
    return 1 if obs_tuple[7] % 2 == 0 else 2


if __name__ == "__main__":
    main()

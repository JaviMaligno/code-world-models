"""Danger-vs-rarity curve, efficiently: the play_cost is ~constant across caps
(competent play always reaches the cap region), while rarity (random-play
incidence) varies. So measure the CHEAP part (rarity, random rollouts, no MCTS)
on a fine cap grid, the EXPENSIVE part (play_cost, MCTS) precisely at a few caps,
and COMPUTE danger = play_cost * (1 - rarity)^N.

The fair baseline is 0.5 by symmetry (alternating starts, identical models); we
verify it once at high n and then use 0.5 as the reference so play_cost has only
one noisy term (blind_winrate), measured with enough games to resolve ~0.1.

Run: PYTHONPATH=src python scripts/law_curve.py
"""
import json
from pathlib import Path

from cwm.law import rarity, arena_winrate, danger
from cwm.groundtruth import gen_chess_material as gm
from cwm.groundtruth import gen_chess as base_army


class BaseArmyCap:
    """Rule-blind army at a given cap: the cap is a DRAW (omits the material
    rule) — the on-manifold proxy for a CWM that never learned the rule."""
    def __init__(self, max_plies):
        self.max_plies = max_plies

    def initial_state(self):
        return base_army.initial_state()

    def apply_action(self, s, a):
        return base_army.apply_action(s, a)

    def is_terminal(self, s):
        b = s["board"]
        return ((not base_army._general_alive(b, 1)) or (not base_army._general_alive(b, 2))
                or b[base_army.N] >= self.max_plies)

    def legal_actions(self, s):
        return [] if self.is_terminal(s) else gm._moves(s["board"], s["current_player"])

    def returns(self, s):
        b = s["board"]
        a1, a2 = base_army._general_alive(b, 1), base_army._general_alive(b, 2)
        if a1 and not a2:
            return {1: 1.0, 2: -1.0}
        if a2 and not a1:
            return {1: -1.0, 2: 1.0}
        return {1: 0.0, 2: 0.0}

# CHEAP rarity grid (no MCTS): many caps, many random games.
CAP_GRID = [25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100, 120, 140]
RARITY_GAMES = 2000
# EXPENSIVE cost probes (MCTS): a few caps, enough games to resolve ~0.1.
COST_CAPS = [30, 60, 100]
COST_SIMS = 300
COST_GAMES = 80          # x len(COST_SEEDS) pooled
COST_SEEDS = [0, 1, 2, 3]   # 320 pooled games per probe
N_TRAJ = [20, 40, 80]

import sys


def main():
    Path("results").mkdir(exist_ok=True)
    out = {"rarity_grid": [], "cost_probes": [], "fair_check": None, "danger_curve": []}

    # 1) fair baseline check (truth vs truth) at one cap, high n — expect ~0.5
    g_mid = gm.make_material(max_plies=60)
    fair = arena_winrate(g_mid, g_mid, COST_SIMS, COST_GAMES, COST_SEEDS)
    out["fair_check"] = {"cap": 60, "winrate": fair["winrate"],
                         "ci": [fair["lo"], fair["hi"]], "n": fair["n"]}
    print(f"[fair] truth-vs-truth cap=60: {fair['winrate']:.3f} "
          f"CI[{fair['lo']:.3f},{fair['hi']:.3f}] n={fair['n']}  (expect ~0.5)", flush=True)

    # 2) cheap rarity over the fine grid
    print("[rarity grid] (random play, no MCTS)", flush=True)
    rar_by_cap = {}
    for cap in CAP_GRID:
        g = gm.make_material(max_plies=cap)
        rate, lo, hi = rarity(g, "material", RARITY_GAMES, seed=1)
        rar_by_cap[cap] = rate
        out["rarity_grid"].append({"cap": cap, "rarity": rate, "ci": [lo, hi]})
        print(f"  cap={cap:3d}  rarity={rate:.3f} CI[{lo:.3f},{hi:.3f}]", flush=True)
        Path("results/law_curve.json").write_text(json.dumps(out, indent=2))

    # 3) precise play_cost at a few caps (cost = 0.5 - blind_winrate)
    print("[cost probes] (MCTS, blind vs truth)", flush=True)
    cost_by_cap = {}
    for cap in COST_CAPS:
        truth = gm.make_material(max_plies=cap)
        blind = BaseArmyCap(cap)
        res = arena_winrate(truth, blind, COST_SIMS, COST_GAMES, COST_SEEDS)
        cost = 0.5 - res["winrate"]
        cost_by_cap[cap] = cost
        out["cost_probes"].append({"cap": cap, "blind_winrate": res["winrate"],
                                   "blind_ci": [res["lo"], res["hi"]],
                                   "play_cost": cost, "n": res["n"]})
        print(f"  cap={cap:3d}  blind_winrate={res['winrate']:.3f} "
              f"CI[{res['lo']:.3f},{res['hi']:.3f}]  play_cost={cost:.3f}  n={res['n']}", flush=True)
        Path("results/law_curve.json").write_text(json.dumps(out, indent=2))

    # 4) danger curve: cost interpolated as the mean probe cost (it is ~constant);
    #    report danger = cost_const * (1-rarity)^N over the fine grid.
    cost_const = sum(cost_by_cap.values()) / len(cost_by_cap)
    print(f"[danger] using ~constant play_cost={cost_const:.3f} "
          f"(probes: {', '.join(f'{c}:{v:.3f}' for c,v in cost_by_cap.items())})", flush=True)
    print(f"  {'cap':>4s} {'rarity':>7s} {'dgr@20':>7s} {'dgr@40':>7s} {'dgr@80':>7s}", flush=True)
    for cap in CAP_GRID:
        r = rar_by_cap[cap]
        d = {n: danger(cost_const, r, n) for n in N_TRAJ}
        out["danger_curve"].append({"cap": cap, "rarity": r, "play_cost": cost_const,
                                    "danger": {str(n): d[n] for n in N_TRAJ}})
        print(f"  {cap:>4d} {r:7.3f} {d[20]:7.3f} {d[40]:7.3f} {d[80]:7.3f}", flush=True)
    out["cost_const"] = cost_const
    Path("results/law_curve.json").write_text(json.dumps(out, indent=2))
    print("DONE", flush=True)


if __name__ == "__main__":
    main()

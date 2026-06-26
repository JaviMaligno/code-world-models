"""Run the quantitative-law sweep: army5x5a cap-length rarity knob (the
inverted-U danger curve) + Connect Four low-divergence contrast. CPU only.

Run: PYTHONPATH=src python scripts/law_sweep.py
"""
import json
from pathlib import Path

from cwm.law import rarity, arena_winrate, danger
from cwm.groundtruth import gen_chess_material as gm, connect_four as base_cf
from cwm.groundtruth import gen_chess as base_army

SIMS = 400
N_GAMES = 80
SEEDS = [0, 1, 2]
RARITY_GAMES = 400
N_TRAJ = [20, 40, 80]          # gate sizes for the danger metric

ROWS, COLS = 6, 7
def _i(r, c):
    return r * COLS + c


class CFRule:
    """Connect Four + one extra instant-win shape (low-divergence contrast)."""
    def __init__(self, rule):
        self.rule = rule

    def initial_state(self):
        return base_cf.initial_state()

    def apply_action(self, s, a):
        return base_cf.apply_action(s, a)

    def legal_actions(self, s):
        if self.is_terminal(s):
            return []
        return [c for c in range(COLS) if s["board"][_i(0, c)] == 0]

    def _vthree(self, b):
        for r in range(ROWS - 2):
            p = b[_i(r, 3)]
            if p and b[_i(r + 1, 3)] == p and b[_i(r + 2, 3)] == p:
                return p
        return 0

    def _square(self, b):
        for r in range(ROWS - 1):
            for c in range(COLS - 1):
                p = b[_i(r, c)]
                if p and b[_i(r, c + 1)] == p and b[_i(r + 1, c)] == p and b[_i(r + 1, c + 1)] == p:
                    return p
        return 0

    def outcome(self, s):
        b = s["board"]
        # topcenter is a tiebreak: a base line-win takes priority (the `winner==0`
        # guard), so it only fires when no 4-in-a-row exists. This slightly
        # under-counts topcenter rarity, which is conservative for the contrast.
        if self.rule == "topcenter" and b[_i(0, 3)] != 0 and base_cf.winner(s) == 0:
            return b[_i(0, 3)], "rule"
        if self.rule == "vthree":
            x = self._vthree(b)
            if x:
                return x, "rule"
        if self.rule == "square":
            x = self._square(b)
            if x:
                return x, "rule"
        w = base_cf.winner(s)
        if w:
            return w, "line"
        if all(v != 0 for v in b):
            return 0, "draw"
        return 0, "none"

    def is_terminal(self, s):
        return self.outcome(s)[1] != "none"

    def returns(self, s):
        w, reason = self.outcome(s)
        if reason == "none":
            return {1: 0.0, 2: 0.0}
        return {1: 1.0, 2: -1.0} if w == 1 else {1: -1.0, 2: 1.0} if w == 2 else {1: 0.0, 2: 0.0}


def row(name, truth, blind, reason):
    rar, rlo, rhi = rarity(truth, reason, RARITY_GAMES, seed=1)
    fair = arena_winrate(truth, truth, SIMS, N_GAMES, SEEDS)        # fairness baseline
    blind_res = arena_winrate(truth, blind, SIMS, N_GAMES, SEEDS)
    play_cost = fair["winrate"] - blind_res["winrate"]
    dangers = {str(n): danger(play_cost, rar, n) for n in N_TRAJ}
    return {"config": name, "rarity": rar, "rarity_ci": [rlo, rhi],
            "fair_winrate": fair["winrate"],
            "blind_winrate": blind_res["winrate"],
            "blind_ci": [blind_res["lo"], blind_res["hi"]],
            "play_cost": play_cost, "danger": dangers}


class BaseArmyCap:
    """Rule-blind army at a given cap: cap is a DRAW (omits material rule)."""
    def __init__(self, max_plies):
        self.max_plies = max_plies
    def initial_state(self):
        return base_army.initial_state()
    def apply_action(self, s, a):
        return base_army.apply_action(s, a)
    def _term(self, b):
        return (not base_army._general_alive(b, 1)) or (not base_army._general_alive(b, 2)) or b[base_army.N] >= self.max_plies
    def is_terminal(self, s):
        return self._term(s["board"])
    def legal_actions(self, s):
        from cwm.groundtruth.gen_chess_material import _moves
        return [] if self.is_terminal(s) else _moves(s["board"], s["current_player"])
    def returns(self, s):
        b = s["board"]; a1 = base_army._general_alive(b, 1); a2 = base_army._general_alive(b, 2)
        if a1 and not a2:
            return {1: 1.0, 2: -1.0}
        if a2 and not a1:
            return {1: -1.0, 2: 1.0}
        return {1: 0.0, 2: 0.0}


def main():
    configs = [(f"army cap={mp}", gm.make_material(max_plies=mp), BaseArmyCap(mp), "material")
               for mp in (30, 40, 50, 60, 80, 100, 140)]
    configs += [(f"cf {rule}", CFRule(rule), base_cf, "rule")
                for rule in ("topcenter", "vthree", "square")]

    Path("results").mkdir(exist_ok=True)
    header = (f"{'config':14s} {'rarity':>8s} {'fair':>6s} {'blind':>6s} {'cost':>6s} "
              f"{'dgr@20':>7s} {'dgr@40':>7s} {'dgr@80':>7s}")
    print(f"[0/{len(configs)}] starting", flush=True)
    print(header, flush=True)
    rows = []
    for i, (name, truth, blind, reason) in enumerate(configs, 1):
        r = row(name, truth, blind, reason)
        rows.append(r)
        d = r["danger"]
        # progress: print + persist each row as it completes (crash-resilient)
        print(f"{r['config']:14s} {r['rarity']:8.3f} {r['fair_winrate']:6.3f} "
              f"{r['blind_winrate']:6.3f} {r['play_cost']:6.3f} "
              f"{d['20']:7.3f} {d['40']:7.3f} {d['80']:7.3f}   [{i}/{len(configs)}]", flush=True)
        Path("results/law_sweep.json").write_text(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()

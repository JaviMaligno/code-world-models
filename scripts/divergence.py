"""Random-vs-MCTS reach divergence: rank games by how far competent play's
game-length distribution departs from random play's.

This is the game-selection measurement behind the choice of army5x5a as the
rare-rule instrument (see the "rarity <-> consequence" entry in
docs/EXPERIMENTS.md): a verified-vs-correct gap needs a game where the
random-play and competent-play state distributions genuinely diverge, and
game length (plies to termination) is the cheapest observable proxy --- a
planner that maneuvers into deep positions produces much longer games than
random play, concentrating reach on states the random gate never samples.

For each game we play n self-play games under (a) the uniform-random policy
and (b) UCT-MCTS on the true game, and report median plies, the divergence
(competent - random medians), and the fraction of games hitting army5x5a's
100-ply cap. (The original ad-hoc run of this measurement was not persisted;
this script recreates it --- results land in results/divergence.json.)

Run: PYTHONPATH=src python3.12 scripts/divergence.py [--games N] [--sims S]
"""
import argparse
import json
import random
import statistics
from pathlib import Path

from cwm.groundtruth import gen_chess, gen_tictactoe, trike, connect_four
from cwm.mcts import mcts_policy

GAMES = [("army5x5a", gen_chess), ("gen_tictactoe", gen_tictactoe),
         ("trike", trike), ("connect_four", connect_four)]

_ap = argparse.ArgumentParser(description=__doc__)
_ap.add_argument("--games", type=int, default=30, help="self-play games per arm")
_ap.add_argument("--sims", type=int, default=300, help="MCTS simulations per move")
_args = _ap.parse_args()


def play_lengths(model, policy, n_games, seed):
    lengths = []
    for i in range(n_games):
        s = model.initial_state()
        plies = 0
        while not model.is_terminal(s):
            a = policy(s, seed + i * 10_000 + plies)
            s = model.apply_action(s, a)
            plies += 1
        lengths.append(plies)
    return lengths


def main():
    out = {"games_per_arm": _args.games, "sims": _args.sims, "results": []}
    for name, model in GAMES:
        rng = random.Random(0)
        rand = play_lengths(
            model, lambda s, sd: rng.choice(model.legal_actions(s)),
            _args.games, seed=0)
        comp = play_lengths(
            model, lambda s, sd: mcts_policy(model, s,
                                             n_simulations=_args.sims, seed=sd),
            _args.games, seed=1)
        med_r, med_c = statistics.median(rand), statistics.median(comp)
        cap_frac = (sum(1 for x in comp if x >= 100) / len(comp)
                    if name == "army5x5a" else None)
        cap_str = f"  P(competent hits 100-ply cap)={cap_frac:.2f}" if cap_frac is not None else ""
        print(f"{name:15s} median plies: random={med_r:.0f} competent={med_c:.0f} "
              f"divergence={med_c - med_r:+.0f}{cap_str}", flush=True)
        out["results"].append({"game": name, "median_random": med_r,
                               "median_competent": med_c,
                               "divergence": med_c - med_r,
                               "competent_cap_fraction": cap_frac,
                               "random_lengths": rand, "competent_lengths": comp})
    Path("results").mkdir(exist_ok=True)
    Path("results/divergence.json").write_text(json.dumps(out, indent=2))
    print("wrote results/divergence.json", flush=True)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()

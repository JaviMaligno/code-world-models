"""Why is play_cost ~constant in the rarity knob? Because competent play reaches the
cap region with ~constant high probability regardless of the knob, while random play
rarely does. Measure P(reach ply cap) for competent (MCTS) vs random across cap
lengths. CPU.

Run: PYTHONPATH=src python scripts/play_cost_reach.py
"""
import argparse, random
from cwm.groundtruth.gen_chess_material import make_material, N
from cwm.mcts import mcts_policy

# NOTE: the published Figure 3 uses --games 120; defaults (40 games) reproduce
# the retired small-sample stage only.
# is the n the paper flags as "small-sample"; --games raises it (CPU-only but
# long) -- see the limitations roadmap in docs/EXPERIMENTS.md.
_ap = argparse.ArgumentParser(description=__doc__)
_ap.add_argument("--sims", type=int, default=300)
_ap.add_argument("--games", type=int, default=40)
_args = _ap.parse_args()
SIMS = _args.sims; GAMES = _args.games

def frac_reach_cap(game, competent, seed):
    rng = random.Random(seed); reached = 0
    for i in range(GAMES):
        s = game.initial_state()
        while not game.is_terminal(s):
            if competent:
                a = mcts_policy(game, s, n_simulations=SIMS, seed=seed + i*1000 + s["board"][N])
            else:
                a = rng.choice(game.legal_actions(s))
            s = game.apply_action(s, a)
        if s["board"][N] >= game.max_plies:   # reached the cap region
            reached += 1
    return reached / GAMES

for cap in (30, 60, 100):
    g = make_material(max_plies=cap, lead=1)
    comp = frac_reach_cap(g, True, seed=0)
    rand = frac_reach_cap(g, False, seed=1)
    print(f"cap={cap}: P(reach cap) competent={comp:.3f}  random={rand:.3f}", flush=True)
print("DONE", flush=True)

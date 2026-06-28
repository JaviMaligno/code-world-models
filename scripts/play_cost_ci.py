"""Headline play-cost with Wilson confidence intervals, at higher n for separation.

Pools games across seeds; reports Wilson CI per arm (draws as 0.5) and the
difference. Azure-free (CPU MCTS on the hand-written games).

Run: PYTHONPATH=src python scripts/play_cost_ci.py
"""
from cwm.run_gap import _play_performance
from cwm.groundtruth import gen_chess_material as mat, gen_chess as base
from cwm.law import wilson_ci

SIMS = 600
N = 120
SEEDS = [0, 1, 2, 3, 4]   # 600 games per arm

def pooled(label, cwm_model):
    W = D = L = 0
    for seed in SEEDS:
        r = _play_performance(mat, cwm_model, sims=SIMS, n_games=N, seed=seed)
        W += r["cwm_wins"]; D += r["draws"]; L += r["truth_wins"]
        print(f"  {label:38s} seed={seed}: {r['cwm_wins']}W/{r['draws']}D/{r['truth_wins']}L "
              f"winrate={r['cwm_winrate']:.3f}", flush=True)
    n = W + D + L
    point, lo, hi = wilson_ci(W + 0.5 * D, n)
    print(f"  -> {label}: n={n} W/D/L={W}/{D}/{L} winrate={point:.3f} "
          f"Wilson95 [{lo:.3f},{hi:.3f}]\n", flush=True)
    return point, lo, hi, n

print(f"SIMS={SIMS} games/arm={N*len(SEEDS)}", flush=True)
fair = pooled("truth-vs-truth (fair baseline)", mat)
blind = pooled("rule-blind vs truth (play cost)", base)
print(f"SEPARATION: fair lo={fair[1]:.3f}  vs  rule-blind hi={blind[2]:.3f}  "
      f"-> {'SEPARATED' if blind[2] < fair[1] else 'OVERLAP'}", flush=True)
print(f"play_cost = {fair[0]-blind[0]:.3f}", flush=True)
print("DONE", flush=True)

"""Headline play-cost with Wilson confidence intervals, at higher n for separation.

Reports, for each arm: per-seed winrate, the pooled Wilson CI (draws as 0.5),
AND a seed-clustered analysis of the play-cost difference --- a paired-by-seed
t-interval on (fair_s - blind_s) that treats the SEED, not the individual game,
as the independent unit, addressing the per-game-independence objection. Both
arms share the same start-side balancing (alternated every game) so the paired
difference cancels start-order effects. Azure-free (CPU MCTS on hand-written
games). Writes results/play_cost_ci.json.

Run: PYTHONPATH=src python scripts/play_cost_ci.py
"""
import json, math
from pathlib import Path
from cwm.run_gap import _play_performance
from cwm.groundtruth import gen_chess_material as mat, gen_chess as base
from cwm.law import wilson_ci

SIMS = 600
N = 120
SEEDS = [0, 1, 2, 3, 4]   # 600 games per arm

# two-sided t critical values (df = n_seeds - 1) for 95%
T_CRIT = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447}

def arm(label, cwm_model):
    W = D = L = 0
    per_seed = []
    for seed in SEEDS:
        r = _play_performance(mat, cwm_model, sims=SIMS, n_games=N, seed=seed)
        W += r["cwm_wins"]; D += r["draws"]; L += r["truth_wins"]
        per_seed.append(r["cwm_winrate"])
        print(f"  {label:38s} seed={seed}: {r['cwm_wins']}W/{r['draws']}D/{r['truth_wins']}L "
              f"winrate={r['cwm_winrate']:.3f}", flush=True)
    n = W + D + L
    point, lo, hi = wilson_ci(W + 0.5 * D, n)
    print(f"  -> {label}: n={n} W/D/L={W}/{D}/{L} winrate={point:.3f} "
          f"Wilson95 [{lo:.3f},{hi:.3f}]\n", flush=True)
    return {"label": label, "n": n, "W": W, "D": D, "L": L,
            "winrate": point, "wilson95": [lo, hi], "per_seed": per_seed}

print(f"SIMS={SIMS} games/arm={N*len(SEEDS)} seeds={SEEDS}", flush=True)
fair = arm("truth-vs-truth (fair baseline)", mat)
blind = arm("rule-blind vs truth (play cost)", base)

sep = blind["wilson95"][1] < fair["wilson95"][0]
print(f"POOLED separation: fair lo={fair['wilson95'][0]:.3f} vs blind hi={blind['wilson95'][1]:.3f} "
      f"-> {'SEPARATED' if sep else 'OVERLAP'}", flush=True)

# Seed-clustered (paired-by-seed) play-cost: seed is the independent unit.
diffs = [f - b for f, b in zip(fair["per_seed"], blind["per_seed"])]
k = len(diffs)
mean_d = sum(diffs) / k
sd = math.sqrt(sum((d - mean_d) ** 2 for d in diffs) / (k - 1)) if k > 1 else 0.0
se = sd / math.sqrt(k)
tcrit = T_CRIT.get(k, 2.776)
clo, chi = mean_d - tcrit * se, mean_d + tcrit * se
print(f"play_cost (pooled point) = {fair['winrate'] - blind['winrate']:.3f}", flush=True)
print(f"play_cost (seed-clustered, paired-by-seed): mean={mean_d:.3f} sd={sd:.3f} "
      f"se={se:.3f} t95[df={k-1}] -> [{clo:.3f}, {chi:.3f}]  "
      f"{'EXCLUDES 0' if clo > 0 else 'includes 0'}", flush=True)

out = {"sims": SIMS, "n_per_seed": N, "seeds": SEEDS,
       "fair": fair, "blind": blind,
       "pooled_separated": sep,
       "play_cost_pooled": fair["winrate"] - blind["winrate"],
       "play_cost_by_seed": {"diffs": diffs, "mean": mean_d, "sd": sd, "se": se,
                             "t95": [clo, chi], "excludes_zero": clo > 0}}
Path("results").mkdir(exist_ok=True)
Path("results/play_cost_ci.json").write_text(json.dumps(out, indent=2))
print("DONE", flush=True)

"""Rule-blind arm, 3 seeds (n=360), Wilson CI; fair arm pooled from prior seeds."""
from cwm.run_gap import _play_performance
from cwm.groundtruth import gen_chess_material as mat, gen_chess as base
from cwm.law import wilson_ci

SIMS = 600; N = 120; SEEDS = [0, 1, 2]
W=D=L=0
for seed in SEEDS:
    r = _play_performance(mat, base, sims=SIMS, n_games=N, seed=seed)
    W+=r["cwm_wins"]; D+=r["draws"]; L+=r["truth_wins"]
    print(f"  rule-blind seed={seed}: {r['cwm_wins']}W/{r['draws']}D/{r['truth_wins']}L winrate={r['cwm_winrate']:.3f}", flush=True)
n=W+D+L; p,lo,hi = wilson_ci(W+0.5*D, n)
print(f"  -> rule-blind: n={n} W/D/L={W}/{D}/{L} winrate={p:.3f} Wilson95 [{lo:.3f},{hi:.3f}]", flush=True)
# fair arm pooled from already-run seeds 0,1,2: 36/43/41, 41/45/34, 32/49/39
fW,fD,fL = 36+41+32, 43+45+49, 41+34+39
fn=fW+fD+fL; fp,flo,fhi = wilson_ci(fW+0.5*fD, fn)
print(f"  -> fair (pooled seeds 0-2): n={fn} W/D/L={fW}/{fD}/{fL} winrate={fp:.3f} Wilson95 [{flo:.3f},{fhi:.3f}]", flush=True)
print(f"SEPARATION: fair_lo={flo:.3f} vs blind_hi={hi:.3f} -> {'SEPARATED' if hi<flo else 'OVERLAP'}", flush=True)
print(f"play_cost = {fp-p:.3f}", flush=True)
print("DONE", flush=True)

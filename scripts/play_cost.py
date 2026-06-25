"""Clean, Azure-free measurement of the rare rule's PLAY cost.

The rule-omitting (incomplete) synthesized CWM is, for play purposes, equivalent
to hand-written base army5x5a: it differs from the true (material) game only at
the rare cap+unequal-material states (gap_cwm ~ 0). So base-vs-truth measures the
rule's play cost exactly, at any scale, with no LLM. truth-vs-truth is the
fairness baseline (expect ~0.5 at high n).

Run: PYTHONPATH=src python scripts/play_cost.py
"""
from cwm.run_gap import _play_performance
from cwm.groundtruth import gen_chess_material as mat, gen_chess as base

SIMS = 600
N = 120
SEEDS = [0, 1]

for label, cwm_model in [("truth-vs-truth (fairness baseline)", mat),
                         ("base-vs-truth (rule-blind play cost)", base)]:
    rates = []
    for seed in SEEDS:
        r = _play_performance(mat, cwm_model, sims=SIMS, n_games=N, seed=seed)
        rates.append(r["cwm_winrate"])
        print(f"  {label:42s} seed={seed}: winrate={r['cwm_winrate']:.3f} "
              f"({r['cwm_wins']}W/{r['draws']}D/{r['truth_wins']}L, illegal={r['cwm_illegal']})",
              flush=True)
    print(f"  -> {label}: mean winrate = {sum(rates)/len(rates):.3f}\n", flush=True)

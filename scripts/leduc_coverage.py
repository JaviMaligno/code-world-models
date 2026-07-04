"""Claim A for imperfect information (Leduc). CPU only.

(1) Coverage gap: competent-play info-sets not covered by N random-play trajectories.
(2) The WrongInference instrument passes the random-sampled inference gate yet
    loses at play vs the truth (Wilson-CI-separated).
(3) Danger vs N: play_cost x P(tail info-set absent from N random samples).

Run: PYTHONPATH=src python scripts/leduc_coverage.py
"""
import inspect
import json
import random
from pathlib import Path

from cwm.groundtruth import leduc_poker as L
from cwm.leduc_instrument import (WrongInference, _is_tail, infoset_key,
                                  random_infoset_coverage, competent_infosets)
from cwm.gap import inference_accuracy
from cwm.determinized import imperfect_arena

SIMS = 200
N_GAMES = 400
SEEDS = [0, 1, 2]


def main():
    Path("results").mkdir(exist_ok=True)
    out = {}

    # (1) coverage gap
    comp = competent_infosets(L, n_games=80, sims=SIMS, seed=0)
    rand = random_infoset_coverage(L, n_games=8000, seed=0)
    comp_tail = {k for k in comp if _is_tail(list(k))}
    uncovered_tail = {k for k in comp_tail if k not in rand}
    out["coverage"] = {"competent_infosets": len(comp), "competent_tail": len(comp_tail),
                       "random_covered": len(rand),
                       "tail_uncovered_by_random": len(uncovered_tail)}
    print(f"coverage: competent={len(comp)} tail={len(comp_tail)} "
          f"random_covered={len(rand)} tail_uncovered={len(uncovered_tail)}", flush=True)

    # (2) instrument: gate (random-sampled states) vs play
    w = WrongInference()
    rng = random.Random(1)
    deals = L.initial_states()
    sample = []
    for _ in range(400):                       # random-play states = what the gate sees
        d = deals[rng.randrange(len(deals))]
        s = {"board": list(d["board"]), "current_player": d["current_player"]}
        while not L.is_terminal(s):
            sample.append({"board": list(s["board"]), "current_player": s["current_player"]})
            s = L.apply_action(s, rng.choice(L.legal_actions(s)))
    gate = inference_accuracy(inspect.getsource(L), sample, L)  # truth passes (sanity)
    # the instrument is a live object, not code; check its inference on the sample directly
    inst_mismatch = sum(1 for st in sample
                        for p in (1, 2)
                        if w.infer_states(L.observation(st, p), p) != L.infer_states(L.observation(st, p), p))
    out["instrument_gate"] = {"truth_inference_rate": gate["inference_rate"],
                              "instrument_mismatches_on_random_sample": inst_mismatch,
                              "n_checks": len(sample) * 2}
    print(f"instrument gate: truth_inference_rate={gate['inference_rate']:.3f} "
          f"instrument mismatches on random sample={inst_mismatch}/{len(sample)*2}", flush=True)

    fair = imperfect_arena(L, L, L, simulations=SIMS, n_games=N_GAMES, seeds=SEEDS,
                           n_determinizations=8)
    play = imperfect_arena(L, w, L, simulations=SIMS, n_games=N_GAMES, seeds=SEEDS,
                           n_determinizations=8)
    out["play"] = {"fair_winrate": fair["a_winrate"], "fair_ci": [fair["lo"], fair["hi"]],
                   "instrument_winrate": play["a_winrate"], "instrument_ci": [play["lo"], play["hi"]],
                   "instrument_net": play["a_net"], "n": play["n"]}
    print(f"play: fair={fair['a_winrate']:.3f}[{fair['lo']:.3f},{fair['hi']:.3f}] "
          f"instrument={play['a_winrate']:.3f}[{play['lo']:.3f},{play['hi']:.3f}] "
          f"net={play['a_net']:.1f}", flush=True)

    # (3) danger vs N: play_cost x P(tail info-set absent from N random samples)
    play_cost = max(0.0, fair["a_winrate"] - play["a_winrate"])
    p_tail = (len(comp_tail) and len(uncovered_tail) / len(comp_tail)) or 0.0
    out["danger"] = {"play_cost": play_cost,
                     "frac_tail_uncovered_at_8000": p_tail}
    print(f"danger: play_cost={play_cost:.3f} tail_uncovered_frac={p_tail:.3f}", flush=True)

    Path("results/leduc_coverage.json").write_text(json.dumps(out, indent=2))
    print("DONE", flush=True)


if __name__ == "__main__":
    main()

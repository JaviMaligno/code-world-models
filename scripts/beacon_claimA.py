"""Claim A for imperfect information (Beacon), CPU only. The provable witness:
a CWM whose inference is wrong only on the final-round region D passes a random
inference gate yet loses at play.

(1) Gate: instrument inference matches truth on random-play states (D unreached).
(2) Play: instrument loses vs the fair truth-vs-truth baseline, CI-separated.
(3) Danger vs T: measured gate-miss rate vs the exact (1-(1/2)^{2T})^N.

Run: PYTHONPATH=src python scripts/beacon_claimA.py
"""
import json
import random
from pathlib import Path

from cwm.groundtruth import beacon as B
from cwm.beacon_instrument import BeaconWrongInference, random_reach_final_rate
from cwm.determinized import imperfect_arena
from cwm.law import danger

T = 8
SIMS = 100
N_GAMES = 400
SEEDS = [0, 1, 2]
GATE_GAMES = 2000


def gate_mismatches_on_random(truth, inst, n_games, seed):
    """(mismatches, checks): count of random-play (state,player) inferences where
    instrument != truth, and the total number checked."""
    rng = random.Random(seed)
    deals = truth.initial_states()
    checks = mismatches = 0
    for _ in range(n_games):
        d = deals[rng.randrange(len(deals))]
        s = {"board": list(d["board"]), "current_player": d["current_player"]}
        while not truth.is_terminal(s):
            for p in (1, 2):
                obs = truth.observation(s, p)
                checks += 1
                if inst.infer_states(obs, p) != truth.infer_states(obs, p):
                    mismatches += 1
            s = truth.apply_action(s, rng.choice(truth.legal_actions(s)))
    return mismatches, checks


def main():
    Path("results").mkdir(exist_ok=True)
    truth = B.make_beacon(T)
    inst = BeaconWrongInference(T)
    out = {"T": T}

    # (1) gate on random-play states
    mm, ch = gate_mismatches_on_random(truth, inst, GATE_GAMES, seed=0)
    reach = random_reach_final_rate(truth, GATE_GAMES, seed=0)
    out["gate"] = {"mismatches": mm, "checks": ch, "random_reach_final_rate": reach}
    print(f"gate: instrument mismatches on random sample = {mm}/{ch}; "
          f"random reaches final at rate {reach:.5f}", flush=True)

    # (2) play vs fair baseline
    fair = imperfect_arena(truth, truth, truth, simulations=SIMS, n_games=N_GAMES,
                           seeds=SEEDS, n_determinizations=2)
    play = imperfect_arena(truth, inst, truth, simulations=SIMS, n_games=N_GAMES,
                           seeds=SEEDS, n_determinizations=2)
    out["play"] = {"fair_winrate": fair["a_winrate"], "fair_ci": [fair["lo"], fair["hi"]],
                   "instrument_winrate": play["a_winrate"],
                   "instrument_ci": [play["lo"], play["hi"]],
                   "instrument_net": play["a_net"], "n": play["n"]}
    print(f"play: fair={fair['a_winrate']:.3f}[{fair['lo']:.3f},{fair['hi']:.3f}] "
          f"instrument={play['a_winrate']:.3f}[{play['lo']:.3f},{play['hi']:.3f}] "
          f"net={play['a_net']:.1f}", flush=True)

    # (3) danger vs T: exact gate-miss factor against measured reach
    cost = max(0.0, fair["a_winrate"] - play["a_winrate"])
    rows = []
    for t in (4, 6, 8, 10):
        eps = (0.5) ** (2 * t)
        miss = (1 - eps) ** GATE_GAMES
        rows.append({"T": t, "eps": eps, "gate_miss_prob": miss,
                     "danger": danger(cost, eps, GATE_GAMES)})
        print(f"danger T={t}: eps={eps:.2e} gate_miss={miss:.3f} "
              f"danger={danger(cost, eps, GATE_GAMES):.4f}", flush=True)
    out["danger_curve"] = {"play_cost": cost, "rows": rows}

    Path("results/beacon_claimA.json").write_text(json.dumps(out, indent=2))
    print("DONE", flush=True)


if __name__ == "__main__":
    main()

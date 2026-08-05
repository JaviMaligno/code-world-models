"""Does changing the mode's post-state make the region's interior witnessable?

Proposition prop:entryclass says a freeze-at-previous-position mode keeps every visited
state outside the region, so a sample witnesses only entries and an ENTRY rule is
indistinguishable from the true MEMBERSHIP rule on any sample. This script measures, for
each `mode_effect` variant, the two things that decide whether a synthesis campaign on it
would answer anything:

  ADMISSIBILITY OF THE INTERVENTION
    * are there sampled transitions whose previous position is IN the region? (the
      premise's negation)
    * do the membership rule and the entry rule DISAGREE on some sampled transition?
      (the equivalence class collapsing -- what actually matters, since the premise could
      break without the evidence separating the two rules)

  ADMISSIBILITY OF THE INSTRUMENT
    * is the rarity still in the band the disc campaign used?
    * is the exploitation geometry intact -- blind planner pinned, play_cost near 1?
      A variant that breaks the trap has nothing to omit and its repair rate is
      uninterpretable, which is the failure the slab calibration caught late.

Run: PYTHONPATH=src python scripts/calibrate_mode_effect.py [--rollouts N] [--episodes N]
Writes: results/mode_effect_calibration.json
"""
import argparse
import json
import math
import pathlib
import random
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.continuous.envs import PatchField2D, blind_of_modes  # noqa: E402
from cwm.continuous import harness                            # noqa: E402
from cwm.continuous.contract import collect_transitions       # noqa: E402

RES = _REPO / "results"
VARIANTS = ("freeze", "landing", "clamp")


def wilson(k, n, z=1.959963984540054):
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def landing_of(env, s, a):
    return env._integrate(s, a)[:2]


def measure(env, rollouts, seed):
    """Rarity, and whether the interior is witnessed, over independent rollouts."""
    n_hit = n_steps = n_prev_inside = n_strictly_inside = 0
    n_disagree = 0
    for r in range(rollouts):
        rng = random.Random(seed + r)
        s = env.initial_state(rng)
        hit = False
        for _ in range(env.h_episode):
            a = rng.uniform(-env.a_max, env.a_max)
            prev_in = (env._inside(s[0], s[1], env.p1)
                       or env._inside(s[0], s[1], env.p2))
            # strictly inside: in the region and not on its boundary
            if prev_in:
                n_prev_inside += 1
                d1 = math.hypot(s[0] - env.p1[0], s[1] - env.p1[1]) if env.p1 else 9e9
                d2 = math.hypot(s[0] - env.p2[0], s[1] - env.p2[1]) if env.p2 else 9e9
                if min(d1, d2) < env.R - 1e-9:
                    n_strictly_inside += 1
            lx, ly = landing_of(env, s, a)
            memb = env._inside(lx, ly, env.p1) or env._inside(lx, ly, env.p2)
            entry = memb and not prev_in          # the rival rule
            if memb != entry:
                n_disagree += 1
            s, _, contact = env.step(s, a)
            n_steps += 1
            hit = hit or contact
        n_hit += hit
    lo, hi = wilson(n_hit, rollouts)
    return {"rollouts": rollouts, "n_steps": n_steps,
            "rarity": n_hit / rollouts, "rarity_ci": [lo, hi],
            "steps_from_inside_the_region": n_prev_inside,
            "steps_from_STRICTLY_inside": n_strictly_inside,
            "transitions_separating_membership_from_entry": n_disagree,
            "premise_broken": n_prev_inside > 0,
            "equivalence_class_collapsed": n_disagree > 0}


def play(env, episodes):
    blind = blind_of_modes(env, ("p1", "p2"))
    jt = jb = jr = 0.0
    contact = 0
    for i in range(episodes):
        sd = 900_000 + 1000 * i
        et = harness.run_episode(env, env, "mpc", sd)
        eb = harness.run_episode(env, blind, "mpc", sd)
        jt += et.ret
        jb += eb.ret
        contact += bool(eb.contact)
        jr += harness.run_episode(env, policy="random", seed=sd).ret
    jt, jb, jr = jt / episodes, jb / episodes, jr / episodes
    return {"episodes": episodes, "j_truth": jt, "j_blind": jb, "j_random": jr,
            "play_cost": (jt - jb) / (jt - jr) if jt != jr else None,
            "blind_contact_rate": contact / episodes}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rollouts", type=int, default=4000)
    ap.add_argument("--episodes", type=int, default=20)
    ap.add_argument("--k1", type=float, default=3.0)
    ap.add_argument("--k2", type=float, default=7.0)
    ap.add_argument("--seed", type=int, default=555_000)
    args = ap.parse_args()

    out = {"script": "calibrate_mode_effect.py", "params": vars(args),
           "question": "does the mode's post-state make the region's interior "
                       "witnessable, and does the instrument still carry the trap?",
           "variants": {}}
    for me in VARIANTS:
        env = PatchField2D(p1=(args.k1, 0.0), p2=(args.k2, 0.0), mode_effect=me)
        rec = {"mode_effect": me}
        rec.update(measure(env, args.rollouts, args.seed))
        rec.update(play(env, args.episodes))
        # what a synthesis campaign's own gate sample would contain
        tr = collect_transitions(env, 40, seed=10_000)
        rec["gate_sample_contacts"] = sum(1 for t in tr if t["contact"])
        out["variants"][me] = rec
        print(f"{me:8} rarity {rec['rarity']:.4f} {[round(x,4) for x in rec['rarity_ci']]}"
              f" | steps from inside {rec['steps_from_inside_the_region']:5}"
              f" (strictly {rec['steps_from_STRICTLY_inside']:5})"
              f" | separating transitions {rec['transitions_separating_membership_from_entry']:5}"
              f" | play_cost {rec['play_cost']:.4f} contact {rec['blind_contact_rate']:.2f}")

    base = out["variants"]["freeze"]
    for me in ("landing", "clamp"):
        v = out["variants"][me]
        v["admissible"] = {
            "premise_broken": v["premise_broken"],
            "equivalence_collapsed": v["equivalence_class_collapsed"],
            "rarity_within_2x_of_freeze":
                0.5 * base["rarity"] <= v["rarity"] <= 2.0 * base["rarity"],
            "trap_preserved": (v["play_cost"] is not None and v["play_cost"] > 0.8
                               and v["blind_contact_rate"] >= 0.9),
        }
        v["admissible"]["all"] = all(v["admissible"].values())
    (RES / "mode_effect_calibration.json").write_text(json.dumps(out, indent=2))
    print()
    for me in ("landing", "clamp"):
        a = out["variants"][me]["admissible"]
        print(f"{me:8} admissible: {a['all']}   {a}")
    print(f"\nwrote {RES / 'mode_effect_calibration.json'}")


if __name__ == "__main__":
    main()

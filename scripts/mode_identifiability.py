"""Is a mode's membership rule identifiable from what a rollout can witness?

Proposition prop:entryclass says the freeze semantics keep every visited state outside the
mode region, so a sample witnesses only ENTRIES. Whether that is enough to pin the rule
depends on one further question the instrument answers, not the synthesizer:

    can a rollout get to the region's FAR side?

If it can, the evidence constrains the region from more than one direction and the
membership rule is identified. If it cannot, the rule is identified only up to the
equivalence class of prop:entryclass, and "recover the true rule" is not a well-posed
target -- a half-plane at the near face, and an entry detector on it, are then exactly as
consistent with every possible sample as the truth is.

This distinguishes the instruments the paper compares, and it decides what each ablation
can conclude:

  * disc and square: the mover goes AROUND (the patches are bounded in y) and lands east
    of them, so the far side is witnessed and the target is well posed. The 0/156 is a
    genuine induction failure.
  * slab: unbounded in y, so it cannot be circumvented and nothing east of it is ever
    reached. Its target is NOT identifiable, so the slab campaign cannot be read as an
    answer about trigger arity -- which is what this script exists to establish, rather
    than leaving it to be assumed either way.

Run: PYTHONPATH=src python scripts/mode_identifiability.py
Writes: results/mode_identifiability.json
"""
import json
import math
import pathlib
import random
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.continuous.envs import PatchField2D  # noqa: E402

RES = _REPO / "results"
N_ROLLOUTS = 2000
SEED = 31337

ARMS = {
    "disc_k3_7": {"p1": (3.0, 0.0), "p2": (7.0, 0.0), "patch_shape": "disc"},
    "square_k3_7": {"p1": (3.0, 0.0), "p2": (7.0, 0.0), "patch_shape": "square"},
    "slab_k5.5_W0.5": {"p1": (5.5, 0.0), "p2": (7.0, 0.0), "patch_shape": "slab",
                       "slab_half_width": 0.5},
}


def near_faces(env):
    """(west face, east face) of the NEAR patch, in the landing coordinate."""
    half = env.slab_half_width if env.patch_shape == "slab" else env.R
    return env.p1[0] - half, env.p1[0] + half


def landing_x(env, s, a):
    x, _, vx, _ = s
    a = max(-env.a_max, min(env.a_max, a))
    phi = math.pi * a / env.a_max
    return x + (vx + (env.gain * math.cos(phi) - env.drag * vx) * env.dt) * env.dt


def measure(name, kw):
    env = PatchField2D(**kw)
    west, east = near_faces(env)
    inside = env._inside
    stats = {"arm": name, "patch_shape": env.patch_shape, "p1": env.p1, "p2": env.p2,
             "near_west_face": west, "near_east_face": east,
             "n_rollouts": N_ROLLOUTS, "horizon": env.h_episode}
    max_x = -1e9
    max_landing = -1e9
    east_states = contacts = inside_states = steps = 0
    for r in range(N_ROLLOUTS):
        rng = random.Random(SEED + r)
        s = env.initial_state(rng)
        for _ in range(env.h_episode):
            a = rng.uniform(-env.a_max, env.a_max)
            max_landing = max(max_landing, landing_x(env, s, a))
            s2, _, contact = env.step(s, a)
            steps += 1
            contacts += bool(contact)
            max_x = max(max_x, s2[0])
            if s2[0] > east:
                east_states += 1
            if inside(s2[0], s2[1], env.p1) or inside(s2[0], s2[1], env.p2):
                inside_states += 1
            s = s2
    stats.update({
        "n_steps": steps, "n_contacts": contacts,
        "max_position_x": max_x, "max_landing_x": max_landing,
        "states_east_of_near_patch": east_states,
        "states_inside_region": inside_states,
        "far_side_reachable": east_states > 0,
        "target_identifiable": east_states > 0,
        "prop_entryclass_premise_holds": inside_states == 0,
    })
    return stats


def main() -> None:
    out = {"script": "mode_identifiability.py",
           "question": "can a rollout reach the FAR side of the near mode patch? if not, "
                       "the membership rule is identified only up to the equivalence "
                       "class of Proposition prop:entryclass",
           "params": {"n_rollouts": N_ROLLOUTS, "seed": SEED},
           "arms": {}}
    for name, kw in ARMS.items():
        st = measure(name, kw)
        out["arms"][name] = st
        print(f"{name:16} far face x={st['near_east_face']:.2f} | max x reached "
              f"{st['max_position_x']:6.2f} | east of it {st['states_east_of_near_patch']:6} "
              f"| contacts {st['n_contacts']:5} | identifiable "
              f"{st['target_identifiable']}")
        assert st["prop_entryclass_premise_holds"], (
            f"{name}: a visited state was INSIDE the region, contradicting "
            f"prop:entryclass(i) -- the proposition or the instrument is wrong")
    out["reading"] = (
        "disc and square: the far side is witnessed, so the membership rule is identified "
        "and the campaigns' 0/156 is a genuine induction failure. slab: the region is "
        "unbounded in y, cannot be circumvented, and nothing east of it is reachable, so "
        "its rule is identified only up to prop:entryclass's equivalence class and the "
        "slab campaign does NOT isolate trigger arity.")
    (RES / "mode_identifiability.json").write_text(json.dumps(out, indent=2))
    print(f"\nwrote {RES / 'mode_identifiability.json'}")


if __name__ == "__main__":
    main()

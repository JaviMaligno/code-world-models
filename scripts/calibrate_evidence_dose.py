"""Does a wider start arc actually widen the evidence, and does the instrument survive it?

The evidence-dose experiment asks whether the synthesizer's failure to induce the region's
FORM yields to wider angular coverage of the contacts. For that to be answerable, the
intervention has to do two things and avoid a third:

  it must RAISE the coverage         -- measured here as the arc the contact landings
                                        actually cover (360 degrees minus the largest
                                        angular gap), against the default sample's median
                                        of about 111 degrees;
  it must KEEP the instrument         -- the mode must still be rare enough to be worth
                                        omitting, and the blind planner must still be
                                        exploited, or there is no danger left to study;
  it must NOT confound coverage with quantity -- so this script also reports the rollout
                                        count at which each arc's contact count matches the
                                        default's, which is what the campaign then uses.

Run: PYTHONPATH=src python scripts/calibrate_evidence_dose.py
Writes: results/evidence_dose_calibration.json
"""
import json
import math
import pathlib
import sys

import numpy as np

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.continuous.envs import PatchField2D, blind_of_modes   # noqa: E402
from cwm.continuous import harness                             # noqa: E402
from cwm.continuous.contract import collect_transitions        # noqa: E402

RES = _REPO / "results"
ARCS = [None, 120.0, 240.0, 360.0]
N_CANDIDATES = [10, 15, 20, 25, 30, 40]
SEEDS = [10_000 * (i + 1) for i in range(20)]


def arc_covered(pts, c):
    if len(pts) < 2:
        return 0.0
    a = np.sort(np.degrees(np.arctan2([p[1] - c[1] for p in pts],
                                      [p[0] - c[0] for p in pts])) % 360.0)
    gaps = np.diff(np.r_[a, a[0] + 360.0])
    return float(360.0 - gaps.max())


def sample_stats(env, n_rollouts):
    """Contacts and their angular coverage, over the campaign's own seed blocks."""
    n_contacts, arcs, n_fired = [], [], 0
    for seed in SEEDS:
        tr = collect_transitions(env, n_rollouts, seed=seed)
        land = []
        for t in tr:
            if not t["contact"]:
                continue
            lx, ly = env._integrate(tuple(t["state"]), t["action"])[:2]
            if env._inside(lx, ly, env.p1):
                land.append((lx, ly))
        n_contacts.append(len(land))
        if land:
            arcs.append(arc_covered(land, env.p1))
        n_fired += bool(any(t["contact"] for t in tr))
    return {"n_rollouts": n_rollouts,
            "median_contacts": float(np.median(n_contacts)),
            "min_contacts": int(min(n_contacts)),
            "median_arc_deg": float(np.median(arcs)) if arcs else 0.0,
            "min_arc_deg": float(min(arcs)) if arcs else 0.0,
            "blocks_with_a_contact": n_fired, "n_blocks": len(SEEDS)}


def play(env, episodes=12):
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
    return {"j_truth": jt, "j_blind": jb, "j_random": jr,
            "play_cost": (jt - jb) / (jt - jr) if jt != jr else None,
            "blind_contact_rate": contact / episodes}


def main() -> None:
    base_env = PatchField2D(p1=(3.0, 0.0), p2=(7.0, 0.0))
    base = sample_stats(base_env, 40)
    out = {"script": "calibrate_evidence_dose.py",
           "default_sample": base, "default_play": play(base_env),
           "target_median_contacts": base["median_contacts"], "arms": {}}
    print(f"default (box start, N=40): median contacts {base['median_contacts']:.0f}, "
          f"median arc {base['median_arc_deg']:.1f} deg, "
          f"{base['blocks_with_a_contact']}/{base['n_blocks']} blocks fire")
    print(f"  play_cost {out['default_play']['play_cost']:.4f} "
          f"contact {out['default_play']['blind_contact_rate']:.2f}\n")

    for arc in ARCS:
        if arc is None:
            continue
        env = PatchField2D(p1=(3.0, 0.0), p2=(7.0, 0.0), start_arc_deg=arc)
        # pick the rollout count whose median contact count is closest to the default's,
        # so the dose varies COVERAGE and not the amount of evidence
        cands = [sample_stats(env, n) for n in N_CANDIDATES]
        best = min(cands, key=lambda c: abs(c["median_contacts"]
                                            - base["median_contacts"]))
        rec = {"start_arc_deg": arc, "matched": best, "sweep": cands}
        rec.update({"play_" + k: v for k, v in play(env).items()})
        rec["admissible"] = {
            "coverage_raised": best["median_arc_deg"] > base["median_arc_deg"] + 10,
            "contacts_matched": abs(best["median_contacts"]
                                    - base["median_contacts"]) <= 3,
            "every_block_fires": best["blocks_with_a_contact"] == best["n_blocks"],
            "trap_preserved": (rec["play_play_cost"] is not None
                               and rec["play_play_cost"] > 0.8
                               and rec["play_blind_contact_rate"] >= 0.9),
        }
        rec["admissible"]["all"] = all(rec["admissible"].values())
        out["arms"][f"arc{arc:g}"] = rec
        print(f"arc {arc:5.0f} deg -> N={best['n_rollouts']:2}: median contacts "
              f"{best['median_contacts']:5.1f} (min {best['min_contacts']}), median arc "
              f"{best['median_arc_deg']:6.1f} deg (min {best['min_arc_deg']:.1f}), "
              f"blocks firing {best['blocks_with_a_contact']}/{best['n_blocks']}")
        print(f"                play_cost {rec['play_play_cost']:.4f} "
              f"contact {rec['play_blind_contact_rate']:.2f}  "
              f"admissible={rec['admissible']['all']}  {rec['admissible']}")

    (RES / "evidence_dose_calibration.json").write_text(json.dumps(out, indent=2))
    print(f"\nwrote {RES / 'evidence_dose_calibration.json'}")


if __name__ == "__main__":
    main()

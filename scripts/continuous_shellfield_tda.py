"""ShellFieldN contact-cloud TDA arm (paper 3, n-dim program, measurement 3 of
docs/paper3/SHELLFIELD-N-DESIGN.md "First measurements"): for n = 2..6, does
the contact set -- the refuted landing positions of a random-policy walk on
the TRUTH ShellFieldN -- actually let persistent homology recover the shell's
signature Betti number beta_{n-1}(S^{n-1}) = 1, or is the cloud too sparse
(concentration data-starvation, since results/continuous_shellfield.json
shows r(n) collapsing 0.013 -> ~0 by n=5-6) to reach the Niyogi-Smale-
Weinberger (NSW) density needed for that recovery at all?

Tooling (design note, "Tooling decision RESOLVED"): gudhi's alpha complex
(Delaunay-based) for n <= 5 -- the pure-Python Rips reducer in
`cwm.continuous.tda` stops being viable at n >= 3 (needs tetrahedra+). The
alpha-complex signal is the DOMINANT persistence interval in homological
dimension n-1 vs the 2nd-most-persistent (the "max-vs-2nd gap"; a large gap
is a Cohen-Steiner-stable sign that one real feature dominates noise). n = 6
uses 2-plane coordinate SLICES instead (Delaunay in R^6 on non-trivial
clouds explodes): project the contact cloud onto a few coordinate pairs and
run the from-scratch 2D Rips reducer's H1 (`cwm.continuous.tda.
rips_persistence`) on each projection, reporting the best (max-dominant)
pair. `cwm.continuous.tda.dedupe`/`subsample` are 2D-specific (contact
clouds re-fire near-identical landings); this script's `dedupe_nd` is their
straightforward n-dim generalization, reusing the exact same grid-snap idea.

Contact-collection convention (matches scripts/ring2d_tda_probe.py exactly):
every freeze ("contact") event across an episode counts, not just the
rollout's first -- a rollout can re-enter the shell after freezing if the
next sampled thrust points back in. The recorded position is the raw
INTEGRATED landing (pre-freeze), the same "refuted landing" the mitigation/
repair machinery would see, not the frozen (= previous) position ShellFieldN
.step() actually returns.

NSW heuristic (task-scoped, documented, not rigorous): ShellFieldN's default
`--start outside` always starts far OUTSIDE the shell (distance ~12 from c
vs r_out=5), so contacts land predominantly on the shell's reachable OUTER
sphere S^{n-1} of radius r_out -- the same "contact set carries the
REACHABLE boundary's topology" finding as RESEARCH-DIRECTION.md SS4.3,
transferred to n dims. `--start inside` (the n-dim analogue of ring2d's
inside-start arm, ring_in in scripts/ring2d_tda_probe.py) starts the probe
strictly inside the inner ball ||x-c|| < r_in instead, so contacts trace the
INNER sphere S^{n-1} of radius r_in from within -- in 2D this was the only
start that even posed the hole (the ring2d D-cell finding). A round sphere's
reach (Federer) equals its radius, so tau ~= r_out (outside) or tau ~= r_in
(inside; set automatically by --start). NSW (Niyogi-Smale-Weinberger 2008)
needs a sample dense enough that no covering ball of radius eps <
~sqrt(3/5)*tau misses; we use eps = eps_frac * tau (default eps_frac=0.25,
comfortably inside that bound) and estimate the number of eps-balls needed
to cover S^{n-1} of radius tau as
    N_NSW(n) = area_{n-1}(tau) / vol_{n-1}(eps-ball)
             = 2*sqrt(pi) * Gamma((n-1)/2 + 1) / Gamma(n/2) * (tau/eps)^{n-1}
-- a covering-number order-of-magnitude gate, reported alongside n_contacts
per n so the reader can see whether "not recovered" is explained by falling
short of this floor (sparsity) or happens despite clearing it (something
else, e.g. the SS4.3 reachability effect: an outside-only walk may only ever
trace an ARC of the outer sphere, not the full loop, regardless of count).

RESUMABLE (hard project rule): atomic write to --out (default
results/continuous_shellfield_tda.json, or results/continuous_shellfield_
tda_inside.json under --start inside) after EVERY n; a restart loads the
existing file, skips n's already present, and refuses to resume under a
different --budget/--seed/--cap/--gap-threshold/--start (the numbers would
silently mix configurations).

Run: PYTHONPATH=src python3.12 scripts/continuous_shellfield_tda.py
      PYTHONPATH=src python3.12 scripts/continuous_shellfield_tda.py --start inside
(needs the `.[tda]` gudhi extra; lower --budget if this is slow -- the
random-thrust walk in R^n costs the same per step at every n, so runtime
scales ~linearly in budget x len(ns)). A few minutes CPU at the defaults.
"""
import argparse
import json
import math
import os
import pathlib
import random
import time

from cwm.continuous.envs import ShellFieldN
from cwm.continuous.tda import rips_persistence, subsample

try:
    import gudhi
except ImportError as exc:  # pragma: no cover - environment guard
    raise SystemExit(
        "gudhi is required (optional dep `.[tda]`, gudhi>=3.13.0). Install "
        "it in the interpreter you run this with, e.g. "
        "`python3.12 -m pip install '.[tda]'`, or invoke with an "
        "interpreter that already has it."
    ) from exc

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("--ns", type=int, nargs="+", default=[2, 3, 4, 5, 6])
ap.add_argument("--budget", type=int, default=20_000,
                 help="rollout budget per n (random-thrust policy)")
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--cap", type=int, default=300,
                 help="max points fed to the alpha complex / a 2D slice "
                      "reducer, after dedupe (subsampled deterministically)")
ap.add_argument("--dedupe-grid", type=float, default=0.05)
ap.add_argument("--gap-threshold", type=float, default=10.0,
                 help="recovered_bool requires dominant/2nd persistence >= "
                      "this (pre-registered; well below the ~100-700x cited "
                      "for clean synthetic shells, to allow real noisy data "
                      "a real but more modest gap)")
ap.add_argument("--eps-frac", type=float, default=0.25,
                 help="NSW covering radius as a fraction of the reach tau")
ap.add_argument("--start", choices=["outside", "inside"], default="outside",
                 help="ShellFieldN start placement (mu0 knob): 'outside' "
                      "(default, byte-identical to the pre-existing arm) "
                      "or 'inside' the inner ball -- the n-dim analogue of "
                      "ring2d's inside-start arm")
ap.add_argument("--out", type=str, default=None,
                 help="default: results/continuous_shellfield_tda.json "
                      "(outside) or results/continuous_shellfield_tda_"
                      "inside.json (inside)")
args = ap.parse_args()
if args.out is None:
    args.out = ("results/continuous_shellfield_tda.json" if args.start == "outside"
                else "results/continuous_shellfield_tda_inside.json")

SLICE_PAIRS_N6 = [(0, 1), (0, 2), (2, 3), (4, 5)]


def _atomic_write_json(path: pathlib.Path, obj) -> None:
    """Same discipline as continuous_shellfield.py: write to a sibling temp
    file, then os.replace() -- one atomic rename, so a kill mid-write never
    corrupts the previous checkpoint."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2))
    os.replace(tmp, path)


def contact_cloud(env: ShellFieldN, n_rollouts: int, seed: int) -> list:
    """All freeze events across every rollout's episode (see module
    docstring's "contact-collection convention"). Recomputes the freeze
    branch of `ShellFieldN.step` inline (integrate once, check `_in_mode`,
    apply the freeze-at-previous-position semantics directly) to avoid
    integrating twice per step."""
    pts = []
    for i in range(n_rollouts):
        rng = random.Random(seed + i)
        s = env.initial_state(rng)
        for _ in range(env.h_episode):
            a = tuple(rng.uniform(-1.0, 1.0) for _ in range(env.n))
            s2 = env._integrate(s, a)
            pos2 = s2[: env.n]
            if env._in_mode(pos2):
                pts.append(pos2)
                s = s[: env.n] + (0.0,) * env.n  # freeze semantics (step())
            else:
                s = s2
    return pts


def dedupe_nd(points: list, grid: float = 0.05) -> list:
    """n-dim generalization of `cwm.continuous.tda.dedupe`'s grid-snap
    idea (contact clouds repeat near-identical refuted landings when a
    mover re-fires from rest near the same spot)."""
    seen, out = set(), []
    for p in points:
        key = tuple(round(c / grid) for c in p)
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def nsw_points_needed(n: int, tau: float, eps_frac: float) -> float:
    """Rough NSW covering-number heuristic -- see module docstring."""
    eps = eps_frac * tau
    k = n - 1
    const = 2 * math.sqrt(math.pi) * math.gamma(k / 2 + 1) / math.gamma(n / 2)
    return const * (tau / eps) ** k


def _top_two_persistences(intervals) -> tuple:
    """intervals: iterable of (birth, death). Returns (dominant, second,
    n_intervals, n_essential) with 0.0 defaults when fewer than 2 exist.
    Essential (infinite-death) bars are excluded from the persistence
    values reported (not expected for H_{n-1} of a full alpha complex on
    a generic finite point set -- the complex is contractible by its final
    filtration value -- but guarded defensively) and counted separately."""
    finite = []
    n_essential = 0
    for b, d in intervals:
        if math.isinf(d):
            n_essential += 1
        else:
            finite.append(d - b)
    finite.sort(reverse=True)
    dominant = finite[0] if len(finite) >= 1 else 0.0
    second = finite[1] if len(finite) >= 2 else 0.0
    return dominant, second, len(finite) + n_essential, n_essential


def alpha_dominant_vs_second(points: list, dim: int) -> dict:
    """gudhi alpha-complex persistence, dominant vs 2nd interval in
    dimension `dim`. Filtration units are alpha-complex squared-radius
    (gudhi convention); the dominant/2nd RATIO is unit-invariant, which is
    the quantity actually used for the recovered_bool decision."""
    ac = gudhi.AlphaComplex(points=[list(p) for p in points], precision="fast")
    st = ac.create_simplex_tree()
    st.persistence(homology_coeff_field=2, min_persistence=0.0)
    intervals = st.persistence_intervals_in_dimension(dim)
    dominant, second, n_int, n_ess = _top_two_persistences(
        [(float(b), float(d)) for b, d in intervals])
    return {"dominant": dominant, "second": second, "n_intervals": n_int,
            "n_essential": n_ess}


def slices_dominant_vs_second(points: list, pairs: list) -> dict:
    """n=6 fallback: project the (already deduped/subsampled) n-dim cloud
    onto each coordinate pair in `pairs`, run the from-scratch 2D Rips
    reducer's H1, and report the pair with the largest dominant persistence
    (i.e. give the method its best shot across a few candidate slices)."""
    best = {"dominant": 0.0, "second": 0.0, "pair": None, "per_pair": []}
    for (i, j) in pairs:
        proj = [(p[i], p[j]) for p in points]
        bars = rips_persistence(proj)["h1"] if len(proj) >= 3 else []
        dominant, second, n_int, n_ess = _top_two_persistences(
            [(b, d if d is not None else float("inf")) for b, d in bars])
        best["per_pair"].append({"pair": [i, j], "dominant": dominant,
                                  "second": second, "n_intervals": n_int})
        if dominant > best["dominant"]:
            best["dominant"], best["second"], best["pair"] = dominant, second, [i, j]
    return best


def process_n(n: int, budget: int, seed: int, cap: int, dedupe_grid: float,
              gap_threshold: float, eps_frac: float, start: str) -> dict:
    env = ShellFieldN(n=n, start=start)
    t0 = time.time()
    raw = contact_cloud(env, budget, seed)
    n_contacts = len(raw)
    deduped = dedupe_nd(raw, grid=dedupe_grid)
    used = subsample(deduped, cap, seed=1)
    # reach tau ~= the sphere a start actually approaches: r_out from far
    # outside, r_in from inside the inner ball (see module docstring's NSW
    # section).
    tau = env.r_out if start == "outside" else env.r_in
    n_nsw = nsw_points_needed(n, tau, eps_frac)

    method = "alpha" if n <= 5 else "slices"
    dim = n - 1
    detail: dict = {}
    min_pts = n + 2  # need at least this many points for a non-degenerate
                     # full-dimensional Delaunay triangulation in R^n
    if method == "alpha":
        if len(used) >= min_pts:
            res = alpha_dominant_vs_second(used, dim)
            dominant, second = res["dominant"], res["second"]
            detail = {"n_intervals_dim": res["n_intervals"],
                       "n_essential_dim": res["n_essential"]}
        else:
            dominant, second = 0.0, 0.0
            detail = {"skipped": f"n_used={len(used)} < min_pts={min_pts}"}
    else:
        if len(used) >= 3:
            res = slices_dominant_vs_second(used, SLICE_PAIRS_N6)
            dominant, second = res["dominant"], res["second"]
            detail = {"best_pair": res["pair"], "per_pair": res["per_pair"]}
        else:
            dominant, second = 0.0, 0.0
            detail = {"skipped": f"n_used={len(used)} < 3"}

    gap = (dominant / second) if second > 0 else (float("inf") if dominant > 0 else 0.0)
    # A lone dim-(n-1) bar with no runner-up (second == 0) has no noise
    # floor to be clear ABOVE -- gap is formally infinite but that is not
    # evidence of a clean signal, just of a single accidental cycle in a
    # tiny point set. Require a genuine competitor (second > 0) before
    # calling the dominant bar "recovered".
    if dominant > 0.0 and second <= 0.0:
        detail["single_bar_no_competitor"] = True
    recovered = bool(dominant > 0.0 and second > 0.0 and gap >= gap_threshold)

    return {
        "n": n,
        "n_contacts": n_contacts,
        "n_deduped": len(deduped),
        "n_used": len(used),
        "dominant_persistence": dominant,
        "second_persistence": second,
        "gap": None if math.isinf(gap) else round(gap, 3),
        "recovered_bool": recovered,
        "method": method,
        "nsw_points_needed": round(n_nsw, 1),
        "density_vs_nsw": (round(n_contacts / n_nsw, 4) if n_nsw > 0 else None),
        "detail": detail,
        "elapsed_s": round(time.time() - t0, 1),
    }


def main() -> None:
    out_path = pathlib.Path(args.out)
    if out_path.exists():
        out = json.loads(out_path.read_text())
        out.setdefault("rows", [])
        stored_p = out.get("params", {}) or {}
        current_p = vars(args)
        mismatch = {k: (stored_p[k], current_p[k])
                    for k in ("budget", "seed", "cap", "dedupe_grid",
                              "gap_threshold", "eps_frac", "start")
                    if k in stored_p and stored_p[k] != current_p[k]}
        if mismatch:
            raise ValueError(
                f"refusing to resume {out_path}: it was produced under a "
                f"different configuration {mismatch}; rerun with matching "
                f"flags or move the file aside")
    else:
        out = {"script": "continuous_shellfield_tda.py", "params": vars(args),
               "rows": []}

    done = {row["n"] for row in out["rows"]}
    t0 = time.time()
    header = (f"{'n':>3} {'n_contacts':>10} {'used':>5} {'dominant':>12} "
              f"{'second':>12} {'gap':>8} {'recov':>6} {'method':>7} "
              f"{'N_NSW':>10}")
    print(header, flush=True)
    for row in sorted(out["rows"], key=lambda r: r["n"]):
        gap_s = "inf" if row["gap"] is None else f"{row['gap']:.2f}"
        print(f"{row['n']:3d} {row['n_contacts']:10d} {row['n_used']:5d} "
              f"{row['dominant_persistence']:12.5f} "
              f"{row['second_persistence']:12.5f} {gap_s:>8} "
              f"{str(row['recovered_bool']):>6} {row['method']:>7} "
              f"{row['nsw_points_needed']:10.1f}  [cached]", flush=True)

    for n in args.ns:
        if n in done:
            continue
        row = process_n(n, args.budget, args.seed + 60_000, args.cap,
                         args.dedupe_grid, args.gap_threshold, args.eps_frac,
                         args.start)
        out["rows"].append(row)
        out["elapsed_s"] = round(time.time() - t0, 1)
        _atomic_write_json(out_path, out)
        gap_s = "inf" if row["gap"] is None else f"{row['gap']:.2f}"
        print(f"{row['n']:3d} {row['n_contacts']:10d} {row['n_used']:5d} "
              f"{row['dominant_persistence']:12.5f} "
              f"{row['second_persistence']:12.5f} {gap_s:>8} "
              f"{str(row['recovered_bool']):>6} {row['method']:>7} "
              f"{row['nsw_points_needed']:10.1f}", flush=True)

    out["elapsed_s"] = round(time.time() - t0, 1)
    _atomic_write_json(out_path, out)
    print(f"wrote {out_path}  [{out['elapsed_s']}s]", flush=True)


if __name__ == "__main__":
    main()

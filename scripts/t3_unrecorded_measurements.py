"""Emit T3's load-bearing measurements that had no committed artifact.

Same failure class as a hand-computed constant, one level up: these numbers were
quoted in docs/paper3/THEORY.md with no script and no results/*.json, so nobody
could re-derive them. One of them (f(0)) did not even reproduce at the obvious
kernel bandwidth, because the bandwidth was never recorded. Emitted here:

  (a) R  = P(a ring-free rollout ever reaches r_out)                and
      R' = P(it does so within h - k steps), the deadline version, together with
      the OFF-BY-ONE that a 0-based index check introduces (`hit <= H - k`
      leaves k-1 steps, not k), reported both ways rather than silently.
  (b) the |Z_t| table: median displacement and P(|Z_t| in the annulus) at
      several t, which is the radial law the isotropy bound consumes.
  (c) the corridor table: P(|v_tan| <= r*gamma/(2 k dt)) at channel arrival,
      the non-freeze fraction, and f(0) -- with the BANDWIDTH recorded and the
      SIGNED and FOLDED conventions emitted separately, since the bound is on
      the signed density while the criterion consumes the folded one.
  (d) the arrival-angle profile, folded, per 0.1 rad bin. A lower bound needs
      inf rho over the channel, not rho(pi), which is its MAXIMUM -- so the
      profile, not just its peak, is the artifact.
  (e) the crossing-duration distribution (median/mean/p90). k ~ 9 is a MEDIAN,
      so the horizon term leaves a residue P(crossing > k); that residue is
      only visible if the distribution is emitted.
  (f) the failure census at channel arrival: froze on the band / turned back
      out / ran out of horizon / entered.
  (g) the steering derivative |d theta / d a_0| at first arrival: median, p90
      and the observed max, with n -- because Lemma D needs a SUP and a
      percentile is not one, and the gap between them is the claim's slack.
  (h) P(a root of theta(a_0) = pi exists), the factor Lemma D requires and an
      earlier version silently set to 1.

Resumable: each cell is keyed and written as it finishes.

  PYTHONPATH=src python scripts/t3_unrecorded_measurements.py
"""
import argparse
import json
import math
import pathlib
import random
import statistics
import sys
import time

_REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from cwm.continuous.envs import RingField2D                      # noqa: E402

OUT = _REPO / "results" / "t3_unrecorded_measurements.json"
CX, CY = 12.0, 0.0
K_CROSS = 9                 # the MEDIAN crossing duration, not a bound
GAPS = (0.1, 0.2, 0.4, 0.6)
t0 = time.time()


def _fold(theta):
    """|theta - pi| folded into [0, pi]."""
    return abs((theta - math.pi + math.pi) % (2 * math.pi) - math.pi)


def ring_free_reach(n, seed_base, k):
    """(a) R, R' both ways, and (b) the |Z_t| table -- one pass.

    Z_t is the displacement from the start under the RING-FREE dynamics, which
    is what the reach factor is about.
    """
    env = RingField2D(gap=0.0, r_in=None)
    H = env.h_episode
    probe_t = [20, 40, 60, H - k, H - k - 1]
    zs = {t: [] for t in probe_t}
    reach = reach_deadline_k = reach_deadline_km1 = 0
    L_lo, L_hi = float("inf"), 0.0
    for i in range(n):
        rng = random.Random(seed_base + i)
        s = env.initial_state(rng)
        x0, y0 = s[0], s[1]
        L = math.hypot(CX - x0, CY - y0)
        L_lo, L_hi = min(L_lo, L), max(L_hi, L)
        hit = None
        for t in range(H):
            s, _, _ = env.step(s, rng.uniform(-env.a_max, env.a_max))
            if t in zs:
                zs[t].append(math.hypot(s[0] - x0, s[1] - y0))
            if hit is None and math.hypot(s[0] - CX, s[1] - CY) <= env.r_out:
                hit = t
        if hit is not None:
            reach += 1
            # The two readings of "within h - k steps" on a 0-based index.
            reach_deadline_k += (hit <= H - k - 1)      # leaves k steps
            reach_deadline_km1 += (hit <= H - k)        # leaves k-1 steps
    ann_lo, ann_hi = L_lo - env.r_out, L_hi + env.r_out
    return {
        "n": n, "seed_base": seed_base, "k": k, "h_episode": H,
        "r_out": env.r_out, "L_range": [L_lo, L_hi],
        "annulus": [ann_lo, ann_hi],
        "R": reach / n,
        "R_prime_leaving_k_steps": reach_deadline_k / n,
        "R_prime_leaving_k_minus_1_steps": reach_deadline_km1 / n,
        "off_by_one_note": (
            "`hit <= h_episode - k` on a 0-based step index leaves k-1 steps, "
            "not k. Both are emitted; quote the one the argument needs."),
        "Z_table": [
            {"t": t,
             "median_abs_Z": statistics.median(v),
             "P_in_annulus": sum(1 for z in v if ann_lo <= z <= ann_hi) / len(v)}
            for t, v in sorted(zs.items()) if v],
    }


def arrival_profile(n, seed_base, bins):
    """(d) the folded arrival-angle profile, and rho at pi, ring-free."""
    env = RingField2D(gap=0.0, r_in=None)
    offs = []
    for i in range(n):
        rng = random.Random(seed_base + i)
        s = env.initial_state(rng)
        for _ in range(env.h_episode):
            s, _, _ = env.step(s, rng.uniform(-env.a_max, env.a_max))
            if math.hypot(s[0] - CX, s[1] - CY) <= env.r_out:
                offs.append(_fold(math.atan2(s[1] - CY, s[0] - CX)))
                break
    w = math.pi / bins
    prof = []
    for j in range(bins):
        lo, hi = j * w, (j + 1) * w
        k = sum(1 for o in offs if lo <= o < hi)
        # Folded density per radian of OFFSET: the sector at offset <= x has
        # angular width 2x, so this is the density the decomposition consumes.
        prof.append({"offset_lo": lo, "offset_hi": hi, "count": k,
                     "density_per_rad": k / len(offs) / (2 * w)})
    # Per gap: what a LOWER bound may use (the infimum over the channel) and
    # what the integral actually averages, so the cost of substituting the
    # peak is derived here instead of by hand.
    rho_pi = prof[0]["density_per_rad"]
    per_gap = {}
    for gap in GAPS + (0.9, 1.2):
        half = gap / 2
        inside = [b for b in prof if b["offset_lo"] < half]
        if not inside:
            continue
        dens = [b["density_per_rad"] for b in inside]
        # mass-weighted mean over the channel = the integral / gap
        mass = sum(b["count"] for b in inside) / len(offs)
        per_gap[str(gap)] = {
            "bins_spanned": len(inside),
            "inf_rho": min(dens),
            "mean_rho_over_channel": mass / gap if gap else None,
            "rho_pi_over_inf": rho_pi / min(dens) if min(dens) else None,
            "rho_pi_over_mean": (rho_pi * gap / mass) if mass else None,
        }
    return {"n": n, "seed_base": seed_base, "arrivals": len(offs),
            "bin_width_rad": w, "profile": prof,
            "rho_at_pi": rho_pi, "per_gap": per_gap,
            "note": ("pi is the MAXIMUM of rho, so a lower bound needs "
                     "inf_rho over the channel; rho_pi_over_inf is the factor "
                     "by which substituting the peak inflates a lower bound, "
                     "and rho_pi_over_mean the factor by which it overstates "
                     "the integral itself.")}


def corridor(gap, n, seed_base, bandwidths):
    """(c), (e), (f): the corridor criterion, durations and failure census.

    Unit = channel arrival. f(0) is emitted at several bandwidths, signed and
    folded, because the bound is on the signed density and the criterion
    consumes the folded one -- mixing the two is a factor 2.
    """
    env = RingField2D(gap=gap)
    H = env.h_episode
    # The corridor threshold depends on WHICH radius the arc is measured at,
    # and the arc's radius varies across the band. An UPPER bound on T must
    # use the loosest (largest) threshold, i.e. r_out; r = 4.0 is the value an
    # earlier table used. All three are emitted so the display can quote the
    # one its direction needs instead of a single unlabelled number.
    radii = {"r_in": env.r_in, "r_4.0": 4.0, "r_out": env.r_out}
    thresh = env.r_out * gap / (2 * K_CROSS * env.dt)
    v_signed, durations = [], []
    froze = out = horizon = entered = 0
    for i in range(n):
        rng = random.Random(seed_base + i)
        s = env.initial_state(rng)
        arrived_at = None
        for t in range(H):
            s, _, contact = env.step(s, rng.uniform(-env.a_max, env.a_max))
            if contact:
                if arrived_at is not None:
                    froze += 1
                break
            r = math.hypot(s[0] - CX, s[1] - CY)
            if arrived_at is None and r <= env.r_out:
                if _fold(math.atan2(s[1] - CY, s[0] - CX)) <= gap / 2:
                    arrived_at = t
                    # tangential velocity at arrival, SIGNED
                    dx, dy = s[0] - CX, s[1] - CY
                    nx, ny = dx / max(1e-12, r), dy / max(1e-12, r)
                    v_signed.append(-s[2] * ny + s[3] * nx)
            if arrived_at is not None and r > env.r_out:
                out += 1
                break
            if env.in_interior(s[0], s[1]):
                if arrived_at is not None:
                    entered += 1
                    durations.append(t - arrived_at)
                break
        else:
            if arrived_at is not None:
                horizon += 1
    arr = len(v_signed)
    folded = [abs(v) for v in v_signed]
    dens = []
    for b in bandwidths:
        ks = sum(1 for v in v_signed if abs(v) <= b)
        dens.append({"bandwidth": b,
                     "f0_signed": ks / arr / (2 * b) if arr else None,
                     "f0_folded": ks / arr / b if arr else None})
    return {
        "gap": gap, "n": n, "seed_base": seed_base, "unit": "channel arrival",
        "arrivals": arr, "k_cross_used": K_CROSS,
        "corridor_threshold": thresh,
        "corridor_thresholds": {k: r * gap / (2 * K_CROSS * env.dt)
                                for k, r in radii.items()},
        "P_corridor_satisfied":
            (sum(1 for v in folded if v <= thresh) / arr) if arr else None,
        "P_corridor_satisfied_by_radius": {
            k: (sum(1 for v in folded
                    if v <= r * gap / (2 * K_CROSS * env.dt)) / arr)
            if arr else None for k, r in radii.items()},
        # Two DIFFERENT fractions, both per channel arrival, and an earlier
        # table compared the corridor criterion against the second while
        # labelling it like the first:
        "P_entered": (entered / arr) if arr else None,
        "non_freeze_fraction": (1 - froze / arr) if arr else None,
        "fraction_note": (
            "non_freeze_fraction = 1 - P(froze on the band | arrival), which "
            "is what the corridor criterion is compared against. P_entered is "
            "the smaller quantity P(reached the interior | arrival): an arrival "
            "can avoid freezing and still run out of horizon."),
        "f0": dens,
        "f0_convention_note": (
            "f0_signed is what Lemma D's arcsine bound bounds; f0_folded is "
            "what the corridor criterion consumes, and equals twice the "
            "signed value. Quote the one matching the display."),
        "failure_census": {"froze_on_band": froze, "turned_back_out": out,
                           "ran_out_of_horizon": horizon, "entered": entered},
        "crossing_duration": ({
            "n": len(durations),
            "median": statistics.median(durations),
            "mean": statistics.fmean(durations),
            "p90": sorted(durations)[int(0.9 * (len(durations) - 1))],
            "max": max(durations),
        } if durations else None),
        "horizon_residue_note": (
            "k = %d is the MEDIAN; the deadline argument leaves a residue of "
            "order P(crossing > k), which this distribution gives."
            % K_CROSS),
    }


def steering(n_configs, grid, seed_base):
    """(g) and (h): the steering derivative's spread, and P(root exists).

    For each configuration of the other actions, scan a_0 on a grid and record
    the arrival angle. The derivative is a finite difference at the arrival;
    a root exists when the scanned angle brackets pi.
    """
    env = RingField2D(gap=0.0, r_in=None)
    H = env.h_episode
    derivs, jumps, roots, usable = [], [], 0, 0
    for c in range(n_configs):
        base = random.Random(seed_base + c)
        tail = [base.uniform(-env.a_max, env.a_max) for _ in range(H)]
        angles = []
        for j in range(grid):
            a0 = -env.a_max + 2 * env.a_max * j / (grid - 1)
            s = env.initial_state(random.Random(seed_base + c))
            ang, step = None, None
            for t in range(H):
                a = a0 if t == 0 else tail[t]
                s, _, _ = env.step(s, a)
                if math.hypot(s[0] - CX, s[1] - CY) <= env.r_out:
                    ang, step = math.atan2(s[1] - CY, s[0] - CX), t
                    break
            angles.append((a0, ang, step))
        hit = [(a, t, st) for a, t, st in angles if t is not None]
        if len(hit) < 2:
            continue
        usable += 1
        # A root of theta(a_0) = pi exists iff the SIGNED offset from pi
        # changes sign between two consecutive reaching grid points. Using the
        # folded offset cannot see this -- folding destroys the sign that a
        # bracketing argument needs.
        sgn = [(a, (t - math.pi + math.pi) % (2 * math.pi) - math.pi)
               for a, t, _ in hit]
        crossed = any(sgn[j][1] == 0.0 or sgn[j][1] * sgn[j + 1][1] < 0
                      for j in range(len(sgn) - 1))
        roots += bool(crossed)
        for j in range(len(hit) - 1):
            da = hit[j + 1][0] - hit[j][0]
            dth = hit[j + 1][1] - hit[j][1]
            dth = (dth + math.pi) % (2 * math.pi) - math.pi
            if not da:
                continue
            val = abs(dth / da)
            # theta(a_0) is differentiable only where the ARRIVAL STEP is
            # constant: when the step changes, theta jumps and the finite
            # difference is not a derivative. Lemma D's change of variables
            # lives on the differentiable pieces (summing over roots), so the
            # restricted series is the one it consumes -- but the jumps are
            # where a root can sit without any derivative existing, so both
            # are emitted rather than one silently filtered.
            if hit[j][2] == hit[j + 1][2]:
                derivs.append(val)
            else:
                jumps.append(val)
    derivs.sort()
    jumps.sort()
    return {
        "arrival_step_changed": {
            "n": len(jumps),
            "median": statistics.median(jumps) if jumps else None,
            "p90": jumps[int(0.9 * (len(jumps) - 1))] if jumps else None,
            "max": max(jumps) if jumps else None,
            "note": ("finite differences ACROSS an arrival-step change: theta "
                     "jumps there, so these are not derivatives. They bound "
                     "nothing by themselves, but a root sitting at a jump has "
                     "no derivative for Lemma D to divide by."),
        },
        "n_configs": n_configs, "usable_configs": usable, "grid": grid,
        "seed_base": seed_base, "n_derivatives": len(derivs),
        "median": statistics.median(derivs) if derivs else None,
        "p90": derivs[int(0.9 * (len(derivs) - 1))] if derivs else None,
        "max": max(derivs) if derivs else None,
        "roots_found": roots,
        # Lemma D's factor is the UNCONDITIONAL probability that a root exists,
        # so it divides by all configurations drawn. The conditional version
        # (given the rollout reaches r_out at all) is emitted beside it because
        # it is the one that describes the geometry; conflating them is a factor
        # of R.
        "P_root_exists": roots / n_configs,
        "P_root_exists_given_reaching": roots / usable if usable else None,
        "sup_note": ("Lemma D needs a SUP; the p90 is not one. The gap between "
                     "p90 and max is the slack a percentile-based claim hides, "
                     "and P_root_exists is a grid-scan FLOOR (a finer grid can "
                     "only find more roots)."),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-reach", type=int, default=200_000)
    ap.add_argument("--n-profile", type=int, default=60_000)
    ap.add_argument("--n-corridor", type=int, default=200_000)
    ap.add_argument("--n-steer", type=int, default=900)
    ap.add_argument("--steer-grid", type=int, default=161)
    args = ap.parse_args()

    state = json.loads(OUT.read_text()) if OUT.exists() else {}
    cells = state.setdefault("cells", {})

    key = f"reach|{args.n_reach}"
    if key not in cells:
        print(f"(a,b) ring-free reach and |Z_t| table, n={args.n_reach}",
              flush=True)
        cells[key] = ring_free_reach(args.n_reach, 50_000, K_CROSS)
        OUT.write_text(json.dumps(state, indent=1, sort_keys=True))
        print(f"   R={cells[key]['R']:.5f} "
              f"R'(k)={cells[key]['R_prime_leaving_k_steps']:.5f} "
              f"R'(k-1)={cells[key]['R_prime_leaving_k_minus_1_steps']:.5f}",
              flush=True)

    key = f"profile|{args.n_profile}|v2"
    if key not in cells:
        print(f"(d) arrival-angle profile, n={args.n_profile}", flush=True)
        cells[key] = arrival_profile(args.n_profile, 90_000, 31)
        OUT.write_text(json.dumps(state, indent=1, sort_keys=True))

    for gap in GAPS:
        key = f"corridor|{gap}|{args.n_corridor}|v2"
        if key not in cells:
            print(f"(c,e,f) corridor at gap={gap}, n={args.n_corridor}",
                  flush=True)
            cells[key] = corridor(gap, args.n_corridor, 50_000,
                                  [0.1, 0.2, 0.3, 0.5])
            OUT.write_text(json.dumps(state, indent=1, sort_keys=True))

    key = f"steering|{args.n_steer}|{args.steer_grid}|v2"
    if key not in cells:
        print(f"(g,h) steering derivative, {args.n_steer} configs", flush=True)
        cells[key] = steering(args.n_steer, args.steer_grid, 70_000)
        OUT.write_text(json.dumps(state, indent=1, sort_keys=True))

    OUT.write_text(json.dumps(state, indent=1, sort_keys=True))
    print(f"\nwrote {OUT}  ({time.time() - t0:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

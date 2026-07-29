"""Make every printed zero and every over-precise cell in docs/paper2/main.tex say what
it is (review minor points m4, m5, m6).

THE DEFECT. The paper declares once, in prose, that "a printed 0 is a censored zero", and
then relies on that convention in seven tables. A per-cell reader cannot tell which kind of
zero a cell is, and three kinds are in fact mixed:

  (i)   a CENSORED zero -- no occurrence in a finite sample. Its content is an interval.
  (ii)  a ROUNDED-AWAY POSITIVE -- the quantity is not zero at all; it is 1.4e-5 printed at
        two decimals. The convention does not license these, and they currently masquerade
        as censored zeros.
  (iii) a DEMONSTRATED exact zero -- bit-identical returns. Also not a censored zero, in
        the other direction.

This script rewrites those cells. Every replacement value is READ FROM results/ at runtime
(the repo rule: a number in the paper is produced by a script, never retyped), and every
substitution asserts its anchor, so a stale anchor is a hard error rather than a silent
no-op. Idempotent: a second run reports nothing to do.

Run:  PYTHONPATH=src python scripts/apply_table_bounds.py --dry-run
      PYTHONPATH=src python scripts/apply_table_bounds.py --apply
"""
import argparse
import json
import math
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
TEX = REPO / "docs" / "paper2" / "main.tex"
RES = REPO / "results"


def load(name: str) -> dict:
    return json.loads((RES / f"{name}.json").read_text())


def wilson_hi(k: int, n: int, z: float = 1.959963984540054) -> float:
    if n == 0:
        return 1.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return min(1.0, c + h)


def cp_upper(k: int, n: int, alpha: float = 0.05) -> float:
    """One-sided Clopper-Pearson upper limit. For k = 0 this is 1 - alpha**(1/n)."""
    if n == 0:
        return 1.0
    if k == 0:
        return 1.0 - alpha ** (1.0 / n)

    def tail(p):
        return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))

    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if tail(mid) > alpha else (lo, mid)
    return (lo + hi) / 2


def sci(x: float, digits: int = 1) -> str:
    """LaTeX scientific notation for a table cell, e.g. 1.4e-5 -> $1.4{\\times}10^{-5}$."""
    if x == 0:
        return "0"
    e = math.floor(math.log10(abs(x)))
    m = x / 10 ** e
    return f"${m:.{digits}f}{{\\times}}10^{{{e}}}$"


def build_subs() -> list[tuple[str, str, str]]:
    """(id, anchor, replacement). Anchors are whole table rows, matched on content."""
    subs: list[tuple[str, str, str]] = []
    reach = load("continuous_reach")
    pend = load("continuous_pendulum")
    patch = load("continuous_patch2d")
    cem = load("continuous_cem")
    axes = load("continuous_axes")
    epsw = load("continuous_eps_sweep")

    # ---- tab:danger. Columns: x_wall & rarity & J_truth & J_blind & J_rand &
    #      play_cost & blind hit & truth hit & d@20 & d@40 & d@80
    # J_blind and the d@N cells are kind (ii); "truth hit" is kind (i) at 0/20.
    truth_hit_hi = wilson_hi(0, reach["params"].get("episodes", 20))
    for row in reach["rows"]:
        xw = row["x_wall"]
        d = row["danger"]

        def cell(v: float, printed_digits: int) -> str:
            """Print the value at `printed_digits`, or in exponent form if that would
            round it to zero."""
            return (f"{v:.{printed_digits}f}" if round(v, printed_digits) != 0
                    else sci(v))

        old = (f"{xw:.0f} & {row['rarity']:.4f} & {row['j_truth']:.2f} & "
               f"{row['j_blind']:.2f} & {row['j_random']:.2f} & "
               f"{row['play_cost']:.3f} & {row['blind_contact_rate']:.2f} & "
               f"{row['truth_contact_rate']:.2f} & "
               f"{d['20']:.3f} & {d['40']:.3f} & {d['80']:.3f} \\\\")
        # The "truth hit" column is the same censored bound in every row, so it belongs
        # in the caption rather than in eleven identical cells -- which also keeps the
        # table inside \\textwidth once J_blind and d@N carry exponents.
        mid = (f"{xw:.0f} & {row['rarity']:.4f} & {row['j_truth']:.2f} & "
               f"{cell(row['j_blind'], 2)} & {row['j_random']:.2f} & "
               f"{row['play_cost']:.3f} & {row['blind_contact_rate']:.2f} & "
               f"$<{truth_hit_hi:.2f}$ & "
               f"{cell(d['20'], 3)} & {cell(d['40'], 3)} & {cell(d['80'], 3)} \\\\")
        new = (f"{xw:.0f} & {row['rarity']:.4f} & {row['j_truth']:.2f} & "
               f"{cell(row['j_blind'], 2)} & {row['j_random']:.2f} & "
               f"{row['play_cost']:.3f} & {row['blind_contact_rate']:.2f} & "
               f"{cell(d['20'], 3)} & {cell(d['40'], 3)} & {cell(d['80'], 3)} \\\\")
        subs.append((f"tab:danger x_wall={xw:g}", old, new))
        subs.append((f"tab:danger x_wall={xw:g} (drop truth-hit column)", mid, new))

    subs.append((
        "tab:danger column spec",
        r"\begin{tabular}{rrrrrrrrrrr}" "\n" r"\toprule" "\n"
        r"$x_\mathrm{wall}$ & rarity & $J_\mathrm{truth}$ & $J_\mathrm{blind}$ & "
        r"$J_\mathrm{rand}$ & play\_cost & blind hit & truth hit & d@20 & d@40 & d@80 \\",
        r"\begin{tabular}{rrrrrrrrrr}" "\n" r"\toprule" "\n"
        r"$x_\mathrm{wall}$ & rarity & $J_\mathrm{truth}$ & $J_\mathrm{blind}$ & "
        r"$J_\mathrm{rand}$ & play\_cost & blind hit & d@20 & d@40 & d@80 \\"))
    subs.append((
        "tab:danger caption",
        r"``blind/truth hit'' = fraction of episodes in which that planner's trajectory "
        r"fires the wall mode;",
        r"``blind hit'' = fraction of episodes in which the blind planner's trajectory "
        r"fires the wall mode; the truth planner's trajectory fires it in no episode at "
        rf"any knob ($0/20$, so $<{truth_hit_hi:.2f}$);"))

    # ---- tab:pendulum. th_stop & rarity & J_truth & J_blind & play_cost & blind hit & d@40
    for row in pend["rows"]:
        d40 = row["danger"]["40"]
        old = (f"{row['th_stop']:.1f} & {row['rarity']:.4f} & {row['j_truth']:.2f} & "
               f"{row['j_blind']:.2f} & {row['play_cost']:.3f} & "
               f"{row['blind_contact_rate']:.2f} & {d40:.3f} \\\\")
        new = (f"{row['th_stop']:.1f} & {row['rarity']:.4f} & {row['j_truth']:.2f} & "
               f"{row['j_blind']:.2f} & {row['play_cost']:.3f} & "
               f"{row['blind_contact_rate']:.2f} & "
               f"{d40 if round(d40,3) != 0 else 0:.3f} \\\\"
               if round(d40, 3) != 0 else
               f"{row['th_stop']:.1f} & {row['rarity']:.4f} & {row['j_truth']:.2f} & "
               f"{row['j_blind']:.2f} & {row['play_cost']:.3f} & "
               f"{row['blind_contact_rate']:.2f} & {sci(d40)} \\\\")
        if old != new:
            subs.append((f"tab:pendulum th_stop={row['th_stop']:g}", old, new))

    # ---- tab:patch2d. k1 & k2 & r1 & r2 & r_union & J_truth & play_cost &
    #      d@40 P1 & d@40 P2 & d@40 joint
    # m5: 600 rollouts resolve 1/600 = 0.0017, so r2 and the d@40 columns are printed to
    # three decimals; m4: the d@40 P1/joint zeros are kind (ii).
    nroll = patch["params"]["rollouts"]
    for row in patch["rows"]:
        def c4(v: float) -> str:
            return f"{v:.4f}"

        def c3(v: float) -> str:
            return f"{v:.3f}" if round(v, 3) != 0 else sci(v)

        old = (f"{row['k1']:.0f} & {row['k2']:.0f} & {row['r1']:.4f} & {row['r2']:.4f} & "
               f"{row['r_either']:.4f} & {row['j_truth']:.2f} & {row['play_cost']:.3f} & "
               f"{c4(row['d40_p1'])} & {c4(row['d40_p2'])} & {c4(row['d40_joint'])} \\\\")
        new = (f"{row['k1']:.0f} & {row['k2']:.0f} & {row['r1']:.3f} & {row['r2']:.3f} & "
               f"{row['r_either']:.3f} & {row['j_truth']:.2f} & {row['play_cost']:.3f} & "
               f"{c3(row['d40_p1'])} & {c3(row['d40_p2'])} & {c3(row['d40_joint'])} \\\\")
        subs.append((f"tab:patch2d k=({row['k1']:g},{row['k2']:g})", old, new))

    # ---- tab:cem. instrument & knob & pc MPC & pc CEM & contact CEM & crossing CEM &
    #      crossing MPC.  pc CEM on the cart rows is a DEMONSTRATED zero (bit-identical
    #      per-seed differences); the crossing zeros are censored, at a denominator the
    #      planner config fixes; contact zeros are censored at 0/20.
    ccb = None
    try:
        ccb = load("cem_crossing_bound")
    except FileNotFoundError:
        pass
    def mpc_pc(instr: str, knob: float) -> float:
        """The MPC play-cost column of tab:cem is not in the CEM artifact; it comes from
        the mechanism sweeps, which is where the paper measured it."""
        src = reach["rows"] if instr == "cart" else pend["rows"]
        key = "x_wall" if instr == "cart" else "th_stop"
        for r in src:
            if abs(r[key] - knob) < 1e-9:
                return r["play_cost"]
        sys.exit(f"no MPC play_cost for {instr}@{knob}")

    n_ep = cem["params"].get("episodes", 20)
    contact_hi = wilson_hi(0, n_ep)
    for row in cem["rows"]:
        pc_cem = row["play_cost_blind_cem"]
        paired = row.get("play_cost_blind_cem_paired") or {}
        per_seed = paired.get("per_seed") or []
        exact_zero = bool(per_seed) and all(v == 0.0 for v in per_seed)
        cr_cem, cr_mpc = row["crossing_frac_cem_blind"], row["crossing_frac_mpc_blind"]

        def fmt_pc(v: float) -> str:
            if round(v, 3) != 0:
                return f"{v:.3f}" if v >= 0 else f"$-{abs(v):.3f}$"
            return r"$0$ (exact)" if exact_zero else sci(v)

        def fmt_cross(v: float) -> str:
            if round(v, 4) != 0:
                return f"{v:.4f}"
            # A printed 0.0000 here is a censored zero at 6400 sampled trajectories.
            # results/cem_crossing_bound.json re-measures each such row at 200x that
            # sample; report what it found, which for one row is that the zero was
            # censoring a positive value.
            if ccb and row["instrument"] == "cart":
                m = [b for b in ccb["rows"] if abs(b["x_wall"] - row["knob"]) < 1e-9]
                if m:
                    b = m[0]["initial_state"]
                    if b["crossings_observed"] > 0:
                        return (f"{b['crossing_frac_point']:.1e}\\rlap{{$^\\dagger$}}")
                    return f"$<{b['p_upper_cp95_onesided']:.1e}$"
            n_traj = 6400   # 20 episodes x 5 CEM iterations x 64 samples, one plan each
            return f"$<{cp_upper(0, n_traj):.1e}$"

        pc_mpc = mpc_pc(row["instrument"], row["knob"])
        label = "pendulum" if row["instrument"].startswith("pend") else row["instrument"]
        old = (f"{label} & {row['knob']:.1f} & "
               f"{pc_mpc:.3f} & "
               + (f"{pc_cem:.3f}" if pc_cem >= 0 else f"$-{abs(pc_cem):.3f}$")
               + f" & {row['blind_contact_rate']:.2f} & "
               f"{cr_cem:.4f} & {cr_mpc:.4f} \\\\")
        new = (f"{label} & {row['knob']:.1f} & "
               f"{pc_mpc:.3f} & {fmt_pc(pc_cem)} & "
               + (f"{row['blind_contact_rate']:.2f}"
                  if round(row['blind_contact_rate'], 2) != 0
                  else f"$<{contact_hi:.2f}$")
               + f" & {fmt_cross(cr_cem)} & {cr_mpc:.4f} \\\\")
        if old != new:
            subs.append((f"tab:cem {row['instrument']}@{row['knob']:g}", old, new))

    # ---- tab:axes. arm & reveal-rarity & (1-r)^40 & pass@40 & play_cost & d@40
    # pass@40 zeros are censored at 0/300 gates; play_cost and d@40 zeros are exact
    # (j_blind == j_truth bit for bit); the (1-r)^40 zero has a censored complement.
    # the table's printed labels, keyed by the JSON's arm name
    AXES_LABEL = {
        "wall@4 omitted": "wall@4 omitted",
        "wall@8 omitted": "wall@8 omitted",
        "bias x1.03 (sub-eps)": r"drag bias $\times$1.03 (sub-$\varepsilon$)",
        "bias x2.0 (supra-eps)": r"drag bias $\times$2.0 (supra-$\varepsilon$)",
        "bump@4 amp0.5 (smooth)": r"$C^\infty$ bump@4, amp 0.5",
        "bump@4 amp1.0 (smooth)": r"$C^\infty$ bump@4, amp 1.0",
    }
    n_gates = axes["params"].get("gates", 300)
    for row in axes["rows"]:
        pr, pass_m = row["predicted_pass"], row["pass_rate"]
        pc, d40 = row["play_cost"], row["danger"]
        ci = row.get("pass_rate_ci") or [0.0, wilson_hi(0, n_gates)]

        def fmt(v: float, digits: int, zero_is_exact: bool) -> str:
            if round(v, digits) != 0:
                return f"{v:.{digits}f}" if v >= 0 else f"$-{abs(v):.{digits}f}$"
            return r"$0$ (exact)" if zero_is_exact else sci(v)

        old = (f"{AXES_LABEL[row['arm']]} & {row['rarity']:.4f} & {pr:.4f} & "
               f"{pass_m:.3f} & "
               + (f"{pc:.3f}" if pc >= 0 else f"$-{abs(pc):.3f}$")
               + " & "
               + (f"{d40:.4f}" if d40 >= 0 else f"$-{abs(d40):.4f}$") + " \\\\")
        exact = abs(pc) < 1e-12
        new = (f"{AXES_LABEL[row['arm']]} & {row['rarity']:.4f} & "
               + (f"{pr:.4f}" if round(pr, 4) != 0 else f"$<10^{{-4}}$")
               + " & "
               + (f"{pass_m:.3f}" if round(pass_m, 3) != 0 else f"$<{ci[1]:.3f}$")
               + f" & {fmt(pc, 3, exact)} & {fmt(d40, 4, exact)} \\\\")
        if old != new:
            subs.append((f"tab:axes {row['arm'][:28]}", old, new))

    # ---- tab:eps-sweep: the bias x1.03 zeros are censored at 0/2000
    sweep_n = epsw["params"].get("rollouts", 2000)
    hi = wilson_hi(0, sweep_n)
    cart = [r for r in epsw["rows"] if r["instrument"] == "cart"]
    by_eps: dict[float, dict] = {}
    for r in cart:
        by_eps.setdefault(r["eps"], {})[r["arm"]] = r["rarity"]
    def pick(d: dict, *needles):
        for k, v in d.items():
            if all(n in k for n in needles):
                return v
        return None
    # tab:eps-sweep prints an ABRIDGED four-row subset of the sweep; declared here so
    # that a change to which rows the table shows is caught rather than skipped.
    EPS_PRINTED = {1e-6: "$10^{-6}$", 1e-2: "$10^{-2}$", 0.1: "0.1", 0.3: "0.3"}
    for eps_v, vals in by_eps.items():
        if eps_v not in EPS_PRINTED:
            continue
        w8 = pick(vals, "wall", "8")
        b103 = pick(vals, "1.03")
        b20 = pick(vals, "2.0")
        if w8 is None or b103 is None or b20 is None:
            continue
        old_eps = EPS_PRINTED[eps_v]
        old = f"{old_eps} & {w8:.4f} & {b103:.4f} & {b20:.4f} \\\\"
        new = (f"{old_eps} & {w8:.4f} & "
               + (f"{b103:.4f}" if round(b103, 4) != 0 else f"$<{hi:.4f}$")
               + " & "
               + (f"{b20:.4f}" if round(b20, 4) != 0 else f"$<{hi:.4f}$") + " \\\\")
        if old != new:
            subs.append((f"tab:eps-sweep eps={eps_v:g}", old, new))

    # ---- the convention paragraph must stop being load-bearing
    subs.append((
        "convention paragraph",
        "We do not restate this at each cell, but no zero in this paper should be read as "
        "``never''.",
        "Every zero-valued table cell now carries its own bound, its own interval, or the "
        "note that it is a demonstrated rather than a censored zero, so this convention is "
        "a reading aid and not a load-bearing one."))
    return subs


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not (args.apply or args.dry_run):
        args.dry_run = True

    text = TEX.read_text()
    subs = build_subs()

    # Substitutions can CHAIN: an earlier revision of this script may have left the file
    # in an intermediate state, so a sub's anchor can be absent while another sub still
    # has to produce its replacement. Iterate to a fixed point before judging anything
    # missing, otherwise a legitimate migration reports a false failure.
    applied, already, missing = [], [], []
    remaining = [(n, o, w) for n, o, w in subs if o != w]
    while True:
        progressed = False
        still = []
        for name, old, new in remaining:
            if old in text:
                if text.count(old) != 1:
                    sys.exit(f"ANCHOR NOT UNIQUE ({name}): {old[:80]!r}")
                text = text.replace(old, new)
                applied.append((name, old, new))
                progressed = True
            else:
                still.append((name, old, new))
        remaining = still
        if not progressed:
            break
    for name, old, new in remaining:
        (already.append(name) if new in text else missing.append((name, old)))

    for name, old in missing:
        print(f"  MISSING  {name}\n           anchor: {old[:110]!r}")
    for name, old, new in applied:
        print(f"  CHANGED  {name}\n      from {old[:105]}\n        to {new[:105]}")
    if already:
        print(f"  already applied: {len(already)} anchors")
    if missing:
        sys.exit(f"\n{len(missing)} anchor(s) not found and not already applied; "
                 f"main.tex is not in the state this script expects.")

    print(f"\n{len(applied)} changed, {len(already)} already applied")
    if args.apply:
        TEX.write_text(text)
        print(f"wrote {TEX}")
    else:
        print("dry run: nothing written")


if __name__ == "__main__":
    main()

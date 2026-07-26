"""Audit every numeric table in paper 2 against the result JSONs it came from.

Motivation: the paper's tables were transcribed by hand from the versioned
results. Transcription is exactly the step no reviewer can check without doing
it again, so this script does it mechanically: it parses each `tabular` in
docs/paper2/main.tex, looks up the corresponding row in the JSON the experiment
wrote, and compares every cell AT THE PRINTED PRECISION (a cell printed as
"1.031" must agree to within half of the last printed digit). Derived columns
(the d@N danger products) are recomputed from rarity and play_cost rather than
trusted.

Cross-source checks are deliberate: the MPC play_cost column of the CEM table
must equal the play_cost of the mechanism tables, so a stale copy in either
place is caught.

Exit code 0 iff every checked cell agrees. Run:
  PYTHONPATH=src python scripts/audit_paper2_numbers.py
"""
import json
import math
import pathlib
import re
import sys

_REPO = pathlib.Path(__file__).resolve().parents[1]
TEX = _REPO / "docs" / "paper2" / "main.tex"


def load(name):
    return json.loads((_REPO / "results" / f"{name}.json").read_text())


# --- LaTeX table extraction -------------------------------------------------

def tabular_rows(label):
    """The data rows of the tabular preceding \\label{label}, as cell lists."""
    tex = TEX.read_text()
    at = tex.index("\\label{" + label + "}")
    start = tex.rindex("\\begin{tabular}", 0, at)
    end = tex.index("\\end{tabular}", start)
    body = tex[start:end]
    # booktabs layout: the header sits between \toprule and the first \midrule,
    # so the data rows are everything after it (\bottomrule ends the tabular).
    body = body[body.index("\\midrule") + len("\\midrule"):]
    rows = []
    for raw in body.split("\\\\"):
        line = raw.strip()
        for rule in ("\\toprule", "\\midrule", "\\bottomrule"):
            line = line.replace(rule, "")
        line = line.strip()
        if not line:
            continue
        if "&" not in line:
            # a \multicolumn sub-header spans every column, so it carries no
            # ampersand; keep it, callers use it for context (which instrument)
            if "multicolumn" in line:
                rows.append([line])
            continue
        cells = [c.strip() for c in line.split("&")]
        rows.append(cells)
    return rows


NUM = re.compile(r"-?\d+\.?\d*(?:\s*\\mathrm\{e\}\{-?\d+\}|e-?\d+)?")


def numbers(cell):
    """Every number in a LaTeX cell, with the decimals each was printed to.
    Returns [(value, decimals)]; decimals is None for exponent notation."""
    c = cell
    for junk in ("\\textbf{", "\\emph{", "\\leq", "\\geq", "\\le", "\\ge",
                 "$", "}", "{", "\\,", "\\ ", "~"):
        c = c.replace(junk, "")
    # brace removal above turns "\mathrm{e}{-15}" into "\mathrme-15", so drop
    # the command name itself to recover "3.6e-15"
    c = c.replace("\\mathrm", "")
    c = re.sub(r"e\s*\{?(-?\d+)\}?", r"e\1", c)
    out = []
    for m in re.finditer(r"-?\d+(?:\.\d+)?(?:e-?\d+)?", c):
        tok = m.group(0)
        if "e" in tok:
            out.append((float(tok), None))
        else:
            dec = len(tok.split(".")[1]) if "." in tok else 0
            out.append((float(tok), dec))
    return out


FAILS = []
CHECKS = [0]


def agree(label, row_id, col, printed, actual):
    """printed = (value, decimals) as it appears in the paper."""
    CHECKS[0] += 1
    val, dec = printed
    if dec is None:                       # exponent form: 2 significant digits
        tol = abs(val) * 0.05 + 1e-30
    else:
        tol = 0.5 * 10 ** (-dec) + 1e-12
    if abs(val - actual) > tol:
        FAILS.append(f"{label} [{row_id}] {col}: paper {val} vs data {actual}")


def d(pc, r, n):
    return pc * (1 - r) ** n


# --- tab:danger -------------------------------------------------------------
reach = {row["x_wall"]: row for row in load("continuous_reach")["rows"]}
for cells in tabular_rows("tab:danger"):
    k = numbers(cells[0])[0][0]
    j = reach[k]
    for col, actual in (
            ("rarity", j["rarity"]), ("J_truth", j["j_truth"]),
            ("J_blind", j["j_blind"]), ("J_rand", j["j_random"]),
            ("play_cost", j["play_cost"]), ("blind hit", j["blind_contact_rate"]),
            ("truth hit", j["truth_contact_rate"]),
            ("d@20", d(j["play_cost"], j["rarity"], 20)),
            ("d@40", d(j["play_cost"], j["rarity"], 40)),
            ("d@80", d(j["play_cost"], j["rarity"], 80))):
        i = ["x_wall", "rarity", "J_truth", "J_blind", "J_rand", "play_cost",
             "blind hit", "truth hit", "d@20", "d@40", "d@80"].index(col)
        agree("tab:danger", k, col, numbers(cells[i])[0], actual)

# --- tab:pendulum -----------------------------------------------------------
pend = {row["th_stop"]: row for row in load("continuous_pendulum")["rows"]}
for cells in tabular_rows("tab:pendulum"):
    k = numbers(cells[0])[0][0]
    j = pend[k]
    if "/" in cells[1]:                   # censored zero, printed as 0/3000
        agree("tab:pendulum", k, "rarity count", numbers(cells[1])[0],
              j["rarity"] * 3000)
    else:
        agree("tab:pendulum", k, "rarity", numbers(cells[1])[0], j["rarity"])
    for col, i, actual in (("J_truth", 2, j["j_truth"]),
                           ("J_blind", 3, j["j_blind"]),
                           ("play_cost", 4, j["play_cost"]),
                           ("blind hit", 5, j["blind_contact_rate"]),
                           ("d@40", 6, d(j["play_cost"], j["rarity"], 40))):
        agree("tab:pendulum", k, col, numbers(cells[i])[0], actual)

# --- tab:patch2d ------------------------------------------------------------
p2d = {(row["k1"], row["k2"]): row for row in load("continuous_patch2d")["rows"]}
for cells in tabular_rows("tab:patch2d"):
    key = (numbers(cells[0])[0][0], numbers(cells[1])[0][0])
    j = p2d[key]
    for col, i, actual in (
            ("r1", 2, j["r1"]), ("r2", 3, j["r2"]),
            ("r_union", 4, j["r_either"]),
            ("J_truth", 5, j["j_truth"]), ("play_cost", 6, j["play_cost"]),
            ("d@40 P1", 7, d(j["play_cost"], j["r1"], 40)),
            ("d@40 P2", 8, d(j["play_cost"], j["r2"], 40)),
            # the joint factor is the law at the union event, NOT the product of
            # the per-mode factors (that would assume within-rollout independence)
            ("d@40 joint", 9, d(j["play_cost"], j["r_either"], 40))):
        agree("tab:patch2d", key, col, numbers(cells[i])[0], actual)

# --- tab:cem (with the cross-source play_cost check) ------------------------
cem = {(r["instrument"], r["knob"] if not isinstance(r["knob"], list)
        else tuple(r["knob"])): r for r in load("continuous_cem")["rows"]}
for cells in tabular_rows("tab:cem"):
    inst = cells[0].strip()
    knob = numbers(cells[1])[0][0]
    j = cem[(inst if inst != "pendulum" else "pend", knob)]
    mech = reach[knob] if inst == "cart" else pend[knob]
    agree("tab:cem", (inst, knob), "pc MPC (cross-source)",
          numbers(cells[2])[0], mech["play_cost"])
    for col, i, actual in (("pc CEM", 3, j["play_cost_blind_cem"]),
                           ("contact CEM", 4, j["blind_contact_rate"]),
                           ("crossing CEM", 5, j["crossing_frac_cem_blind"]),
                           ("crossing MPC", 6, j["crossing_frac_mpc_blind"])):
        agree("tab:cem", (inst, knob), col, numbers(cells[i])[0], actual)

# --- tab:axes ---------------------------------------------------------------
axes = load("continuous_axes")["rows"]
N_AXES_ROLLOUTS = 2000
for cells in tabular_rows("tab:axes"):
    # a censored extreme is printed as a raw count (e.g. 0/2000), not a rate
    if "/" in cells[1]:
        k, n = (v for v, _ in numbers(cells[1]))
        r = k / n
        assert n == N_AXES_ROLLOUTS
    else:
        r = numbers(cells[1])[0][0]
    cand = [a for a in axes if abs(a["rarity"] - r) < 5e-4]
    if len(cand) != 1:
        FAILS.append(f"tab:axes: {cells[0]!r} matched {len(cand)} arms by rarity")
        continue
    j = cand[0]
    for col, i, actual in (("reveal-rarity", 1,
                            j["rarity"] * (N_AXES_ROLLOUTS if "/" in cells[1] else 1)),
                           ("(1-r)^40", 2, j["predicted_pass"]),
                           ("pass@40", 3, j["pass_rate"]),
                           ("play_cost", 4, j["play_cost"]),
                           ("d@40", 5, d(j["play_cost"], j["rarity"], 40))):
        agree("tab:axes", j["arm"], col, numbers(cells[i])[0], actual)

# --- tab:eps-sweep (cart rows) ---------------------------------------------
eps_rows = load("continuous_eps_sweep")["rows"]


def eps_rarity(arm_key, eps):
    hits = [r for r in eps_rows if r["instrument"] == "cart"
            and arm_key in r["arm"] and abs(r["eps"] - eps) < 1e-12]
    return hits[0]["rarity"] if len(hits) == 1 else None


for cells in tabular_rows("tab:eps-sweep"):
    eps = numbers(cells[0])[0][0]
    if "10^{-6}" in cells[0]:
        eps = 1e-6
    elif "10^{-2}" in cells[0]:
        eps = 1e-2
    for col, i, arm in (("wall@8", 1, "wall@8"),
                        ("bias x1.03", 2, "1.03"),
                        ("bias x2.0", 3, "2.0")):
        actual = eps_rarity(arm, eps)
        if actual is None:
            FAILS.append(f"tab:eps-sweep: no unique cart row for {arm} at eps={eps}")
            continue
        agree("tab:eps-sweep", eps, col, numbers(cells[i])[0], actual)

# --- tab:mitigation ---------------------------------------------------------
mit = load("continuous_mitigation")["rows"]
inst = None
for cells in tabular_rows("tab:mitigation"):
    if "multicolumn" in cells[0]:
        # the sub-header naming the instrument: "\emph{cart} ($x_wall$)"
        inst = "cart" if "cart" in cells[0] else "pend"
        continue
    knob = numbers(cells[0])[0][0]
    # cart x_wall=2.0 and pendulum th_stop=2.0 collide, so the instrument from
    # the sub-header is part of the key
    cand = [r for r in mit if abs(r["knob"] - knob) < 1e-9
            and r["instrument"].startswith(inst)]
    j = cand[0] if len(cand) == 1 else None
    if j is None:
        FAILS.append(f"tab:mitigation: {inst} knob {knob} matched {len(cand)} rows")
        continue
    for col, i, actual in (("pc_blind", 1, j["play_cost_blind"]),
                           ("pc_mit", 2, j["play_cost_mitigated"]),
                           ("first contact", 3, j["mean_first_contact_step"])):
        agree("tab:mitigation", knob, col, numbers(cells[i])[0], actual)

# --- tab:patch2d-mitigation ------------------------------------------------
mitp = {(r["k1"], r["k2"]): r for r in load("continuous_mitigation_patch2d")["rows"]}
for cells in tabular_rows("tab:patch2d-mitigation"):
    ks = numbers(cells[0])
    key = (ks[0][0], ks[1][0])
    j = mitp[key]
    for col, i, actual in (("pc_blind", 1, j["play_cost_blind"]),
                           ("pc_mit", 2, j["play_cost_mitigated"]),
                           ("mean viol", 3, j["mean_violations"]),
                           ("first contact", 4, j["mean_first_contact_step"])):
        agree("tab:patch2d-mitigation", key, col, numbers(cells[i])[0], actual)

# --- tab:smooth -------------------------------------------------------------
smooth = {(r["model"], r["trained_on"]): r for r in load("continuous_smooth_probe")["rows"]}
for cells in tabular_rows("tab:smooth"):
    # the JSON stores the same strings the table prints
    key = [k for k in smooth
           if k[0] == cells[0].strip() and k[1] == cells[1].strip()]
    if len(key) != 1:
        FAILS.append(f"tab:smooth: {cells[0]}/{cells[1]} matched {len(key)} rows")
        continue
    j = smooth[key[0]]
    mean, mx = numbers(cells[2])[:2]
    agree("tab:smooth", key[0], "off-mode mean", mean, j["off_mode_mean"])
    agree("tab:smooth", key[0], "off-mode max", mx, j["off_mode_max"])
    agree("tab:smooth", key[0], "probe err", numbers(cells[3])[0],
          j["wall_probe_max_err"])
    for col, i, field in (("gate 1e-9", 4, "gate_pass_eps1e-09"),
                          ("gate 1e-2", 5, "gate_pass_eps0.01")):
        printed_pass = "PASS" in cells[i].upper()
        CHECKS[0] += 1
        if printed_pass != bool(j[field]):
            FAILS.append(f"tab:smooth [{key[0]}] {col}: paper "
                         f"{'PASS' if printed_pass else 'fail'} vs data {j[field]}")

# --- synthesis counts cited in prose ---------------------------------------
def synth_cells(name):
    return load(name)["cells"]


disc = [c for f in ("continuous_synthesis_patch2d_mini_k3_7",
                    "continuous_synthesis_patch2d_large_k3_7",
                    "continuous_synthesis_patch2d_mini_k5_9",
                    "continuous_synthesis_patch2d_large_k5_9")
        for c in synth_cells(f) if c["arm"] == "incomplete"]
mode_present = [c for c in disc
                if any(c["sample_contains_mode_per"].values())]
see_one = [c for c in disc
           if sum(c["sample_contains_mode_per"].values()) == 1]
miss_both = [c for c in disc if not any(c["sample_contains_mode_per"].values())]
repaired = [c for c in mode_present if c["gate_passed"]]
certified_missboth = [c for c in miss_both if c["gate_passed"]]

PROSE = [("76 mode-containing disc seeds", len(mode_present), 76),
         ("66 see-one-miss-the-other", len(see_one), 66),
         ("80 incomplete disc seeds", len(disc), 80),
         ("4/80 miss-both certified", len(certified_missboth), 4),
         ("0 repaired among mode-containing", len(repaired), 0)]
for name, got, want in PROSE:
    CHECKS[0] += 1
    if got != want:
        FAILS.append(f"prose count {name}: paper {want} vs data {got}")

abl = [c for f in ("continuous_synthesis_patch2dsq_mini_k3_7",
                   "continuous_synthesis_patch2dsq_large_k3_7")
       for c in synth_cells(f) if c["arm"] == "incomplete"]
gui = [c for f in ("continuous_synthesis_patch2d_mini_k3_7_pv-region_it15",
                   "continuous_synthesis_patch2d_large_k3_7_pv-region_it15")
       for c in synth_cells(f) if c["arm"] == "incomplete"]
for name, cells, want in (("square ablation 0/40", abl, 40),
                          ("guided ablation 0/40", gui, 40)):
    CHECKS[0] += 1
    n_present = len([c for c in cells
                     if any(c["sample_contains_mode_per"].values())])
    n_pass = len([c for c in cells if c["gate_passed"]])
    if (n_present, n_pass) != (want, 0):
        FAILS.append(f"prose count {name}: paper {want}/0 vs data "
                     f"{n_present}/{n_pass}")

CHECKS[0] += 1
if len(mode_present) + len(abl) + len(gui) != 156:
    FAILS.append(f"pooled 0/156: data gives "
                 f"{len(mode_present) + len(abl) + len(gui)}")


def claim(name, ok, detail=""):
    CHECKS[0] += 1
    if not ok:
        FAILS.append(f"claim {name}: FALSE ({detail})")


# --- prose claims that are not table cells ---------------------------------
# "the full arm is clean (20/20 per cell, both sizes)" on PatchField2D
for f in ("continuous_synthesis_patch2d_mini_k3_7",
          "continuous_synthesis_patch2d_large_k3_7",
          "continuous_synthesis_patch2d_mini_k5_9",
          "continuous_synthesis_patch2d_large_k5_9"):
    full = [c for c in synth_cells(f) if c["arm"] == "full"]
    claim(f"patch2d full arm clean [{f[-14:]}]",
          len(full) == 20 and all(c["gate_passed"] for c in full),
          f"{sum(c['gate_passed'] for c in full)}/{len(full)}")

# "the only certified incomplete artifacts were the 4/80 miss-both seeds ...
#  exploited at play_cost 1.095, contact rate 1.0"
pcs = [c.get("play_cost") for c in certified_missboth]
contacts = [c.get("play_contact_rate") for c in certified_missboth]
claim("miss-both play_cost 1.095",
      all(pc is not None and abs(pc - 1.095) < 5e-4 for pc in pcs), str(pcs))
claim("miss-both contact 1.0",
      all(ct == 1.0 for ct in contacts), str(contacts))

# GPT-5.x repair: cart 20/20 on the headline cell, pendulum 62/62 pooled -> 82/82
cart_present = [c for f in ("continuous_synthesis_mini_xwall8",
                            "continuous_synthesis_large_xwall8")
                for c in synth_cells(f)
                if c["arm"] == "incomplete" and c["sample_contains_wall"]]
pend_present = [c for f in ("continuous_synthesis_pendulum_mini_thstop1.4",
                            "continuous_synthesis_pendulum_large_thstop1.4",
                            "continuous_synthesis_pendulum_mini_thstop1",
                            "continuous_synthesis_pendulum_large_thstop1")
                for c in synth_cells(f)
                if c["arm"] == "incomplete" and c["sample_contains_wall"]]
cart_rep = [c for c in cart_present if c["gate_passed"]
            and (c["wall_blindness"] or 0) == 0.0]
pend_rep = [c for c in pend_present if c["gate_passed"]
            and (c["wall_blindness"] or 0) == 0.0]
claim("cart repair 20/20", (len(cart_present), len(cart_rep)) == (20, 20),
      f"{len(cart_rep)}/{len(cart_present)}")
claim("pendulum repair 62/62", (len(pend_present), len(pend_rep)) == (62, 62),
      f"{len(pend_rep)}/{len(pend_present)}")
claim("pooled repair 82/82",
      len(cart_rep) + len(pend_rep) == 82 == len(cart_present) + len(pend_present),
      f"{len(cart_rep) + len(pend_rep)}/{len(cart_present) + len(pend_present)}")

# mode-absent -> blind & exploited at play_cost 0.999 (cart), 20/20 across sizes
cart_absent = [c for f in ("continuous_synthesis_mini_xwall8",
                           "continuous_synthesis_large_xwall8")
               for c in synth_cells(f)
               if c["arm"] == "incomplete" and not c["sample_contains_wall"]]
claim("cart mode-absent 20/20 certified-blind-exploited",
      len(cart_absent) == 20
      and all(c["gate_passed"] and c["wall_blindness"] == 1.0
              and abs(c["play_cost"] - 0.999) < 5e-4 for c in cart_absent),
      f"n={len(cart_absent)}")

# mitigation: "exactly one violation suffices on every one of the 11 rows",
# "pc_mit never exceeds 0.81"
claim("mitigation 1 violation on all 11 rows",
      all(abs(r["mean_violations"] - 1.0) < 1e-9 for r in mit) and len(mit) == 11,
      str(sorted({r["mean_violations"] for r in mit})))
claim("pc_mit <= 0.81 on all rows",
      max(r["play_cost_mitigated"] for r in mit) <= 0.81,
      f"max {max(r['play_cost_mitigated'] for r in mit):.3f}")

# CEM: paired t-interval includes zero on all 11 rows; crossing_CEM < crossing_MPC
cem_rows = load("continuous_cem")["rows"]
claim("CEM t-interval includes zero on all 11 rows",
      len(cem_rows) == 11
      and not any(r["play_cost_blind_cem_paired"]["excludes_zero"]
                  for r in cem_rows),
      str([r["knob"] for r in cem_rows
           if r["play_cost_blind_cem_paired"]["excludes_zero"]]))
claim("CEM crossing < MPC crossing on every row",
      all(r["crossing_frac_cem_blind"] < r["crossing_frac_mpc_blind"]
          for r in cem_rows))
claim("CEM pc within [-0.0213, 0.0248]",
      all(-0.0213 - 5e-5 <= r["play_cost_blind_cem"] <= 0.0248 + 5e-5
          for r in cem_rows),
      f"range [{min(r['play_cost_blind_cem'] for r in cem_rows):.4f}, "
      f"{max(r['play_cost_blind_cem'] for r in cem_rows):.4f}]")

# smooth probe: "four contact rows out of 3200"
sm = load("continuous_smooth_probe")
claim("smooth probe 4 contact rows of 3200",
      (sm.get("n_contact_rows"), sm.get("n_rows")) == (4, 3200),
      f"{sm.get('n_contact_rows')}/{sm.get('n_rows')}")

# patch2d artifact audit: 0 artifacts ENCODE a seen patch, 34 merely contain one
audit = load("patch2d_artifact_audit")["files"]
KEYMAP = {"patch1": "p1", "patch2": "p2"}
contains = encodes = 0
for k in ("disc_large_k3_7", "disc_mini_k3_7", "disc_large_k5_9", "disc_mini_k5_9"):
    for c in audit[k]["cells"]:
        seen = [KEYMAP[n] for n, v in (c.get("modes_in_sample") or {}).items()
                if v and n in KEYMAP]
        if not seen:
            continue
        cov = max((c.get(f"cover_{p}") or 0) for p in seen)
        if cov > 0.9:
            contains += 1
            if (c.get("area_frac") or 1.0) <= 0.03:
                encodes += 1
claim("34/76 contain a seen patch", contains == 34, str(contains))
# the paper's partial-repair numbers live on the see-one-miss-the-other branch
_see_one, _cont1, _sel = [], [], []
for k in ("disc_large_k3_7", "disc_mini_k3_7", "disc_large_k5_9", "disc_mini_k5_9"):
    for c in audit[k]["cells"]:
        per = c.get("modes_in_sample") or {}
        seen = [KEYMAP[n] for n, v in per.items() if v and n in KEYMAP]
        unseen = [KEYMAP[n] for n, v in per.items() if not v and n in KEYMAP]
        if len(seen) == 1 and len(unseen) == 1:
            cs = c.get(f"cover_{seen[0]}") or 0
            cu = c.get(f"cover_{unseen[0]}") or 0
            af = c.get("area_frac")
            _see_one.append(c)
            if cs > 0.9:
                _cont1.append(af)
                if cu < 0.1:
                    _sel.append((c["seed"], c["class"], af))
PATCH_SHARE = 3.141592653589793 / (16 * 16)
claim("66 see-one seeds", len(_see_one) == 66, str(len(_see_one)))
claim("28 of them contain the seen patch", len(_cont1) == 28, str(len(_cont1)))
claim("their area spans 15x-81x the patch (median 61x)",
      (round(min(_cont1) / PATCH_SHARE) == 15
       and round(max(_cont1) / PATCH_SHARE) == 81
       and round(sorted(_cont1)[len(_cont1) // 2] / PATCH_SHARE) == 61),
      f"{min(_cont1)/PATCH_SHARE:.1f}x-{max(_cont1)/PATCH_SHARE:.1f}x")
claim("exactly one patch-selective artifact, a half-plane at 31x",
      len(_sel) == 1 and _sel[0][0] == 180000 and _sel[0][1] == "halfplane"
      and round(_sel[0][2] / PATCH_SHARE) == 31, str(_sel))

# --- Prop 8's hypothesis: the truth planner's knob-invariance regime --------
cert = load("truth_plan_invariance_certificate")["rows"]
in_sweep = [r for r in cert if r["in_sweep"]]
claim("the invariance certificate holds at every sweep knob",
      all(r["certificate"] for r in in_sweep) and len(in_sweep) == 7,
      str([(r["x_wall"], r["certificate"]) for r in in_sweep]))
claim("argmax candidate never exceeds x = 0.344 in the sweep",
      max(r["argmax_max_x_over_run"] for r in in_sweep) < 0.345,
      f"{max(r['argmax_max_x_over_run'] for r in in_sweep):.3f}")
claim("clamping candidates lose by >= 5.25 in the sweep",
      min(r["min_margin_argmax_minus_best_clamping"] for r in in_sweep) >= 5.25,
      f"{min(r['min_margin_argmax_minus_best_clamping'] for r in in_sweep):.3f}")
_m = {r["x_wall"]: r["min_margin_argmax_minus_best_clamping"] for r in cert}
claim("the margin contracts to 4.12 at 11 and 0.51 at 12",
      abs(_m[11.0] - 4.12) < 0.02 and abs(_m[12.0] - 0.51) < 0.02,
      f"{_m[11.0]:.2f}, {_m[12.0]:.2f}")
claim("the certificate fails at 12.5 (argmax itself reaches the wall)",
      not [r for r in cert if r["x_wall"] == 12.5][0]["certificate"])

regime = load("truth_planner_knob_regime")["rows"]
inside = [r for r in regime if r["x_wall"] <= 12.0]
outside = [r for r in regime if r["x_wall"] > 12.0]
claim("truth J is bit-identical for x_wall <= 12 (the invariance regime)",
      len({r["j_truth"] for r in inside}) == 1
      and all(r["truth_contact_rate"] == 0.0 for r in inside),
      str(sorted({r["j_truth"] for r in inside})))
claim("truth J as quoted inside the regime",
      abs(next(iter({r["j_truth"] for r in inside})) - 17.659688408965) < 5e-12)
claim("the plan flips past x_right = 12 (contact 1.00, J jumps)",
      all(r["truth_contact_rate"] == 1.0 for r in outside)
      and min(r["j_truth"] for r in outside) > 30,
      str([(r["x_wall"], round(r["j_truth"], 2)) for r in outside]))

# --- Corollary: the gate density constant, analytic vs Monte Carlo -----------
dens = load("gate_density_constant")
claim("analytic gate density is 5/6", abs(dens["c_analytic"] - 5 / 6) < 1e-12)
claim("Monte Carlo confirms it within 2%",
      abs(dens["c_monte_carlo"] - dens["c_analytic"]) / dens["c_analytic"] < 0.02,
      f"{dens['c_monte_carlo']:.6f}")
claim("plant Lipschitz constant is the 1.27 the paper quotes",
      abs(dens["L_plant_sup_metric"] - 1.27) < 5e-3)
_hide = {round(r["eta"], 2): r["L_min_delta0.5"] for r in dens["hiding_table"]}
for eta, want in ((0.1, 0.33), (0.5, 1.78), (4.2, 15.2)):
    claim(f"hiding L bound as quoted for eta={eta}",
          abs(_hide[eta] - want) < 0.05, f"{_hide[eta]:.3f}")

# --- Proposition (eps-invariance): the threshold and its predictions --------
# eps* = min over mode-firing rollouts of the max per-contact disagreement. The
# paper's table quotes eps* per arm and the first grid eps at or above it, and
# claims reveal/firing is exactly 1.000 below eps*: check all three.
eps_thr = load("eps_invariance_threshold")
GRID_EPS = eps_thr["grid"]
# The table now quotes eps* computed on the SWEEP'S OWN stream (--seed 10000),
# because a threshold from one sample compared against dips in another is not a
# prediction; in-sample it is an identity. Values from the paper's Table epsstar.
QUOTED = {"cart wall@8": (0.3959, None),
          "cart wall@4": (0.1137, 0.3),
          "pendulum stop@1.0": (0.0791, 0.1),
          "pendulum stop@1.4": (0.0805, 0.1)}
for row in eps_thr["rows"]:
    want_star, want_break = QUOTED[row["arm"]]
    claim(f"eps* as quoted for {row['arm']}",
          abs(row["eps_star"] - want_star) < 5e-5, f"{row['eps_star']:.4f}")
    claim(f"first grid eps at/above eps* for {row['arm']}",
          row["first_grid_eps_above_eps_star"] == want_break,
          str(row["first_grid_eps_above_eps_star"]))
    below = [r for e, r in zip(GRID_EPS, row["reveal_over_firing"])
             if e < row["eps_star"]]
    claim(f"reveal/firing is exactly 1 below eps* for {row['arm']}",
          all(r == 1.0 for r in below), str(below))

# --- Proposition (fence covering number) ------------------------------------
mit_rows = load("continuous_mitigation")["rows"]
claim("1D: covering number 1 => exactly one violation on all 11 rows",
      all(r["mean_violations"] == 1.0 for r in mit_rows) and len(mit_rows) == 11)
# the covering number is READ from the brute-force script, not recomputed here:
# a hand-computed constant is exactly what went wrong once (13 for 7).
_circ = load("circle_covering_number")
_cov = _circ["metric_centres_on_circle"]["n"]
claim("brute force verifies the on-circle covering number is 7", _cov == 7,
      str(_cov))
claim("its cover is verified and one fewer fails",
      _circ["metric_centres_on_circle"]["verified_cover"]
      and _circ["metric_centres_on_circle"]["n_minus_1_fails"])
claim("free-centre optimum is 6", _circ["metric_centres_free"]["n"] == 6,
      str(_circ["metric_centres_free"]["n"]))
claim("closed form agrees with brute force",
      _circ["closed_form_n"] == _cov)
claim("the classic eps=R case is 3 (a different quantity from the bound)",
      _circ["classic_eps_equals_R_n"] == 3)
# and the arc fractions the paper quotes
_half = _circ["metric_centres_on_circle"]["half_width"]
for v, want in ((1.05, 17), (2.65, 43), (4.25, 68)):
    frac = round(100 * v * 2 * _half / (2 * math.pi))
    claim(f"arc fraction for {v} fences is {want}%", frac == want, f"{frac}%")
for r in load("continuous_mitigation_patch2d")["rows"]:
    claim(f"2D violations under the covering bound {(r['k1'], r['k2'])}",
          r["mean_violations"] <= _cov, f"{r['mean_violations']} vs {_cov}")

# --- Proposition (knob-invariance): the affine identity, to the digit -------
# play_cost(k) = J_truth/(J_truth-J_rand) - J_blind(k)/(J_truth-J_rand) whenever
# the two baselines are knob-free. The paper quotes both the predicted play_cost
# error and the predicted spread, so check the identity itself on both variants.
for label, name, tol_pred, tol_spread in (
        ("cart sharp", "continuous_reach_sharp", 1e-9, 1e-8),
        ("cart default", "continuous_reach", 1e-5, 1e-5)):
    rows = load(name)["rows"]
    jt = {r["j_truth"] for r in rows}
    claim(f"{label}: J_truth is knob-independent (bit-identical)", len(jt) == 1,
          f"{len(jt)} distinct values")
    JT = next(iter(jt))
    JR = max(r["j_random"] for r in rows)
    c0 = JT / (JT - JR)
    worst = max(abs((c0 - r["j_blind"] / (JT - JR)) - r["play_cost"])
                for r in rows)
    claim(f"{label}: affine identity predicts play_cost", worst < tol_pred,
          f"worst {worst:.2e}")
    pred = ((max(r["j_blind"] for r in rows) - min(r["j_blind"] for r in rows))
            / (JT - JR))
    meas = (max(r["play_cost"] for r in rows)
            - min(r["play_cost"] for r in rows))
    claim(f"{label}: predicted spread matches measured",
          abs(pred - meas) < tol_spread, f"pred {pred:.6e} vs meas {meas:.6e}")
    # the paper quotes both figures: 3.9e-9 (sharp) and 1.2e-4 (default)
    jr_spread = (max(r["j_random"] for r in rows)
                 - min(r["j_random"] for r in rows))
    want = 3.9e-9 if "sharp" in name else 1.2e-4
    claim(f"{label}: J_rand knob-variation as quoted ({want:.1e})",
          abs(jr_spread - want) < 0.05 * want, f"{jr_spread:.3e}")

# --- Proposition (coverage certificate): the two instantiated bounds ---------
cov = load("gate_coverage_certificate")
_reg = {r["regime"].split(" (")[0]: r for r in cov["regimes"]}
claim("rigorous regime: rho = 1.165 and bound 2.97 (with the COMPUTED ball-mass "
      "factor, 0.950 * 2^-DIM for this sheared U)",
      abs(_reg["one step per rollout"]["rho"] - 1.165) < 0.006
      and abs(_reg["one step per rollout"]["uniform_bound"] - 2.969) < 0.02,
      str(_reg["one step per rollout"]))
claim("all-steps regime: rho = 0.310 and bound 0.797",
      abs(_reg["all steps"]["rho"] - 0.310) < 0.006
      and abs(_reg["all steps"]["uniform_bound"] - 0.797) < 0.02,
      str(_reg["all steps"]))
claim("both bounds are below the hard mode's own disagreement (4.2)",
      all(r["uniform_bound"] < cov["wall_probe_error"] for r in cov["regimes"]))
claim("the wall's error is excluded only for pairs with L <= 1.80",
      abs(cov["max_L_excluding_wall_error"] - 1.798) < 0.005,
      f"{cov['max_L_excluding_wall_error']:.3f}")
claim("the corner hypothesis holds: U's narrowest extent 0.6 >= rho/2 = 0.583",
      0.6 >= _reg["one step per rollout"]["rho"] / 2)
claim("the certificate's c and L match the corollary's", 
      abs(cov["c"] - 5 / 6) < 1e-12 and abs(cov["L_plant"] - 1.27) < 5e-3)

# --- the 1D repair count, ALL cells (peer review 2026-07-25 caught 106/106
# excluding the x_wall=4 cell, where 2 of 5 mode-present seeds are not repaired)
_1d_files = ["continuous_synthesis_mini_xwall8", "continuous_synthesis_large_xwall8",
             "continuous_synthesis_large_xwall8_off20",
             "continuous_synthesis_mini_xwall4",
             "continuous_synthesis_pendulum_mini_thstop1.4",
             "continuous_synthesis_pendulum_large_thstop1.4",
             "continuous_synthesis_pendulum_large_thstop1.4_off20",
             "continuous_synthesis_pendulum_mini_thstop1",
             "continuous_synthesis_pendulum_large_thstop1"]
_present = _repaired = 0
for _f in _1d_files:
    for c in synth_cells(_f):
        if c["arm"] == "incomplete" and c["sample_contains_wall"]:
            _present += 1
            if c["gate_passed"] and (c["wall_blindness"] or 0) == 0.0:
                _repaired += 1
claim("GPT-5.x 1D repair is 109/111 over ALL cells, not 106/106",
      (_repaired, _present) == (109, 111), f"{_repaired}/{_present}")
_x4 = [c for c in synth_cells("continuous_synthesis_mini_xwall4")
       if c["arm"] == "incomplete" and c["sample_contains_wall"]]
claim("the x_wall=4 cell is 3/5 (the two exceptions)",
      len(_x4) == 5 and sum(1 for c in _x4 if c["gate_passed"]
                            and (c["wall_blindness"] or 0) == 0.0) == 3)

# --- CEM: only the zero-crossing rows instantiate the low-query-reach branch --
_cem = load("continuous_cem")["rows"]
_zero = [r for r in _cem if r["crossing_frac_cem_blind"] == 0.0]
claim("exactly two CEM rows have crossing fraction exactly zero",
      len(_zero) == 2 and all(r["instrument"] == "cart" for r in _zero),
      str([(r["instrument"], r["knob"]) for r in _zero]))

# --- the universal two-action Jacobian and the query-mass measurement --------
_qm = load("certified_region_query_mass")["rows"]
_blind = [r for r in _qm if "blind" in r["planner"]][0]
_truth = [r for r in _qm if r["planner"] == "truth"][0]
claim("certified region carries 1.9% of the blind planner's queries",
      abs(_blind["inside_fraction"]["1.0,1.0"] - 0.019) < 0.002,
      f"{_blind['inside_fraction']['1.0,1.0']:.4f}")
claim("larger region carries 7.8% of them",
      abs(_blind["inside_fraction"]["3.0,2.0"] - 0.078) < 0.002,
      f"{_blind['inside_fraction']['3.0,2.0']:.4f}")
claim("truth planner: 2.3% and 7.3%",
      abs(_truth["inside_fraction"]["1.0,1.0"] - 0.023) < 0.002
      and abs(_truth["inside_fraction"]["3.0,2.0"] - 0.073) < 0.002,
      str(_truth["inside_fraction"]))
# the universal Jacobian: gain^2 dt^3 for the paper's constants
claim("universal two-action Jacobian equals gain^2 dt^3 = 0.009",
      abs(3.0 ** 2 * 0.1 ** 3 - 0.009) < 1e-12)

# --- density at step t, and the tightness validation -------------------------
dst = load("gate_density_step_t")
claim("|det M| = 0.009 and the parallelogram (2-D) density is 27.78",
      abs(abs(dst["det_M"]) - 0.009) < 1e-9
      and abs(dst["parallelogram_density_2d"] - 27.7778) < 1e-3)
claim("the 3-D density divides by 2*a_max (the action factor the first version "
      "dropped)",
      all(ls["alpha"] <= dst["parallelogram_density_2d"] / 2.0
          for r in dst["rows"] for ls in r["level_sets"]))
_certs = [(r["step"], ls["alpha"], ls["certificate"])
          for r in dst["rows"] for ls in r["level_sets"] if ls["certificate"]]
claim("with a shape-free ball-mass bound, N = 40 certifies NOTHING on any step-t "
      "level set (the retracted 3.67 came from an unjustified 2^-DIM factor)",
      _certs == [] and dst["best"] is None, str(len(_certs)))
_vols = {(r["step"], ls["alpha"]): ls["vol_sa"]
         for r in dst["rows"] for ls in r["level_sets"]}
claim("step-20 {p>=0.05} has volume 3.09 in (x,v,a)",
      abs(_vols[(20, 0.05)] - 3.087) < 0.02, f"{_vols[(20, 0.05)]:.3f}")
claim("step-40 {p>=0.02} has volume 6.13 and step-80 {p>=0.01} has 6.21",
      abs(_vols[(40, 0.02)] - 6.125) < 0.02
      and abs(_vols[(80, 0.01)] - 6.206) < 0.02,
      f"{_vols[(40, 0.02)]:.3f}, {_vols[(80, 0.01)]:.3f}")
val = {round(r["rho"], 3): r for r in load("gate_coverage_validation")["rows"]}
claim("validation: 200/200 gates cover at the licensed net radius 1.0",
      val[1.0]["covered"] == 200, str(val[1.0]["covered"]))
claim("validation: 198/200 at radius 0.667, which the certificate declines "
      "(N >= 42 > 40) -- conservative by ~5% in N",
      val[0.667]["covered"] == 198 and val[0.667]["n_needed_certificate"] == 42,
      f"{val[0.667]['covered']}, N={val[0.667]['n_needed_certificate']}")
claim("validation: coverage collapses to 128/200 at 0.50 and 10/200 at 0.40",
      val[0.5]["covered"] == 128 and val[0.4]["covered"] == 10,
      f"{val[0.5]['covered']}, {val[0.4]['covered']}")
claim("the validation grid is honest: every cell at most rho wide",
      all(r["cell_width"] <= r["rho"] + 1e-12
          for r in load("gate_coverage_dependent")["rows"]))

# --- the invariance certificate's SCOPE, not just its verdict -----------------
_inv = load("truth_plan_invariance_certificate")
claim("the invariance certificate covers the harness's 20 episodes per knob",
      _inv["params"]["episodes"] == 20, str(_inv["params"]["episodes"]))
claim("uniqueness (C3) is a diagnostic and does in fact fail -- ties occur, and "
      "the certificate rests on C1, C2 and the knob-independent tie-break",
      any(not r.get("C3_argmax_unique", True) for r in _inv["rows"]))
claim("every sweep knob is certified", all(r["certificate"] for r in _inv["rows"]
                                           if r["in_sweep"]))

# --- the eps-flatness RATE: the population statement behind eps* ---------------
_rt = {r["arm"]: r for r in load("eps_flatness_rate")["rows"]}
claim("the running minimum of D falls and does not settle (no positive floor): "
      "wall@4 goes 0.420 at 25 firing rollouts to 0.041 at 3200",
      abs(dict(_rt["cart wall@4"]["running_min"])[25] - 0.4195) < 5e-4
      and abs(dict(_rt["cart wall@4"]["running_min"])[3200] - 0.0405) < 5e-4)
claim("the measured tail exponents are 2.57 (wall@4) and 2.10 (stop@1.0), both at "
      "or above the proved 2",
      abs(_rt["cart wall@4"]["measured_exponent"] - 2.57) < 0.02
      and abs(_rt["pendulum stop@1.0"]["measured_exponent"] - 2.10) < 0.02
      and all(r["measured_exponent"] >= 2.0 for r in _rt.values()),
      f"{_rt['cart wall@4']['measured_exponent']:.2f}, "
      f"{_rt['pendulum stop@1.0']['measured_exponent']:.2f}")
claim("the proved constant is C = 222 and its bound holds at every grid point on "
      "both arms",
      all(abs(r["C_quadratic"] - 222.2) < 0.2 and r["bound_holds_on_grid"]
          for r in _rt.values()))
claim("M <= 16.67 bounds the position density with no extra hypothesis",
      all(abs(r["M_position_density_bound"] - 16.667) < 0.01 for r in _rt.values()))

# --- the partition certificate: the recovery, and it must stay exact ----------
_part = load("gate_partition_certificate")
claim("partition route: the largest admissible K at N = 40 is 8",
      _part["max_admissible_K_exact"] == 8,
      str(_part["max_admissible_K_exact"]))
claim("K = 8 has failure probability 0.0383 and K = 9 would exceed delta",
      abs(8 * (7 / 8) ** 40 - 0.0383) < 5e-4 and 9 * (8 / 9) ** 40 > 0.05)
_ba = _part["exact_best"]
claim("the optimal split is (n_y, n_v, n_a) = (2, 1, 4)",
      (_ba["n_y"], _ba["n_v"], _ba["n_a"]) == (2, 1, 4),
      str((_ba["n_y"], _ba["n_v"], _ba["n_a"])))
claim("it gives rho = 0.600 and certifies 1.534",
      abs(_ba["rho"] - 0.600) < 1e-9
      and abs(_ba["uniform_bound"] - 1.534) < 5e-4,
      f"{_ba['rho']:.3f} -> {_ba['uniform_bound']:.4f}")
claim("rho is pinned by Delta_v = 2V = 0.6, the whole reachable velocity range",
      abs(_ba["cell_extents"][1] - 0.6) < 1e-9 and _ba["n_v"] == 1)
claim("the net radius accounts for the shear: Delta_y + dt*Delta_v <= rho",
      _ba["cell_extents"][0] + 0.1 * _ba["cell_extents"][1] <= _ba["rho"] + 1e-12)
claim("the partition route beats the packing route by a factor ~2",
      _ba["uniform_bound"] < 0.55 * 2.969,
      f"{_ba['uniform_bound']:.3f} vs 2.969")

# --- the partition certificate's all-steps arm, and its falsification test -----
_bb = _part["measured_best"]
claim("all-steps partition: K = 36 at (3, 2, 6), rho = 0.363, bound 0.933",
      _bb["K"] == 36 and (_bb["n_y"], _bb["n_v"], _bb["n_a"]) == (3, 2, 6)
      and abs(_bb["rho"] - 0.3633) < 5e-4
      and abs(_bb["uniform_bound"] - 0.9329) < 5e-4,
      f"K={_bb['K']} rho={_bb['rho']:.4f} bound={_bb['uniform_bound']:.4f}")
claim("its worst per-rollout miss probability is 0.800, bounded above by 0.814",
      abs(_bb["worst_p_C"] - 0.8001) < 5e-4
      and abs(_bb["worst_p_C_ub"] - 0.8140) < 5e-4,
      f"{_bb['worst_p_C']:.4f} / {_bb['worst_p_C_ub']:.4f}")
claim("the union failure 36 * 0.814^40 = 0.0096 is within delta/2",
      abs(_bb["union_failure"] - 0.0096) < 5e-4 and _bb["union_failure"] <= 0.025,
      f"{_bb['union_failure']:.4f}")
claim("all steps buys a factor 1.6 over independent single samples",
      abs(_ba["uniform_bound"] / _bb["uniform_bound"] - 1.64) < 0.03,
      f"{_ba['uniform_bound']/_bb['uniform_bound']:.2f}")
claim("and it is only 1.2x worse than the retired all-steps-independent promise",
      abs(_bb["uniform_bound"] / 0.7847 - 1.19) < 0.03)
_pv = {r["regime"]: r for r in load("gate_partition_validation")["rows"]}
_va = _pv["(a) one step per rollout"]
claim("validation (a): 385/400 gates cover the K = 8 partition",
      _va["covered"] == 385 and _va["trials"] == 400, str(_va["covered"]))
claim("measured failure 0.0375 against the bound 0.0383 -- tight to 2%",
      abs(_va["measured_failure"] - 0.0375) < 5e-4
      and _va["measured_failure"] <= _va["certificate_failure_bound"],
      f"{_va['measured_failure']:.4f} vs {_va['certificate_failure_bound']:.4f}")
_vb = _pv["(b) all steps"]
claim("validation (b): 400/400 cover the K = 36 partition, failure CI upper 0.0095 "
      "against a bound of 0.0096",
      _vb["covered"] == 400
      and abs(_vb["measured_failure_ci"][1] - 0.0095) < 5e-4,
      f"{_vb['covered']}/{_vb['trials']}")
claim("the validation reads the partition from the certificate rather than "
      "re-implementing it (same K)",
      _va["K"] == _ba["K"] and _vb["K"] == _bb["K"])

# --- the fence census: what the proposition bounds vs what the table counts ----
_fc = load("fence_separation_census")
_pc = {tuple(r["knob"]): r for r in _fc["patch2d_episode_census"]}
claim("census reproduces the mitigation table's means 1.05/2.65/4.25",
      all(abs(_pc[k]["mean_violations"] - v) < 5e-3 for k, v in
          (((2.0, 6.0), 1.05), ((3.0, 7.0), 2.65), ((4.0, 8.0), 4.25))))
claim("per-episode medians are 1/1/2, not the means",
      [_pc[k]["median_violations"] for k in ((2.0, 6.0), (3.0, 7.0), (4.0, 8.0))]
      == [1, 1, 2])
claim("maxima are 2/28/28 violations",
      [_pc[k]["max_violations"] for k in ((2.0, 6.0), (3.0, 7.0), (4.0, 8.0))]
      == [2, 28, 28])
claim("but DISTINCT fences never exceed 2/5/6 -- a quarter of the 24-fence "
      "two-patch packing budget, so the bounded quantity is comfortably under it",
      [_pc[k]["max_distinct_fences"]
       for k in ((2.0, 6.0), (3.0, 7.0), (4.0, 8.0))] == [2, 5, 6]
      and max(_pc[k]["max_distinct_fences"] for k in _pc) < 24)
claim("pinned (blind-level) episodes are 0/20, 2/20, 7/20",
      [_pc[k]["pinned_episodes"] for k in ((2.0, 6.0), (3.0, 7.0), (4.0, 8.0))]
      == [0, 2, 7])
claim("directly measured median probed arc is 0%/0%/87%",
      abs(_pc[(2.0, 6.0)]["median_probed_arc_fraction"]) < 1e-9
      and abs(_pc[(3.0, 7.0)]["median_probed_arc_fraction"]) < 1e-9
      and abs(_pc[(4.0, 8.0)]["median_probed_arc_fraction"] - 0.873) < 0.005,
      f"{100*_pc[(4.0,8.0)]['median_probed_arc_fraction']:.1f}%")
claim("1D fence overshoot exceeds the band on the cart (4 of 5 episodes), so the "
      "covering hypothesis fails where the conclusion holds",
      [r for r in _fc["fence_placement_1d"] if "cart" in r["arm"]][0]
      ["band_misses_boundary"] == 4)
claim("1D outcomes are bit-identical over a 20x eps range on the pendulum",
      [r for r in _fc["eps_invariance_1d"] if "pendulum" in r["arm"]][0]
      ["identical_across_eps"])
claim("and they move on the cart only at eps = 0.01 (identical from 0.25 to 0.05)",
      not [r for r in _fc["eps_invariance_1d"] if "cart" in r["arm"]][0]
      ["identical_across_eps"])

# --- the fence bound is a PACKING number, and the counterexample is exhibited ---
_circ = load("circle_covering_number")
claim("circle covering number at eps=0.5 is 7 (centres on the circle)",
      _circ["metric_centres_on_circle"]["n"] == 7)
claim("circle PACKING number is 12, and every one of the 12 adds coverage",
      _circ["packing_on_circle"]["n"] == 12
      and _circ["packing_on_circle"]["all_add_coverage"],
      str(_circ["packing_on_circle"]["n"]))
claim("the 12 packing points are pairwise farther than eps apart",
      _circ["packing_on_circle"]["min_pairwise_chord"] > 0.5,
      f"{_circ['packing_on_circle']['min_pairwise_chord']:.4f}")
claim("so packing exceeds covering: the covering bound was the wrong direction",
      _circ["packing_on_circle"]["n"] > _circ["metric_centres_on_circle"]["n"])

# --- the dependence sign, resolved at 50k -------------------------------------
_dep50 = {(r["k1"], r["k2"]): r for r in load("patch2d_dependence_50k")["rows"]}
claim("50k: (2,6) shows negative dependence with the interval excluding r1*r2",
      _dep50[(2.0, 6.0)]["verdict"] == "negative dependence",
      _dep50[(2.0, 6.0)]["verdict"])
claim("50k: (4,6) shows POSITIVE dependence -- the sign changes across the grid",
      _dep50[(4.0, 6.0)]["verdict"] == "positive dependence",
      _dep50[(4.0, 6.0)]["verdict"])
claim("50k: (3,7) negative and (4,7) undecided",
      _dep50[(3.0, 7.0)]["verdict"] == "negative dependence"
      and _dep50[(4.0, 7.0)]["verdict"] == "undecided at this sample size")
claim("50k P(both) at (2,6) is 8.6e-4 against r1*r2 = 19.0e-4",
      abs(_dep50[(2.0, 6.0)]["P_both"] - 8.6e-4) < 0.05e-4
      and abs(_dep50[(2.0, 6.0)]["r1_times_r2"] - 19.0e-4) < 0.1e-4,
      f"{_dep50[(2.0,6.0)]['P_both']:.5f}")
claim("50k P(both) at (4,6) is 12.8e-4 against r1*r2 = 6.2e-4",
      abs(_dep50[(4.0, 6.0)]["P_both"] - 12.8e-4) < 0.05e-4
      and abs(_dep50[(4.0, 6.0)]["r1_times_r2"] - 6.2e-4) < 0.1e-4,
      f"{_dep50[(4.0,6.0)]['P_both']:.5f}")
claim("the in-sample inclusion-exclusion residual is exactly 0 (so bracket "
      "containment at 600 rollouts is an identity, not a confirmation)",
      all(abs(r["hits_union"] - (r["hits1"] + r["hits2"] - r["hits_both"])) == 0
          for r in load("patch2d_dependence_50k")["rows"]))

# --- the sampling unit is the rollout-seed block ------------------------------
_cen = {f["family"]: f for f in load("sample_stream_census")["families"]}
claim("1D cart: 22 distinct rollout-seed blocks behind the repair claim",
      [c for c in load("sample_stream_census")["claims"]
       if c["claim"] == "1D cart repair"][0]["distinct_blocks"] == 22)
claim("1D pendulum: 34 blocks", [c for c in load("sample_stream_census")["claims"]
      if c["claim"] == "1D pendulum repair"][0]["distinct_blocks"] == 34)
claim("PatchField2D disc: 195 mode-present cells over only 20 blocks",
      [c for c in load("sample_stream_census")["claims"]
       if c["claim"] == "PatchField2D repair (disc)"][0]["distinct_blocks"] == 20)
claim("block-level Wilson: all-repair lower bounds 0.851 (cart), 0.898 (pendulum)",
      abs([c for c in load("sample_stream_census")["claims"]
           if c["claim"] == "1D cart repair"][0]
          ["wilson_lower_if_all_repair_blocks"] - 0.851) < 0.002
      and abs([c for c in load("sample_stream_census")["claims"]
               if c["claim"] == "1D pendulum repair"][0]
              ["wilson_lower_if_all_repair_blocks"] - 0.898) < 0.002)
claim("block-level Wilson upper for the 2D negative result is 0.161, not 'never'",
      abs([c for c in load("sample_stream_census")["claims"]
           if c["claim"] == "PatchField2D repair (disc)"][0]
          ["wilson_upper_if_none_repair_blocks"] - 0.161) < 0.002)

# --- eps* is a sample minimum: the spread is quoted, so check it --------------
_es = {r["arm"]: r for r in load("eps_invariance_threshold")["rows"]}
claim("eps* on wall@4 moves by a factor 1.8 across equal-sized streams",
      abs(max(o["eps_star"] for o in _es["cart wall@4"]["eps_star_other_streams"]
              + [{"eps_star": _es["cart wall@4"]["eps_star"]}])
          / _es["cart wall@4"]["eps_star"] - 1.76) < 0.05)
claim("at 20k rollouts wall@8's eps* falls to 0.272, BELOW the grid top of 0.3",
      abs(_es["cart wall@8"]["eps_star_big_sample"]["eps_star"] - 0.2718) < 5e-4
      and _es["cart wall@8"]["eps_star_big_sample"]["eps_star"] < 0.3,
      f"{_es['cart wall@8']['eps_star_big_sample']['eps_star']:.4f}")
claim("the smallest single-contact disagreement on wall@4 is 0.0018",
      abs(_es["cart wall@4"]["min_single_contact_disagreement"] - 0.001794) < 5e-6,
      f"{_es['cart wall@4']['min_single_contact_disagreement']:.5f}")
claim("wall@8's eps* rests on only 25 firing rollouts",
      _es["cart wall@8"]["n_firing"] == 25, str(_es["cart wall@8"]["n_firing"]))

# --- the dependence-exact coverage certificate --------------------------------
dep = load("gate_coverage_dependent")["rows"]
_by = {round(r["rho"], 3): r for r in dep}
claim("dependence-exact: deployed gate certifies net radius 1.0 (N >= 7)",
      _by[1.0]["n_needed_rigorous"] == 7 and _by[1.0]["certified_at_deployed_N"],
      str(_by[1.0]["n_needed_rigorous"]))
claim("its bound is 2.55", abs(_by[1.0]["uniform_bound"] - 2.550) < 0.005,
      f"{_by[1.0]['uniform_bound']:.3f}")
claim("radius 0.667 needs N >= 42, two more than the gate has",
      _by[0.667]["n_needed_rigorous"] == 42
      and not _by[0.667]["certified_at_deployed_N"],
      str(_by[0.667]["n_needed_rigorous"]))
claim("radius 0.5 needs N >= 194 for a bound of 1.28",
      _by[0.5]["n_needed_rigorous"] == 194
      and abs(_by[0.5]["uniform_bound"] - 1.280) < 0.005,
      str(_by[0.5]["n_needed_rigorous"]))
# --- geometry of the one fitted disc (the claim that got a correction) -------
# Claude's single radial attempt: the paper describes where the fitted disc sits
# relative to the true patch. Recompute that geometry rather than trust prose.
_C = (2.3275291505576885, -0.13505551993070315)
_RFIT = 0.824
_TRUE_C, _TRUE_R = (3.0, 0.0), 1.0
_d = math.hypot(_C[0] - _TRUE_C[0], _C[1] - _TRUE_C[1])
claim("fitted disc's centre is INSIDE the true patch, 0.69 from its centre",
      _d < _TRUE_R and abs(_d - 0.69) < 0.01, f"{_d:.4f}")
claim("fitted disc spans x in [1.50, 3.15]",
      abs((_C[0] - _RFIT) - 1.50) < 0.01 and abs((_C[0] + _RFIT) - 3.15) < 0.01,
      f"[{_C[0]-_RFIT:.3f}, {_C[0]+_RFIT:.3f}]")
claim("true patch spans x in [2, 4]",
      (_TRUE_C[0] - _TRUE_R, _TRUE_C[0] + _TRUE_R) == (2.0, 4.0))
claim("a half-plane x>2 covers 75% of the probed box (matches the audit median)",
      abs((14 - 2) / 16 - 0.75) < 1e-9)

# --- sharp-plateau variant: the claims the variant exists to make -----------
sharp_cart = load("continuous_reach_sharp")["rows"]
sharp_pend = load("continuous_pendulum_sharp")["rows"]
base_cart = load("continuous_reach")["rows"]
base_pend = load("continuous_pendulum")["rows"]
for label, sharp, base, want_sharp, want_base in (
        ("cart", sharp_cart, base_cart, 7, 6),
        ("pendulum", sharp_pend, base_pend, 5, 3)):
    below_s = sum(r["j_blind"] < r["j_random"] for r in sharp)
    below_b = sum(r["j_blind"] < r["j_random"] for r in base)
    claim(f"{label}: blind below random at {want_sharp}/{len(sharp)} knobs (sharp)",
          below_s == want_sharp, f"{below_s}/{len(sharp)}")
    claim(f"{label}: below random at {want_base}/{len(base)} knobs (default)",
          below_b == want_base, f"{below_b}/{len(base)}")
    spread_s = (max(r["play_cost"] for r in sharp)
                - min(r["play_cost"] for r in sharp))
    spread_b = (max(r["play_cost"] for r in base)
                - min(r["play_cost"] for r in base))
    claim(f"{label}: sharp play_cost spread ~1e-4 and >100x tighter than default",
          spread_s < 2e-4 and spread_b / spread_s > 100,
          f"sharp {spread_s:.2e} vs default {spread_b:.2e}")
    claim(f"{label}: contact stays 1.00 at every sharp knob",
          all(r["blind_contact_rate"] == 1.0 for r in sharp))
# the asymmetric variant: only the phantom plateau narrowed, so J_rand survives
ph = load("continuous_pendulum_sharpphantom")
ph_rows = ph["rows"]
claim("asymmetric variant: below random at 6/6 pendulum knobs",
      sum(r["j_blind"] < r["j_random"] for r in ph_rows) == 6)
claim("asymmetric variant: J_rand survives in [0.057, 0.059]",
      all(0.057 <= r["j_random"] <= 0.059 for r in ph_rows),
      str(sorted({round(r["j_random"], 4) for r in ph_rows})))
claim("asymmetric variant: J_blind in [4.3e-4, 7.2e-4]",
      4.3e-4 <= min(r["j_blind"] for r in ph_rows)
      and max(r["j_blind"] for r in ph_rows) <= 7.2e-4,
      f"[{min(r['j_blind'] for r in ph_rows):.2e}, "
      f"{max(r['j_blind'] for r in ph_rows):.2e}]")
_sp = (max(r["play_cost"] for r in ph_rows)
       - min(r["play_cost"] for r in ph_rows))
claim("asymmetric variant: play_cost spread ~7.1e-5", abs(_sp - 7.1e-5) < 1e-5,
      f"{_sp:.2e}")
claim("asymmetric variant: J_truth unchanged at 20.08 and contact 1.00",
      all(abs(r["j_truth"] - 20.08) < 5e-3 and r["blind_contact_rate"] == 1.0
          for r in ph_rows))
claim("asymmetric variant narrows only the phantom plateau",
      ph["params"]["width_right"] == 0.08 and ph["params"]["width"] is None)

claim("sharp widths are the ones the paper names (cart 0.2, pendulum 0.1)",
      load("continuous_reach_sharp")["params"]["width"] == 0.2
      and load("continuous_pendulum_sharp")["params"]["width"] == 0.1)

# --- Proposition (joint gate miss): bracket + sign rule vs the measurement --
# The paper proves a two-sided bracket for the joint gate-miss factor and a sign
# rule for the product's error. Both are checkable on every knob, so check them:
# a proof that contradicted the data would be a bug in one of the two.
N_GATE = 40
for j in load("continuous_patch2d")["rows"]:
    r1, r2, ru, rb = j["r1"], j["r2"], j["r_either"], j["r_both"]
    lo = max(0.0, 1 - min(1.0, r1 + r2)) ** N_GATE
    hi = (1 - max(r1, r2)) ** N_GATE
    truth = (1 - ru) ** N_GATE
    prod = ((1 - r1) * (1 - r2)) ** N_GATE
    knob = (j["k1"], j["k2"])
    claim(f"bracket contains the measured joint factor {knob}",
          lo - 1e-15 <= truth <= hi + 1e-15, f"[{lo:.6f},{hi:.6f}] vs {truth:.6f}")
    claim(f"bracket contains the product form {knob}",
          lo - 1e-15 <= prod <= hi + 1e-15, f"[{lo:.6f},{hi:.6f}] vs {prod:.6f}")
    # sign rule: product over-estimates the miss iff P(both) < r1*r2
    if abs(prod - truth) > 1e-12:
        claim(f"sign rule predicts the product's error direction {knob}",
              (rb < r1 * r2) == (prod > truth),
              f"P(both)={rb:.4f} r1r2={r1*r2:.5f} prod-truth={prod-truth:.2e}")
    # inclusion-exclusion consistency of the measured quantities themselves
    claim(f"measured r_union = r1 + r2 - P(both) {knob}",
          abs(ru - (r1 + r2 - rb)) < 1e-9, f"{ru:.6f} vs {r1+r2-rb:.6f}")

# --- cited code artifacts: paths exist, quoted code is verbatim ------------
TEX = TEX  # noqa: PLW0127 — readability: the paper source, parsed again below
_tex = TEX.read_text()

# (a) every repo path the paper names in \texttt{} must exist
for m in re.finditer(r"\\texttt\{((?:[^{}]|\\[_{}])*)\}", _tex):
    s = (m.group(1).replace("\\_", "_").replace("\\allowbreak", "")
         .replace(" ", ""))
    if s.startswith(("scripts/", "src/", "tests/", "docs/", "results/")) \
            and not s.endswith("*.py") and "*" not in s:
        claim(f"cited path exists: {s}", (_REPO / s).exists())

# (b) code the paper quotes from artifacts must appear in a committed artifact.
# Whitespace-normalised containment; the corpus is every synthesized artifact and
# every relayed reply under results/. This is the check that catches a quote
# nobody produced (it caught a fabricated "abs(v2) <= 1.1" clamp on 2026-07-25).
_corpus = []
for f in (_REPO / "results").glob("continuous_synthesis_*.json"):
    try:
        blob = json.loads(f.read_text())
    except Exception:
        continue
    _corpus += [c.get("code", "") for c in blob.get("cells", [])]
_relay = _REPO / "results" / "continuous_claude_relay.json"
if _relay.exists():
    _corpus += [c.get("code", "") for c in json.loads(_relay.read_text())]
for f in (_REPO / "results" / "claude_relay_transcripts").glob("*_reply*.txt"):
    _corpus.append(f.read_text())
# ";" is Python's statement separator: a paper that inlines a multi-line body as
# "if c: a = 1; b = 2" quotes the same code, so it is normalised away too.
def _flat(s):
    return re.sub(r"[\s;]+", "", s)


_norm = [_flat(c) for c in _corpus]

QUOTED_CODE = [
    ("cart repair (return form)", "if x2 >= 8.0: return [8.0, 0.0]"),
    ("cart repair (assign form)", "if x2 > 8.0: x2 = 8.0"),
    ("superstitious clamp (x_wall=4 cell)",
     "if abs(x2 - 4.0) <= 0.15 and abs(v2) <= 2.5: x2 = 4.0; v2 = 0.0"),
    ("Qwen superstitious patch", "if x2 >= 8.0 and v2 <= 0.0:"),
    ("pendulum repair at the headline knob", "if th2 >= 1.4: return [1.4, 0.0]"),
    ("Claude phantom stop (elif branch)",
     "elif th2 < -th_max: th2 = -th_max; om2 = 0.0"),
    ("patch2d dimensional reduction", "if x2 > 4.0:"),
    ("square-ablation dimensional reduction", "if x2 >= 2.0"),
    ("reward-lode disc (mini k3_7 seed 130000)", "if d1 <= 2.0 or d2 <= 2.0:"),
]
for label, snippet in QUOTED_CODE:
    q = _flat(snippet)
    claim(f"quoted verbatim in some artifact: {label}",
          any(q in c for c in _norm))
    CHECKS[0] += 0  # claim() already counted it

# (c) the fitted constants the paper attributes to Claude's one radial attempt
_claude_disc = [c for c in _norm if "OBSTACLE_R" in c]
claim("Claude's fitted disc constants (2.3275291505576885 / -0.13505551993070315 / 0.824)",
      any(all(v in c for v in ("2.3275291505576885", "-0.13505551993070315",
                               "0.824")) for c in _claude_disc),
      f"{len(_claude_disc)} artifact(s) with OBSTACLE_R")

# --- report ----------------------------------------------------------------
print(f"checked {CHECKS[0]} values from docs/paper2/main.tex against results/")
if FAILS:
    print(f"\n{len(FAILS)} MISMATCH(ES):")
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("all agree at printed precision")

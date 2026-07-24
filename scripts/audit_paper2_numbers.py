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
            ("J_truth", 4, j["j_truth"]), ("play_cost", 5, j["play_cost"]),
            ("d@40 P1", 6, d(j["play_cost"], j["r1"], 40)),
            ("d@40 P2", 7, d(j["play_cost"], j["r2"], 40)),
            ("d@40 joint", 8,
             j["play_cost"] * ((1 - j["r1"]) * (1 - j["r2"])) ** 40)):
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
for cells in tabular_rows("tab:axes"):
    r = numbers(cells[1])[0][0]
    cand = [a for a in axes if abs(a["rarity"] - r) < 5e-4]
    if len(cand) != 1:
        FAILS.append(f"tab:axes: {cells[0]!r} matched {len(cand)} arms by rarity")
        continue
    j = cand[0]
    for col, i, actual in (("reveal-rarity", 1, j["rarity"]),
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
claim("0/76 encode a seen patch", encodes == 0, str(encodes))

# --- report ----------------------------------------------------------------
print(f"checked {CHECKS[0]} values from docs/paper2/main.tex against results/")
if FAILS:
    print(f"\n{len(FAILS)} MISMATCH(ES):")
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("all agree at printed precision")

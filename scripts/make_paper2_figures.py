"""Generate paper 2's figures from the versioned results JSONs.

Unlike paper 1's figure script (which transcribed numbers from the tex tables,
because results were not yet versioned), this reads results/continuous_*.json
directly — the figures are exactly the measured numbers, by construction.
Outputs to docs/paper2/figures/ as vector PDF (+ PNG for inspection).

Uncertainty (review minor point m7). Every plotted point keeps the value it
had before this change; what is new is the interval around it, and each
interval is derived from a committed JSON, never assumed:

  * rarity-derived quantities — (1-r)^N and play_cost·(1-r)^N — carry the
    rarity's Wilson interval propagated through the map. The map is monotone
    decreasing in r, so the transformed interval is the corner pair
    [f(r_hi), f(r_lo)]: exact, not a delta-method approximation.
  * 20-episode proportions (blind / truth mode-reach) carry Wilson intervals;
    the saturated 20/20 and censored 0/20 cells are drawn as capped one-sided
    bounds, never as bare points on the 1.00 / 0.00 lines.
  * play_cost carries a *paired* bootstrap interval only where the per-episode
    triples (J_truth, J_blind, J_random) are committed — today that is the
    cart x_wall = 8 row, from results/play_cost_intervals.json, whose first 20
    episodes reproduce the published cell exactly (asserted below). Rows
    without per-episode records get no play-cost interval, and the captions in
    docs/paper2/figure-captions.md say so.

Run: python scripts/make_paper2_figures.py
     python scripts/make_paper2_figures.py --dump /tmp/plotted_series.json
       (--dump writes every plotted series and band to JSON, for auditing the
        figures against results/ without reading pixels; it writes nothing
        into the repository unless asked to.)
"""
import argparse
import json
import math
import os
import random
import statistics
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

_ap = argparse.ArgumentParser(description=__doc__)
_ap.add_argument("--dump", default=None,
                 help="also write every plotted series and band to this JSON")
ARGS = _ap.parse_args()

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "docs", "paper2", "figures")
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, os.path.join(ROOT, "src"))

from cwm.law import t_crit_95, wilson_ci  # noqa: E402

plt.rcParams.update({
    "font.size": 10, "axes.titlesize": 11, "axes.labelsize": 10,
    "legend.fontsize": 9, "xtick.labelsize": 9, "ytick.labelsize": 9,
    "axes.grid": True, "grid.alpha": 0.3, "figure.dpi": 150,
})

# Colorblind-friendly (Wong) palette — same fixed order as paper 1's figures.
C_BLUE, C_ORANGE, C_GREEN, C_RED, C_GREY = (
    "#0072B2", "#E69F00", "#009E73", "#D55E00", "#555555")

BAND_ALPHA = 0.18
N_BOOT = 20000
BOOT_SEED = 20260727  # fixed: the bands are reproducible run to run

DUMP = {}  # filled as figures are drawn; written out by --dump


def save(fig, name):
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(OUT, f"{name}.{ext}"), bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {name}.pdf / .png")


def load(name):
    with open(os.path.join(ROOT, "results", name)) as f:
        return json.load(f)


def load_optional(name):
    try:
        return load(name)
    except FileNotFoundError:
        return None


def prop_ci(hits, n):
    """Wilson 95% interval for hits/n, as (point, lo, hi)."""
    return wilson_ci(hits, n)


def paired_playcost_ci(triples, n_boot=N_BOOT, seed=BOOT_SEED):
    """Seed-paired interval for play_cost from per-episode return triples.

    `triples` is [(j_truth, j_blind, j_random), ...] over the SAME episode
    seeds (the pairing convention of cwm.continuous.harness.play_cost:
    sd = seed + 1000*i for all three arms).

    Returns the published point estimator (ratio of means), a paired bootstrap
    percentile interval that recomputes the ratio inside each resample (so the
    skewed J_random denominator's uncertainty is carried), and the paired
    t-interval with a common aggregate denominator (the estimator of
    scripts/continuous_cem.py::paired_play_cost_ci, whose centre is exactly
    the published ratio of means). The bootstrap interval is what the figures
    shade, because the denominator uncertainty is the dominant term here.
    """
    jt = [t for t, _, _ in triples]
    jb = [b for _, b, _ in triples]
    jr = [r for _, _, r in triples]
    n = len(triples)
    denom = statistics.mean(jt) - statistics.mean(jr)
    point = (statistics.mean(jt) - statistics.mean(jb)) / denom

    normalized = [(t - b) / denom for t, b in zip(jt, jb)]
    sd = statistics.stdev(normalized)
    se = sd / math.sqrt(n)
    margin = t_crit_95(n - 1) * se

    rng = random.Random(seed)
    boot = []
    for _ in range(n_boot):
        idx = [rng.randrange(n) for _ in range(n)]
        t_m = statistics.mean(jt[i] for i in idx)
        b_m = statistics.mean(jb[i] for i in idx)
        r_m = statistics.mean(jr[i] for i in idx)
        boot.append((t_m - b_m) / (t_m - r_m))
    boot.sort()
    lo = boot[int(0.025 * n_boot)]
    hi = boot[int(0.975 * n_boot) - 1]
    return {"n": n, "point": point, "boot95": [lo, hi],
            "t95": [point - margin, point + margin]}


def per_episode_playcost(published_rows, key_field, n_pub):
    """Paired play_cost intervals for the rows whose per-episode triples exist.

    Reads results/play_cost_intervals.json (review point 9), which re-runs the
    headline rows over 100 paired episodes and checkpoints one unit per
    (row, episode). We use its FIRST `n_pub` episodes only: those are the very
    episodes behind the published cell, so the interval belongs to the point
    that is plotted. A row is used only if (a) episodes 0..n_pub-1 are all
    present and (b) their ratio of means reproduces the published play_cost to
    1e-9 — otherwise the figure gets no band rather than a wrong one.

    `published_rows` maps a play_cost_intervals row key to the results row it
    belongs to, e.g. {"cart_xwall8": row_of_continuous_reach_with_x_wall_8}.
    """
    src = load_optional("play_cost_intervals.json")
    if src is None:
        return {}
    units = {}
    for u in src.get("units", {}).values():
        units.setdefault(u["row"], {})[u["episode"]] = u
    out = {}
    for row_key, published in published_rows.items():
        eps = units.get(row_key, {})
        if not set(range(n_pub)).issubset(eps):
            continue
        triples = [(eps[i]["j_truth"], eps[i]["j_blind"], eps[i]["j_random"])
                   for i in range(n_pub)]
        ci = paired_playcost_ci(triples)
        if abs(ci["point"] - published["play_cost"]) > 1e-9:
            print(f"  ! {row_key}: per-episode reconstruction "
                  f"{ci['point']:.12g} != published "
                  f"{published['play_cost']:.12g} — no band drawn")
            continue
        ci["source"] = "results/play_cost_intervals.json"
        out[published[key_field]] = ci
        print(f"  play_cost band for {row_key}: point {ci['point']:.4f} "
              f"boot95 [{ci['boot95'][0]:.4f}, {ci['boot95'][1]:.4f}] "
              f"(n = {n_pub} paired episodes)")
    return out


reach = load("continuous_reach.json")["rows"]
axes_rows = load("continuous_axes.json")["rows"]
probe = load("continuous_smooth_probe.json")["rows"]

# Per-episode play-cost triples, keyed by the plotted row's identifier.
pc_by_wall = per_episode_playcost(
    {"cart_xwall8": next(r for r in reach if r["x_wall"] == 8.0)},
    "x_wall", 20)
pc_by_arm = per_episode_playcost(
    {"cart_xwall8": next(r for r in axes_rows if r["arm"] == "wall@8 omitted")},
    "arm", 20)

# ---------------------------------------------------------------- figure 1
# Threshold law: danger(N) vs rarity (the knob traced by x_wall).
# Bands: rarity's Wilson interval propagated through play_cost·(1-r)^N on both
# axes; where per-episode returns exist, a second bar multiplies in the paired
# play-cost interval.
fig, ax = plt.subplots(figsize=(4.6, 3.2))
rarity = [r["rarity"] for r in reach]
r_lo = [r["rarity_lo"] for r in reach]
r_hi = [r["rarity_hi"] for r in reach]
DUMP["danger_threshold"] = {"rarity": rarity, "rarity_lo": r_lo,
                            "rarity_hi": r_hi, "curves": {}}
for n, color in ((20, C_BLUE), (40, C_ORANGE), (80, C_GREEN)):
    danger = [r["play_cost"] * (1 - r["rarity"]) ** n for r in reach]
    # (1-r)^N is decreasing in r: the transformed interval is the corner pair.
    d_lo = [r["play_cost"] * (1 - r["rarity_hi"]) ** n for r in reach]
    d_hi = [r["play_cost"] * (1 - r["rarity_lo"]) ** n for r in reach]
    ax.fill_between(rarity, d_lo, d_hi, color=color, alpha=BAND_ALPHA, lw=0)
    ax.errorbar(rarity, danger,
                xerr=[[p - lo for p, lo in zip(rarity, r_lo)],
                      [hi - p for p, hi in zip(rarity, r_hi)]],
                fmt="o-", color=color, lw=2, ms=5, elinewidth=0.8, capsize=1.5,
                label=f"N = {n}")
    DUMP["danger_threshold"]["curves"][n] = {
        "danger": danger, "danger_rarity_lo": d_lo, "danger_rarity_hi": d_hi}

pc_bars = {"x": [], "y": [], "lo": [], "hi": []}
for i, r in enumerate(reach):
    ci = pc_by_wall.get(r["x_wall"])
    if ci is None:
        continue
    for n, color in ((20, C_BLUE), (40, C_ORANGE), (80, C_GREEN)):
        # d@N is monotone in both factors, so the joint interval is the corner
        # product of the play-cost and rarity intervals.
        lo = ci["boot95"][0] * (1 - r["rarity_hi"]) ** n
        hi = ci["boot95"][1] * (1 - r["rarity_lo"]) ** n
        y = r["play_cost"] * (1 - r["rarity"]) ** n
        ax.errorbar([r["rarity"]], [y], yerr=[[y - lo], [hi - y]], fmt="none",
                    ecolor=C_GREY, elinewidth=1.4, capsize=3.5, zorder=4)
        pc_bars["x"].append(r["rarity"])
        pc_bars["y"].append(y)
        pc_bars["lo"].append(lo)
        pc_bars["hi"].append(hi)
if pc_bars["x"]:
    ax.errorbar([], [], yerr=[[0], [0]], fmt="none", ecolor=C_GREY,
                elinewidth=1.4, capsize=3.5,
                label="+ play-cost interval\n(20 paired episodes)")
DUMP["danger_threshold"]["playcost_bars"] = pc_bars
DUMP["danger_threshold"]["playcost_ci"] = {
    str(k): v for k, v in pc_by_wall.items()}
ax.set_xscale("log")
ax.invert_xaxis()  # reading direction: rule gets rarer to the right
ax.set_xlabel("rarity  r  (wall-contact rate under random rollouts, log)")
ax.set_ylabel(r"danger $= \mathrm{play\_cost}\cdot(1-r)^N$")
ax.set_title("The threshold law on the wall-position knob")
ax.legend(frameon=False)
save(fig, "danger_threshold")

# ---------------------------------------------------------------- figure 2
# Reach mechanism: exploited-planner reach flat at 1, random reach falling,
# truth-planner trajectory reach 0.
# Bands: Wilson on the two 20-episode proportions (both are boundary cells —
# 20/20 and 0/20 — so they are drawn as capped one-sided bounds), and the
# committed Wilson interval on the 30,000-rollout rarity.
fig, ax = plt.subplots(figsize=(4.6, 3.2))
xw = [r["x_wall"] for r in reach]
n_ep = [r["n_episodes"] for r in reach]
DUMP["reach_mechanism"] = {"x_wall": xw, "n_episodes": n_ep}


def contact_band(rows, field):
    """(values, lower errs, upper errs) with Wilson intervals on k/n_episodes."""
    vals, lo, hi = [], [], []
    for r in rows:
        n = r["n_episodes"]
        k = round(r[field] * n)
        p, w_lo, w_hi = prop_ci(k, n)
        vals.append(r[field])
        lo.append(r[field] - w_lo)
        hi.append(w_hi - r[field])
    return vals, lo, hi


blind, b_lo, b_hi = contact_band(reach, "blind_contact_rate")
truth, t_lo, t_hi = contact_band(reach, "truth_contact_rate")
ax.errorbar(xw, blind, yerr=[b_lo, b_hi], fmt="o-", color=C_RED, lw=2, ms=5,
            elinewidth=0.9, capsize=3,
            label="blind-planner reach (exploited)")
ax.errorbar(xw, [r["rarity"] for r in reach],
            yerr=[[r["rarity"] - r["rarity_lo"] for r in reach],
                  [r["rarity_hi"] - r["rarity"] for r in reach]],
            fmt="s-", color=C_BLUE, lw=2, ms=5, elinewidth=0.9, capsize=3,
            label="random reach (= rarity)")
ax.errorbar(xw, truth, yerr=[t_lo, t_hi], fmt="^-", color=C_GREEN, lw=2, ms=5,
            elinewidth=0.9, capsize=3, label="truth-planner reach")
# Name the two boundary cells for what they are: 20/20 and 0/20, so the flat
# lines are not read as measurements without error.
ax.annotate(f"20/20 every knob: $\\geq {blind[0] - b_lo[0]:.2f}$",
            (xw[1], blind[1]), textcoords="offset points", xytext=(2, -14),
            fontsize=8, color=C_RED)
ax.annotate(f"0/20 every knob: $\\leq {truth[0] + t_hi[0]:.2f}$",
            (xw[1], truth[1] + t_hi[1]), textcoords="offset points",
            xytext=(2, 4), fontsize=8, color=C_GREEN)
DUMP["reach_mechanism"]["blind_contact_rate"] = blind
DUMP["reach_mechanism"]["blind_wilson"] = [
    [v - l, v + h] for v, l, h in zip(blind, b_lo, b_hi)]
DUMP["reach_mechanism"]["truth_contact_rate"] = truth
DUMP["reach_mechanism"]["truth_wilson"] = [
    [v - l, v + h] for v, l, h in zip(truth, t_lo, t_hi)]
DUMP["reach_mechanism"]["rarity"] = [r["rarity"] for r in reach]
DUMP["reach_mechanism"]["rarity_wilson"] = [
    [r["rarity_lo"], r["rarity_hi"]] for r in reach]
ax.set_xlabel(r"wall position $x_\mathrm{wall}$ (the rarity knob)")
ax.set_ylabel("P(episode fires the wall mode)")
ax.set_title("The two reach distributions of the danger law")
ax.set_ylim(-0.05, 1.08)
ax.legend(frameon=False, loc="center right")
save(fig, "reach_mechanism")

# ---------------------------------------------------------------- figure 3
# Danger quadrant: gate-miss probability vs play_cost, one point per arm.
# Danger = the product; only the rare hard mode reaches the top-right.
# Bands: x from the rarity Wilson interval propagated through (1-r)^40;
# y only where per-episode returns exist. Arms whose (1-r)^40 is a censored
# zero are drawn at the display floor with a left-pointing arrow, so a zero
# that the sample cannot resolve does not look like a measured value.
fig, ax = plt.subplots(figsize=(5.0, 3.4))
STYLE = {  # fixed per-arm color: entity, not rank; label offset & alignment
    "wall@4 omitted": (C_RED, "o", (8, 2), "left"),
    "wall@8 omitted": (C_RED, "D", (-9, 2), "right"),
    "bias x1.03 (sub-eps)": (C_BLUE, "s", (-9, 2), "right"),
    "bias x2.0 (supra-eps)": (C_BLUE, "^", (8, 8), "left"),
    "bump@4 amp0.5 (smooth)": (C_GREEN, "v", (8, -14), "left"),
    "bump@4 amp1.0 (smooth)": (C_GREEN, "P", (8, 2), "left"),
}
FLOOR = 1e-4  # display floor for log axis (measured zeros)
XMIN = FLOOR / 1.8
N_GATE = 40
DUMP["axis_separation"] = {"floor": FLOOR, "arms": {}}
for row in axes_rows:
    color, marker, offset, halign = STYLE[row["arm"]]
    x = max(row["predicted_pass"], FLOOR)
    # (1-r)^40 is decreasing in r: corner pair of the rarity Wilson interval.
    r_ci = row["rarity_ci"]
    x_lo = (1 - r_ci[1]) ** N_GATE
    x_hi = (1 - r_ci[0]) ** N_GATE
    ax.scatter(x, row["play_cost"], s=55, color=color, marker=marker,
               zorder=3)
    if x_hi < XMIN:
        # Censored: the whole interval is below the display floor. Draw the
        # bound as an arrow, not as a point sitting on the floor.
        ax.annotate("", xy=(XMIN * 1.05, row["play_cost"]),
                    xytext=(x, row["play_cost"]),
                    arrowprops=dict(arrowstyle="-|>", color=color, lw=1.2,
                                    shrinkA=3, shrinkB=0))
        ax.annotate(f"$\\leq 10^{{{math.floor(math.log10(x_hi)):d}}}$",
                    (XMIN * 1.15, row["play_cost"]),
                    textcoords="offset points", xytext=(0, -12), fontsize=7.5,
                    ha="left", color=color)
    else:
        ax.errorbar([x], [row["play_cost"]],
                    xerr=[[max(x - max(x_lo, XMIN * 1.02), 0.0)], [x_hi - x]],
                    fmt="none", ecolor=color, elinewidth=1.0, capsize=3,
                    zorder=2)
    ci = pc_by_arm.get(row["arm"])
    if ci is not None:
        ax.errorbar([x], [row["play_cost"]],
                    yerr=[[row["play_cost"] - ci["boot95"][0]],
                          [ci["boot95"][1] - row["play_cost"]]],
                    fmt="none", ecolor=color, elinewidth=1.4, capsize=3.5,
                    zorder=2)
    label = row["arm"].replace(" omitted", "").replace(" (smooth)", "")
    ax.annotate(label, (x, row["play_cost"]),
                textcoords="offset points", xytext=offset, fontsize=8,
                ha=halign, color=C_GREY)
    DUMP["axis_separation"]["arms"][row["arm"]] = {
        "predicted_pass": row["predicted_pass"], "plotted_x": x,
        "predicted_pass_band": [x_lo, x_hi], "play_cost": row["play_cost"],
        "play_cost_boot95": ci["boot95"] if ci else None}
ax.set_xscale("log")
ax.set_xlim(XMIN, 4)
ax.axhline(0, color=C_GREY, lw=0.8)
ax.set_xlabel(r"gate-miss probability $(1-r)^{40}$  (log; floored at $10^{-4}$)")
ax.set_ylabel("play_cost (normalized regret)")
ax.set_title("Axis separation: danger is the top-right product")
save(fig, "axis_separation")

# ---------------------------------------------------------------- figure 4
# Smooth learners cannot localize: off-mode max error (log) by model/data.
# No bands: results/continuous_smooth_probe.json stores one fit per cell, with
# no per-seed field, so there is nothing to build an interval from. The
# synthesized-code bar is an exact zero drawn at the axis floor and is hatched
# and labelled to say so.
fig, ax = plt.subplots(figsize=(4.8, 3.2))
labels, vals, colors = [], [], []
order = [("linear-LSQ", "wall-free", C_BLUE), ("linear-LSQ", "wall-data", C_BLUE),
         ("MLP h=8", "wall-free", C_ORANGE), ("MLP h=8", "wall-data", C_ORANGE)]
for model, data, color in order:
    row = next(r for r in probe if r["model"] == model and r["trained_on"] == data)
    labels.append(f"{model}\n{data}")
    vals.append(row["off_mode_max"])
    colors.append(color)
labels.append("synthesized\ncode")
vals.append(1e-16)  # bit-exact off-mode; drawn at the axis floor
colors.append(C_GREEN)
bars = ax.bar(labels, vals, color=colors, width=0.62)
bars[-1].set_hatch("///")  # not a measured magnitude: an exact zero
bars[-1].set_edgecolor("white")
DUMP["smooth_localization"] = {"labels": labels, "off_mode_max": vals,
                               "bands": None,
                               "exact_zero_drawn_at": 1e-16}
ax.set_yscale("log")
ax.set_ylim(3e-17, 1)
ax.set_ylabel("off-mode max error (sup-norm, log)")
ax.set_title("The mode cannot be localized by a smooth hypothesis")
for eps, txt in ((1e-9, r"$\varepsilon=10^{-9}$ gate"),
                 (1e-2, r"$\varepsilon=10^{-2}$ gate")):
    ax.axhline(eps, color=C_GREY, lw=0.9, ls="--")
    ax.annotate(txt, (4.45, eps), fontsize=8, color=C_GREY,
                va="bottom", ha="right")
ax.annotate("exactly 0\n(drawn at floor)", (4, 1e-16), ha="center",
            va="bottom", fontsize=8, color=C_GREEN)
ax.tick_params(axis="x", labelsize=8)
save(fig, "smooth_localization")

if ARGS.dump:
    with open(ARGS.dump, "w") as f:
        json.dump(DUMP, f, indent=1, sort_keys=True)
    print(f"dumped plotted series to {ARGS.dump}")

print("done")

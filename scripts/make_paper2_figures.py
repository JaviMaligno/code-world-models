"""Generate paper 2's figures from the versioned results JSONs.

Unlike paper 1's figure script (which transcribed numbers from the tex tables,
because results were not yet versioned), this reads results/continuous_*.json
directly — the figures are exactly the measured numbers, by construction.
Outputs to docs/paper2/figures/ as vector PDF (+ PNG for inspection).

Run: python scripts/make_paper2_figures.py
"""
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "docs", "paper2", "figures")
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({
    "font.size": 10, "axes.titlesize": 11, "axes.labelsize": 10,
    "legend.fontsize": 9, "xtick.labelsize": 9, "ytick.labelsize": 9,
    "axes.grid": True, "grid.alpha": 0.3, "figure.dpi": 150,
})

# Colorblind-friendly (Wong) palette — same fixed order as paper 1's figures.
C_BLUE, C_ORANGE, C_GREEN, C_RED, C_GREY = (
    "#0072B2", "#E69F00", "#009E73", "#D55E00", "#555555")


def save(fig, name):
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(OUT, f"{name}.{ext}"), bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {name}.pdf / .png")


def load(name):
    with open(os.path.join(ROOT, "results", name)) as f:
        return json.load(f)


reach = load("continuous_reach.json")["rows"]
axes_rows = load("continuous_axes.json")["rows"]
probe = load("continuous_smooth_probe.json")["rows"]

# ---------------------------------------------------------------- figure 1
# Threshold law: danger(N) vs rarity (the knob traced by x_wall).
fig, ax = plt.subplots(figsize=(4.6, 3.2))
rarity = [r["rarity"] for r in reach]
for n, color in ((20, C_BLUE), (40, C_ORANGE), (80, C_GREEN)):
    danger = [r["play_cost"] * (1 - r["rarity"]) ** n for r in reach]
    ax.plot(rarity, danger, "o-", color=color, lw=2, ms=5, label=f"N = {n}")
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
fig, ax = plt.subplots(figsize=(4.6, 3.2))
xw = [r["x_wall"] for r in reach]
ax.plot(xw, [r["blind_contact_rate"] for r in reach], "o-", color=C_RED,
        lw=2, ms=5, label="blind-planner reach (exploited)")
ax.plot(xw, [r["rarity"] for r in reach], "s-", color=C_BLUE, lw=2, ms=5,
        label="random reach (= rarity)")
ax.plot(xw, [r["truth_contact_rate"] for r in reach], "^-", color=C_GREEN,
        lw=2, ms=5, label="truth-planner reach")
ax.set_xlabel(r"wall position $x_\mathrm{wall}$ (the rarity knob)")
ax.set_ylabel("P(episode fires the wall mode)")
ax.set_title("The two reach distributions of the danger law")
ax.set_ylim(-0.05, 1.08)
ax.legend(frameon=False, loc="center right")
save(fig, "reach_mechanism")

# ---------------------------------------------------------------- figure 3
# Danger quadrant: gate-miss probability vs play_cost, one point per arm.
# Danger = the product; only the rare hard mode reaches the top-right.
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
for row in axes_rows:
    color, marker, offset, halign = STYLE[row["arm"]]
    x = max(row["predicted_pass"], FLOOR)
    ax.scatter(x, row["play_cost"], s=55, color=color, marker=marker,
               zorder=3)
    label = row["arm"].replace(" omitted", "").replace(" (smooth)", "")
    ax.annotate(label, (x, row["play_cost"]),
                textcoords="offset points", xytext=offset, fontsize=8,
                ha=halign, color=C_GREY)
ax.set_xscale("log")
ax.set_xlim(FLOOR / 1.8, 4)
ax.axhline(0, color=C_GREY, lw=0.8)
ax.set_xlabel(r"gate-miss probability $(1-r)^{40}$  (log; floored at $10^{-4}$)")
ax.set_ylabel("play_cost (normalized regret)")
ax.set_title("Axis separation: danger is the top-right product")
save(fig, "axis_separation")

# ---------------------------------------------------------------- figure 4
# Smooth learners cannot localize: off-mode max error (log) by model/data.
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
ax.set_yscale("log")
ax.set_ylim(3e-17, 1)
ax.set_ylabel("off-mode max error (sup-norm, log)")
ax.set_title("The mode cannot be localized by a smooth hypothesis")
for eps, txt in ((1e-9, r"$\varepsilon=10^{-9}$ gate"),
                 (1e-2, r"$\varepsilon=10^{-2}$ gate")):
    ax.axhline(eps, color=C_GREY, lw=0.9, ls="--")
    ax.annotate(txt, (4.45, eps), fontsize=8, color=C_GREY,
                va="bottom", ha="right")
ax.annotate("exact (0)", (4, 1e-16), ha="center", va="bottom", fontsize=8,
            color=C_GREEN)
ax.tick_params(axis="x", labelsize=8)
save(fig, "smooth_localization")

print("done")

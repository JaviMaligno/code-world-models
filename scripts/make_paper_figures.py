"""Generate the paper's figures from the numbers already reported in the tables.

This script does NOT re-run any experiment. Every value below is transcribed
from a table in docs/paper/main.tex, so the figures are exactly the published
numbers rendered visually. Outputs go to docs/paper/figures/ as vector PDF
(for \includegraphics) and PNG (for quick visual inspection).

Run: python scripts/make_paper_figures.py
"""

import os
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.path.join(os.path.dirname(__file__), "..", "docs", "paper", "figures")
OUT = os.path.normpath(OUT)
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update(
    {
        "font.size": 10,
        "axes.titlesize": 11,
        "axes.labelsize": 10,
        "legend.fontsize": 9,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "figure.dpi": 150,
    }
)

# Colorblind-friendly (Wong) palette
C_BLUE = "#0072B2"
C_ORANGE = "#E69F00"
C_GREEN = "#009E73"
C_RED = "#D55E00"
C_GREY = "#555555"


def save(fig, name):
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(OUT, f"{name}.{ext}"), bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {name}.pdf / .png")


# ---------------------------------------------------------------------------
# Figure 1: the danger law on both axes of the CWM contract (unification).
# Panel (a) transition axis (army5x5a + material-at-cap), Sec. 4 table.
# Panel (b) inference axis (Beacon), Sec. 6.6 table.
# In both: smooth analytic curve danger = play_cost * (1 - r)^N, with the
# measured operating points from the table overlaid as markers.
# ---------------------------------------------------------------------------
def fig_danger_law():
    # --- Panel (a): transition axis. play_cost = 0.12 (round constant used in
    # the Sec. 4 table). Measured (rarity, danger) points from that table. ---
    play_cost_a = 0.12
    cap = np.array([25, 40, 60, 80, 100, 120, 140])
    rarity = np.array([0.337, 0.208, 0.107, 0.056, 0.025, 0.011, 0.007])
    danger_measured = {
        20: np.array([0.000, 0.001, 0.012, 0.038, 0.072, 0.096, 0.105]),
        40: np.array([0.000, 0.000, 0.001, 0.012, 0.043, 0.076, 0.092]),
        80: np.array([0.000, 0.000, 0.000, 0.001, 0.015, 0.048, 0.070]),
    }

    # --- Panel (b): inference axis. play_cost = 0.5, fixed gate N = 2000. ---
    play_cost_b = 0.5
    N_b = 2000
    T = np.array([4, 6, 8, 10])
    eps = np.array([3.9e-3, 2.4e-4, 1.5e-5, 9.5e-7])
    danger_b = np.array([0.000, 0.307, 0.485, 0.499])

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(9.6, 3.8))

    # Panel (a)
    r_grid = np.logspace(np.log10(0.004), np.log10(0.45), 400)
    for N, col in zip((20, 40, 80), (C_BLUE, C_ORANGE, C_GREEN)):
        axA.plot(
            r_grid,
            play_cost_a * (1 - r_grid) ** N,
            color=col,
            lw=1.8,
            label=f"$N={N}$ (theory)",
        )
        axA.plot(
            rarity,
            danger_measured[N],
            "o",
            color=col,
            ms=5,
            markeredgecolor="white",
            markeredgewidth=0.6,
            zorder=5,
        )
    axA.axvline(0.025, color=C_GREY, ls="--", lw=1.0)
    axA.annotate(
        "army5x5a\noperating point\n$r=0.025$",
        xy=(0.025, 0.072),
        xytext=(0.018, 0.094),
        fontsize=8,
        color=C_GREY,
        ha="center",
    )
    axA.set_xscale("log")
    axA.set_xlabel("rule rarity $r$ (random-play incidence)")
    axA.set_ylabel(r"danger $= \mathrm{play\_cost}\,(1-r)^N$")
    axA.set_title("(a) Transition axis — army5x5a")
    axA.set_ylim(-0.005, 0.125)
    axA.legend(loc="upper left", framealpha=0.95)
    axA.invert_xaxis()  # rare on the right: danger rises as the rule gets rarer

    # Panel (b)
    e_grid = np.logspace(-6.3, -2.0, 400)
    axB.plot(
        e_grid,
        play_cost_b * (1 - e_grid) ** N_b,
        color=C_RED,
        lw=1.8,
        label=f"$N={N_b}$ (theory)",
    )
    axB.plot(
        eps,
        danger_b,
        "o",
        color=C_RED,
        ms=6,
        markeredgecolor="white",
        markeredgewidth=0.6,
        zorder=5,
    )
    t_offsets = {4: (3.0, -0.005), 6: (2.2, 0.030), 8: (0.45, 0.040), 10: (0.5, 0.012)}
    for Ti, ei, di in zip(T, eps, danger_b):
        dx, dy = t_offsets[Ti]
        axB.annotate(
            f"$T={Ti}$",
            xy=(ei, di),
            xytext=(ei * dx, di + dy),
            fontsize=8,
            color=C_RED,
        )
    axB.axvline(1.5e-5, color=C_GREY, ls="--", lw=1.0)
    axB.annotate(
        "Beacon\noperating point",
        xy=(1.5e-5, 0.25),
        xytext=(6.0e-5, 0.20),
        fontsize=8,
        color=C_GREY,
        ha="center",
    )
    axB.set_xscale("log")
    axB.set_xlabel(r"deep-region reach $\varepsilon=(1/2)^{2T}$ (random play)")
    axB.set_ylabel(r"danger $= \mathrm{play\_cost}\,(1-\varepsilon)^N$")
    axB.set_title("(b) Inference axis — Beacon")
    axB.set_ylim(-0.02, 0.55)
    axB.legend(loc="upper left", framealpha=0.95)
    axB.invert_xaxis()

    fig.suptitle(
        "The danger law is a threshold in rarity, on both halves of the CWM contract",
        fontsize=11,
        y=1.02,
    )
    save(fig, "danger_law")


# ---------------------------------------------------------------------------
# Figure 2: the headline play result with Wilson 95% intervals (Sec. 3.3,
# Panel A). Makes the non-overlap of the intervals immediately visible.
# ---------------------------------------------------------------------------
def fig_headline_play():
    labels = ["truth vs truth\n(fair baseline)", "rule-blind vs truth\n(play cost)"]
    point = np.array([0.507, 0.376])
    lo = np.array([0.467, 0.338])
    hi = np.array([0.547, 0.415])
    colors = [C_BLUE, C_RED]

    fig, ax = plt.subplots(figsize=(5.0, 3.6))
    x = np.arange(len(labels))
    yerr = np.vstack([point - lo, hi - point])
    ax.bar(x, point, width=0.55, color=colors, alpha=0.85,
           yerr=yerr, capsize=8, error_kw={"elinewidth": 1.6, "ecolor": "#222222"})
    ax.axhline(0.5, color=C_GREY, ls="--", lw=1.0, zorder=0)
    ax.text(1.45, 0.505, "0.5", color=C_GREY, fontsize=8, va="bottom", ha="right")

    # annotate the gap between the two intervals (0.467 vs 0.415)
    ax.annotate(
        "",
        xy=(0.5, 0.415), xytext=(0.5, 0.467),
        arrowprops=dict(arrowstyle="<->", color=C_GREEN, lw=1.4),
    )
    ax.text(0.56, 0.441, "intervals\nseparated", color=C_GREEN, fontsize=8, va="center")

    for xi, p in zip(x, point):
        ax.text(xi, p + 0.001, f"{p:.3f}", ha="center", va="bottom", fontsize=9)

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("win rate [Wilson 95% CI]")
    ax.set_ylim(0.30, 0.58)
    ax.set_title("Headline play result (army5x5a + material-at-cap, $n=600$)")
    ax.grid(axis="x", visible=False)
    save(fig, "headline_play")


# ---------------------------------------------------------------------------
# Figure 3: mechanism behind play_cost-constancy (Sec. 4 remark). Competent
# reach of the cap region is ~flat across the cap knob while random reach
# falls -> play_cost rides competent reach, rarity rides random reach.
# 40 games / 300 sims per point: suggestive, not a proof (as the text says).
# ---------------------------------------------------------------------------
def fig_play_cost_mechanism():
    cap = np.array([30, 60, 100])
    competent = np.array([0.200, 0.200, 0.225])
    random = np.array([0.375, 0.200, 0.075])

    fig, ax = plt.subplots(figsize=(5.0, 3.6))
    ax.plot(cap, competent, "o-", color=C_BLUE, lw=1.8, ms=6,
            label="competent (MCTS) reach")
    ax.plot(cap, random, "s--", color=C_ORANGE, lw=1.8, ms=6,
            label="random reach")
    ax.set_xlabel("ply cap (rarity knob)")
    ax.set_ylabel("P(reach cap region)")
    ax.set_xticks(cap)
    ax.set_ylim(0.0, 0.42)
    ax.set_title(r"Why play$\_$cost is $\approx$rarity-invariant (40 games/pt: suggestive)")
    ax.legend(loc="upper right", framealpha=0.95)
    save(fig, "play_cost_mechanism")


if __name__ == "__main__":
    fig_danger_law()
    fig_headline_play()
    fig_play_cost_mechanism()
    print("done ->", OUT)

"""Generate paper 3's figures from the versioned results JSONs.

Same convention as make_paper2_figures.py: read results/*.json directly so
the figures ARE the measured numbers; output vector PDF (+ PNG for
inspection) to docs/paper3/figures/.

Run: python scripts/make_paper3_figures.py
"""
import json
import os
import statistics

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "docs", "paper3", "figures")
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({
    "font.size": 10, "axes.titlesize": 11, "axes.labelsize": 10,
    "legend.fontsize": 9, "xtick.labelsize": 9, "ytick.labelsize": 9,
    "axes.grid": True, "grid.alpha": 0.3, "figure.dpi": 150,
})

# Colorblind-friendly (Wong) palette — same fixed order as papers 1-2.
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


def fig_danger_curve():
    """H1: pc_blind(gamma) facing collapses over a knee; hidden persists.
    Three measured series, no transcription:
      - dense CPU curve, facing (16 paired MPC episodes/point);
      - hidden-channel control (mechanism grid, same method);
      - LLM-arm confirmations (mean play_cost of the exploited blind
        artifacts per facing gap, from the open-sweep summary)."""
    curve = load("continuous_ring2d_pcblind_curve.json")
    gaps = [r["gap"] for r in curve]
    pcs = [r["play_cost"] for r in curve]

    mech = load("continuous_ring2d_mechanism.json")
    rows = mech if isinstance(mech, list) else (mech.get("rows")
                                                or mech.get("cells"))
    hid = sorted((r["gap"], r["play_cost_blind"]) for r in rows
                 if r.get("start") == "outside"
                 and (r.get("channel") == "hidden" or r["gap"] == 0.0))

    summ = load("continuous_ring2d_open_sweep_summary.json")
    llm = sorted(
        (d["gap"], statistics.mean(d["pc_values"]))
        for d in summ["danger"].values()
        if d["channel"] == "facing" and d["pc_values"])

    fig, ax = plt.subplots(figsize=(5.4, 3.4))
    ax.plot(gaps, pcs, "-o", color=C_BLUE, ms=4, lw=1.6, zorder=3,
            label="facing channel (CPU)")
    ax.plot([g for g, _ in hid], [p for _, p in hid], "s--", color=C_ORANGE,
            ms=6, lw=1.4, zorder=4,
            label=r"hidden channel (same $\beta_1$)")
    ax.plot([g for g, _ in llm], [p for _, p in llm], "x", color=C_GREEN,
            ms=7, mew=2, zorder=5,
            label="LLM blind artifacts")

    ax.axhline(0.0, color=C_GREY, lw=0.8, zorder=1)
    ax.annotate("knee: arc-width $\\approx$ planner step",
                xy=(0.12, 0.20), xytext=(0.28, 0.30), fontsize=9,
                arrowprops=dict(arrowstyle="->", color=C_GREY, lw=1.0))
    ax.annotate("same $\\beta_1 = 0$, opposite danger",
                xy=(0.6, 0.999), xytext=(0.20, 0.84), fontsize=9,
                arrowprops=dict(arrowstyle="->", color=C_GREY, lw=1.0))

    ax.set_xlabel(r"channel width $\gamma$ (rad)")
    ax.set_ylabel(r"$\mathrm{play\_cost}$ of the blind model")
    ax.set_xlim(-0.04, 1.3)
    ax.set_ylim(-0.13, 1.22)
    ax.legend(loc="center right", bbox_to_anchor=(1.0, 0.58),
              framealpha=0.95)
    save(fig, "danger_curve")


def fig_gamma_curves():
    """Props 5-9 measured: r(gamma) nonincreasing, r_int(gamma) rising from
    the exact zero at gamma=0 (Lemma 2). CRN rollouts, Wilson 95% CIs."""
    probe = load("continuous_ring2d_rint_probe.json")
    rows = sorted(probe["rows"], key=lambda r: r["gap"])
    g = [r["gap"] for r in rows]
    rr = [r["r"] for r in rows]
    rlo = [r["r"] - r["r_ci"][0] for r in rows]
    rhi = [r["r_ci"][1] - r["r"] for r in rows]
    ri = [r["r_int"] for r in rows]
    rilo = [r["r_int"] - r["r_int_ci"][0] for r in rows]
    rihi = [r["r_int_ci"][1] - r["r_int"] for r in rows]

    fig, ax = plt.subplots(figsize=(5.4, 3.2))
    ax.errorbar(g, rr, yerr=[rlo, rhi], fmt="-o", color=C_BLUE, ms=4,
                lw=1.5, capsize=2, label=r"$r(\gamma)$ (contact rarity)")
    ax.errorbar(g, ri, yerr=[rilo, rihi], fmt="-s", color=C_RED, ms=4,
                lw=1.5, capsize=2,
                label=r"$r_{\mathrm{int}}(\gamma)$ (interior entry)")
    ax.set_xlabel(r"channel width $\gamma$ (rad)")
    ax.set_ylabel("per-rollout rate")
    ax.legend(loc="upper right")
    save(fig, "gamma_curves")


if __name__ == "__main__":
    fig_danger_curve()
    fig_gamma_curves()

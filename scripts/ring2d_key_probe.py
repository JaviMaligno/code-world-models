"""(KEY) stress probe + first-divergence identity check (paper 3 THEORY.md).

Part 1 — adversarial configurations. (KEY) claims h1(freeze(s), t) <=
h2(move(s,a), t) at EVERY divergence configuration. Suspicion: false. The
freeze PARKS the gamma1-chain at rest at s's position — if s sits in the
gamma1 corridor 0.1 from the interior, that is a privileged spot — while the
gamma2-chain keeps a velocity that may be pointing outward, flying away.
We scan hand-built corridor configs (position in channel(gamma1), velocity
outward+tangential so the landing falls in the sliver D) and Monte-Carlo
both sides. A config with h1 >> h2 (separated CIs) REFUTES (KEY) pointwise.

Part 2 — the exact identity (Lemma 4):
  r_int(g2) - r_int(g1) = E[ 1{first divergence, no prior entry}
                             * (h2(move, t_rem) - h1(freeze, t_rem)) ].
Harvest real first-divergence configs from CRN rollouts at (0.4, 0.6),
Monte-Carlo the integrand per config, and check the weighted sum against the
directly measured r_int difference — a numerical self-validation of the
identity, and the empirical distribution of the integrand (where M1 lives).

Run: PYTHONPATH=src python scripts/ring2d_key_probe.py   (~5-10 min CPU)
"""
import json
import math
import pathlib
import random
import time

from cwm.continuous.envs import RingField2D
from cwm.law import wilson_ci

G1, G2 = 0.4, 0.6
E1, E2 = RingField2D(gap=G1), RingField2D(gap=G2)
C = E1.center
H = E1.h_episode


def mc_entry(env, state, t_rem, n, seed):
    hits = 0
    for i in range(n):
        rng = random.Random(seed + i)
        s = state
        for _ in range(t_rem):
            s, _, _ = env.step(s, rng.uniform(-1.0, 1.0))
            if env.in_interior(s[0], s[1]):
                hits += 1
                break
    return hits, n


def polar_state(radius, offset, v_out, v_tang):
    """State at angle pi+offset from center, velocity in (outward, tangent)
    components (tangent = direction of increasing angle)."""
    ang = math.pi + offset
    ux, uy = math.cos(ang), math.sin(ang)          # outward radial
    tx, ty = -math.sin(ang), math.cos(ang)         # tangent
    return (C[0] + radius * ux, C[1] + radius * uy,
            v_out * ux + v_tang * tx, v_out * uy + v_tang * ty)


def in_sliver(x, y):
    d = math.hypot(x - C[0], y - C[1])
    if not (E1.r_in <= d <= E1.r_out):
        return False
    off = abs((math.atan2(y - C[1], x - C[0]) - math.pi + math.pi)
              % (2 * math.pi) - math.pi)
    return G1 / 2 < off <= G2 / 2


t0 = time.time()
out = {"script": "ring2d_key_probe.py", "g1": G1, "g2": G2}

# ---- Part 1: adversarial scan -----------------------------------------------
N_MC = 2000
adversarial = []
print("Part 1: adversarial (KEY) configs (corridor-parked vs flying-out)")
for radius in (3.55, 3.6, 3.7):
    for offset in (0.05, 0.1, 0.15):
        for v_out in (6.0, 8.0):
            for v_tang in (4.0, 5.5, 7.0):
                s = polar_state(radius, offset, v_out, v_tang)
                for a in (-0.5, 0.0, 0.5):
                    x2, y2, vx2, vy2 = E1._integrate(s, a)
                    if not in_sliver(x2, y2):
                        continue
                    freeze = (s[0], s[1], 0.0, 0.0)
                    move = (x2, y2, vx2, vy2)
                    h1, n1 = mc_entry(E1, freeze, 40, N_MC, 1_000_000)
                    h2, n2 = mc_entry(E2, move, 40, N_MC, 2_000_000)
                    p1, p1l, p1h = wilson_ci(h1, n1)
                    p2, p2l, p2h = wilson_ci(h2, n2)
                    cfg = {"radius": radius, "offset": offset,
                           "v_out": v_out, "v_tang": v_tang, "action": a,
                           "h1": p1, "h1_ci": [p1l, p1h],
                           "h2": p2, "h2_ci": [p2l, p2h],
                           "violated": p1l > p2h}
                    adversarial.append(cfg)
                    if cfg["violated"]:
                        print(f"  VIOLATION r={radius} off={offset} "
                              f"v=({v_out},{v_tang}) a={a}: "
                              f"h1={p1:.4f}[{p1l:.4f},{p1h:.4f}] > "
                              f"h2={p2:.4f}[{p2l:.4f},{p2h:.4f}]", flush=True)
out["adversarial"] = adversarial
nv = sum(c["violated"] for c in adversarial)
print(f"  scanned {len(adversarial)} sliver configs, {nv} CI-separated "
      f"violations", flush=True)

# ---- Part 2: real first-divergence distribution + identity check -----------
print("Part 2: harvesting first divergences from CRN rollouts")
N_ROLL = 6000
configs = []
ent1 = ent2 = 0
for i in range(N_ROLL):
    rng = random.Random(50_000 + i)
    s1 = s2 = E1.initial_state(rng)
    e1 = e2 = False
    div = None
    for t in range(H):
        a = rng.uniform(-1.0, 1.0)
        if div is None:
            x2, y2, vx2, vy2 = E1._integrate(s1, a)
            if in_sliver(x2, y2):
                div = {"freeze": (s1[0], s1[1], 0.0, 0.0),
                       "move": (x2, y2, vx2, vy2), "t_rem": H - t - 1,
                       "entered_before": e1}
            s1 = E1.step(s1, a)[0]
            s2 = E2.step(s2, a)[0] if div else s1
            # (before divergence s2 == s1; after, evolve separately)
        else:
            s1 = E1.step(s1, a)[0]
            s2 = E2.step(s2, a)[0]
        e1 = e1 or E1.in_interior(s1[0], s1[1])
        e2 = e2 or E2.in_interior(s2[0], s2[1])
        if e1 and e2:
            break
    ent1 += e1
    ent2 += e2
    if div is not None and not div["entered_before"]:
        configs.append(div)
p_ent1, p_ent2 = ent1 / N_ROLL, ent2 / N_ROLL
print(f"  r_int({G1})={p_ent1:.5f}  r_int({G2})={p_ent2:.5f}  "
      f"divergences={len(configs)}/{N_ROLL}", flush=True)

N_MC2 = 400
integrand = []
for k, cfg in enumerate(configs):
    h1, n = mc_entry(E1, cfg["freeze"], cfg["t_rem"], N_MC2, 3_000_000 + 10_000 * k)
    h2, _ = mc_entry(E2, cfg["move"], cfg["t_rem"], N_MC2, 4_000_000 + 10_000 * k)
    integrand.append({"t_rem": cfg["t_rem"], "h1": h1 / n, "h2": h2 / n,
                      "delta": (h2 - h1) / n})
neg = sum(1 for d in integrand if d["delta"] < 0)
mean_delta = (sum(d["delta"] for d in integrand) / len(integrand)
              if integrand else 0.0)
identity_lhs = p_ent2 - p_ent1
identity_rhs = mean_delta * len(configs) / N_ROLL
print(f"  integrand: n={len(integrand)}, negative at {neg} configs, "
      f"mean delta={mean_delta:.4f}", flush=True)
print(f"  identity check: measured r_int diff={identity_lhs:.5f}  vs  "
      f"E[1_div * delta]={identity_rhs:.5f}", flush=True)
out["first_divergence"] = {
    "n_rollouts": N_ROLL, "r_int_g1": p_ent1, "r_int_g2": p_ent2,
    "n_divergences": len(configs), "mc_per_side": N_MC2,
    "integrand": integrand, "n_negative": neg, "mean_delta": mean_delta,
    "identity_lhs": identity_lhs, "identity_rhs": identity_rhs}

out["elapsed_s"] = round(time.time() - t0, 1)
path = pathlib.Path("results/continuous_ring2d_key_probe.json")
path.write_text(json.dumps(out, indent=2))
print(f"wrote {path}  [{out['elapsed_s']}s]", flush=True)

"""Smooth learned-model probe: thesis point 3 made measurable.

Off the wall, CartWall's dynamics are EXACTLY linear in (x, v, a):
  v2 = (1 - drag*dt) * v + gain*dt * a
  x2 = x + dt * v2
so a linear least-squares model is the most favorable smooth learner
imaginable — on wall-free data it recovers the dynamics to numerical
precision. The probe trains smooth models on a wall-CONTAINING sample and
measures where their error lives: a smooth hypothesis class cannot put the
error exactly on the mode (a synthesized program can — the omitted/repaired
branch), so the contact rows tilt the fit and the error smears off-mode,
breaking the tiny-eps gate that synthesized code passes bit-exactly.

Both fitters are pure stdlib and deterministic (seeded); the MLP is a small
tanh net trained by momentum SGD — a stand-in for "a smooth learner with
capacity", not a tuned baseline (scope per the design doc: probe, not sweep).
"""
import math
import random


def _solve(a, b):
    """Gaussian elimination with partial pivoting. a: n x n, b: n."""
    n = len(a)
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        m[col], m[piv] = m[piv], m[col]
        d = m[col][col]
        for r in range(n):
            if r != col and m[r][col] != 0.0:
                f = m[r][col] / d
                for c in range(col, n + 1):
                    m[r][c] -= f * m[col][c]
    return [m[i][n] / m[i][i] for i in range(n)]


class LinearModel:
    """Least-squares [x2, v2] ~ W @ [x, v, a, 1], closed form."""

    def __init__(self, transitions):
        feats = [[t["state"][0], t["state"][1], t["action"], 1.0]
                 for t in transitions]
        self.w = []
        for k in range(2):  # x2, v2
            ys = [t["next_state"][k] for t in transitions]
            ata = [[sum(f[i] * f[j] for f in feats) for j in range(4)]
                   for i in range(4)]
            aty = [sum(f[i] * y for f, y in zip(feats, ys)) for i in range(4)]
            self.w.append(_solve(ata, aty))

    def predict(self, x, v, a):
        f = (x, v, a, 1.0)
        return (sum(wi * fi for wi, fi in zip(self.w[0], f)),
                sum(wi * fi for wi, fi in zip(self.w[1], f)))


class MLPModel:
    """3 -> hidden(tanh) -> 2, predicting the residual (x2-x, v2-v)."""

    def __init__(self, transitions, hidden=8, epochs=100, lr=0.05,
                 momentum=0.9, batch=64, seed=0):
        rng = random.Random(seed)
        data = [((t["state"][0], t["state"][1], t["action"]),
                 (t["next_state"][0] - t["state"][0],
                  t["next_state"][1] - t["state"][1])) for t in transitions]
        # input normalization from the data
        n = len(data)
        self.mu = [sum(d[0][i] for d in data) / n for i in range(3)]
        self.sd = [max(1e-9, math.sqrt(sum((d[0][i] - self.mu[i]) ** 2
                                           for d in data) / n))
                   for i in range(3)]
        s = 1.0 / math.sqrt(3)
        self.w1 = [[rng.gauss(0, s) for _ in range(3)] for _ in range(hidden)]
        self.b1 = [0.0] * hidden
        self.w2 = [[rng.gauss(0, 1.0 / math.sqrt(hidden))
                    for _ in range(hidden)] for _ in range(2)]
        self.b2 = [0.0] * 2
        vel = {"w1": [[0.0] * 3 for _ in range(hidden)], "b1": [0.0] * hidden,
               "w2": [[0.0] * hidden for _ in range(2)], "b2": [0.0] * 2}
        for _ in range(epochs):
            rng.shuffle(data)
            for start in range(0, n, batch):
                chunk = data[start:start + batch]
                g_w1 = [[0.0] * 3 for _ in range(hidden)]
                g_b1 = [0.0] * hidden
                g_w2 = [[0.0] * hidden for _ in range(2)]
                g_b2 = [0.0] * 2
                for (xi, yi) in chunk:
                    z = [(xi[i] - self.mu[i]) / self.sd[i] for i in range(3)]
                    h_pre = [sum(self.w1[j][i] * z[i] for i in range(3))
                             + self.b1[j] for j in range(hidden)]
                    h = [math.tanh(p) for p in h_pre]
                    out = [sum(self.w2[k][j] * h[j] for j in range(hidden))
                           + self.b2[k] for k in range(2)]
                    d_out = [2 * (out[k] - yi[k]) / len(chunk) for k in range(2)]
                    for k in range(2):
                        for j in range(hidden):
                            g_w2[k][j] += d_out[k] * h[j]
                        g_b2[k] += d_out[k]
                    for j in range(hidden):
                        dh = sum(d_out[k] * self.w2[k][j] for k in range(2)) \
                            * (1 - h[j] * h[j])
                        for i in range(3):
                            g_w1[j][i] += dh * z[i]
                        g_b1[j] += dh
                for j in range(hidden):
                    for i in range(3):
                        vel["w1"][j][i] = momentum * vel["w1"][j][i] - lr * g_w1[j][i]
                        self.w1[j][i] += vel["w1"][j][i]
                    vel["b1"][j] = momentum * vel["b1"][j] - lr * g_b1[j]
                    self.b1[j] += vel["b1"][j]
                for k in range(2):
                    for j in range(hidden):
                        vel["w2"][k][j] = momentum * vel["w2"][k][j] - lr * g_w2[k][j]
                        self.w2[k][j] += vel["w2"][k][j]
                    vel["b2"][k] = momentum * vel["b2"][k] - lr * g_b2[k]
                    self.b2[k] += vel["b2"][k]

    def predict(self, x, v, a):
        z = [(p - self.mu[i]) / self.sd[i] for i, p in enumerate((x, v, a))]
        h = [math.tanh(sum(self.w1[j][i] * z[i] for i in range(3)) + self.b1[j])
             for j in range(len(self.w1))]
        dx = sum(self.w2[0][j] * h[j] for j in range(len(h))) + self.b2[0]
        dv = sum(self.w2[1][j] * h[j] for j in range(len(h))) + self.b2[1]
        return (x + dx, v + dv)


class FittedModel:
    """Adapter exposing the CartWall step interface for the gate and MPC.
    Reward is the shared known spec (as for synthesized models)."""

    def __init__(self, fitted, base_env):
        self._f = fitted
        self._env = base_env
        self.a_max = base_env.a_max
        self.h_episode = base_env.h_episode

    def step(self, state, action):
        s2 = self._f.predict(state[0], state[1], action)
        return s2, self._env.reward(s2), False

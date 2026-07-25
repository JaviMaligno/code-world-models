"""T5 machine checks: the tangent-cone bound (Lemmas C/E/F and Theorem
T5-C in docs/paper3/THEORY.md). The measurement across dimensions is
scripts/t5_cone_bound.py; these are the fast guards on each lemma."""
import math
import random

from cwm.continuous.envs import ShellFieldN, thrust_vector_nd


def _kappa(L, r_out):
    return math.sqrt(L * L - r_out * r_out) / L


def test_t5_lemma_c_tangent_cone():
    # Lemma C: landing in B(c, r_out) forces the displacement into the
    # tangent cone. Checked against random points inside the ball.
    rng = random.Random(31)
    for n in (2, 3, 6):
        env = ShellFieldN(n=n)
        c = env.center()
        x0 = tuple([0.3, -0.2] + [0.0] * (n - 2))
        d = [c[k] - x0[k] for k in range(n)]
        L = math.sqrt(sum(v * v for v in d))
        e = [v / L for v in d]
        k = _kappa(L, env.r_out)
        for _ in range(300):
            # uniform-ish point in the ball B(c, r_out)
            v = [rng.gauss(0, 1) for _ in range(n)]
            nv = math.sqrt(sum(t * t for t in v))
            rad = env.r_out * rng.random() ** (1.0 / n)
            x = [c[j] + rad * v[j] / nv for j in range(n)]
            z = [x[j] - x0[j] for j in range(n)]
            nz = math.sqrt(sum(t * t for t in z))
            assert sum(z[j] * e[j] for j in range(n)) >= k * nz - 1e-9


def test_t5_lemma_f_thrust_is_exchangeable_and_sign_symmetric():
    # Lemma F's hypotheses, checked structurally: permuting or flipping
    # signs of the action permutes/flips the thrust identically, so the
    # induced law is invariant.
    rng = random.Random(17)
    n, gain, a_max = 6, 3.0, 1.0
    for _ in range(200):
        a = tuple(rng.uniform(-1, 1) for _ in range(n))
        t = thrust_vector_nd(a, gain, a_max)
        perm = list(range(n))
        rng.shuffle(perm)
        t_perm = thrust_vector_nd(tuple(a[p] for p in perm), gain, a_max)
        for j in range(n):
            assert abs(t_perm[j] - t[perm[j]]) < 1e-12
        signs = [rng.choice((1, -1)) for _ in range(n)]
        t_flip = thrust_vector_nd(tuple(s * v for s, v in zip(signs, a)),
                                  gain, a_max)
        for j in range(n):
            assert abs(t_flip[j] - signs[j] * t[j]) < 1e-12


def test_t5_lemma_e_bound_holds_on_the_real_displacement():
    # Lemma E on the actual process: P(<Z,e> >= kappa||Z||) <= 4/(n kappa^2)
    # per time step. Checked as a Monte Carlo frequency with slack.
    for n in (4, 8):
        env = ShellFieldN(n=n)
        c = env.center()
        hits = total = 0
        for i in range(400):
            rng = random.Random(2200 + i)
            s = env.initial_state(rng)
            x0 = s[:n]
            d = [c[k] - x0[k] for k in range(n)]
            L = math.sqrt(sum(v * v for v in d))
            k = _kappa(L, env.r_out)
            e = [v / L for v in d]
            for _ in range(env.h_episode):
                a = tuple(rng.uniform(-env.a_max, env.a_max)
                          for _ in range(n))
                s, _, _ = env.step(s, a)
                z = [s[j] - x0[j] for j in range(n)]
                nz = math.sqrt(sum(t * t for t in z))
                if nz == 0.0:
                    continue
                total += 1
                hits += sum(z[j] * e[j] for j in range(n)) >= k * nz
        rate = hits / total
        bound = 4.0 / (n * k * k)
        assert rate <= bound, (n, rate, bound)


def test_t5_theorem_bound_dominates_measured_contact_rate():
    # Theorem T5-C end-to-end on a small sample: r(n) <= h*4/(n kappa^2)
    for n in (3, 6):
        env = ShellFieldN(n=n)
        fired = 0
        for i in range(300):
            rng = random.Random(3300 + i)
            s = env.initial_state(rng)
            for _ in range(env.h_episode):
                a = tuple(rng.uniform(-env.a_max, env.a_max)
                          for _ in range(n))
                s, _, contact = env.step(s, a)
                if contact:
                    fired += 1
                    break
        k2 = (12.0 ** 2 - env.r_out ** 2) / 12.0 ** 2
        assert fired / 300 <= min(1.0, env.h_episode * 4.0 / (n * k2))

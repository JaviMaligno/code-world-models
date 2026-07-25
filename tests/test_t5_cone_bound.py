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


def _cap_exact(n, kappa, steps=20000):
    """P(U_1 >= kappa), U uniform on S^{n-1}, by quadrature."""
    def integ(a, b):
        h = (b - a) / steps
        s = 0.0
        for i in range(steps + 1):
            u = a + i * h
            v = 1.0 - u * u
            t = 0.0 if v <= 0.0 else math.exp(((n - 3) / 2) * math.log(v))
            s += (0.5 if i in (0, steps) else 1.0) * t
        return s * h
    return integ(kappa, 1.0) / integ(-1.0, 1.0)


def test_t5_lemma_g_cap_bound():
    # Lemma G: P(U_1 >= kappa) <= (1/2)(1-kappa^2)^((n-2)/2), n >= 3.
    kappa = _kappa(12.0, ShellFieldN(n=3).r_out)
    k2 = kappa * kappa
    for n in (3, 4, 6, 10, 20):
        assert _cap_exact(n, kappa) <= 0.5 * (1 - k2) ** ((n - 2) / 2) + 1e-15


def test_t5_isotropic_displacement_is_spherically_symmetric():
    # Theorem T5-I's engine: a sum of independent spherically symmetric
    # thrusts is spherically symmetric, so the displacement direction is
    # uniform — checked as coordinate-marginal symmetry of Z/||Z||.
    n, h = 5, 40
    rng = random.Random(23)
    m1 = [0.0] * n
    trials = 3000
    for _ in range(trials):
        vel = [0.0] * n
        pos = [0.0] * n
        for _ in range(h):
            g = [rng.gauss(0, 1) for _ in range(n)]
            ng = math.sqrt(sum(v * v for v in g)) or 1.0
            thrust = [3.0 * x / ng for x in g]
            vel = [v + (t - 0.3 * v) * 0.1 for v, t in zip(vel, thrust)]
            pos = [p + v * 0.1 for p, v in zip(pos, vel)]
        nz = math.sqrt(sum(v * v for v in pos)) or 1.0
        for k in range(n):
            m1[k] += (pos[k] / nz) ** 2 / trials
    # every coordinate of a uniform direction has E[U_k^2] = 1/n
    for k in range(n):
        assert abs(m1[k] - 1.0 / n) < 0.02, (k, m1[k])


def test_t5_theorem_i_bound_holds_on_the_isotropic_interface():
    # r(n) <= (h/2) (r_out/L)^(n-2) for the isotropic action interface
    env = ShellFieldN(n=6)
    L, h = 12.0, env.h_episode
    k2 = (L * L - env.r_out ** 2) / (L * L)
    kappa = math.sqrt(k2)
    hits, n_roll, n = 0, 400, 6
    for i in range(n_roll):
        rng = random.Random(90_000 + i)
        s = env.initial_state(rng)
        x0 = list(s[:n])
        c = env.center()
        d = [c[k] - x0[k] for k in range(n)]
        LL = math.sqrt(sum(v * v for v in d))
        e = [v / LL for v in d]
        pos, vel = list(x0), [0.0] * n
        for _ in range(h):
            a = [rng.uniform(-1, 1) for _ in range(n)]
            mag = env.gain * min(1.0, math.sqrt(sum(v * v for v in a)))
            g = [rng.gauss(0, 1) for _ in range(n)]
            ng = math.sqrt(sum(v * v for v in g)) or 1.0
            th = [mag * x / ng for x in g]
            vel = [v + (t - env.drag * v) * env.dt for v, t in zip(vel, th)]
            pos = [p + v * env.dt for p, v in zip(pos, vel)]
            z = [pos[k] - x0[k] for k in range(n)]
            nz = math.sqrt(sum(v * v for v in z))
            if nz > 0 and sum(z[k] * e[k] for k in range(n)) >= kappa * nz:
                hits += 1
                break
    assert hits / n_roll <= min(1.0, (h / 2) * (1 - k2) ** ((n - 2) / 2))


def test_t5_lemma_h_conditional_coordinate_independence():
    # Lemma H, checked EXACTLY: given the absolute values, coordinate i of
    # the displacement depends only on the i-th column of signs, so the
    # coordinates are conditionally independent. Bitwise, not statistical.
    from cwm.continuous.envs import thrust_vector_nd
    n, h, gain, a_max, dt, drag = 6, 30, 3.0, 1.0, 0.1, 0.3
    rng = random.Random(11)
    absa = [[abs(rng.uniform(-1, 1)) for _ in range(n)] for _ in range(h)]

    def disp(signs):
        vel, pos = [0.0] * n, [0.0] * n
        for s in range(h):
            a = tuple(sg * v for sg, v in zip(signs[s], absa[s]))
            t = thrust_vector_nd(a, gain, a_max)
            vel = [v + (x - drag * v) * dt for v, x in zip(vel, t)]
            pos = [p + v * dt for p, v in zip(pos, vel)]
        return pos

    base = [[rng.choice((1, -1)) for _ in range(n)] for _ in range(h)]
    z0 = disp(base)
    for _ in range(60):
        s, j = rng.randrange(h), rng.randrange(n)
        flip = [row[:] for row in base]
        flip[s][j] *= -1
        z1 = disp(flip)
        for i in range(n):
            if i != j:
                assert z1[i] == z0[i], (i, j, s)
        assert z1[j] != z0[j]      # non-vacuous: its own coordinate moves


def test_t5_transfer_scheme_is_sharp():
    # Proposition T5-T: the Chernoff scheme's optimum reproduces the
    # spherical-cap rate up to sqrt(n) — never an exponential loss.
    k2 = (12.0 ** 2 - 5.0 ** 2) / 12.0 ** 2
    g2 = (1 - k2) / k2
    for n in (8, 12, 20, 40):
        ustar = ((n - 1) - g2) / (n * g2)
        scheme = (1 - g2 * ustar) ** -0.5 * (1 + ustar) ** (-(n - 1) / 2)
        cap = (1 - k2) ** ((n - 1) / 2)
        predicted = math.sqrt(math.e * n / (1 + g2))
        assert abs(scheme / cap / predicted - 1) < 0.05, (n, scheme / cap)
        # and the optimum really is a minimum of the scheme
        for du in (0.8, 1.2):
            u = ustar * du
            if u < 1 / g2:
                assert (1 - g2 * u) ** -0.5 * (1 + u) ** (-(n - 1) / 2) \
                    >= scheme - 1e-15

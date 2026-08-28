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


def _phibar(x):
    return 0.5 * math.erfc(x / math.sqrt(2))


def test_t5_lemma_i_pointwise_inequality():
    # x0 = 1.7780 is exactly the crossover of |cos x| and exp(-x^2/2)
    x0 = 1.7780
    for i in range(1, 17781):
        x = i * 1e-4
        assert abs(math.cos(x)) <= math.exp(-x * x / 2) + 1e-12, x
    assert abs(math.cos(x0 + 2e-4)) > math.exp(-(x0 + 2e-4) ** 2 / 2)


def test_t5_lemma_i_bound_holds_on_extreme_profiles():
    # Lemma I is valid with NO weight-profile hypothesis: check from a
    # single weight (rho = 1) to many equal weights.
    import itertools
    x0, u = 1.7780, 4.76
    for cs in ([1.0], [1.0, 1.0], [1.0] + [0.05] * 9,
               [0.7 ** k for k in range(10)], [1.0] * 12):
        s2 = sum(c * c for c in cs)
        lam = u / (2 * s2)
        exact = sum(math.exp(-lam * sum(s * c for s, c in zip(sg, cs)) ** 2)
                    for sg in itertools.product((1, -1), repeat=len(cs)))
        exact /= 2 ** len(cs)
        rho = math.sqrt(s2) / max(abs(c) for c in cs)
        bound = (1 + u) ** -0.5 + 2 * _phibar(x0 * rho / math.sqrt(u))
        assert exact <= bound, (cs, exact, bound)


def test_t5_gaussian_domination_without_error_is_false():
    # The clean statement E[e^{-lam Z^2}] <= (1+2 lam sigma^2)^{-1/2} is
    # FALSE for lattice weights: the atom at 0 survives lam -> infinity.
    # Guarded so the error term is never dropped as "cosmetic".
    import itertools
    h = 8
    cs = [1.0] * h
    s2 = float(h)
    lam = 500.0 / s2                    # large lambda
    exact = sum(math.exp(-lam * sum(s for s in sg) ** 2)
                for sg in itertools.product((1, -1), repeat=h)) / 2 ** h
    gaussian = (1 + 2 * lam * s2) ** -0.5
    assert exact > gaussian, (exact, gaussian)


def test_t5_instrument_weight_profile_is_non_degenerate():
    # The transfer's remaining quantitative input: the instrument's
    # conditional weight profile has rho = sigma/c_max well above 1, so
    # Lemma I's error term is negligible at the scheme's optimum.
    from cwm.continuous.envs import thrust_vector_nd
    dt, drag, gain, a_max, h, n = 0.1, 0.3, 3.0, 1.0, 80, 6
    beta = 1 - drag * dt
    w = [(1 - beta ** (h - s)) / (1 - beta) for s in range(h)]
    rng = random.Random(7)
    worst = 99.0
    for _ in range(40):
        cols = [[0.0] * h for _ in range(n)]
        for s in range(h):
            t = thrust_vector_nd(tuple(rng.uniform(-1, 1) for _ in range(n)),
                                 gain, a_max)
            for i in range(n):
                cols[i][s] = dt * dt * w[s] * abs(t[i])
        for col in cols:
            cm = max(col)
            worst = min(worst, math.sqrt(sum(x * x for x in col)) / cm)
    assert worst > 2.0, worst
    q = (1 + 4.76) ** -0.5 + 2 * _phibar(1.7780 * worst / math.sqrt(4.76))
    assert q < 0.50, (worst, q)        # vs the sharp 0.4167


def test_t5_lemma_i_prime_subset_refinement():
    # Lemma I': the bound may be evaluated on any SUBSET of the steps,
    # because the omitted part is an independent shift whose phase has
    # modulus 1. Checked on profiles with a deliberately dominant weight,
    # which is exactly what the refinement is for.
    import itertools
    x0, u = 1.7780, 4.76
    for trial in range(24):
        rng2 = random.Random(500 + trial)
        h = rng2.randint(4, 12)
        cs = [abs(rng2.gauss(0, 1)) + 0.02 for _ in range(h)]
        if trial % 2 == 0:
            cs[0] *= 8                      # dominant weight
        s2 = sum(c * c for c in cs)
        lam = u / (2 * s2)
        exact = sum(math.exp(-lam * sum(s * c for s, c in zip(sg, cs)) ** 2)
                    for sg in itertools.product((1, -1), repeat=h)) / 2 ** h
        keep = sorted(range(h), key=lambda j: -cs[j])[1:]     # drop largest
        s2s = sum(cs[j] ** 2 for j in keep)
        cms = max(cs[j] for j in keep)
        bound = ((1 + 2 * lam * s2s) ** -0.5
                 + 2 * _phibar(x0 / (math.sqrt(2 * lam) * cms)))
        assert exact <= bound + 1e-12, (trial, exact, bound)


def test_t5_corollary_u_unconditional_exponential():
    # Corollary T5-U: rho >= 1 is Cauchy-Schwarz, and q(u,1) < 1 for EVERY
    # u > 0, with minimum 0.7783 — so the cube interface decays
    # exponentially with no probabilistic input at all.
    x0 = 1.7780

    def q(u):
        return (1 + u) ** -0.5 + 2 * _phibar(x0 / math.sqrt(u))

    for e in range(-6, 7):
        for m in range(1, 10):
            u = m * 10.0 ** e
            assert q(u) < 1.0, (u, q(u))
    best = min(q(1.0 + i * 0.001) for i in range(-900, 2000))
    assert 0.777 < best < 0.779, best
    # and rho >= 1 really is free
    for cs in ([1.0], [3.0, 0.1], [1.0] * 7, [0.2, 5.0, 1.0]):
        sigma = math.sqrt(sum(c * c for c in cs))
        assert sigma / max(abs(c) for c in cs) >= 1.0 - 1e-15


def test_t5_window_is_wide_but_not_infinite():
    # Guards the CORRECTED reading of Corollary T5-U: q(u) < 1 for all u
    # does NOT give an exponential rate by itself (sup q = 1), but the
    # window where q is bounded away from 1 is very wide. Both halves
    # matter; the first was overclaimed once and must not be again.
    x0 = 1.7780

    def q(u):
        return (1 + u) ** -0.5 + 2 * _phibar(x0 / math.sqrt(u))

    # sup over u is 1 and is NOT attained -> no uniform rate for free
    assert q(1e-8) > 0.999 and q(1e8) > 0.999
    assert max(q(1e-8), q(1e8)) < 1.0
    # but a factor-5 window around the optimum keeps q <= 0.89
    for ratio in (0.2, 0.5, 1.0, 2.0, 5.0):
        assert q(1.32 * ratio) <= 0.89, (ratio, q(1.32 * ratio))
    # and a factor-10 window keeps it <= 0.94
    for ratio in (0.1, 10.0):
        assert q(1.32 * ratio) <= 0.94, (ratio, q(1.32 * ratio))


def _S_and_w(h=80, dt=0.1, drag=0.3):
    beta = 1 - drag * dt
    w = [(1 - beta ** (h - s)) / (1 - beta) for s in range(h)]
    return w, sum(x * x for x in w)


def test_t5_lemma_k_sandwich_is_valid_and_norm_free():
    # Lemma K: A_s = w_s^2/max(1,||a_s||^2) in [w_s^2/n, w_s^2], so
    # sigma_i^2 >= (1/n) sum w_s^2 a_{s,i}^2 and m <= S/n. Checked directly.
    w, S = _S_and_w()
    rng = random.Random(19)
    for n in (4, 8, 16):
        for _ in range(20):
            cols = [0.0] * n
            low = [0.0] * n
            m_num = 0.0
            for s, ws in enumerate(w):
                a = [rng.uniform(-1, 1) for _ in range(n)]
                nrm2 = sum(x * x for x in a)
                A = ws * ws / max(1.0, nrm2)
                for i in range(n):
                    cols[i] += A * a[i] * a[i]
                    low[i] += ws * ws * a[i] * a[i] / n
                m_num += A * nrm2
            m = m_num / n
            assert m <= S / n + 1e-9
            for i in range(n):
                assert cols[i] >= low[i] - 1e-9


def test_t5_exact_chernoff_beats_the_range_bound_and_holds():
    # The exact MGF Chernoff for P(sum w^2 a^2 < z S), against (a) the
    # crude range-based multiplicative bound and (b) simulation.
    w, S = _S_and_w()

    def mgf_neg(c):
        return 1.0 if c < 1e-12 else 0.5 * math.sqrt(math.pi / c) * math.erf(
            math.sqrt(c))

    z = 0.2
    best = 1.0
    for k in range(1, 2000):
        th = k * 0.004 / (S / len(w))
        best = min(best, math.exp(th * z * S
                                  + sum(math.log(mgf_neg(th * x * x))
                                        for x in w)))
    crude = math.exp(-((1 - 3 * z) ** 2) * (S / 3)
                     / max(x * x for x in w) / 2)
    assert best < crude / 100, (best, crude)      # 300x in practice
    rng = random.Random(5)
    hits, T = 0, 20000
    for _ in range(T):
        hits += sum(ws * ws * rng.uniform(-1, 1) ** 2
                    for ws in w) < z * S
    assert hits / T <= best, (hits / T, best)     # the bound must hold


def test_t5_theorem_f_is_floor_free():
    # Theorem T5-F: with the binomial tail replacing Markov, both terms
    # decay geometrically — there is no constant floor.
    x0 = 1.7780

    def q(u):
        return (1 + u) ** -0.5 + 2 * _phibar(x0 / math.sqrt(u))

    z, K, alpha, p = 0.2, 10, 0.05, 9.72e-4
    q_max = max(q(1.32 * z), q(1.32 * K))
    main = q_max ** (1 - alpha - 1.0 / K)
    tail = (math.e * p / alpha) ** alpha
    assert main < 1.0 and tail < 1.0
    assert max(main, tail) < 0.91, (main, tail)

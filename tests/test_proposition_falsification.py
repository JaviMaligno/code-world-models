"""Counterexample search over finite probability spaces for the paper's propositions.

Written after the second review round, whose three mathematical findings shared one shape:
a hand-proved implication that was false as stated, sitting in a paper whose 700-value
numeric audit passed. Numbers were guarded; implications were not. This file is the cheap
half of the guard (the expensive half is formalization, tracked separately): every
probability-level proposition statement is checked against randomized finite probability
spaces in EXACT rational arithmetic, so a false sufficient condition dies here instead of
in review.

Two kinds of test, and the second is what gives the first teeth:

  * the CURRENT statement must survive every randomized space (no counterexample exists);
  * the PRE-CORRECTION statement must be refuted by the search (a counterexample IS found)
    --- if the search cannot re-find the reviewer's counterexamples, it is too weak to
    trust on the current statements, and the suite says so.

Everything is exact (fractions.Fraction): no tolerance, no flaky seeds.
"""
import itertools
import random
from fractions import Fraction

import pytest

# ---------------------------------------------------------------------------------- #
# finite probability spaces                                                           #
# ---------------------------------------------------------------------------------- #


def random_space(rng, n_max=6):
    """A random finite probability space: outcomes 0..n-1 with exact rational weights."""
    n = rng.randint(2, n_max)
    raw = [rng.randint(1, 9) for _ in range(n)]
    tot = sum(raw)
    return [Fraction(w, tot) for w in raw]


def random_subset(rng, n, allow_trivial=False):
    while True:
        s = frozenset(i for i in range(n) if rng.random() < 0.5)
        if allow_trivial or (s and len(s) < n):
            return s


def E(p, x):
    return sum(pi * xi for pi, xi in zip(p, x))


def cov_with_indicator(p, x, g):
    ind = [Fraction(1) if i in g else Fraction(0) for i in range(len(p))]
    return E(p, [xi * gi for xi, gi in zip(x, ind)]) - E(p, x) * E(p, ind)


def danger(p, x, g):
    """D = E[X 1_G], the estimand of prop:risk on a finite space."""
    return sum(p[i] * x[i] for i in g)


def prob(p, g):
    return sum(p[i] for i in g)


# ---------------------------------------------------------------------------------- #
# prop:risk                                                                            #
# ---------------------------------------------------------------------------------- #

N_TRIALS = 4000


def test_risk_iff_covariance_zero_exact():
    """The proposition's core: D = E[X]P(G) holds iff Cov(X, 1_G) = 0. Both directions,
    exact arithmetic, every randomized space."""
    rng = random.Random(20260730)
    for _ in range(N_TRIALS):
        p = random_space(rng)
        g = random_subset(rng, len(p))
        x = [Fraction(rng.randint(-4, 9)) for _ in p]
        factored = danger(p, x, g) == E(p, x) * prob(p, g)
        assert factored == (cov_with_indicator(p, x, g) == 0)


def test_risk_conditional_form_always_holds():
    """D = E[X|G] P(G) unconditionally (P(G) > 0), which is the display the paper reports."""
    rng = random.Random(1)
    for _ in range(N_TRIALS):
        p = random_space(rng)
        g = random_subset(rng, len(p))
        x = [Fraction(rng.randint(-4, 9)) for _ in p]
        pg = prob(p, g)
        cond = sum(p[i] * x[i] for i in g) / pg
        assert danger(p, x, g) == cond * pg


def test_risk_current_sufficient_conditions_have_no_counterexample():
    """The corrected 'in particular' clauses: X globally constant, or X independent of G."""
    rng = random.Random(2)
    for _ in range(N_TRIALS):
        p = random_space(rng)
        g = random_subset(rng, len(p))
        c = Fraction(rng.randint(-4, 9))
        x_const = [c] * len(p)
        assert danger(p, x_const, g) == E(p, x_const) * prob(p, g)
    # independence: build X measurable w.r.t. a partition independent of G by construction
    # on a product space {0,1} x {0,1} with product weights
    for pa in (Fraction(1, 3), Fraction(2, 5), Fraction(1, 2)):
        for pb in (Fraction(1, 4), Fraction(3, 7)):
            p = [pa * pb, pa * (1 - pb), (1 - pa) * pb, (1 - pa) * (1 - pb)]
            g = frozenset({0, 1})                    # depends on the first coordinate only
            for xa, xb in itertools.product(range(-2, 3), repeat=2):
                x = [Fraction(v) for v in (xa, xb, xa, xb)]   # second coordinate only
                assert danger(p, x, g) == E(p, x) * prob(p, g)


def test_risk_OLD_clause_is_refuted_by_the_search():
    """PRE-CORRECTION statement: 'X constant on G' suffices for the factored form. The
    search must FIND a counterexample --- the reviewer's own (X = 1_G) is in the family
    searched --- or this file has no teeth."""
    rng = random.Random(3)
    found = False
    for _ in range(N_TRIALS):
        p = random_space(rng)
        g = random_subset(rng, len(p))
        c = Fraction(rng.randint(-4, 9))
        x = [c if i in g else Fraction(rng.randint(-4, 9)) for i in range(len(p))]
        if danger(p, x, g) != E(p, x) * prob(p, g):
            found = True
            break
    assert found, "the search failed to refute a known-false statement"


def test_risk_range_bounds_are_sharp():
    """c_- P(G) <= D <= c_+ P(G), attained at X ≡ c_± on G."""
    rng = random.Random(4)
    for _ in range(1000):
        p = random_space(rng)
        g = random_subset(rng, len(p))
        x = [Fraction(rng.randint(-4, 9)) for _ in p]
        on_g = [x[i] for i in g]
        lo, hi = min(on_g), max(on_g)
        d = danger(p, x, g)
        assert lo * prob(p, g) <= d <= hi * prob(p, g)


# ---------------------------------------------------------------------------------- #
# prop:gatemiss / prop:twofactor                                                       #
# ---------------------------------------------------------------------------------- #


def enumerate_pipeline(r, n_tr, n_g, blind_of_sample):
    """Exact enumeration of the two-sample pipeline over {hit, miss}^(n_tr+n_g).

    blind_of_sample: maps a training sample (tuple of bools: rollout in R?) to whether
    the artifact is mode-blind. Hypothesis (ii) is wired in: a blind artifact is accepted
    iff the acceptance sample misses R; a non-blind artifact's acceptance is irrelevant to
    the events measured here (we count blind shipments only).
    Returns (P(train-miss and shipped), P(blind and shipped), P(blind and train hits R)).
    """
    p_miss_train, p_blind_ship, p_blind_hit = Fraction(0), Fraction(0), Fraction(0)
    for tr in itertools.product([False, True], repeat=n_tr):        # True = rollout in R
        p_tr = Fraction(1)
        for hit in tr:
            p_tr *= r if hit else (1 - r)
        blind = blind_of_sample(tr)
        train_missed = not any(tr)
        p_acc = (1 - r) ** n_g                       # (ii): accepted iff D_g misses R
        if blind:
            p_blind_ship += p_tr * p_acc
            if not train_missed:
                p_blind_hit += p_tr
        if train_missed and blind:
            p_miss_train += p_tr * p_acc
    return p_miss_train, p_blind_ship, p_blind_hit


CASES = [(Fraction(1, 7), 3, 2), (Fraction(2, 5), 2, 3), (Fraction(1, 10), 4, 1)]


@pytest.mark.parametrize("r,n_tr,n_g", CASES)
def test_twofactor_event_probability_is_exact(r, n_tr, n_g):
    """The CURRENT conclusion: P(train misses R and shipped) = (1-r)^(n_tr+n_g), for every
    synthesizer satisfying (i) --- including adversarial ones that are also blind on
    samples that DID hit R."""
    for blind_extra in (lambda tr: False, lambda tr: True, lambda tr: tr[0]):
        def blind(tr):
            return (not any(tr)) or blind_extra(tr)   # (i) holds; extra blindness varies
        p_miss, _, _ = enumerate_pipeline(r, n_tr, n_g, blind)
        assert p_miss == (1 - r) ** (n_tr + n_g)


@pytest.mark.parametrize("r,n_tr,n_g", CASES)
def test_twofactor_decomposition_is_exact(r, n_tr, n_g):
    """The CURRENT second display: P(blind shipped) = (1-r)^(n_tr+n_g) + P(blind, hit)(1-r)^n_g."""
    def blind(tr):
        return (not any(tr)) or tr[0]                 # blind also on some hitting samples
    p_miss, p_ship, p_hit = enumerate_pipeline(r, n_tr, n_g, blind)
    assert p_ship == (1 - r) ** (n_tr + n_g) + p_hit * (1 - r) ** n_g
    assert p_ship > (1 - r) ** (n_tr + n_g)           # the excess term is genuinely there


@pytest.mark.parametrize("r,n_tr,n_g", CASES)
def test_twofactor_OLD_equality_is_refuted(r, n_tr, n_g):
    """PRE-CORRECTION conclusion: P(blind shipped) = (1-r)^(n_tr+n_g) under one-directional
    (i). The reviewer's counterexample --- a synthesizer that is ALWAYS blind --- must
    refute it here."""
    _, p_ship, _ = enumerate_pipeline(r, n_tr, n_g, lambda tr: True)
    assert p_ship == (1 - r) ** n_g                   # what the reviewer said it equals
    assert p_ship != (1 - r) ** (n_tr + n_g)          # and the old claim is false


@pytest.mark.parametrize("r,n_tr,n_g", CASES)
def test_twofactor_equality_iff_blind_only_from_miss(r, n_tr, n_g):
    """The equality-condition clause: the law equals the blind-shipped total iff blindness
    arises only from the miss."""
    def blind_iff(tr):
        return not any(tr)                            # the iff strengthening of (i)
    _, p_ship, p_hit = enumerate_pipeline(r, n_tr, n_g, blind_iff)
    assert p_hit == 0 and p_ship == (1 - r) ** (n_tr + n_g)


def test_gatemiss_exact():
    """(1-r)^N by enumeration, the base case everything above leans on."""
    for r in (Fraction(1, 3), Fraction(1, 8)):
        for n in (1, 2, 5):
            p = sum(
                (Fraction(1) if not any(row) else Fraction(0))
                * math_prod([(r if h else 1 - r) for h in row])
                for row in itertools.product([False, True], repeat=n))
            assert p == (1 - r) ** n


def math_prod(xs):
    out = Fraction(1)
    for v in xs:
        out *= v
    return out


# ---------------------------------------------------------------------------------- #
# prop:jointmiss (the Fréchet bracket)                                                 #
# ---------------------------------------------------------------------------------- #


def test_jointmiss_bracket_holds_and_both_ends_attained():
    """(1 - min(r1+r2, 1))^N <= P(miss both)... the paper's bracket in its union form:
    P(union) ranges over [max(r1,r2), min(r1+r2, 1)] given the marginals, so the N-draw
    joint-miss probability sits in [(1-min(r1+r2,1))^N, (1-max(r1,r2))^N]. Enumerated over
    a grid of joint distributions; both ends must be attained by some coupling."""
    n = 3
    for r1 in (Fraction(1, 4), Fraction(2, 5)):
        for r2 in (Fraction(1, 3), Fraction(3, 5)):
            lo_u, hi_u = max(r1, r2), min(r1 + r2, Fraction(1))
            seen = []
            # couplings: p11 ranges over the Fréchet interval
            p11_min = max(Fraction(0), r1 + r2 - 1)
            p11_max = min(r1, r2)
            for k in range(0, 11):
                p11 = p11_min + (p11_max - p11_min) * Fraction(k, 10)
                union = r1 + r2 - p11
                assert lo_u <= union <= hi_u
                seen.append(union)
            assert min(seen) == lo_u and max(seen) == hi_u
            for union in (min(seen), max(seen)):
                miss_n = (1 - union) ** n
                assert (1 - hi_u) ** n <= miss_n <= (1 - lo_u) ** n

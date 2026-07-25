"""Golden pins for the 1D distrust-region path (paper 2, sec:mitigation).

The mitigation was generalised to n-D positions when PatchField2D was added, and
that generalisation rewrote the shared internals (`_crosses_fence`,
`_dist_to_nearest`). The paper claims the 1D cart/pendulum behaviour is bit-identical
across that change; `test_mitigation.py` pins the *no-violation* case (mitigated ==
plain MPC on a correct model) and the qualitative escape, but nothing pinned the
exact 1D outcome WITH violations — which is precisely the path the n-D rewrite
touches (fence construction, interval overlap, distance tie-break).

These are regression pins, not predictions: the values were recorded from the
implementation the paper's sweep was run with. Any future edit that perturbs the
1D path — including an n-D refactor that "should not" affect it — fails here.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from cwm.continuous import harness                      # noqa: E402
from cwm.continuous.envs import CartWall, PendulumStop, blind_of  # noqa: E402
from cwm.continuous.mitigation import run_mitigated_episode       # noqa: E402

# (instrument, eps as used by the paper's sweep, seed) -> (ret, violations,
# first_contact_step)
GOLDEN = {
    ("cart", 0.25, 3): (5.766157694922821, 1, 25),
    ("cart", 0.25, 7): (5.766191412001584, 1, 25),
    ("pendulum", 0.1, 3): (16.882082843990457, 1, 10),
    ("pendulum", 0.1, 7): (16.882097797616808, 1, 10),
}


def _env(kind):
    return CartWall(x_wall=8.0) if kind == "cart" else PendulumStop(th_stop=1.4)


def test_1d_mitigated_episodes_are_bit_identical_to_the_recorded_path():
    for (kind, eps, seed), (ret, viol, first) in GOLDEN.items():
        env = _env(kind)
        m = run_mitigated_episode(env, blind_of(env), seed=seed,
                                  n_samples=40, eps=eps)
        assert m.ret == ret, f"{kind} seed={seed}: {m.ret!r} != {ret!r}"
        assert m.violations == viol, f"{kind} seed={seed} violations"
        assert m.first_contact_step == first, f"{kind} seed={seed} first contact"


def test_one_violation_suffices_in_1d():
    """The paper's mechanism claim for the 1D instruments: a single refuted
    prediction is enough to fence the mode (contrast PatchField2D, where the
    planner rounds a fence disc and accrues several)."""
    for kind, eps in (("cart", 0.25), ("pendulum", 0.1)):
        env = _env(kind)
        for seed in (3, 7, 11, 13):
            m = run_mitigated_episode(env, blind_of(env), seed=seed,
                                      n_samples=40, eps=eps)
            assert m.violations == 1, f"{kind} seed={seed}: {m.violations}"


def test_mitigation_beats_the_pin_it_replaces():
    """Sanity direction: the mitigated run must recover materially more return
    than the pinned blind planner it replaces (the sweep's pc_mit < pc_blind)."""
    for kind, eps in (("cart", 0.25), ("pendulum", 0.1)):
        env = _env(kind)
        blind = blind_of(env)
        mit = run_mitigated_episode(env, blind, seed=3, n_samples=40, eps=eps)
        plain = harness.run_episode(env, blind, "mpc", seed=3, n_samples=40)
        assert mit.ret > 10 * plain.ret

"""Tests for the smooth learned-model probe (paper 2, step 5)."""
from cwm.continuous.envs import CartWall
from cwm.continuous.contract import collect_transitions, sample_contains_wall
from cwm.continuous.smooth_fit import LinearModel, MLPModel


def test_linear_recovers_exact_dynamics_on_wall_free_data():
    """Off the wall the dynamics are exactly linear, so LSQ on wall-free data
    must recover them to numerical precision — the most favorable smooth
    learner, and exactly as wall-blind as the synthesized blind code."""
    env = CartWall(x_wall=8.0)
    sample = collect_transitions(env, 10, seed=10_000)
    assert not sample_contains_wall(sample)
    m = LinearModel(sample)
    for t in sample[:50]:
        p = m.predict(t["state"][0], t["state"][1], t["action"])
        assert abs(p[0] - t["next_state"][0]) < 1e-9
        assert abs(p[1] - t["next_state"][1]) < 1e-9
    # wall-blind: predicts straight through the wall
    px, _ = m.predict(7.9, 4.0, 1.0)
    assert px > 8.0


def test_contact_rows_tilt_the_linear_fit():
    """A handful of contact rows breaks off-mode exactness — the smooth
    hypothesis class cannot localize the mode; the error leaks everywhere."""
    env = CartWall(x_wall=8.0)
    sample = collect_transitions(env, 40, seed=20_000)
    assert sample_contains_wall(sample)
    m = LinearModel(sample)
    off_max = max(
        max(abs(m.predict(t["state"][0], t["state"][1], t["action"])[k]
                - t["next_state"][k]) for k in range(2))
        for t in sample if not t["contact"])
    assert off_max > 1e-4  # vs ~1e-14 on wall-free data


def test_mlp_trains_and_beats_trivial_baseline():
    env = CartWall(x_wall=8.0)
    sample = collect_transitions(env, 5, seed=10_000)
    m = MLPModel(sample, hidden=4, epochs=15, seed=0)
    mlp_err, zero_err = 0.0, 0.0
    for t in sample:
        p = m.predict(t["state"][0], t["state"][1], t["action"])
        mlp_err += abs(p[0] - t["next_state"][0]) + abs(p[1] - t["next_state"][1])
        zero_err += abs(t["state"][0] - t["next_state"][0]) \
            + abs(t["state"][1] - t["next_state"][1])
    assert mlp_err < 0.5 * zero_err  # learns something real, deterministic

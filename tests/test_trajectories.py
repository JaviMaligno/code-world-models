from cwm.groundtruth import tictactoe as g
from cwm.trajectories import collect_trajectories, Trajectory

def test_collect_is_deterministic_with_seed():
    a = collect_trajectories(g, n_games=3, seed=42)
    b = collect_trajectories(g, n_games=3, seed=42)
    assert [t.action for t in a] == [t.action for t in b]

def test_trajectories_are_valid_transitions():
    traj = collect_trajectories(g, n_games=5, seed=1)
    assert len(traj) > 0
    for t in traj:
        assert isinstance(t, Trajectory)
        assert t.action in t.legal_actions
        assert g.apply_action(t.state, t.action) == t.next_state

def test_terminal_flag_matches_model():
    traj = collect_trajectories(g, n_games=5, seed=7)
    for t in traj:
        assert t.terminal == g.is_terminal(t.next_state)

import inspect
from cwm.refiner import transition_accuracy, refine_cwm, RefineResult
from cwm.groundtruth import tictactoe as g
from cwm.trajectories import collect_trajectories
from cwm.world_model import CONTRACT_TEXT
from cwm.llm.provider import FakeProvider

PERFECT = inspect.getsource(g)  # ground-truth source implements the contract

BROKEN = (
    "def initial_state():\n    return {'board':[0]*9,'current_player':1}\n"
    "def legal_actions(state):\n    return [i for i,c in enumerate(state['board']) if c==0]\n"
    "def apply_action(state, action):\n"
    "    b=list(state['board']); b[action]=99\n"   # wrong: writes 99
    "    return {'board':b,'current_player':2 if state['current_player']==1 else 1}\n"
    "def is_terminal(state):\n    return all(c!=0 for c in state['board'])\n"
    "def returns(state):\n    return {1:0.0,2:0.0}\n"
)

def test_perfect_code_scores_1():
    traj = collect_trajectories(g, n_games=5, seed=3)
    acc, failures = transition_accuracy(PERFECT, traj)
    assert acc == 1.0 and failures == []

def test_broken_code_scores_below_1():
    traj = collect_trajectories(g, n_games=5, seed=3)
    acc, failures = transition_accuracy(BROKEN, traj)
    assert acc < 1.0 and len(failures) > 0

def test_refine_stops_at_perfect_accuracy():
    traj = collect_trajectories(g, n_games=3, seed=3)
    # provider would "fix" by returning PERFECT, but starting code is already perfect
    fake = FakeProvider([f"```python\n{PERFECT}\n```"])
    res = refine_cwm(fake, "nano", CONTRACT_TEXT, PERFECT, traj, max_iters=5)
    assert isinstance(res, RefineResult)
    assert res.accuracy == 1.0 and res.iterations == 0  # already perfect, no LLM call

def test_refine_recovers_from_broken():
    traj = collect_trajectories(g, n_games=3, seed=3)
    fake = FakeProvider([f"```python\n{PERFECT}\n```"])  # one fix is enough
    res = refine_cwm(fake, "nano", CONTRACT_TEXT, BROKEN, traj, max_iters=5)
    assert res.accuracy == 1.0 and res.iterations == 1

from cwm.beacon_instrument import BeaconWrongInference, random_reach_final_rate
from cwm.groundtruth import beacon as B

T = 3
truth = B.make_beacon(T)
inst = BeaconWrongInference(T)

def test_instrument_delegates_dynamics():
    s = truth.initial_state_with(1, 0)
    assert inst.legal_actions(s) == truth.legal_actions(s)
    assert inst.apply_action(s, truth.safe(0, 1)) == truth.apply_action(s, truth.safe(0, 1))
    assert inst.is_terminal(s) == truth.is_terminal(s)
    assert inst.initial_states() == truth.initial_states()
    assert inst.observation(s, 1) == truth.observation(s, 1)

def test_instrument_correct_on_walk_states():
    # walk state (status 0): inference equals the truth
    s = {"board": [1, 1, 1, 0, 1, 0, -1, -1, 0], "current_player": 1}
    obs = inst.observation(s, 1)
    assert inst.infer_states(obs, 1) == truth.infer_states(obs, 1)

def test_instrument_flips_type_on_final_round():
    # final-round state (status 1): P2 type 0 moved (last2=0 at T=3 -> safe(2,0)=0)
    s = {"board": [3, 3, 1, 0, 1, 0, -1, -1, 1], "current_player": 1}
    obs = inst.observation(s, 1)
    truth_inf = truth.infer_states(obs, 1)
    wrong_inf = inst.infer_states(obs, 1)
    assert truth_inf[0]["board"][3] == 0                  # truth: t2 = 0
    assert wrong_inf[0]["board"][3] == 1                  # instrument flips to 1
    assert len(wrong_inf) == 1

def test_random_reach_final_rate_is_tiny():
    # P(random reaches final) = (1/2)^{2T}; at T=3 that's 1/64 ~ 0.0156. Sample loosely.
    rate = random_reach_final_rate(truth, n_games=4000, seed=0)
    assert rate < 0.05

"""Regression guards for the headline Azure-free results.

These lock in the *causal foundations* of the paper's two main empirical claims so
that a future change to the engine or oracles cannot silently turn a real result
into an artifact:

  1. play-cost (rule-blind vs truth on army5x5a + material-at-cap): the result is
     only meaningful if `gen_chess` (rule-blind) and `gen_chess_material` (truth)
     share IDENTICAL transitions and differ ONLY in `returns` at the cap. If they
     ever diverged elsewhere, the measured play deficit would be a representation
     confound rather than the material rule. We assert the isolation directly, plus
     that the material-terminal rate stays in the rare band the danger law uses.

  2. Beacon Claim A (verified-but-wrong inference is play-inadequate): the
     instrument must (a) be indistinguishable from truth to a random-trajectory
     inference gate, and (b) actually lose at play while truth-vs-truth draws. Both
     are deterministic at small T, so we check them at tiny scale.

All checks are CPU-only (no LLM) and fast.
"""
import random

from cwm.groundtruth import gen_chess as base, gen_chess_material as mat
from cwm.groundtruth import beacon as B
from cwm.beacon_instrument import BeaconWrongInference
from cwm.determinized import imperfect_arena


# --- Claim: play-cost isolates the material rule, nothing else -----------------

def test_base_and_material_share_transitions_differ_only_in_returns():
    """Across many random army5x5a games, base and material agree on
    legal_actions / is_terminal / apply_action at every state, and disagree only on
    returns (and only at terminal states). This is what makes the rule-blind-vs-
    truth play deficit attributable to the material rule alone."""
    rng = random.Random(0)
    transitions_checked = 0
    returns_diffs = 0
    for _ in range(300):
        s = base.initial_state()
        while not base.is_terminal(s):
            assert base.legal_actions(s) == mat.legal_actions(s)
            assert base.is_terminal(s) == mat.is_terminal(s)
            a = rng.choice(base.legal_actions(s))
            assert base.apply_action(s, a) == mat.apply_action(s, a)
            # non-terminal returns are 0/0 for both by contract
            assert base.returns(s) == mat.returns(s) == {1: 0.0, 2: 0.0}
            s = base.apply_action(s, a)
            transitions_checked += 1
        # at a terminal state they may differ — only via the cap material rule
        if base.returns(s) != mat.returns(s):
            returns_diffs += 1
            assert s["board"][base.N] >= base.MAX_PLIES   # difference only at the cap
            assert base.returns(s) == {1: 0.0, 2: 0.0}    # base is rule-blind: draw
    assert transitions_checked > 1000
    assert returns_diffs > 0   # the rule must actually fire on some random games


def test_material_terminal_rarity_in_danger_law_band():
    """The danger law uses the material-terminal rate as `rarity` (~2.5%). Guard it
    stays in the rare-but-present band; a value of 0 or a large value would mean the
    instrument changed character."""
    g = mat.make_material(max_plies=100, lead=1)
    rng = random.Random(0)
    hits = 0
    n = 1500
    for _ in range(n):
        s = g.initial_state()
        while not g.is_terminal(s):
            s = g.apply_action(s, rng.choice(g.legal_actions(s)))
        if g.outcome(s)[1] == "material":
            hits += 1
    rate = hits / n
    assert 0.01 < rate < 0.06, f"material-terminal rarity {rate} outside expected band"


# --- Claim A (Beacon): verified-but-wrong inference loses at play --------------

def test_beacon_instrument_passes_random_inference_gate():
    """The instrument's inference equals truth on every state a random-trajectory
    gate samples (it differs only at the final round). Random play reaches the final
    round w.p. (1/2)^{2T}, so gate-blindness REQUIRES depth: this is exactly the
    danger-law mechanism (at small T the gate catches the flip; at the experiment's
    T=8, (1/2)^16 ~ 1.5e-5, so a 2000-game gate sees zero mismatches). We assert the
    clean zero at T=8 (the reported setting)."""
    T = 8
    truth = B.make_beacon(T)
    inst = BeaconWrongInference(T)
    rng = random.Random(0)
    deals = truth.initial_states()
    mismatches = checks = 0
    for _ in range(2000):
        d = deals[rng.randrange(len(deals))]
        s = {"board": list(d["board"]), "current_player": d["current_player"]}
        while not truth.is_terminal(s):
            for p in (1, 2):
                obs = truth.observation(s, p)
                checks += 1
                if inst.infer_states(obs, p) != truth.infer_states(obs, p):
                    mismatches += 1
            s = truth.apply_action(s, rng.choice(truth.legal_actions(s)))
    assert checks > 0
    assert mismatches == 0


def test_beacon_instrument_loses_at_play_while_truth_draws():
    """Play witness of Claim A: under competent (determinized-MCTS) play, truth-vs-
    truth all-draws while the gate-passing instrument loses every decided game. The
    flip is deterministic at the final round, so this holds at small sims/games."""
    for T in (3, 4):
        truth = B.make_beacon(T)
        inst = BeaconWrongInference(T)
        fair = imperfect_arena(truth, truth, truth, simulations=40, n_games=20,
                               seeds=[0], n_determinizations=2)
        play = imperfect_arena(truth, inst, truth, simulations=40, n_games=20,
                               seeds=[0], n_determinizations=2)
        # fair baseline never loses (symmetric optimal guessing -> draws)
        assert fair["b_wins"] == 0 and fair["a_wins"] == 0
        # instrument wins nothing and loses at least most games (play-inadequate)
        assert play["a_wins"] == 0
        assert play["a_winrate"] < fair["a_winrate"]
        assert play["b_wins"] >= play["n"] // 2

"""Beacon's play_cost is EXACT: 0.5, by exhaustion (companion to the paper's
"play-cost exactness" proposition).

Part (a) — mechanical check of the proof by exhaustion, at the belief->guess
abstraction: an agent (i) plays the safe walk action derived from its own
(observed) type and (ii) in the final round guesses the opponent type returned by
its model's infer_states. There are exactly 4 equally-likely deals and 2 seatings;
all 8 games are deterministic. Verified against the ground-truth implementation:
  truth vs truth      -> draw on every deal      -> win rate exactly 1/2
  instrument (either seat) vs truth -> instrument loses every deal -> exactly 0
  => play_cost = 1/2 - 0 = 1/2, exactly.

Part (b) — planner check (NOT part of the proof): the same 8 games driven by the
actual determinized-MCTS policy on both seats reproduce the outcomes, confirming
the planner converts each belief into the corresponding guess.

Run: PYTHONPATH=src python scripts/play_cost_exact_beacon.py
"""
from cwm.groundtruth import beacon as B
from cwm.beacon_instrument import BeaconWrongInference
from cwm.determinized import determinized_policy

T = 8


def abstraction_action(truth, model, state):
    """The belief->guess abstraction: safe walk action from own (observed) type;
    final-round guess = opponent type in the model's inferred state."""
    p = state["current_player"]
    b = state["board"]
    if b[8] == 1:                                   # final round: guess
        obs = model.observation(state, p)
        dets = model.infer_states(obs, p)
        assert len(dets) == 1, "posterior must be a singleton at D"
        return dets[0]["board"][3 if p == 1 else 2]
    k = b[0] if p == 1 else b[1]                    # walk: safe action, own type
    t = b[2] if p == 1 else b[3]                    # own type is observable
    return truth.safe(k, t)


def play(truth, model_p1, model_p2, t1, t2, policy):
    s = truth.initial_state_with(t1, t2)
    move = 0
    while not truth.is_terminal(s):
        model = model_p1 if s["current_player"] == 1 else model_p2
        a = policy(truth, model, s, move)
        s = truth.apply_action(s, a)
        move += 1
    return truth.returns(s)


def sweep(truth, inst, policy, label):
    deals = [(t1, t2) for t1 in (0, 1) for t2 in (0, 1)]
    fair = [play(truth, truth, truth, t1, t2, policy)[1] for t1, t2 in deals]
    inst_p1 = [play(truth, inst, truth, t1, t2, policy)[1] for t1, t2 in deals]
    inst_p2 = [play(truth, truth, inst, t1, t2, policy)[2] for t1, t2 in deals]
    assert all(r == 0.0 for r in fair), f"{label}: fair arm must draw every deal"
    assert all(r == -1.0 for r in inst_p1 + inst_p2), \
        f"{label}: instrument seat must lose every deal"
    def winrate(payoffs):
        return sum(1.0 if r > 0 else 0.5 if r == 0 else 0.0 for r in payoffs) / len(payoffs)
    print(f"[{label}] fair win rate = {winrate(fair):.3f} (all draws); "
          f"instrument win rate = {winrate(inst_p1 + inst_p2):.3f} "
          f"(loses all {len(inst_p1 + inst_p2)} deal x seat games); "
          f"play_cost = {winrate(fair) - winrate(inst_p1 + inst_p2):.3f} EXACT", flush=True)


def main():
    truth = B.make_beacon(T)
    inst = BeaconWrongInference(T)

    # (a) proof-by-exhaustion check at the belief->guess abstraction
    sweep(truth, inst,
          lambda tr, m, s, move: abstraction_action(tr, m, s),
          "abstraction (proof)")

    # (b) planner check: the real determinized-MCTS policy on the same 8 games
    sweep(truth, inst,
          lambda tr, m, s, move: determinized_policy(
              m, s, n_determinizations=2, simulations=100, seed=1000 + move),
          "determinized MCTS (check)")

    print("DONE", flush=True)


main()

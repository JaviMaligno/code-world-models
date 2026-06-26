"""Leduc poker oracle — imperfect-information contract (core dynamics).

Cards are physical ids 0..5; rank(id)=id//2 (0,1=J;2,3=Q;4,5=K), value J<Q<K.
board (len 9): [p1_id, p2_id, community_id, round, committed_p1, committed_p2,
raises_round, acted_round, status]. community is dealt at start but hidden until
round 1. status: 0 ongoing, 1 folded, 2 showdown. Antes 1; bet 2 (round 0)/4
(round 1); max 2 raises/round. Actions: 0 fold, 1 check/call, 2 raise. returns are
NET CHIPS. observation/infer_states are added in the imperfect surface (same file).
"""
DECK = (0, 1, 2, 3, 4, 5)


def _rank(card: int) -> int:
    return card // 2


def _bet_size(rnd: int) -> int:
    return 2 if rnd == 0 else 4


def _other(p: int) -> int:
    return 2 if p == 1 else 1


def _cp_from_board(board: list) -> int:
    return 1 if board[7] % 2 == 0 else 2


def initial_states() -> list:
    out = []
    for p1 in DECK:
        for p2 in DECK:
            if p2 == p1:
                continue
            for comm in DECK:
                if comm == p1 or comm == p2:
                    continue
                out.append({"board": [p1, p2, comm, 0, 1, 1, 0, 0, 0],
                            "current_player": 1})
    return out


def initial_state() -> dict:
    return initial_states()[0]


def is_terminal(state: dict) -> bool:
    return state["board"][8] != 0


def legal_actions(state: dict) -> list:
    if is_terminal(state):
        return []
    b = state["board"]
    outstanding = b[4] != b[5]
    acts = [0, 1] if outstanding else [1]     # fold only when facing a bet
    if b[6] < 2:
        acts.append(2)
    return acts


def apply_action(state: dict, action: int) -> dict:
    b = list(state["board"])
    p = state["current_player"]
    opp = _other(p)
    rnd = b[3]
    bet = _bet_size(rnd)
    ci, oi = (4, 5) if p == 1 else (5, 4)     # committed indices for p, opp
    pre_acted = b[7]
    b[7] = pre_acted + 1
    if action == 0:                            # fold
        b[8] = 1
        return {"board": b, "current_player": opp}   # current_player = winner
    if action == 2:                            # raise: match then add bet
        b[ci] = b[oi] + bet
        b[6] += 1
        return {"board": b, "current_player": opp}   # round continues
    # action == 1: check or call
    outstanding = b[4] != b[5]
    if outstanding:                            # call closes the round
        b[ci] = b[oi]
        round_ends = True
    else:                                      # check; closes only if not the opener
        round_ends = pre_acted >= 1
    if not round_ends:
        return {"board": b, "current_player": opp}
    if rnd == 0:                               # advance to round 1
        b[3] = 1
        b[6] = 0
        b[7] = 0
        return {"board": b, "current_player": 1}
    b[8] = 2                                    # round 1 ended -> showdown
    return {"board": b, "current_player": opp}


def _showdown_winner(board: list) -> int:
    r1, r2, rc = _rank(board[0]), _rank(board[1]), _rank(board[2])
    p1pair, p2pair = (r1 == rc), (r2 == rc)
    if p1pair and not p2pair:
        return 1
    if p2pair and not p1pair:
        return 2
    if r1 > r2:
        return 1
    if r2 > r1:
        return 2
    return 0                                    # equal rank (incl. both pair) -> split


def returns(state: dict) -> dict:
    b = state["board"]
    if b[8] == 0:
        return {1: 0.0, 2: 0.0}
    if b[8] == 1:                               # fold: current_player is the winner
        winner = state["current_player"]
        folder = _other(winner)
        amt = float(b[4] if folder == 1 else b[5])
        return {winner: amt, folder: -amt}
    w = _showdown_winner(b)                      # showdown: committeds equal
    if w == 0:
        return {1: 0.0, 2: 0.0}
    amt = float(b[4])
    return {w: amt, _other(w): -amt}

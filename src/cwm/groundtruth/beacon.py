"""Beacon — a minimal deep partially-observable game (Claim A witness).

Two players, each with a hidden type t in {0,1} drawn at the deal. Phase 1 (walk):
each player must complete T "safe" steps; the safe action at own step k is
safe(k,t)=(k+t)%2 (depends on the mover's own type), and any other action is an
immediate loss. Random play survives each step w.p. 1/2 so reaches the final round
w.p. (1/2)^{2T}; optimal play reaches it w.p. 1. Phase 2 (final round): each player
guesses the opponent's hidden type (inferable from the opponent's observed moves);
scoring g==t_opponent. Net-chip returns. All chance is in the deal, so apply_action
is deterministic. observation/infer_states/registration are added in Task 2.

board (len 9): [step1, step2, t1, t2, last1, last2, guess1, guess2, status]
status: 0 walking, 1 final round, 2 P1 wins, 3 P2 wins, 4 draw.
"""


class _Beacon:
    def __init__(self, T: int):
        self.T = T

    def safe(self, k: int, t: int) -> int:
        return (k + t) % 2

    def _cp_from_board(self, board: list) -> int:
        if board[8] == 1:                              # final round
            made = (board[6] != -1) + (board[7] != -1)
            return 1 if made % 2 == 0 else 2
        return 1 if (board[0] + board[1]) % 2 == 0 else 2   # walk

    def initial_states(self) -> list:
        out = []
        for t1 in (0, 1):
            for t2 in (0, 1):
                out.append({"board": [0, 0, t1, t2, -1, -1, -1, -1, 0],
                            "current_player": 1})
        return out

    def initial_state(self) -> dict:
        return self.initial_states()[0]

    def initial_state_with(self, t1: int, t2: int) -> dict:
        return {"board": [0, 0, t1, t2, -1, -1, -1, -1, 0], "current_player": 1}

    def is_terminal(self, state: dict) -> bool:
        return state["board"][8] in (2, 3, 4)

    def legal_actions(self, state: dict) -> list:
        if self.is_terminal(state):
            return []
        return [0, 1]

    def apply_action(self, state: dict, action: int) -> dict:
        b = list(state["board"])
        p = state["current_player"]
        opp = 2 if p == 1 else 1
        if b[8] == 1:                                  # final round: a guess
            b[6 if p == 1 else 7] = action
            if b[6] != -1 and b[7] != -1:              # both guessed -> resolve
                s1 = 1 if b[6] == b[3] else 0          # P1 guesses t2
                s2 = 1 if b[7] == b[2] else 0          # P2 guesses t1
                b[8] = 2 if s1 > s2 else 3 if s2 > s1 else 4
                return {"board": b, "current_player": p}
            return {"board": b, "current_player": opp}
        # walk
        k = b[0] if p == 1 else b[1]
        t = b[2] if p == 1 else b[3]
        if action != self.safe(k, t):                  # unsafe -> immediate loss
            b[8] = 3 if p == 1 else 2                   # opponent wins
            return {"board": b, "current_player": opp}
        if p == 1:
            b[0] += 1; b[4] = action
        else:
            b[1] += 1; b[5] = action
        if b[0] == self.T and b[1] == self.T:          # both done -> final round
            b[8] = 1
        return {"board": b, "current_player": opp}

    def returns(self, state: dict) -> dict:
        st = state["board"][8]
        if st == 2:
            return {1: 1.0, 2: -1.0}
        if st == 3:
            return {1: -1.0, 2: 1.0}
        return {1: 0.0, 2: 0.0}                         # draw or non-terminal


def make_beacon(T: int = 8) -> "_Beacon":
    return _Beacon(T)

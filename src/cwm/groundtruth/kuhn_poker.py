"""Kuhn poker oracle — imperfect-information contract.

board = [p1_card, p2_card, unused_card, h0, h1, h2]:
  cards 0=J,1=Q,2=K (all distinct); unused_card is dealt to neither player.
  h0,h1,h2 = betting actions in order (-1 = not played). Action 0 = pass
  (check if no bet pending, else fold); action 1 = bet (bet if none pending,
  else call). Antes 1 each; one bet size 1.
state = {"board": board, "current_player": cp}; P1 acts first.
Hidden from player p: the opponent's card and the unused card.
returns are NET CHIPS (real-valued), positive = that player gains.
"""
CARDS = (0, 1, 2)


def initial_states() -> list:
    out = []
    for p1 in CARDS:
        for p2 in CARDS:
            if p2 == p1:
                continue
            unused = (set(CARDS) - {p1, p2}).pop()
            out.append({"board": [p1, p2, unused, -1, -1, -1], "current_player": 1})
    return out


def initial_state() -> dict:
    return initial_states()[0]


def _history(board: list) -> list:
    return [a for a in board[3:6] if a != -1]


def _cp_from_board(board: list) -> int:
    return 1 if len(_history(board)) % 2 == 0 else 2


def _terminal_kind(board: list):
    h = _history(board)
    if h == [0, 0]:
        return "showdown1"          # check-check, pot 2
    if h == [1, 0]:
        return "fold"               # bet-fold (P2 folds)
    if h == [1, 1]:
        return "showdown2"          # bet-call, pot 4
    if h == [0, 1, 0]:
        return "fold"               # check-bet-fold (P1 folds)
    if h == [0, 1, 1]:
        return "showdown2"          # check-bet-call, pot 4
    return None


def is_terminal(state: dict) -> bool:
    return _terminal_kind(state["board"]) is not None


def legal_actions(state: dict) -> list:
    if is_terminal(state):
        return []
    return [0, 1]


def apply_action(state: dict, action: int) -> dict:
    board = list(state["board"])
    for i in (3, 4, 5):
        if board[i] == -1:
            board[i] = action
            break
    return {"board": board, "current_player": 2 if state["current_player"] == 1 else 1}


def returns(state: dict) -> dict:
    board = state["board"]
    kind = _terminal_kind(board)
    if kind is None:
        return {1: 0.0, 2: 0.0}
    h = _history(board)
    if kind == "fold":
        folder = 1 if len(h) % 2 == 1 else 2      # [1,0]->P2 folds; [0,1,0]->P1 folds
        winner = 2 if folder == 1 else 1
        amt = 1.0
    else:
        winner = 1 if board[0] > board[1] else 2  # higher card; cards always distinct
        amt = 1.0 if kind == "showdown1" else 2.0
    loser = 2 if winner == 1 else 1
    return {winner: amt, loser: -amt}


def observation(state: dict, player: int) -> list:
    board = list(state["board"])
    if player == 1:
        board[1] = -1      # hide P2 card
    else:
        board[0] = -1      # hide P1 card
    board[2] = -1          # unused card hidden from both
    return board


def infer_states(obs_board: list, player: int) -> list:
    obs = list(obs_board)
    own = obs[0] if player == 1 else obs[1]
    x, y = [c for c in CARDS if c != own]         # the two cards not held by `player`
    cp = _cp_from_board(obs)
    out = []
    for a, b in [(x, y), (y, x)]:                 # both (opponent, unused) assignments
        s = list(obs)
        if player == 1:
            s[1], s[2] = a, b      # opponent card, unused
        else:
            s[0], s[2] = a, b
        out.append({"board": s, "current_player": cp})
    return out


RULES_TEXT = """\
This game is Kuhn poker (2 players).
  - board has 6 integers: [p1_card, p2_card, unused_card, h0, h1, h2].
    Cards are 0,1,2 (all three distinct); unused_card belongs to neither player.
    h0,h1,h2 are betting actions in order, -1 meaning not yet played.
  - current_player is 1 or 2; P1 acts first; players alternate.
  - Each player antes 1. Action 0 = pass (a check if no bet is pending, a fold if a
    bet is pending). Action 1 = bet (a bet of 1 if none pending, a call if pending).
  - Betting lines and outcomes:
      pass,pass            -> showdown for pot 2 (each anted 1)
      bet,pass             -> the passing player folds, the bettor wins their ante (net +1)
      bet,bet              -> showdown for pot 4
      pass,bet,pass        -> the second passing player folds (net -1 for them)
      pass,bet,bet         -> showdown for pot 4
  - At a showdown the higher card wins. returns are net chips: showdown pot 2 ->
    +1/-1; showdown pot 4 -> +2/-2; fold -> +1/-1.
  - This is imperfect information: each player sees only their own card and the
    public betting history, not the opponent's card or the unused card.
"""

POLICY_DESCRIPTION = (
    "You play Kuhn poker. board = [p1_card, p2_card, unused_card, h0, h1, h2]; you "
    "see only your own card and the betting history (others are -1). Action 0 = "
    "pass (check/fold), 1 = bet (bet/call).")

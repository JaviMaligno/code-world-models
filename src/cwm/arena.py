"""Run matches between two agents, refereed by the ground-truth model."""
from dataclasses import dataclass

@dataclass
class MatchResult:
    winner: int          # 0 draw, else player number
    illegal_by: dict     # {1: count, 2: count}
    moves: int

@dataclass
class ArenaResult:
    games: int
    cwm_wins: int
    baseline_wins: int
    draws: int
    baseline_illegal: int
    cwm_illegal: int

def play_match(referee, agent1, agent2, seed) -> MatchResult:
    agents = {1: agent1, 2: agent2}
    illegal_by = {1: 0, 2: 0}
    state = referee.initial_state()
    moves = 0
    while not referee.is_terminal(state):
        p = state["current_player"]
        legal = referee.legal_actions(state)
        action = agents[p](state, legal)
        if action is None or action not in legal:
            illegal_by[p] += 1
            return MatchResult(winner=(2 if p == 1 else 1),
                               illegal_by=illegal_by, moves=moves)
        state = referee.apply_action(state, action)
        moves += 1
    r = referee.returns(state)
    winner = 1 if r[1] > 0.5 else (2 if r[2] > 0.5 else 0)
    return MatchResult(winner=winner, illegal_by=illegal_by, moves=moves)

def run_arena(referee, cwm_agent, baseline_agent, n_games, seed) -> ArenaResult:
    cwm_wins = baseline_wins = draws = baseline_illegal = cwm_illegal = 0
    for i in range(n_games):
        cwm_is_p1 = (i % 2 == 0)   # alternate who starts
        if cwm_is_p1:
            m = play_match(referee, cwm_agent, baseline_agent, seed + i)
            cwm_player, base_player = 1, 2
        else:
            m = play_match(referee, baseline_agent, cwm_agent, seed + i)
            cwm_player, base_player = 2, 1
        cwm_illegal += m.illegal_by[cwm_player]
        baseline_illegal += m.illegal_by[base_player]
        if m.winner == 0:
            draws += 1
        elif m.winner == cwm_player:
            cwm_wins += 1
        else:
            baseline_wins += 1
    return ArenaResult(games=n_games, cwm_wins=cwm_wins, baseline_wins=baseline_wins,
                       draws=draws, baseline_illegal=baseline_illegal,
                       cwm_illegal=cwm_illegal)

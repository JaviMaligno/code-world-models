"""External-sampling MCCFR over the imperfect-information CWM contract.

Works on any module implementing the contract (initial_states, legal_actions,
apply_action, is_terminal, returns, observation): chance is the uniform deal
from initial_states() and returns are net payoffs (zero-sum dict {1: x, 2: -x}).

Info-sets are keyed by (player, tuple(observation), public action history).
The public history matters: an instantaneous observation can MERGE distinct
betting histories (in Leduc, committed/raise counters reset between rounds, so
e.g. check-bet-call and bet-call become indistinguishable in round 1), which
makes the observation-only game one of IMPERFECT RECALL -- where CFR has no
convergence guarantee and a per-branch best response overstates exploitation.
Appending the exact public action sequence restores perfect recall (each
info-set occurs in exactly one public-tree branch), so CFR converges and the
public-tree best response below is exact. Coverage analyses that need the
gate's own observation keys should PROJECT reach onto (player, observation)
afterwards.

Provides:
  - MCCFR: external-sampling regret minimization (Lanctot et al., 2009) ->
    average strategy profile.
  - expected_value(model, strategy): exact expected P1 payoff under a profile
    (full tree walk, uniform chance).
  - best_response_value(model, strategy, br_player): exact best-response value
    for br_player against the profile, via public-tree backward induction
    (states sharing the BR player's info-set are partitioned and decide one
    action per info-set, maximizing the reach-weighted group value).
  - exploitability(model, strategy) = BR_1 + BR_2 (>= 0; 0 at equilibrium).
"""
import random


def infoset_key(model, state, player, hist=()):
    """Perfect-recall info-set key: observation + exact public action history.
    Pass hist=() for games whose observation already encodes the full history
    (e.g. Kuhn), or to key by raw observation (the gate's view)."""
    return (player, tuple(model.observation(state, player)), tuple(hist))


class MCCFR:
    def __init__(self, model, seed: int = 0):
        self.model = model
        self.rng = random.Random(seed)
        self.regret: dict = {}
        self.strategy_sum: dict = {}

    def _sigma(self, key, n_actions):
        """Current strategy at an info-set via regret matching."""
        r = self.regret.setdefault(key, [0.0] * n_actions)
        pos = [max(x, 0.0) for x in r]
        tot = sum(pos)
        return [p / tot for p in pos] if tot > 0 else [1.0 / n_actions] * n_actions

    def _walk(self, state, update_player, hist=()):
        m = self.model
        if m.is_terminal(state):
            return m.returns(state)[update_player]
        cp = state["current_player"]
        actions = m.legal_actions(state)
        key = infoset_key(m, state, cp, hist)
        sigma = self._sigma(key, len(actions))
        if cp == update_player:
            utils = [self._walk(m.apply_action(state, a), update_player,
                                hist + (a,))
                     for a in actions]
            node_util = sum(s * u for s, u in zip(sigma, utils))
            reg = self.regret[key]
            for i, u in enumerate(utils):
                reg[i] += u - node_util
            return node_util
        # Opponent node: sample one action; accumulate the opponent's average
        # strategy here (external-sampling convention).
        ssum = self.strategy_sum.setdefault(key, [0.0] * len(actions))
        for i, s in enumerate(sigma):
            ssum[i] += s
        a = self.rng.choices(actions, weights=sigma)[0]
        return self._walk(m.apply_action(state, a), update_player, hist + (a,))

    def iterate(self, n_iterations: int):
        deals = self.model.initial_states()
        for _ in range(n_iterations):
            for p in (1, 2):
                d = deals[self.rng.randrange(len(deals))]
                self._walk({"board": list(d["board"]),
                            "current_player": d["current_player"]}, p)

    def average_strategy(self) -> dict:
        out = {}
        for key, ssum in self.strategy_sum.items():
            tot = sum(ssum)
            out[key] = ([x / tot for x in ssum] if tot > 0
                        else [1.0 / len(ssum)] * len(ssum))
        return out


class VanillaCFRPlus:
    """Full-tree CFR+ (Tammelin, 2014): exact counterfactual regrets (no
    sampling variance), regret-matching+ (regrets floored at zero after each
    update), and linearly-weighted strategy averaging. Far faster convergence
    per effective iteration than sampling variants on small games; same
    contract surface as MCCFR."""

    def __init__(self, model):
        self.model = model
        self.regret: dict = {}
        self.strategy_sum: dict = {}
        self.t = 0

    def _sigma(self, key, n_actions):
        r = self.regret.setdefault(key, [0.0] * n_actions)
        tot = sum(r)          # regrets are already >= 0 under RM+
        return [x / tot for x in r] if tot > 0 else [1.0 / n_actions] * n_actions

    def _walk(self, state, pi_me, pi_opp, update_player, hist=()):
        """Returns expected utility for update_player. pi_me = update player's
        own reach; pi_opp = opponent x chance reach (counterfactual weight)."""
        m = self.model
        if m.is_terminal(state):
            return m.returns(state)[update_player]
        cp = state["current_player"]
        actions = m.legal_actions(state)
        key = infoset_key(m, state, cp, hist)
        sigma = self._sigma(key, len(actions))
        if cp == update_player:
            utils = [self._walk(m.apply_action(state, a), pi_me * s, pi_opp,
                                update_player, hist + (a,))
                     for a, s in zip(actions, sigma)]
            node_util = sum(s * u for s, u in zip(sigma, utils))
            reg = self.regret[key]
            for i, u in enumerate(utils):
                reg[i] = max(reg[i] + pi_opp * (u - node_util), 0.0)  # RM+
            ssum = self.strategy_sum.setdefault(key, [0.0] * len(actions))
            for i, s in enumerate(sigma):
                ssum[i] += self.t * pi_me * s          # linear averaging
            return node_util
        return sum(s * self._walk(m.apply_action(state, a), pi_me,
                                  pi_opp * s, update_player, hist + (a,))
                   for a, s in zip(actions, sigma) if s > 0.0)

    def iterate(self, n_iterations: int):
        deals = self.model.initial_states()
        pc = 1.0 / len(deals)
        for _ in range(n_iterations):
            self.t += 1
            for p in (1, 2):
                for d in deals:
                    self._walk({"board": list(d["board"]),
                                "current_player": d["current_player"]},
                               1.0, pc, p)

    def average_strategy(self) -> dict:
        out = {}
        for key, ssum in self.strategy_sum.items():
            tot = sum(ssum)
            out[key] = ([x / tot for x in ssum] if tot > 0
                        else [1.0 / len(ssum)] * len(ssum))
        return out


def _profile_sigma(model, strategy, state, n_actions, hist=()):
    """Strategy at `state` for its mover under a profile dict (uniform fallback
    for info-sets the profile never visited)."""
    key = infoset_key(model, state, state["current_player"], hist)
    sig = strategy.get(key)
    return sig if sig is not None else [1.0 / n_actions] * n_actions


def expected_value(model, strategy) -> float:
    """Exact expected payoff for player 1 when BOTH players follow `strategy`."""
    def rec(state, prob, hist):
        if model.is_terminal(state):
            return prob * model.returns(state)[1]
        actions = model.legal_actions(state)
        sigma = _profile_sigma(model, strategy, state, len(actions), hist)
        return sum(rec(model.apply_action(state, a), prob * s, hist + (a,))
                   for a, s in zip(actions, sigma) if s > 0.0)
    deals = model.initial_states()
    pc = 1.0 / len(deals)
    return sum(rec({"board": list(d["board"]),
                    "current_player": d["current_player"]}, pc, ())
               for d in deals)


def best_response_value(model, strategy, br_player: int) -> float:
    """Exact best-response value for br_player against `strategy`, via the
    public tree: a group holds all (state, weight) sharing the public history;
    at BR-player nodes the group is partitioned by the BR player's info-set and
    each partition picks its own maximizing action."""
    def group_value(group, hist):
        state0 = group[0][0]
        if model.is_terminal(state0):
            return sum(w * model.returns(s)[br_player] for s, w in group)
        cp = state0["current_player"]
        actions = model.legal_actions(state0)
        if cp != br_player:
            # Opponent (or same public action set): branch every state by the
            # profile's strategy; public action -> one child group per action.
            total = 0.0
            for i, a in enumerate(actions):
                child = []
                for s, w in group:
                    sig = _profile_sigma(model, strategy, s, len(actions), hist)
                    if sig[i] > 0.0:
                        child.append((model.apply_action(s, a), w * sig[i]))
                if child:
                    total += group_value(child, hist + (a,))
            return total
        # BR player: partition by the BR player's perfect-recall info-set
        # (unique to this branch, so a per-partition argmax IS a valid best
        # response); each partition picks its reach-weighted best action.
        parts: dict = {}
        for s, w in group:
            parts.setdefault(infoset_key(model, s, br_player, hist),
                             []).append((s, w))
        total = 0.0
        for part in parts.values():
            total += max(
                group_value([(model.apply_action(s, a), w) for s, w in part],
                            hist + (a,))
                for a in actions)
        return total

    deals = model.initial_states()
    pc = 1.0 / len(deals)
    group = [({"board": list(d["board"]), "current_player": d["current_player"]}, pc)
             for d in deals]
    return group_value(group, ())


def exploitability(model, strategy) -> float:
    """BR_1 + BR_2 against the profile; >= 0, and 0 exactly at equilibrium."""
    return (best_response_value(model, strategy, 1)
            + best_response_value(model, strategy, 2))

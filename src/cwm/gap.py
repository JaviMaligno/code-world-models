"""Measure where a synthesized world model diverges from the ground truth.

contract_divergence compares the sandboxed CWM against the ground-truth module on
a set of states, across legal_actions / is_terminal / returns / apply_action.
collect_visited_states gathers the states MCTS expands while planning on a model.
"""
import json
import sys
from dataclasses import dataclass, field

from .mcts import mcts_policy
from .sandbox import run_in_sandbox
from .world_model import state_from_json


@dataclass
class DivergenceReport:
    n_states: int
    n_pairs: int
    legal_rate: float
    terminal_rate: float
    returns_rate: float
    transition_rate: float
    state_agreement_rate: float
    examples: list = field(default_factory=list)
    # Diagnostics for the terminal-state legal_actions convention. legal_rate and
    # state_agreement_rate exclude legal_actions on truth-terminal states (a move
    # from a finished game is undefined, and MCTS never queries legal_actions there
    # since is_terminal gates expansion). These fields keep that excluded
    # divergence visible rather than hidden.
    n_terminal: int = 0
    legal_terminal_divergences: int = 0
    # States whose CWM evaluation could not be obtained (sandbox timeout/crash on
    # the batch, even after a retry). Excluded from the rate denominators so a slow
    # CWM is never mistaken for a fully-divergent one; surfaced here so a run with
    # many of these reads as unreliable, not as a real gap.
    n_exec_errors: int = 0


def _truth_expectations(states, truth_module):
    """Compute ground-truth outputs in-process. Returns (truth_list, cases)."""
    truth, cases = [], []
    for s in states:
        try:
            legal = sorted(truth_module.legal_actions(s))
        except Exception as e:
            legal = {"__error__": repr(e)}
        term = _safe(lambda: truth_module.is_terminal(s))
        ret = _safe(lambda: {str(k): v for k, v in truth_module.returns(s).items()})
        nexts = {}
        if isinstance(legal, list):
            for a in legal:
                nexts[str(a)] = _safe(lambda a=a: truth_module.apply_action(s, a))
        truth.append({"legal": legal, "terminal": term, "returns": ret, "nexts": nexts})
        cases.append({"state": s, "actions": legal if isinstance(legal, list) else []})
    return truth, cases


def _safe(fn):
    try:
        return fn()
    except Exception as e:  # truth raising on an impossible state is itself a signal
        return {"__error__": repr(e)}


_CALL = (
    "import json\n"
    "_cases = json.loads({payload})\n"
    "_out = []\n"
    "for _c in _cases:\n"
    "    _s = _c['state']\n"
    "    _r = {{}}\n"
    "    try:\n"
    "        _r['legal'] = sorted(legal_actions(_s))\n"
    "    except Exception as e:\n"
    "        _r['legal'] = {{'__error__': repr(e)}}\n"
    "    try:\n"
    "        _r['terminal'] = is_terminal(_s)\n"
    "    except Exception as e:\n"
    "        _r['terminal'] = {{'__error__': repr(e)}}\n"
    "    try:\n"
    "        _r['returns'] = returns(_s)\n"
    "    except Exception as e:\n"
    "        _r['returns'] = {{'__error__': repr(e)}}\n"
    "    _nx = {{}}\n"
    "    for _a in _c['actions']:\n"
    "        try:\n"
    "            _nx[str(_a)] = apply_action(_s, _a)\n"
    "        except Exception as e:\n"
    "            _nx[str(_a)] = {{'__error__': repr(e)}}\n"
    "    _r['nexts'] = _nx\n"
    "    _out.append(_r)\n"
    "print(json.dumps(_out))\n"
)


def _run_chunk(cwm_code: str, cases_chunk: list, timeout: float):
    """Run the CWM on one chunk of cases in the sandbox. Returns the aligned
    `produced` list, or None if the sandbox failed/timed out or output was bad."""
    payload = json.dumps(json.dumps(cases_chunk))
    res = run_in_sandbox(cwm_code, _CALL.format(payload=payload), timeout=timeout)
    if not res.ok:
        return None
    lines = res.stdout.strip().splitlines()
    try:
        produced = json.loads(lines[-1]) if lines else None
    except json.JSONDecodeError:
        return None
    if not isinstance(produced, list) or len(produced) != len(cases_chunk):
        return None
    return produced


def contract_divergence(cwm_code: str, states: list, truth_module,
                        chunk_size: int = 1000, timeout: float = 60.0) -> DivergenceReport:
    if not states:
        return DivergenceReport(0, 0, 1.0, 1.0, 1.0, 1.0, 1.0, [])
    truth, cases = _truth_expectations(states, truth_module)

    legal_ok = legal_denom = term_ok = ret_ok = states_ok = 0
    n_terminal = legal_terminal_divergences = n_exec_errors = 0
    pairs = pairs_ok = measured = 0
    examples = []
    for start in range(0, len(states), chunk_size):
        end = start + chunk_size
        cases_chunk = cases[start:end]
        # Run the chunk; one retry at 3x timeout before giving up (a batch
        # timeout is a sizing artifact, not a per-state divergence).
        produced = _run_chunk(cwm_code, cases_chunk, timeout)
        if produced is None:
            produced = _run_chunk(cwm_code, cases_chunk, timeout * 3)
        if produced is None:
            n_exec_errors += len(cases_chunk)
            if len(examples) < 10:
                examples.append(
                    f"exec error: chunk states[{start}:{end}] "
                    f"failed/timed out in sandbox")
            continue
        for st, tr, got in zip(states[start:end], truth[start:end], produced):
            measured += 1
            truth_terminal = tr["terminal"] is True
            t_ok = got.get("terminal") == tr["terminal"]
            r_ok = got.get("returns") == tr["returns"]
            # legal_actions on a finished game is undefined and never used by MCTS
            # (is_terminal gates expansion), so exclude it from the gap on terminal
            # states; track the divergence separately as a diagnostic.
            if truth_terminal:
                n_terminal += 1
                l_ok = True
                if got.get("legal") != tr["legal"]:
                    legal_terminal_divergences += 1
            else:
                l_ok = got.get("legal") == tr["legal"]
                legal_ok += l_ok
                legal_denom += 1
            trans_ok = True
            for a_str, exp in tr["nexts"].items():
                pairs += 1
                if got.get("nexts", {}).get(a_str) == exp:
                    pairs_ok += 1
                else:
                    trans_ok = False
            term_ok += t_ok
            ret_ok += r_ok
            if l_ok and t_ok and r_ok and trans_ok:
                states_ok += 1
            elif len(examples) < 10:
                examples.append(
                    f"state={st} legal_ok={l_ok} terminal_ok={t_ok} "
                    f"returns_ok={r_ok} transitions_ok={trans_ok}")
    n = measured  # rate denominators exclude exec-errored states
    return DivergenceReport(
        n_states=n, n_pairs=pairs,
        legal_rate=(legal_ok / legal_denom) if legal_denom else 1.0,
        terminal_rate=(term_ok / n) if n else 0.0,
        returns_rate=(ret_ok / n) if n else 0.0,
        transition_rate=(pairs_ok / pairs) if pairs else 1.0,
        state_agreement_rate=(states_ok / n) if n else 0.0, examples=examples,
        n_terminal=n_terminal,
        legal_terminal_divergences=legal_terminal_divergences,
        n_exec_errors=n_exec_errors)


def inference_accuracy(cwm_code: str, states: list, truth_module,
                       timeout: float = 10.0) -> dict:
    """Verify a synthesized imperfect-info CWM's observation() and infer_states()
    against the truth on sampled full states, for both players. Order-insensitive
    MULTISET-equality on the inferred states (sorted tuples, no dedup) — so a
    membership-valid-but-skewed/duplicated set is caught, not just a missing one;
    errors count as mismatches, not silent passes."""
    if not states:
        return {"n": 0, "observation_rate": 1.0, "inference_rate": 1.0,
                "n_exec_errors": 0, "examples": []}
    # truth expectations (in-process)
    def _canon(stlist):
        return sorted(tuple(s["board"]) for s in stlist)
    truth = []
    for s in states:
        row = {}
        for p in (1, 2):
            o = truth_module.observation(s, p)
            row[p] = {"obs": o, "infer": _canon(truth_module.infer_states(o, p))}
        truth.append(row)
    cases = [{"state": s} for s in states]
    payload = json.dumps(json.dumps(cases))
    call = (
        "import json\n"
        f"_cases = json.loads({payload})\n"
        "_out = []\n"
        "for _c in _cases:\n"
        "    _s = _c['state']\n"
        "    _r = {}\n"
        "    for _p in (1, 2):\n"
        "        _e = {}\n"
        "        try:\n"
        "            _o = observation(_s, _p)\n"
        "            _e['obs'] = _o\n"
        "        except Exception as ex:\n"
        "            _e['obs'] = {'__error__': repr(ex)}; _o = None\n"
        "        try:\n"
        "            _inf = infer_states(_o, _p) if _o is not None else None\n"
        "            _e['infer'] = sorted([tuple(x['board']) for x in _inf]) if _inf is not None else {'__error__': 'no obs'}\n"
        "        except Exception as ex:\n"
        "            _e['infer'] = {'__error__': repr(ex)}\n"
        "        _r[str(_p)] = _e\n"
        "    _out.append(_r)\n"
        "print(json.dumps(_out))\n"
    )
    res = run_in_sandbox(cwm_code, call, timeout=timeout)
    lines = res.stdout.strip().splitlines() if res.ok else []
    try:
        produced = json.loads(lines[-1]) if lines else None
    except json.JSONDecodeError:
        produced = None
    if not isinstance(produced, list) or len(produced) != len(states):
        return {"n": 0, "observation_rate": 0.0, "inference_rate": 0.0,
                "n_exec_errors": len(states),
                "examples": [(res.stderr or "malformed output")[-200:]]}

    obs_ok = inf_ok = measured = 0
    examples = []
    for st, tr, got in zip(states, truth, produced):
        for p in (1, 2):
            measured += 1
            g = got.get(str(p), {})
            # observation: JSON round-trips lists fine; compare directly
            if g.get("obs") == tr[p]["obs"]:
                obs_ok += 1
            elif len(examples) < 10:
                examples.append(f"obs mismatch state={st['board']} p={p} got={g.get('obs')}")
            # inference: truth infer is list[tuple]; sandbox gives list[list]
            got_inf = g.get("infer")
            norm = sorted(tuple(x) for x in got_inf) if isinstance(got_inf, list) else got_inf
            if norm == tr[p]["infer"]:
                inf_ok += 1
            elif len(examples) < 10:
                examples.append(f"infer mismatch state={st['board']} p={p} got={got_inf}")
    n = measured
    return {"n": n, "observation_rate": obs_ok / n, "inference_rate": inf_ok / n,
            "n_exec_errors": 0, "examples": examples}


def collect_visited_states(model, n_games: int, simulations: int, seed: int,
                           cap: int = 20000) -> list:
    """States MCTS expands while self-playing `model` against itself."""
    visited: set = set()
    for g in range(n_games):
        state = model.initial_state()
        move = 0
        while not model.is_terminal(state):
            a = mcts_policy(model, state, n_simulations=simulations,
                            seed=seed + g * 1000 + move, visited=visited)
            state = model.apply_action(state, a)
            move += 1
            if len(visited) >= cap:
                break
        if len(visited) >= cap:
            print(f"collect_visited_states: hit cap {cap}; stopping early",
                  file=sys.stderr)
            break
    return [state_from_json(s) for s in list(visited)[:cap]]

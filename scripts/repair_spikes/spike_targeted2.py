"""Decisive targeted-generation run: does generating MANY discriminating
transitions close the gap (winrate -> ~0.50)? Dose-response: 0 -> 0.28,
35 -> 0.42; try ~120. Also a control: COMPLETE rules + targeted (isolates whether
the residual is a data problem or the model's inference limit).
"""
import os, random
from dotenv import load_dotenv
load_dotenv("/Users/javieraguilarmartin1/Documents/repos/code-world-models/.env", override=True)

from cwm.groundtruth import gen_chess, gen_chess_material as mat
from cwm.world_model import build_contract
from cwm.trajectories import collect_trajectories, Trajectory
from cwm.llm.azure_openai import AzureOpenAIProvider
from cwm.synthesizer import synthesize_cwm
from cwm.refiner import refine_cwm
from cwm.run_gap import _load_module_from_code, _play_performance

provider = AzureOpenAIProvider(
    endpoint=os.environ["AZURE_OPENAI_ENDPOINT"], api_key=os.environ["AZURE_OPENAI_API_KEY"],
    api_version=os.environ["AZURE_OPENAI_API_VERSION"])
MODEL = os.environ["AZURE_DEPLOYMENT_MINI"]
SEED = 1


def material(b):
    return sum(1 for v in b[:25] if v in (1, 2, 3)), sum(1 for v in b[:25] if v in (4, 5, 6))


def constructed_disc(n, seed=0):
    rng = random.Random(seed); out = []
    while len(out) < n:
        cells = [0] * 25
        pos = rng.sample(range(25), rng.randint(4, 9))
        cells[pos[0]] = 1; cells[pos[1]] = 4
        extras = pos[2:]; n1 = rng.randint(0, len(extras))
        for i, c in enumerate(extras):
            cells[c] = rng.choice([2, 3]) if i < n1 else rng.choice([5, 6])
        p1, p2 = material(cells)
        if p1 == p2:
            continue
        s = {"board": cells + [99], "current_player": rng.choice([1, 2])}
        legal = mat.legal_actions(s)
        if not legal:
            continue
        a = rng.choice(legal); nxt = mat.apply_action(s, a)
        out.append(Trajectory(state=s, action=a, next_state=nxt, reward=mat.returns(nxt),
                              terminal=mat.is_terminal(nxt), legal_actions=legal))
    return out


def synth_eval(contract, traj, label, max_iters=12):
    code, _ = synthesize_cwm(provider, MODEL, contract, traj)
    refined = refine_cwm(provider, MODEL, contract, code, traj, max_iters=max_iters)
    cwm = _load_module_from_code(refined.code)
    cells = [0] * 25; cells[2] = 1; cells[5] = 2; cells[6] = 3; cells[22] = 4
    rs = {"board": cells + [mat.MAX_PLIES], "current_player": 1}
    try:
        rr = cwm.returns(rs); learned = (rr.get(1) == 1.0 and rr.get(2) == -1.0)
    except Exception as e:
        learned = f"err {e!r}"
    play = _play_performance(mat, cwm, sims=400, n_games=40, seed=SEED)
    print(f"  [{label}] acc={refined.accuracy:.4f} iters={refined.iterations} "
          f"rule_learned={learned} winrate={play['cwm_winrate']:.2f} "
          f"({play['cwm_wins']}W/{play['draws']}D/{play['truth_wins']}L)", flush=True)


random_traj = collect_trajectories(mat, n_games=40, seed=SEED)
incomplete = build_contract(gen_chess.RULES_TEXT)
complete = build_contract(mat.RULES_TEXT)

print("=== targeted dose-response (INCOMPLETE rules) ===", flush=True)
synth_eval(incomplete, constructed_disc(120) + random_traj, "incomplete + 120 targeted")

print("\n=== control: COMPLETE rules + targeted (isolate data vs inference limit) ===", flush=True)
synth_eval(complete, constructed_disc(120) + random_traj, "complete + 120 targeted")

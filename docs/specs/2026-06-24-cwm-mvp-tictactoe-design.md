# Design Spec — Code World Models vs LLM-as-Policy (MVP: Tic-Tac-Toe)

**Date:** 2026-06-24
**Status:** Approved design — pending implementation plan
**Repo:** `code-world-models` (new, Python)

## 1. Purpose & Thesis

Reproduce, at small scale, the central result of *Code World Models for
General Game Playing* (DeepMind, arXiv:2510.04542): **offloading reasoning to
synthesized, verifiable code plus classical search beats scaling the model as a
direct policy.**

The headline comparison the whole project builds toward:

> A **small** model that synthesizes a world model in code + MCTS **vs** a
> **large** model used as a direct policy (LLM-as-policy).

This spec covers **only the MVP**: the same loop end-to-end on **tic-tac-toe**,
without OpenSpiel. The MVP's job is **not** to win at tic-tac-toe (trivial) but
to:

1. Validate the full pipeline works (synthesis → refinement → search → arena).
2. Produce **real token/cost numbers** to extrapolate to Connect Four and poker
   before committing to expensive runs.

## 2. Key Decisions (locked)

- **Language:** Python.
- **Models (subjects of the experiment):** Azure OpenAI GPT-5.4 family —
  `gpt-5.4` (large) as the baseline policy; `gpt-5.4-nano`/`gpt-5.4-mini` as the
  CWM synthesizer. Same family, different sizes → clean size-vs-performance
  curve.
- **Cost gate:** measure real tokens on the tic-tac-toe MVP, extrapolate, and
  *then* decide whether to keep the baseline on the API or move it to a
  subscription (**Plan B: baseline via Codex**). The baseline is the
  token-hungry role (one call per turn × N games), so it is the cost driver.
  - Plan B note: Codex CLI can pin the model (`--model` / `~/.codex/config.toml`).
    If activated, **verify `gpt-5.4` (and small variants) are available via the
    Codex subscription** so we keep the same family *and* version. Not blocking
    now.
- **Provider abstraction from day 1:** a thin `LLMProvider` interface so
  `AzureOpenAIProvider` (now) and `CodexProvider` (Plan B) are interchangeable
  without rewriting the harness. `model` is a parameter, not hardcoded.
- **Sandbox from day 1:** generated code always runs in a subprocess with a
  timeout, no network, no disk. Mandatory even though tic-tac-toe is harmless.
- **No "training":** there is no fine-tuning. The LLM is used for inference only
  (code synthesis + refinement). Heavy compute is the MCTS search (CPU).

## 3. Architecture — Components

Each component is an isolated, independently testable module.

| Module | Responsibility | Depends on |
|--------|----------------|-----------|
| `groundtruth` | Hand-written tic-tac-toe. The oracle: generates real trajectories, referees the arena, and is the reference the CWM is validated against. **Not** shown to the LLM. | — |
| `trajectory_collector` | Plays random-vs-random on the ground truth; stores trajectories `(state, action, next_state, reward, terminal, legal_actions)`. | `groundtruth` |
| `llm_provider` | `LLMProvider.complete(messages, model) -> (text, usage)`. Impl: `AzureOpenAIProvider`. Later: `CodexProvider`. Records token usage. | — |
| `cwm_synthesizer` | Sends rules description + trajectories to the LLM; gets back Python implementing the world model (transition, legal actions, reward, termination). | `llm_provider` |
| `sandbox` | Runs generated code in a subprocess: timeout, no network, no disk. Returns result or stack trace. | — |
| `test_refiner` | Generates unit tests from trajectories ("from S, action A → S' and reward R"); runs the CWM in the sandbox; feeds failing stack traces back to the LLM until **transition accuracy 1.0** or budget exhausted. Records iteration count. | `sandbox`, `cwm_synthesizer` |
| `mcts` | Classical Monte Carlo Tree Search planner that plays using the synthesized CWM. | (the synthesized CWM) |
| `baseline` | LLM-as-policy: each turn receives board + legal actions, returns a move (`gpt-5.4`). | `llm_provider` |
| `arena` | Runs N games CWM+MCTS vs baseline, alternating who starts; logs outcomes and metrics. | `groundtruth`, `mcts`, `baseline` |
| `cost_meter` | Aggregates token usage in/out by role (synthesis vs baseline), estimates USD, extrapolates to larger games. | `llm_provider` usage data |

## 4. Data Flow

```
groundtruth ──> trajectory_collector ──> trajectories
                                              │
                          ┌───────────────────┤
                          ▼                   ▼
                 cwm_synthesizer ──> CWM code  test_refiner (loop, sandboxed)
                          ▲                   │  until transition accuracy = 1.0
                          └─── stack traces ──┘
                                              │
                                       verified CWM
                                              │
                                              ▼
                        mcts (CWM+MCTS agent) ── plays ──┐
                                                         ▼
                              arena  ◄──── baseline (LLM-as-policy)
                                │
                                ▼
              metrics + cost_meter ──> results (win/draw/loss, illegal-move
                                       rate, refinement iters, tokens, $)
```

## 5. Metrics

- **Win / draw / loss** of CWM+MCTS vs baseline. *Caveat:* with perfect play
  tic-tac-toe is almost always a draw, so this number is weakly discriminative
  here. The strong win-rate signal arrives with Connect Four.
- **Baseline illegal-move rate** — the paper's core argument; expected to be the
  most telling metric on tic-tac-toe.
- **Refinement iterations to accuracy 1.0** — how hard the synthesis was.
- **Tokens and USD by role** — the cost-gate deliverable that drives the
  API-vs-Codex decision.

## 6. Expected Result (to avoid fooling ourselves)

On tic-tac-toe with perfect play, expect mostly draws. The thesis shows
*qualitatively*: CWM+MCTS never loses and never plays illegally; the direct
baseline sometimes does. A strong quantitative win-rate is a Connect Four goal;
tic-tac-toe is pipeline validation + cost measurement.

## 7. Out of Scope (MVP)

- OpenSpiel integration.
- Imperfect-information games / inference function (poker).
- Connect Four (next milestone, reuses this loop).
- TextArena / public Elo submission.
- Heuristic value functions to accelerate search.

These are deliberately deferred; the loop built here is designed to extend to
them.

## 8. What's needed to *run* (not to build)

- Azure OpenAI access: endpoint + deployment names for `gpt-5.4`,
  `gpt-5.4-mini`, `gpt-5.4-nano`. API keys go in `.env` (never read by the
  assistant).

## 9. Open Questions / Risks

- Exact Azure deployment names and whether all three sizes are deployed.
- Whether nano is strong enough to synthesize a correct tic-tac-toe CWM (if not,
  it's itself an interesting data point about the lower bound of the synthesizer).
- Plan B viability: GPT-5.4 availability via Codex subscription.
- Sandbox hardening level for the MVP (start: subprocess + timeout + no
  net/disk; harden further before any complex game).

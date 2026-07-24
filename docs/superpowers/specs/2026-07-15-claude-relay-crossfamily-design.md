# Design: third model family for the continuous synthesis arms (Claude, agent-relayed)

Date: 2026-07-15
Branch: `claude/continuous-setting-feasibility-wktp6b`
Status: approved direction (user-ordered A2); design mirrors paper 1's protocol

## Problem

Paper 2's cross-family evidence is one alternate family (Qwen, 3 seeds per
instrument). Paper 1 answered the same critique with a third family — Claude
Sonnet, agent-relayed with pipeline-identical messages
(`scripts/crossfamily_claude_step.py`) — and documented the wrapper artifacts
honestly. This project replicates that protocol on the continuous instruments.

## Protocol (mirror of paper 1's)

New `scripts/continuous_claude_step.py`, a manual-transport harness driving
the EXACT `cwm.continuous.contract` pipeline step by step:

- `init SEED OUTDIR [--instrument cart|pendulum] [--arm incomplete|full]`:
  collect the N=40 rollout sample for that seed (the gate sample, as in
  `synthesize_and_evaluate`), build the contract (mode clause omitted for the
  incomplete arm), build the synthesis messages via
  `build_synthesis_messages`, and write `OUTDIR/{tag}_seed{S}_msg0.txt`
  containing the verbatim system+user messages. Also record
  `sample_contains_wall` for the seed.
- `check SEED OUTDIR ITER CODEFILE [--instrument ...] [--arm ...]`: run
  `contract_accuracy(code, transitions, eps=1e-9)` on the SAME sample; if
  acc < 1.0 and ITER < 5, write the next refinement message (verbatim
  `refine_continuous` format, same failure lines) to `..._msg{ITER+1}.txt`;
  otherwise classify exactly as `synthesize_and_evaluate` does
  (gate_accuracy, gate_passed, wall_blindness via `mode_blindness`) and — if
  the gate passed — run the 6 paired MPC play episodes against the shared
  baselines and append the full cell (incl. play_cost, contact rate, the
  code, and the relay transcript paths) to `OUTDIR/claude_results.json`.
- Determinism: seeds/knobs identical to the Qwen spot-checks (headline
  cells: cart x_wall=8, pendulum th_stop=1.4; seeds 10000/20000/30000 —
  the same 1-absent + 2-present split the Qwen runs had).

## The relay

The controller dispatches, per message, a FRESH context-free Claude (Sonnet)
subagent whose entire prompt is the pipeline message text embedded directly
(paper 1's lesson: file-plus-"output only code" patterns triggered
anti-injection refusals; embedding the content avoids it). The subagent's
reply is saved verbatim as `..._reply{ITER}.txt` and its code block fed to
`check`. Any refusal / wrapper artifact is recorded, not retried silently
(paper 1 recorded two refusals as agent-wrapper behavior).

Methodological honesty (for the paper): this is an AGENT-relayed arm — the
completion comes from a Claude model inside an agent scaffold, not a raw API
call; pipeline messages are byte-identical to the API arms'; the transport
and its artifacts are documented. Same scoping language as paper 1.

## Scope

- Cells: cart x_wall=8 incomplete (3 seeds) + pendulum th_stop=1.4 incomplete
  (3 seeds) + one full-arm control seed per instrument (translation check).
- Up to 5 refinement iterations per seed (pipeline default), ≈ 8–48 relays
  total.
- Output: `results/continuous_claude_relay.json` (one entry per seed, same
  schema as the synthesis cells plus relay-transcript pointers) — committed,
  along with the message/reply transcripts under
  `results/claude_relay_transcripts/` (they are the audit trail).

## Paper integration

- §6 cross-family paragraphs (both files): "two further families" → the
  Claude row joins the Qwen row; report per-branch outcomes (absent →
  blind&exploited expected by Prop 2 regardless of family; present → repairs
  or stalls, THE model-dependent question). Update the "repair is
  model-dependent" sentence with the third family's result either way.
- §9 cross-family limitation updated (three families, still spot-checks).
- EXPERIMENTS.md dated entry with the table + wrapper-artifact notes.
- Guard clean on both papers.

## Out of scope

- More seeds per family (this matches the Qwen n for symmetry).
- Anthropic API arm (no key available; the relay IS the protocol, as paper 1).
- DeepSeek or further families.

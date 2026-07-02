# Experiments Log

## Synthesis sweep at 20 seeds/cell — 6/6 upgraded to 20/20, zero crashes (2026-07-02)

`python3.12 scripts/danger_synthesis_sweep.py {mini,large} 20` under the new
crash/blind/aware semantics (crashes excluded from denominators) and the
corrected contract. 120 syntheses total (2 sizes × 3 N × 20 seeds), each with
≤6 fresh-batch refinement iterations. Results JSON (per-seed, auditable):
`results/danger_synthesis_{mini,large}.json`.

| N | mini rule-blind | large rule-blind | initial-batch floor (1−r)^N |
|---|---|---|---|
| 40  | **20/20 = 1.000** [Wilson LB 0.839] | **20/20 = 1.000** | 0.363 |
| 120 | **20/20 = 1.000** | **20/20 = 1.000** | 0.048 |
| 200 | **20/20 = 1.000** | **20/20 = 1.000** | 0.006 |

**Zero crashes, zero aware, in all 120 runs** — the published 6/6 table is
confirmed at 3.3× the denominator, and the crash-vs-blind methodological
concern is resolved empirically: nothing was ever conflated. Wilson 95% lower
bound on the rule-blind rate rises from ~0.61 (6/6) to **0.839** (20/20).
Gate-accuracy detail: at N=200 large, 0/20 seeds reach gate 1.0 (the rule is in
every sample) yet all 20 are blind — the cleanest (b)-residual cell. At N=120,
6/20 mini and 3/20 large reach gate 1.0 while blind, matching the compounded
per-batch miss rate (≈0.29 over up to 7 batches of (1−r)^120 = 0.048).
Paper updated: tab:synthcurve (20/20 + caption), "On the floor" paragraph
(gate-accuracy narrative re-derived from the 20-seed data). Cost: ~$3-8 Azure,
~2.5 h wall (mini+large chained).

## Mechanism reach at n=120 — the small-sample caveat is retired (2026-07-02)

`python scripts/play_cost_reach.py --games 120` (CPU-only, MCTS 300 sims). Triples
the sample of the §4 mechanism measurement (was n=40):

| cap | competent reach (n=40 → n=120) | random reach (n=40 → n=120) |
|---|---|---|
| 30  | 0.200 → 0.183 [0.124, 0.262] | 0.375 → **0.442** [0.356, 0.531] |
| 60  | 0.200 → 0.242 [0.174, 0.326] | 0.200 → 0.133 [0.084, 0.206] |
| 100 | 0.225 → 0.275 [0.203, 0.361] | 0.075 → 0.067 [0.034, 0.126] |

The story sharpens: competent reach stays flat (Wilson 95% intervals overlap
pairwise — no trend resolved), while random reach falls 6.6× (0.442 → 0.067,
CI-separated end to end; at n=40 the drop was 5×). Paper §4 remark + Figure 3
(make_paper_figures.py) + the §6.4 consistency check updated (reach at the
deployed cap is 0.275, so the omitted rule flips ~half of the games that reach
the region, not ~two-thirds). Cost: $0 (CPU), ~50 min.

## Contract-fix rerun: the `infer_states` crash is gone in all three games (2026-07-02)

Rerun of the three imperfect-info probes under the corrected contract (parameter
renamed `observation` -> `obs` + anti-shadowing note; see the root-cause entry
below). Azure GPT-5.4; single seed per probe, matching the original runs.

| Probe | arm | transition gate | observation_rate | inference_rate | exec_err |
|---|---|---|---|---|---|
| masked TTT (large) | full | 1.000 (0 iters) | 1.000 | **1.000** (was: crash) | **0** |
| masked TTT (large) | withheld | 1.000 | 0.020 | 0.180 | **0** |
| Kuhn (mini) | — | **1.000 (0 iters)** (was: 0.845 fail) | 0.500 (p2 obs-index convention, wrong-but-running) | **1.000** (was: crash) | **0** |
| Beacon T=6 (large) | full | 0.456 (10 iters, fails gate) | 1.000 | 0.200 | **0** |
| Beacon T=6 (large) | withheld revelation | **1.000** (2 iters) | 1.000 | **0.000** | **0** |

**Findings.** (1) Zero execution errors across all three games — the recurring
`'list' object is not callable` was entirely our contract's name collision, as
diagnosed; the "synthesis-robustness failure" narrative is retracted in the paper
(§6.6 correction paragraph). (2) The masked-TTT withheld rates are unchanged
(0.020/0.180) and the full arm's `infer_states` is now **exact** — inference_rate
becomes a second clean discriminator (1.000 vs 0.180). (3) Kuhn mini now passes
both gates and plays at parity (0.470 = fair 0.470); its only divergence is a
player-2 observation-index convention (obs 0.500), not a crash. (4) **Bonus:
synthesized gate-blindness corroboration on Beacon** — the withheld-revelation
arm passes the transition gate at 1.000 with inference_rate 0.000: a
transition-certified, belief-wrong CWM, synthesized end-to-end (single-seed
probe; the full arm fails the transition gate at 0.456, reported honestly).

Paper updated: tab:kuhn (mini row), tab:mtt (full-arm inference 1.000), §6.6
rewritten (both discriminators + correction paragraph + Beacon corroboration),
§8 scope note, contribution 5, §2.4 metric definitions (exec-error exclusion).
Log: scratchpad `llm_chain.log`. Cost: <$1.

## Limitations roadmap — CPU-vs-LLM triage of §7 (2026-07-02)

Triage of every paragraph in the paper's *Limitations and Honest Assessment*
(§7 of `main.tex`), split by whether follow-up work needs the LLM (Azure, must
be run locally with credentials) or is CPU-only (pure-Python MCTS, runnable in
CI/here). This commit lands the CPU-only *enablers*; the long reruns and all
LLM work are listed for local execution.

**Enablers landed in this commit (CPU-only, no result numbers changed):**
- `src/cwm/llm/azure_openai.py`: `max_retries=6` (was the SDK default 2) and a
  120 s timeout, both constructor-overridable. The openai SDK does exponential
  backoff and honours `Retry-After`; the previous ceiling was too low to ride
  out sustained 429s on multi-hour synthesis sweeps. This is the prerequisite
  for every LLM rerun below.
- `src/cwm/law.py`: new `t_crit_95(df)` — two-sided 95% Student-t critical
  values for any df (table to 120, conservative round-down, normal-ish tail).
  Removes the per-script hardcoded dicts that capped at ~6 seeds.
- `scripts/play_cost_ci.py`: `--seeds/--games/--sims` (defaults reproduce the
  published n=600); uses `t_crit_95`, so the seed-clustered interval is no
  longer limited to <=6 seeds. **Bug fixed:** the old code indexed its t table
  by the seed *count* k, i.e. it used the df=5 critical value (2.571) for a
  paired-t over 5 seeds whose correct df is 4 (2.776). The published clustered
  interval `[0.086, 0.175]` was computed with the wrong df; the correct df=4
  interval is **`[0.083, 0.179]`** (still excludes zero — the conclusion holds,
  and the lower bound moves 0.086 -> 0.083). **The paper is now corrected**:
  `main.tex`, the arXiv copy, `preprint-draft.md`, and `RESEARCH-DIRECTION.md`
  all quote `[0.083, 0.179]` / `>= 0.083`, and `main.pdf` + the arXiv tarball
  are rebuilt. (The dated entries lower in this log keep the original numbers as
  a record of what was reported at the time.)
- `scripts/play_cost_reach.py`: `--games/--sims` (defaults reproduce the n=40
  mechanism figures) so the "small-sample" mechanism reach can be raised.
- `scripts/danger_synthesis_sweep.py`: prints the Wilson 95% interval alongside
  each `blind/len(SEEDS)` (a bare 6/6=1.000 has Wilson LB ~0.61), and takes an
  optional seed-count `argv[2]` to grow the denominator.

**Per-limitation triage:**

| §7 paragraph | Follow-up | Where | Command / note |
|---|---|---|---|
| Pure-Python MCTS limits CIs | raise headline seeds 5->~20 (Azure-free) | **CPU-only, long** | `python scripts/play_cost_ci.py --seeds 20` (~3-4 h; then update Table/abstract CIs + rebuild PDF) |
| (same) mechanism n=40 flagged small-sample | raise reach games 40->~120 | **CPU-only, long** | `python scripts/play_cost_reach.py --games 120` (then update §4 numbers + `make_paper_figures.py`) |
| Determinized MCTS not GT-optimal | external-sampling MCCFR equilibrium baseline (CFR is contract-compatible, §8) | **CPU-only, large build** | new solver + validation; measures the gap vs equilibrium reach, not MCTS reach |
| Rare-rule instrument is engineered | broaden the rarity<->consequence characterization across a rule set (rarity via random games + play_cost via hand-coded rule-blind instrument, both in `cwm.law`) | **CPU-only** for the map; **LLM** to confirm the LLM reproduces a gap | extend the Connect-Four 6-rule probe |
| Single model family (GPT-5.x only) | run synthesis on other families (open models / stronger code models) | **LLM (local)** | `danger_synthesis_sweep.py` + gap grid against non-Azure providers; needs a provider adapter |
| finding-3 denominators are 6 seeds | grow `danger_synthesis_sweep` 6->~20 seeds/cell | **LLM (local)** | `python3.12 scripts/danger_synthesis_sweep.py large 20` (retry/backoff now makes this survivable) |
| Beacon is a minimal/trivial witness | synthesize a CWM for a partially-observable army5x5a variant | **LLM (local)** | game/instrument is CPU; the synthesized-CWM demonstration needs the LLM |
| Gate-blindness scope / `infer_states` crash | **root cause found & contract fixed (below)**; then rerun to confirm | fix **CPU-only (done)**; confirm **LLM (local)** | the `'list' object is not callable` crash was a name collision in OUR contract, not an LLM limit — see the root-cause note below |
| Knowledge cutoff / contamination | more declarative recall probes | **LLM (local), inherent** | cutoff dates are approximate; "no detectable recall", not "strictly novel" — not fully closable |

**Root cause of the recurring `'list' object is not callable` crash — very
likely OURS, not the LLM's, and not transient.** The `infer_states` crash the
paper reports across Kuhn-mini / Beacon / masked-tic-tac-toe is a deterministic
Python `TypeError`, so it is neither a rate-limit nor a flake. The mechanism: the
imperfect-info contract (`world_model.IMPERFECT_CONTRACT_API`) prescribed the
signature `def infer_states(observation: list[int], player: int)` — the
**parameter is named `observation`, which shadows the required `observation()`
function** in the same contract. The very next contract sentence tells the model
"every state in `infer_states(observation(s,p),p)` must map back to the same
observation", i.e. it invites the model to call `observation(...)` from inside
`infer_states` — where that name is now the list argument. Any such call yields
exactly `'list' object is not callable`. The reference implementation sidesteps
this by naming the parameter `obs_board` (`groundtruth/masked_tictactoe.py`),
but the *prompt* told the model to use `observation`.
**Fix applied (this commit):** the contract now names the parameter `obs`, adds
an explicit "do not shadow the `observation()` function" note, and spells out the
round-trip invariant as `observation(s',p) == observation(s,p)`. No code depends
on the old parameter name (the sandbox calls `infer_states` positionally and the
reference impls use their own names; 192 tests green). **Confirmation that this
resolves the crash needs a local LLM rerun** (`scripts/mtt_claimB_probe.py`,
`scripts/run_kuhn_validation.py`, `scripts/beacon_claimB_probe.py`) — if it does,
the paper's "GPT-5.4 cannot robustly synthesize `infer_states`" narrative is
partly an artifact of our contract and should be softened.

**Crashes no longer count as results (fixed this commit).** `is_rule_blind`
(bare `except -> True`) counted a synthesized CWM that *crashes* as rule-blind,
conflating a synthesis-robustness failure with genuine rule-blindness. Replaced
by `rule_status(code) -> ('aware'|'blind'|'crash', error)`: a crash is reported
separately and **excluded from the rule-blind denominator** (rate = blind/(blind
+aware)), unless every seed crashes (structural — the crash count makes that
visible). Principle: a crash, unless structural and unavoidable, is not a result.
The same pattern in `gap.inference_accuracy` is **now fixed too**: a crashed
`observation()`/`infer_states()` no longer lands in the rate denominator as a
non-inference. `observation_rate = obs_ok/obs_measured` and `inference_rate =
inf_ok/inf_measured` range only over cases that actually ran; exec errors are
reported separately (`obs_errors`, `inf_errors`, `n_exec_errors` = cases with any
error), and an all-crash surface reads as structural (rate 0.0 with the error
count making it visible) rather than a scored miss. This changes published
masked-TTT/Kuhn `inference_rate` numbers once rerun (e.g. the masked-TTT FULL arm
0.000 was entirely the `infer_states` crash — it will now read as structural
exec-error, and with the contract name-collision fix above the crash itself
should largely disappear). Covered by `test_inference_accuracy_excludes_exec_errors`.

**Per-seed results are now logged (fixed this commit).** The sweep previously
printed per-seed lines to stdout but persisted nothing, so crashes vs blind vs
aware could not be audited after the fact. It now writes
`results/danger_synthesis_<size>.json` with a `summary` (per-N blind/aware/crash
counts, rate + Wilson CI, identifiability floor) and a `per_seed` array (status,
error, gate_acc, iters, n_samples, and the synthesized code for each seed). The
headline play-cost sweep (`play_cost_ci.py`) already logged per-seed win rates
and the paired-difference vector to `results/play_cost_ci.json`.

## §3.2 null upgraded to a proof by exhaustion — tic-tac-toe (2026-06-29)

`scripts/exhaustive_verify_tictactoe.py` (Azure GPT-5.4-mini). Synthesize a
tic-tac-toe CWM, confirm it passes the random gate (accuracy 1.0, 0 refine iters),
then verify it against the truth over the ENTIRE reachable state space by BFS:

- reachable states: **5478**; transitions checked: **16167**
- **search-relevant mismatches: 0** (legal_actions on non-terminal states,
  apply_action on every (state, legal action), is_terminal, returns) →
  **globally correct on reachable states, by exhaustion** (not "no observed divergence").
- terminal-legal convention artifacts (excluded): **880** — the synthesized code
  omits the `is_terminal` guard in `legal_actions`, so it returns moves on won-but-
  not-full boards; a planner never queries `legal_actions` on a terminal state, so
  this is behaviourally irrelevant (the paper's `legal_terminal_divergences`,
  independently re-derived here by exhaustion).

This is the transition-function analogue of the coverage bound (Theorem 1): the
random gate certifies global correctness exactly when its check covers the full
reachable relation. For tic-tac-toe (small enough to enumerate) we make the check
exhaustive → gate-pass ⇒ globally correct, proven. For army5x5a / gen_tictactoe 6×6
the reachable space is too large to enumerate, so the null stays a statement about
the evaluated distributions — consistent with army5x5a being the one game with a
residual (gap 0.002). Result JSON: `results/exhaustive_tictactoe.json`. Tic-tac-toe is the only §3.2 game small enough: **Trike side-6 reachable space exceeds 3,000,000 states** (measured BFS, still growing at the cap), and army5x5a / gen_tictactoe 6×6 are far larger — so those stay sampled, not exhaustively proven.

## Synthesis-pipeline danger curve — translation-not-inference, earned (2026-06-28)

`scripts/danger_synthesis_sweep.py` (Azure GPT-5.4-mini). Synthesize a CWM from the
INCOMPLETE army5x5a rules + N true-game (army5x5a+material) trajectories, with the
**fixed refiner drawing FRESH trajectories each iteration** (`resample_fn`; the
reuse bug is corrected). Rule-blindness tested MCTS-free: does the CWM's `returns`
give the material winner on cap+unequal-material states (truth) or a draw (rule-blind)?

| N (games) | mini rule-blind | large rule-blind | identifiability floor (1−r)^N |
|-----------|-----------------|------------------|-------------------------------|
| 40  | **6/6 = 1.000** | **6/6 = 1.000** | 0.363 |
| 120 | **6/6 = 1.000** | **6/6 = 1.000** | 0.048 |
| 200 | **6/6 = 1.000** | **6/6 = 1.000** | 0.006 |

The rule-blind rate is ≈1.0 across N for BOTH model sizes, **far above** the
identifiability floor (1−r)^N. This is the (a)+(b) split measured on the actual
synthesis pipeline: (a) the floor (1−r)^N is the rate at which the rule is
unidentifiable (any learner); (b) the LLM is rule-blind well above the floor — it
does not infer the rule from trajectories even when present at large N with
resampling.

**large is the sharper case:** its gate accuracy is mostly LOW (0.00–0.13 across
N=120/200 seeds) — i.e. the rule IS heavily present in the sample (the rule-blind
CWM mismatches those transitions, so the gate cannot reach 1.0) — yet after six
refinement iterations the CWM is still rule-blind in every seed. The model sees the
rule en masse and still does not encode it. (mini sometimes reached gate 1.0 = the
rule happened to be absent — the identifiability event; large's low gate accuracy
rules that out, isolating the genuine learning failure.) **nano** (confounded:
gate accuracy is low everywhere because nano cannot synthesize army5x5a at all,
§3.2) is also rule-blind 6/6 at N=40; its rule-blindness reflects gate-attainability,
not the inference question.

This *earns* a strong empirical form of translation-not-inference (mini AND large,
fresh-resampling refiner, up to N=200) rather than asserting it. Fixed-refiner note:
the distinct-sample count (n_samples 1.2k–46.6k with resampling) confirms refinement
now draws fresh trajectories, so the rule had every opportunity to appear; it still
was not learned.

## Revision-2 hardening: coverage constants, identifiability, play_cost mechanism (2026-06-28)

**Coverage bound, exact constants** (`scripts/coverage_bound_constants.py`, exact
enumeration of reachable info-sets + reach probabilities under uniform-random play):
- Kuhn: |𝓘|=12, π_min=0.0833, N_suff(tight)=66; at N=80 the union-bound failure upper bound (from exact reach probs)
  = 0.0028 → **provably covered**.
- Leduc: |𝓘|=576, π_min=3.5e-4; the worst-case-depth bound needs N≈7.4M, the tight
  (π_min) bound N≈27k, and at N=8000 the union-bound failure upper bound over ALL 576 reachable
  info-sets = 2.22 → the theorem does **not** certify full coverage at 8000.
- Leduc, competent-relevant subset (`scripts/coverage_competent_leduc.py`): the 146
  info-sets competent determinized-MCTS visits have π_min=6.9e-4; at N=8000 the exact
  union-bound failure upper bound over this subset = **0.027 < 0.05 → covered w.h.p. (sampled subset)**.
  Since Claim A concerns only competent-relevant info-sets, the Leduc null is covered
  w.h.p. on the SAMPLED competent-visited subset (200 MCTS games — observed, not the
  full competent support; the full-reachable-set bound stays loose). Turns
  "empirically covered" into "covered under exact random-reach probs on the sampled
  competent-relevant subset".

**Enumeration-free error-mass certificate** (`scripts/error_mass_certificate.py`,
2026-07-02; companion to the coverage bound — no |𝓘|, no π_min, no reach
probabilities; only the rule-level constants b and bar_d enter):
- Kuhn (N=80, b=2, bar_d=3): any gate-passing `infer_states` fixed before the gate
  has undetected-error hit mass ≤ ln(1/0.05)/80 = **0.037** under ρ; any-profile
  transfer (×b^bar_d = 8) ≤ **0.30**. Weaker than the enumerative full-coverage
  certificate at the same N — where enumeration is feasible, Theorem 1 stays sharper.
- Leduc (N=8000, b=3, bar_d=8): mass under ρ ≤ **3.7e-4**, but the any-profile
  transfer factor 3^8=6561 is vacuous (consistent with Theorem 1 not certifying
  N=8000). Mixture gate (λ=1/2, same N=8000): deployed-planner error mass ≤
  **7.5e-4** — a competent-relevant certificate the enumeration route could not
  give (it needed N≈27k and only certified the SAMPLED competent subset).
- Occam/class-uniform variant needs N ≳ artifact description length (~10^4 bits
  for kB-scale code) → prefer a held-out gate (sample drawn after synthesis).

**Beacon exact play_cost by exhaustion** (`scripts/play_cost_exact_beacon.py`,
2026-07-02): play_cost on Beacon is now a THEOREM, not a measurement. Two levels,
both mechanically verified against the implementation (4 deals × 2 seatings = 8
deterministic games):
- belief→guess abstraction (the proof): fair arm draws all 8 → win rate exactly
  0.500; instrument seat loses all 8 → exactly 0.000; **play_cost = 0.500 EXACT**.
- real determinized-MCTS policy (the planner check): reproduces all-draws /
  all-losses on the same 8 games.
The arena 0.000 [0.000, 0.003] (n=1200) is now confirmation of a theorem. With
Prop 1 (gate-miss exact) this makes BOTH danger-law factors analytic on the
inference axis. Also recorded in the paper: play_cost upper bound
play_cost ≤ μ_query(E) (coupling argument, Prop 2) — consistency on army5x5a:
competent cap-reach 0.200–0.225 lower-bounds μ_query, measured play_cost 0.131
respects it; and the n=600 CI measurement re-read as a witness-certified lower
bound play_cost ≥ 0.086 (seed-clustered 95%).

**Material-at-cap rarity, two measured rates** (3000 random games, cap=100):
cap reached (both generals alive) = 5.2%; **material-terminal rarity** (the rule
decides the game; used by the danger law) = **2.5%**. (Corrects the earlier loose
"~1%" figure — the law's r=0.025 is the material-terminal rate.)

**play_cost mechanism** (`scripts/play_cost_reach.py`, MCTS 300 sims, 40 games):
P(reach cap) competent vs random by cap — 30: 0.200/0.375; 60: 0.200/0.200;
100: 0.225/0.075. Competent reach-cap is roughly CONSTANT in the cap knob (~0.21)
while random reach-cap VARIES strongly. This is a (small-sample) mechanistic
correlate of the danger law's cheap/expensive split: play_cost (competent reach,
~constant) vs rarity (random reach, knob-dependent). play_cost stays an empirical
regularity, now with a measured mechanism.

## Headline play-cost with Wilson CIs + seed-clustered interval (n=600) — peer-review hardening (2026-06-30)

`scripts/play_cost_ci.py` / `scripts/play_cost_blind3.py` (Azure-free, 600 sims,
**5 seeds × 120 = 600 games/arm**, true game = army5x5a + material-at-cap). Writes
`results/play_cost_ci.json`.

| Arena | W/D/L | win rate | Wilson 95% |
|-------|-------|----------|------------|
| truth-vs-truth (fair baseline) | 197/214/189 | 0.507 | [0.467, 0.547] |
| rule-blind vs truth (play cost) | 169/113/318 | 0.376 | [0.338, 0.415] |

**Pooled separation:** fair lower bound 0.467 > rule-blind upper bound 0.415.
play_cost = 0.131 (consistent with the prior 0.117–0.121).

**Seed-clustered (the seed, not the game, as the independent unit)** — addresses the
per-game-independence objection (reviewer point #2). Per-seed win rates: fair
0.479/0.529/0.471/0.529/0.525, rule-blind 0.383/0.383/0.362/0.417/0.333. The
paired-by-seed difference (cancels start-side/budget, identical across arms) has
mean 0.131, sd 0.039, and a Student-t 95% interval **[0.086, 0.175] (df=4) that
excludes zero**. Wider than the pooled interval (only 5 clusters) but the effect
survives. Upgrades the earlier n=360 (3-seed subset: fair 0.493, rule-blind 0.376)
to n=600 with a cluster-robust interval; the rule-blind point is unchanged.

## Imperfect information — Claim B: the belief model is invisible to a transition gate (2026-06-27)

`scripts/mtt_claimB_probe.py` (Azure GPT-5.4 large). Masked tic-tac-toe = standard
tic-tac-toe dynamics + an arbitrary, non-recallable masking rule (the center cell is
hidden, shown as -1). Synthesize the contract two ways — full rules vs the masking
rule withheld — and gate each on transitions AND inference:

| variant | transition gate | observation_rate | inference_rate |
|---------|-----------------|------------------|----------------|
| FULL rules | **1.000** (0 iters) | **1.000** | 0.000 (infer_states crashes) |
| WITHHELD masking rule | **1.000** | **0.020** | 0.180 |

**The demonstrable triangle (clean on `observation_rate`):**
- **transition gate = 1.000 in BOTH arms** — tic-tac-toe dynamics synthesize by
  recall, unaffected by the masking rule. The transition gate never invokes
  `observation`/`infer_states` (verified: `contract_accuracy` calls only
  apply_action/legal_actions/is_terminal/returns), so it is **structurally blind to
  the belief model**.
- **FULL → observation_rate 1.000:** told the masking rule, the model masks the
  center correctly.
- **WITHHELD → observation_rate 0.020:** without the rule the synthesized
  `observation` does not mask the center — a wrong belief model — yet the transition
  gate still certifies it at 1.000.

This is Claim B: a belief model that fails the inference gate is invisible to a
transition-accuracy gate, because the information partition it encodes appears in no
`(s,a,s')` transition tuple (see RESEARCH-DIRECTION, belief–transition orthogonality
proposition). Complements Claim A (Beacon): a wrong belief both **loses at play** (A)
and is **invisible to a transition gate** (B).

**Caveat (honest):** `inference_rate` is NOT a clean signal here — GPT-5.4's
synthesized `infer_states` raises `'list' object is not callable` (full arm → 0.000),
the same recurring bug seen on Kuhn-mini and Beacon. So `inference_rate` is confounded
by a synthesis-robustness failure in both arms; the clean discriminator is
`observation_rate`. That recurring crash is itself a secondary finding: across three
games GPT-5.4 fails to robustly synthesize an enumeration-style `infer_states`, i.e.
the belief surface is not only un-gateable by transitions but also hard to synthesize
at all.

## Imperfect information — Beacon: a PROVABLE positive Claim A (2026-06-27)

Poker has no inference coverage gap (competent play is shallower than random).
Beacon is the minimal game engineered to have one: a survival walk (depth =
survival; `safe(k,t)=(k+t)%2`, an unsafe move loses immediately) + a final round
where each player must guess the opponent's hidden type (inferable from its observed
moves). Random play reaches the final round with probability `(1/2)^{2T}`; optimal
play with probability 1. Oracle `src/cwm/groundtruth/beacon.py`, instrument
`src/cwm/beacon_instrument.py`, driver `scripts/beacon_claimA.py`.

The Claim A instrument flips the opponent type **only at final-round states**
(`status==1`) — the deep region D a random gate never samples.

**Result (T=8, GATE_GAMES=2000, arena N=400×3 seeds, 100 sims, 2 determinizations):**

| metric | value |
|--------|-------|
| random reaches final round | 0.00000 |
| instrument inference mismatches on random sample | **0 / 8156** (passes the gate) |
| fair baseline (truth vs truth) winrate | 0.500 [0.472, 0.528] (all draws) |
| instrument winrate vs truth | **0.000 [0.000, 0.003]**, net −1200/1200 |

The instrument passes the inference gate perfectly yet loses every game — a
**verified-but-wrong inference function that is play-inadequate**, the
imperfect-information analogue of the perfect-info rare-rule gap, and the first
*positive* imperfect-info Claim A.

**Danger law on the inference axis** (`danger = play_cost·(1−ε)^N`, ε=`(1/2)^{2T}`,
N=2000, play_cost=0.5):

| T | ε | gate-miss (1−ε)^N | danger |
|---|---|-------------------|--------|
| 4 | 3.9e-3 | 0.000 | 0.000 |
| 6 | 2.4e-4 | 0.614 | 0.307 |
| 8 | 1.5e-5 | 0.970 | 0.485 |
| 10 | 9.5e-7 | 0.998 | 0.499 |

At T=4 the rule is frequent enough that the gate catches it (danger≈0); by T≥8 the
gate is blind and harm saturates at play_cost (≈0.5; danger T=10 = 0.499) — the exact `(1−ε)^N` threshold, now
instantiated on the inference half of the contract. Same gate-miss mechanism, two
faces (transition rule ↔ inference info-set).

What is proven vs measured: the reach bound `(1/2)^{2T}`, optimal-reaches-D, and
flip⇒loss are analytic (see RESEARCH-DIRECTION); the table is their instantiation.
Whole-branch review (opus) verified the oracle by hand-trace + live simulation:
instrument loses *only* because of the flipped inference; fair baseline is all-draws;
the determinized planner converts correct inference into the winning guess.

Reproducible record of evaluation runs. All runs use the Azure OpenAI Global
Standard deployments (`gpt-5.4`, `gpt-5.4-mini`, `gpt-5-nano`) configured in
`.env`, baseline = `gpt-5.4` as a direct LLM policy.

Pricing in cost figures is real Azure list price (USD/1M tokens, in/out) as of
2026-06-24: gpt-5.4 = 2.5/15, gpt-5.4-mini = 0.75/4.5, gpt-5.4-nano = 0.2/1.25
(the nano deployment used is `gpt-5-nano`; cost approximated with 5.4-nano list
price). See `src/cwm/cost_meter.py`.

## Known-game results (30 games each, seed 7)

| Game | Synthesizer | Refinement iters | Transition accuracy | CWM W / D / L | Baseline illegal moves | CWM illegal | Total cost |
|------|-------------|------------------|---------------------|---------------|------------------------|-------------|------------|
| Tic-tac-toe | gpt-5.4-mini | 0 | 1.0 | 18 / 10 / 2 | 6 | 0 | $0.043 |
| Tic-tac-toe | gpt-5-nano | 0 | 1.0 | 21 / 8 / 1 | 5 | 0 | $0.043 |
| Connect Four | gpt-5.4-mini | 0 | 1.0 | 29 / 0 / 1 | 0 | 0 | $0.135 |
| Connect Four | gpt-5-nano | 0 | 1.0 | 30 / 0 / 0 | 2 | 0 | $0.132 |

CWM agent = synthesized world model + MCTS. Baseline = same prompt every turn,
model picks a move directly. Starts alternate each game.

### Commands

```bash
# Tic-tac-toe (30 games)
python -m cwm.run_experiment --game tictactoe --games 30 --synth-size mini --baseline-size large --simulations 200 --train-games 15 --seed 7
python -m cwm.run_experiment --game tictactoe --games 30 --synth-size nano --baseline-size large --simulations 200 --train-games 15 --seed 7

# Connect Four (30 games)
python -m cwm.run_experiment --game connect4 --games 30 --synth-size mini --baseline-size large --simulations 400 --train-games 40 --seed 7
python -m cwm.run_experiment --game connect4 --games 30 --synth-size nano --baseline-size large --simulations 400 --train-games 40 --seed 7
```

## Cost-gate conclusion

Running the experiment via API is trivially cheap. The synthesizer is a one-off
(~$0.005–0.01 per game built); the baseline (one call per turn) is the only
cost that scales, at ~$0.001–0.005 per game depending on game length. A
thousand-game study costs a few dollars. **No need for a subscription/Codex
fallback for the baseline.**

## Observations feeding the research direction

- Both tic-tac-toe and Connect Four synthesize to a perfect world model
  (transition accuracy 1.0, full contract) in **0 refinement iterations**, even
  though random trajectories cover a tiny fraction of Connect Four's state space.
  Interpretation: the model **recalls** these well-known games rather than
  inferring their rules from trajectories — so "accuracy 1.0 on sampled
  trajectories" likely coincides with global correctness *here* for the wrong
  reason. The coverage gap (sampled-verification vs correctness on the
  MCTS-visited distribution) is expected to surface on **novel** games where the
  model must genuinely infer rules. That is the planned next experiment.
- The same model encodes the rules perfectly as code (synthesizer) yet commits
  illegal moves as a direct policy (baseline) — code > intuition.

## Gap experiment — verified vs correct (2026-06-24)

Harness: `cwm/gap.py` + `cwm/run_gap.py` (spec/plan dated 2026-06-24). For each
synthesis seed we synthesize+refine a CWM to gate accuracy 1.0, then compare it
against the ground truth on three state distributions — D_gate (random-trajectory
states the gate used), D_cwm (states MCTS expands planning on the CWM), D_truth
(states MCTS expands planning on the ground truth). Headline **gap =
state_agreement(D_gate) − state_agreement(D_cwm)**, search-relevant variant
(legal_actions on truth-terminal states excluded — undefined and never queried by
MCTS; tracked separately as `legal_terminal_divergences`).

Protocol: 5 synthesis seeds × {mini, nano}, 20 self-play games, 300 simulations,
visited-cap 4000, train-games 40, seed 0. Baseline LLM not used (the gap is
intrinsic to the world model).

### Non-triviality sweep (MCTS vs random, CPU-only)

| Game | W/D/L | winrate |
|------|-------|---------|
| gen_tictactoe 6×6 win-4 | 20/0/0 | 1.00 |
| army5x5a | 16/0/0 | 1.00 |
| trike side-6 | 14/2/0 | 0.94 |

All three discriminate skill (MCTS beats random from both sides, zero losses).
army5x5a is balanced under strong search (MCTS-vs-MCTS at 800 sims: ~P1 2 / P2 3
/ 5 draws over 10), so the fast decisive games at low sims are weak-play blunders,
not a forced first-player win.

### Gap results

| Game | Regime | Synth | gap mean | gap max | gate-pass | median refine iters | exec-err |
|------|--------|-------|----------|---------|-----------|---------------------|----------|
| gen_tictactoe | correct prior | mini | 0.000 | 0.001 | 5/5 | 0 | 0 |
| gen_tictactoe | correct prior | nano | 0.000 | 0.000 | 5/5 | 0 | 0 |
| army5x5a | no prior | mini | 0.002 | 0.008 | 4/5 | 0 | 0 |
| army5x5a | no prior | nano | n/a | n/a | 0/5 | – | 0 |
| trike | wrong prior | mini | 0.000 | 0.000 | 4/5 | 1 | 0 |
| trike | wrong prior | nano | 0.000 | 0.000 | 5/5 | 0 | 0 |

### Findings

1. **The verified-vs-correct gap is ≈ 0 in all three regimes.** Whenever a CWM
   passes the random-trajectory gate (accuracy 1.0), it is also correct on the
   MCTS-visited distribution (D_cwm and D_truth agreement ≈ 1.0). The feared
   coverage gap did not materialize. **Honest null result** for the planned
   contribution as stated.
2. **The binding constraint is gate-attainability, not the gap.** What varies
   across regimes/sizes is whether a model can synthesize a gate-passing world
   model at all:
   - gen_tictactoe: trivial, 0 refinements, both sizes (recall).
   - army5x5a (no prior, complex action encoding `from*25+to` + ply counter):
     **mini gets it right first try (0 refinements, 4/5); nano fails 5/5**, stuck
     at ~1–2% accuracy even after refinement.
   - trike (wrong prior): **needs refinement** (0–5 iters) — the confabulated
     mechanics produce initially-wrong code that refinement corrects — but once
     gate-passed, gap 0. nano passes trike (5/5), so the army5x5a failure is
     representational complexity, not the knowledge regime.
3. Once the gate is passed, the synthesized code is **globally correct**. For
   small, fully-specified games, random-trajectory transition accuracy is a
   *sufficient* correctness gate — no wrong-but-verified CWM was observed.
4. `legal_terminal_divergences` is high for gen_tictactoe / army5x5a (the
   synthesized code omits the is_terminal guard in legal_actions) but 0 for trike
   (its terminal = "no legal slide" makes legal_actions=[] on terminal by
   construction). This is a convention artifact, correctly excluded from the gap.

### Harness bug found and fixed mid-run

The first grid run reported a spurious gap of ~0.6–0.8 on gen_tictactoe. Cause:
`contract_divergence` evaluated ~20k visited states in one sandbox call with a
10s timeout; slower (but correct) CWMs timed out and the report counted that as
state_agreement 0.0 → spurious gap 1.0. Fixed by chunking (1000/chunk, 60s, one
retry at 3×), an `n_exec_errors` field excluded from rate denominators, and a
visited-cap (4000). After the fix, exec-errors are 0 across the grid.

### Interpretation / implications

The planned "coverage gap" contribution does not reproduce on these small,
fully-specified games — likely because a CWM wrong anywhere also fails the random
gate here (the gate is a strong filter when the state space is small and rules are
complete). A real gap would need bigger or under-specified dynamics where the gate
is genuinely weak. The richer signal is **gate-attainability vs game complexity ×
model scale**, and the recall-vs-translate-vs-correct-confabulation distinction
across regimes. See RESEARCH-DIRECTION.md for the pivot options.

### Commands

```bash
PYTHONPATH=src python scripts/nontriviality_sweep.py
PYTHONPATH=src python scripts/gap_grid.py   # 3 games × {mini,nano}, 5 seeds each
```

Total grid cost ≈ $0.81 (army5x5a/nano alone $0.43 — wasted refinement loops on
unreachable gate). Per-run JSON in `results/` (git-ignored).

## Pure-inference variant — `--no-rules` (2026-06-24)

To test whether the gap is hidden by *giving* the model the rules (translation,
not inference), we reran the grid withholding `RULES_TEXT` — synthesizing from
trajectories alone (generic `CONTRACT_API` only). `cwm/run_gap.py --no-rules`,
results suffixed `_norules`.

| Game | Regime | Synth | gate-pass | gaps (scored) | skip accuracies |
|------|--------|-------|-----------|---------------|-----------------|
| gen_tictactoe | correct prior | mini | 2/5 | [0.0, 0.0] | [0.61, 0.62, 0.96] |
| gen_tictactoe | correct prior | nano | 2/5 | [0.0, 0.0] | [0.0, 0.50, 0.63] |
| army5x5a | no prior | mini | 0/5 | – | all 0.0 |
| army5x5a | no prior | nano | 0/5 | – | all 0.0 |
| trike | wrong prior | mini | 0/5 | – | all 0.0 |
| trike | wrong prior | nano | 0/5 | – | all 0.0 |

**Findings:**
- Where the gate is reached, gap is still **0** — only gen_tictactoe passes
  (2/5), driven by recall, and those CWMs are correct (gap 0).
- For genuinely novel games (army5x5a, trike) pure inference **fails the gate
  entirely** (0% accuracy): the model cannot infer the dynamics from trajectories
  alone, especially the opaque action encodings (`from*25+to`; disc/pawn value
  scheme). It does not produce a wrong-but-gate-passing CWM — it produces nothing.

**Decisive conclusion.** Across with-rules and no-rules, in all three regimes,
there is **no "passes the gate but wrong on the search distribution" case**.
Either the model gets it right (gap 0) or it fails the gate. The coverage gap
does not materialize here. Diagnosis: for these games the random-trajectory
sample **identifies** the dynamics — there is no compact wrong hypothesis
consistent with 40 random games that diverges elsewhere (no under-determination).
The gate is not weak; it is identifying.

**Implication (pivot).** A real gap needs **sample under-determination**: a rule
that random play almost never exercises but optimal play seeks out (a rarely-
triggered tactic). That is the next instrument — see RESEARCH-DIRECTION.md.

## Rarity↔consequence tension (rule search, 2026-06-24/25)

Before building an instrument we searched for a rule that is **rare under random
play** (so the gate misses it) yet **consequential in competent play** (so a
planner exploits it). Validated empirically (`scratchpad` spikes): rarity =
fraction of random games the rule decides; consequence = R-aware-MCTS vs
R-blind-MCTS in the true game.

| Base | Rule | Rarity (random) | Consequence |
|------|------|-----------------|-------------|
| Connect Four | last-placer-on-full-board wins | 0% | none |
| Connect Four | corner 4-in-a-row is poison | 3% | weak |
| Connect Four | top-centre fill wins | 12% | strong |
| Connect Four | vertical-3 in centre wins | 23% | strong |
| Connect Four | 2×2 square wins | 38% | strong |
| army5x5a | infantry breakthrough wins | 75% | strong |

Six rules across two games lie on a **rarity↔consequence anti-correlation curve**:
anything a planner can force, random play also stumbles into. Connect Four
admits no rare-AND-consequential rule. **Diagnosis:** the gap requires a game
where random-play and competent-play state distributions diverge. A
random-vs-MCTS divergence measurement (`scripts/divergence.py`) ranked the games
by game-length divergence (competent − random median plies): **army5x5a** stands
out (random 23, competent 58, routinely hitting the 100-ply cap), while trike and
gen_tictactoe are Connect-Four-like (low divergence).

## The instrument: army5x5a + material-at-cap (2026-06-25)

In army5x5a's deep tail (competent play maneuvers there; random rarely reaches
it) a **material-at-cap** rule lands in the rare∧consequential quadrant: at the
ply cap with both generals alive, the player with more pieces wins (instead of a
draw). Validated: it *changes the outcome* in only **~1%** of random games (cap
reached 5.3%, mostly equal-material draws) yet decides **~50%** of competent
games. Implemented as `groundtruth/gen_chess_material.py` with paired specs:
`army5x5a_material` (complete rules) and `army5x5a_material_incomplete` (base
rules, omitting the rule). `run_gap.py --game <spec> --play-games N`.

### State-agreement is the wrong lens (dilution)

| Condition (mini, 5 seeds) | gate-pass | gap_truth | note |
|---------------------------|-----------|-----------|------|
| incomplete (omits rule) | 2–3/5 | **0.000** | skipped seeds failed gate at acc 0.998 — the rule WAS in their 40 training trajectories, so the base CWM mismatched it and the gate caught it |
| complete (control) | 5/5 | **0.000** | — |

`gap_truth` ≈ 0 in both conditions. The divergence region (cap+unequal-material)
is <1% of visited states, and symmetric MCTS self-play ties on material → the
states where the rule-blind CWM is wrong are barely visited. **A rare-but-pivotal
rule error does not move the state-agreement rate** (it is diluted), and the gate
is actually *sensitive* when the rule appears in the training sample (it then
fails the gate). nano fails the gate entirely on army5x5a (representational
complexity), as before.

### Play performance IS the lens (the result)

Adequacy for planning must be measured by **play**, not prediction accuracy. The
rule-omitting CWM is, for play, equivalent to hand-written base army5x5a (differs
only at the rare cap+material states), so its play cost is measured exactly and
Azure-free (`scripts/play_cost.py`, 600 sims, 240 games):

| Arena (true game = army5x5a + material) | win rate |
|-----------------------------------------|----------|
| truth-vs-truth (fairness baseline) | 0.479, 0.529 → **0.504** |
| **rule-blind vs truth** (base/incomplete-CWM) | 0.383, 0.383 → **0.383** |

The LLM-synthesized incomplete CWMs (gate-passing, gap_truth = 0) play at
**0.28–0.37** win rate vs a truth agent; the complete-rules CWMs at **0.38–0.45**
(non-overlapping) — and the hand-written rule-blind oracle, measured at scale,
sits at a reproducible **0.383** against a calibrated **0.504** baseline. Losing
~2:1 (≈63L/35W of 120).

**Headline finding.** A world model can pass transition-accuracy verification
(gate 1.0) and be **≥99% state-accurate on the search distribution** (gap_truth
= 0) yet **systematically lose at play** because the <1% it gets wrong is exactly
the pivotal tactic. Transition/state accuracy is the wrong adequacy criterion for
planning — play performance is. Complete rules close it (control plays near
baseline); an incomplete spec leaves a rare branch that sampling-based
verification cannot see but a planner punishes.

### Commands

```bash
# state-agreement grid, treatment + control, with play performance:
for c in army5x5a_material_incomplete army5x5a_material; do
  PYTHONPATH=src python -m cwm.run_gap --game $c --synth-size mini \
    --synth-seeds 5 --selfplay-games 20 --simulations 400 --train-games 40 --play-games 30
done
PYTHONPATH=src python scripts/play_cost.py   # Azure-free play-cost + fairness baseline
```

## Can the gap be repaired? — translation vs inference (2026-06-26)

Spikes on army5x5a + material-at-cap, INCOMPLETE rules unless noted. Play winrate
vs the true game (40 games/400 sims; baseline 0.28, fair truth-vs-truth 0.50).

| Repair attempt | discriminating examples | gate acc | rule learned | winrate |
|----------------|-------------------------|----------|--------------|---------|
| none (random trajectories) | 0 | 1.000 (false security) | no | 0.28 |
| naive DAgger (dump competent traj) | ~2 | 0.9996 | no | 0.28 |
| proper DAgger (flawed model's game path, iterated) | 4–5/round | 0.993 | no | 0.28–0.33 |
| targeted, **artificial** states | 120 | mini 0.916 / **large 0.004** | no | mini 0.35 / **large 0.05** |
| targeted, **real** (harvested on-manifold) | 54 | mini 0.959 / large 0.959 | no | mini 0.35 / **large 0.42** |
| **COMPLETE rules** + targeted (control) | 120 | **1.000 (0 iters)** | **yes** | **0.53** |

**Findings:**
1. **Detection works, repair-by-examples does not.** Verifying on the play/search
   distribution makes the gate drop below 1.0 (it *detects* the inadequacy that
   random-trajectory verification missed). But neither mini nor large can *infer*
   the rare rule from examples — even 54 real discriminating transitions with 12
   refinement iters leave the gate at 0.959 and the rule unlearned.
2. **Spec completeness is decisive.** Given the rule in RULES_TEXT, the model
   encodes it instantly (0 refinement iters) and plays at parity (0.53 ≈ 0.50).
3. **Scale helps only marginally.** large (0.42) > mini (0.35) on real data, both
   far below the complete-rules 0.53. The inference ceiling is general, not a
   mini-only artifact.
4. **Repair data must be on-manifold.** Artificial (unreachable) discriminating
   states *corrupt* synthesis — the large model collapsed to acc 0.004 / winrate
   0.05 trying to fit them. Harvested reachable states (flawed self-play ends at
   cap+unequal-material 6/20, 3× competent's 2/20) are sane but still
   insufficient to teach the rule.

**Unified thesis.** LLM code-world-model synthesis is rule **translation**, not
rule **inference**: it is correct iff the rules are specified. Sampling-based
verification gives false adequacy precisely because the model translates what it
was given — and the gate cannot surface a rule that was never specified and is
too rare to appear in samples. The actionable fix is **spec completeness +
verification on the play distribution** (which detects incompleteness); repairing
by feeding examples does not work at this model scale.

```bash
# repair spikes (Azure). The .env path is hard-coded; adjust if relocated.
PYTHONPATH=src python scripts/repair_spikes/spike_dagger2.py     # proper iterative DAgger
PYTHONPATH=src python scripts/repair_spikes/spike_harvest.py     # on-manifold real data, mini + large
PYTHONPATH=src python scripts/repair_spikes/spike_targeted2.py   # dose-response + complete-rules control
```

## Quantitative law: danger = consequence × P(escape) (2026-06-26)

The harm from accepting a CWM on random-trajectory accuracy is
`danger(rule, N) = play_cost × (1 − rarity)^N`. Measured efficiently by
separating the cheap, varying term (rarity = random-play incidence, no MCTS) from
the expensive, ~constant term (play_cost, MCTS): the rule-blind planner's loss is
~constant across caps because **competent play always reaches the cap region**,
while random-play rarity varies with the cap length. So we measure play_cost
precisely once and sweep rarity cheaply.

- **play_cost ≈ 0.12, ~constant** (independent runs: `play_cost.py` 0.117–0.121 at
  cap=100, n=240, 600 sims; `law_sweep` 0.112 at cap=30). Fair baseline
  truth-vs-truth = 0.504 (n=240) ✓ ≈ 0.5.
- **rarity(cap)** over 3000 random games each, and `danger = 0.12 × (1−rarity)^N`:

| cap | rarity | (1−r)^40 | danger@20 | danger@40 | danger@80 |
|----:|-------:|---------:|----------:|----------:|----------:|
|  25 | 0.337  | 0.0000   | 0.000 | 0.000 | 0.000 |
|  40 | 0.208  | 0.0001   | 0.001 | 0.000 | 0.000 |
|  60 | 0.107  | 0.0107   | 0.012 | 0.001 | 0.000 |
|  80 | 0.056  | 0.0997   | 0.038 | 0.012 | 0.001 |
| 100 | 0.025  | 0.3583   | 0.072 | 0.043 | 0.015 |
| 120 | 0.011  | 0.6339   | 0.096 | 0.076 | 0.048 |
| 140 | 0.007  | 0.7652   | 0.105 | 0.092 | 0.070 |

**Result (threshold law, not an inverted-U).** Because play_cost is ~constant,
danger is ≈0 while the rule is common enough for an N-trajectory gate to catch it
(cap ≤ 50), then **rises through a threshold** as the rule becomes rare (cap
60–100), and plateaus at ≈ the full play_cost once the rule almost always escapes
the gate (cap ≥ 120). The gate size `N` shifts the threshold: more verification
trajectories push it right (a rarer rule is needed to escape).

This generalizes the single-instrument result: a rule harms a sampling-verified
planner **iff** it is rare under random play (escapes the gate) yet consequential
in competent play (high play_cost), and the expected harm is quantitatively
`play_cost × (1−rarity)^N`. Connect Four's consequential rules cannot enter the
danger zone (their rarity 0.12–0.38 keeps `(1−rarity)^40 ≈ 0`); army5x5a's
deep-tail rule can, because competent and random play diverge there.

```bash
PYTHONPATH=src python scripts/law_curve.py   # cheap rarity grid + cost probes (+ danger curve)
```

## Imperfect information — Kuhn poker pipeline validation (2026-06-26)

New machinery (contract `observation`/`infer_states`/`initial_states`,
determinized-MCTS planner, `inference_accuracy` gate, `imperfect_arena`), validated
end-to-end on Kuhn poker. `scripts/run_kuhn_validation.py {mini|large}`.

| Synth | transition gate | inference gate (obs / infer) | CWM-vs-truth play | fair baseline |
|-------|-----------------|------------------------------|-------------------|---------------|
| large | 1.000 (0 iters) | 1.000 / 1.000                | 0.470 [0.422,0.519] | 0.470 [0.422,0.519] |
| mini  | 0.845 (12 iters, fails gate) | 1.000 / 0.000 (infer_states crashes) | — | — |

- **large:** recalls Kuhn; both gates pass; CWM plays identical to the truth-vs-truth
  baseline (overlapping CIs) — gate-pass → play ≈ baseline, validating the pipeline
  (a near-zero gap is the *expected* recall result, not the contribution).
- **mini:** does NOT cleanly synthesize this (non-standard net-chip) encoding — the
  transition gate stalls at 0.845 and the synthesized `infer_states` raises
  (`'list' object is not callable`). A scale/representation dependence consistent
  with translation-not-inference.
- Determinized planner hardened to tolerate a faulty synthesized model (raising/
  empty inference, crashing dynamics) → legal fallback move, so Claim A/B runs on
  deliberately-wrong models don't abort the arena.

Next (Azure): **Claim A** (membership-valid-but-skewed `infer_states` that passes
the gate yet loses at play) and **Claim B** (synthesis with rules withheld).

## Imperfect information — Leduc coverage-gap (Claim A) is structurally NULL (2026-06-27)

Built a Leduc oracle (6-card deck, community card, 2 betting rounds with raises;
`src/cwm/groundtruth/leduc_poker.py`) to attempt Claim A via an inference
coverage gap: a CWM whose `infer_states` is wrong only on info-sets that competent
play reaches but random sampling (the gate) misses. `scripts/leduc_coverage_diagnostic.py`.

**Result — no coverage gap exists.** Random play (8000 games) vs competent
determinized-MCTS play (300 games):

| metric | value |
|--------|-------|
| random-reachable info-sets | 574 |
| competent-visited info-sets | 156 |
| competent visits on random-covered info-sets | 1259/1259 = **1.000** |
| competent visits on info-sets random missed (inference-relevant) | 0/1259 = **0.000** |
| distinct competent-only inference-relevant info-sets | **0** |

Competent info-sets are a strict **subset** of random-covered ones. Reason:
uniform-random play raises/calls indiscriminately (prob 1/3 each), so it
*over-explores* the shallow betting tree relative to selective competent play
(which folds dominated hands). Random play reaches even the deepest capped-pot
lines (`max_committed=13, total=22`) at frequency 0.0071 ≫ 1/8000.

**This is the imperfect-info analogue of the gate-is-identifying result, and it
admits a proof, not just an experiment** (see RESEARCH-DIRECTION "coverage bound"):
under uniform random play every reachable info-set at betting-depth d has reach
probability ≥ b^{-d} (b = max branching), so a sample of N ≳ b^{d_max} games covers
all reachable info-sets — hence all competent-relevant ones. A coverage gap
therefore requires b^{d_max} ≫ N (large branching and/or depth), which shallow
betting games (Kuhn b=2 d≈2; Leduc b=3 d≈8, b^d≈6561 < N) do not have. The
perfect-info rare-rule gap exploited exactly such depth (army5x5a: competent play
reaches the ply cap; short random games do not).

**Implication:** a positive imperfect-info Claim A needs a game with
b^{d_max} ≫ feasible N — a *deep/wide* imperfect-information game, not a toy poker.
The machinery (contract, determinized planner, inference gate, arena, instrument)
is built and validated; only a larger oracle is missing.

## Imperfect information — Leduc coverage-gap (Claim A) is structurally NULL (2026-06-27)

Built a Leduc oracle (6-card deck, community card, 2 betting rounds with raises;
`src/cwm/groundtruth/leduc_poker.py`) to attempt Claim A via an inference
coverage gap: a CWM whose `infer_states` is wrong only on info-sets that competent
play reaches but random sampling (the gate) misses. `scripts/leduc_coverage_diagnostic.py`.

**Result — no coverage gap exists.** Random play (8000 games) vs competent
determinized-MCTS play (300 games):

| metric | value |
|--------|-------|
| random-reachable info-sets | 574 |
| competent-visited info-sets | 156 |
| competent visits on random-covered info-sets | 1259/1259 = **1.000** |
| competent visits on info-sets random missed (inference-relevant) | 0/1259 = **0.000** |
| distinct competent-only inference-relevant info-sets | **0** |

Competent info-sets are a strict **subset** of random-covered ones. Reason:
uniform-random play raises/calls indiscriminately (prob 1/3 each), so it
*over-explores* the shallow betting tree relative to selective competent play
(which folds dominated hands). Random play reaches even the deepest capped-pot
lines (`max_committed=13, total=22`) at frequency 0.0071 ≫ 1/8000.

**This is the imperfect-info analogue of the gate-is-identifying result, and it
admits a proof, not just an experiment** (see RESEARCH-DIRECTION): under uniform
random play every reachable info-set at betting-depth d has reach probability
≥ b^{-d} (b = max branching), so a sample of N ≳ b^{d_max} games covers all
reachable info-sets — hence all competent-relevant ones. A coverage gap therefore
requires b^{d_max} ≫ N (large branching and/or depth), which shallow betting games
(Kuhn b=2 d≈2; Leduc b=3 d≈8, b^d≈6561 < N) do not have. The perfect-info
rare-rule gap exploited exactly such depth (army5x5a: competent play reaches the
ply cap; short random games do not).

**Implication:** a positive imperfect-info Claim A needs a game with
b^{d_max} ≫ feasible N — a *deep/wide* imperfect-information game, not a toy poker.
The machinery (contract, determinized planner, inference gate, arena, instrument)
is built and validated; only a larger oracle is missing.

### Depth probe — poker depth does NOT create a usable inference gap (2026-06-27)

`scripts/leduc_depth_probe.py` sweeps Leduc's per-round raise cap (deepening the
betting tree) at fixed random-gate N=8000, 100 competent determinized-MCTS games:

| raise cap | random infosets (max depth) | competent infosets (max depth) | uncovered inference-relevant |
|-----------|------------------------------|--------------------------------|------------------------------|
| 2 | 574 (8)  | 120 (6) | 0 / 418 = 0.0000 |
| 4 | 1090 (11)| 128 (7) | 0 / 400 = 0.0000 |
| 6 | 1210 (12)| 127 (9) | 5 / 396 = **0.0126** |

A gap appears only at cap 6 and is marginal (1.26% of competent visits, 5 info-sets)
— too weak for a CI-separated play deficit. Mechanism: in poker, betting **depth
comes from aggression**, which competent play *minimizes* (it calls/folds), so
competent play is always SHALLOWER than random (max depth 9 vs 12). Competent ⊆
random-covered persists. **Poker is the wrong family for an inference coverage gap.**

A usable gap needs competent play to reach a deep/rare region MORE than random —
which happens when depth = *survival* (perfect-info board games: competent reaches
the ply cap, random blunders out early; this is exactly the rare-rule gap). The
positive imperfect-info path is therefore a **partially-observable deep board
game** (hidden state over an army5x5a-like game that already exhibits the gap), not
poker.

### Claim B probe — Beacon is confounded for inference-synthesis (2026-06-27)

`scripts/beacon_claimB_probe.py` (Azure GPT-5.4 large). Synthesizing Beacon's
contract, full rules vs the type-revelation rule withheld:

| variant | transition gate | observation_rate | inference_rate |
|---------|------------------|------------------|----------------|
| FULL rules | 0.487 (fails, 10 iters) | 1.000 | 0.000 (infer_states crashes) |
| WITHHELD revelation | 0.443 (fails) | 1.000 | 0.000 |

**Beacon does not work as a Claim B (synthesis) vehicle:** GPT-5.4 large cannot
synthesize even Beacon's *transitions* (≈0.45, near random) with fully-specified
rules, and its `infer_states` crashes (`'list' object is not callable`, the same
shadowing bug seen on Kuhn-mini). With the transition function broken, the full-vs-
withheld inference comparison is confounded — we cannot separate "inference fails
because withheld" from "the model cannot synthesize this unusual game at all."
(Note: this is a synthesis-capability limit on a novel encoding, NOT translation-
not-inference — the rules were given. The hand-built Claim A positive is unaffected;
it never used synthesis.)

Implication for Claim B: it needs a vehicle whose **dynamics synthesize cleanly**
(so the only variable is the belief model) plus a **withholdable observation rule
independent of the dynamics**. Candidate: a familiar-dynamics game (synthesizes at
gate 1.0) overlaid with an arbitrary, non-recallable masking rule — see
RESEARCH-DIRECTION.

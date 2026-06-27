# Masked Tic-Tac-Toe — Claim B (belief model is orthogonal to transition data) — Design

Status: design 2026-06-27. Claim A (Beacon) showed a verified-but-wrong inference
loses at play. Claim B is the complementary verification point: a wrong belief
model (`observation`/`infer_states`) is **invisible to a transition-accuracy gate**,
because the information partition it encodes is not present in transition data. The
Beacon synthesis probe confirmed Beacon is the wrong vehicle (GPT-5.4 cannot even
synthesize its transitions, ≈0.45, confounding any inference comparison). Claim B
needs a game whose **dynamics synthesize cleanly** (so the only variable is the
belief model) plus a **withholdable observation rule independent of the dynamics**.

## The analytic core (a proposition for §6)

**Proposition (belief–transition orthogonality).** A transition dataset is a set of
tuples `(s, a, s', r)` over *full* ground-truth states. The functions
`observation(s, p)` and `infer_states(o, p)` encode the information partition — what
player `p` can distinguish — which appears in no `(s, a, s', r)` tuple. Therefore
(i) no transition dataset constrains the masking convention; (ii) a gate that scores
transition accuracy cannot detect an incorrect `observation`/`infer_states`; (iii)
the belief model must be specified and is verifiable only by a separate inference
gate on `state → observation → inferred-set` consistency. ∎

This is what motivates the inference gate (§ methods); the experiment below
instantiates it: a model can be transition-perfect yet belief-wrong.

## The demonstration — masked tic-tac-toe

- **Dynamics = standard tic-tac-toe** (the most-recalled game; synthesizes at
  transition gate 1.0 — unlike Beacon). Reuse `src/cwm/groundtruth/tictactoe.py`
  dynamics unchanged.
- **Arbitrary, non-recallable masking:** `observation` hides the **center cell
  (index 4)** from both players — it is shown as `-1` even after it is played.
  Nobody plays this variant, so the masking convention cannot be recalled; it must
  be read from the rules. The information partition is otherwise full.
- `infer_states` enumerates the consistent values of the hidden center: cell 4 ∈
  {0,1,2} kept iff the resulting full board has legal tic-tac-toe counts (X starts,
  so `#X == #O` or `#X == #O+1`). The true center always qualifies; usually 1–2 of
  the 3 values do. **`current_player` is not needed from the observation** — the gate
  (`inference_accuracy`) compares the inferred **boards** only (it ignores the
  rebuilt `current_player`); each rebuilt state's `current_player` is set to the
  parity-derived value (`1 if #X==#O else 2`) so it is a genuine legal state. The
  true state is always a member; round-trip (`observation(s,p)==obs`) holds.

**The probe (`scripts/mtt_claimB_probe.py`, Azure GPT-5.4):** synthesize the
contract two ways and gate each on transitions AND inference:
- **full:** rules include the masking rule ("the center cell is hidden, shown as -1,
  even after played; infer_states enumerates its consistent values").
- **withheld:** the masking rule is removed (rules describe tic-tac-toe + that this
  is an imperfect-info variant with `observation`/`infer_states`, but NOT *what* is
  hidden).

Expected (the demonstrable triangle):
- both variants → **transition gate ≈ 1.0** (dynamics are recall, unaffected by
  masking) — the transition gate is blind to the belief model in both cases;
- **full → inference gate passes** (observation masks cell 4; infer_states correct);
- **withheld → inference gate fails** (the synthesized `observation` does not mask
  cell 4 — `observation_rate` drops — so the belief model is wrong while transitions
  are perfect).

No arena/play is needed: Claim B is a *verification-blindness* result, complementary
to Claim A's *play-inadequacy* result. Together: a wrong belief model both (A) loses
at play and (B) is invisible to a transition gate.

## Contract encoding

Reuses the perfect-info dynamics; adds the imperfect surface in a new module
`src/cwm/groundtruth/masked_tictactoe.py`:
- `initial_state`, `legal_actions`, `apply_action`, `winner`, `is_terminal`,
  `returns` — re-exported from `tictactoe` unchanged. State `{"board": list[int]
  (len 9, 0/1/2), "current_player": 1|2}`.
- `HIDDEN = 4` (the center).
- `observation(state, player) -> list[int]`: copy board, set index `HIDDEN` to -1
  (same for both players — a fixed hidden cell).
- `infer_states(obs_board, player) -> list[dict]`: for v in (0,1,2), build the board
  with cell `HIDDEN=v`; keep it iff legal tic-tac-toe counts hold (`#1 == #2` or
  `#1 == #2 + 1`). Rebuilt `current_player = 1 if #1==#2 else 2` (parity-derived;
  the gate ignores it but it keeps each state legal). `player` does not affect the
  result here (the mask is symmetric). The true state is a member; round-trip holds.
- `RULES_TEXT` = tic-tac-toe rules + the masking rule (the withheld variant is this
  string with the masking sentence removed, constructed in the probe).
- `POLICY_DESCRIPTION` reused/adapted from tic-tac-toe.
- Registered as `"masked_tictactoe"` in `src/cwm/games.py`.

## Testing

Oracle: dynamics match `tictactoe` (delegation); `observation` masks only cell 4 for
both players; `infer_states` returns the parity-consistent center values, includes
the true state, round-trips (`observation(s,player)==obs`), and on a board where the
center is forced (e.g. 8 visible cells filled) returns a singleton; `initial_state`
observation masks the (empty) center to -1.
Probe: a unit test that the withheld-rules construction actually removes the masking
sentence (non-empty diff, `assert "center" / "-1" masking phrase gone`), guarding
against a silent no-op; the synthesis call itself is exercised by a manual Azure run
(documented, not in CI).

## Out of scope

- Arena / play results (not needed for the verification-blindness claim; Claim A
  already covers play-inadequacy).
- Repairing the belief model from data (the Proposition shows transition data cannot;
  a richer "can ANY observation-bearing data teach it" study is future work).
- Player-specific masking / fog-of-war variants (a fixed hidden cell is the minimal
  non-recallable convention; richer partitions are future work).

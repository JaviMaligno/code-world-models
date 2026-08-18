# H4 handoff: common danger law and uncertainty certificate

Claude Code with `claude-fable-5` was requested for H3--H7, but the provider
reported an inference-credit block before H4 could execute. This H4 artifact is
therefore a local Codex implementation, not Claude output.

## What is now earned

`scripts/danger_law_h4.py` versions one common formulation:

- always-valid pipeline risk: `E[X 1_G] = P(G) E[X | G]`;
- exact adaptive/non-i.i.d. miss chain rule:
  `P(no E_1,...,no E_N) = product_i (1-r_i)`, where each `r_i` is conditioned
  on the previous misses;
- sharp product bounds for history-dependent hazards known only by intervals;
- the i.i.d. exponent, independent train/gate exponent, stratified schedule,
  and two-mode Frechet bracket as corollaries;
- an explicit failure limit: unconditional marginal event rates do not identify
  a miss probability under dependence or adaptive sampling.

The script also emits `results/danger_law_h4.json` (schema
`danger-law-h4/v1`). Every cart, pendulum, and PatchField2D danger event gets a
family-wise 95% exact rarity interval, propagated monotonically through every
reported danger budget. Bonferroni makes the rarity family coverage valid even
though knob rows and PatchField2D mode events are dependent.

The same records carry planner reach, its simultaneous exact interval, and the
planner-to-gate reach ratio. That ratio makes the distribution shift auditable,
but the certificate explicitly does not multiply it into
`E[X | shipped] P(shipped)`: planner reach changes the consequence summarized
by conditional play cost, whereas gate rarity determines the miss factor.

## Remaining empirical gap (must not be hidden)

Full uncertainty from *both* estimated factors is currently possible only for
the three cells with committed paired episode triples:

- cart `x_wall=8`;
- pendulum `th_stop=1.4`;
- PatchField2D `k=(3,7)` (three critical-event curves: mode 1, mode 2, union).

For those five curve/event rows, H4 recomputes a paired bootstrap from episodes
0--19, verifies that it reproduces the published play-cost point, and combines
its corners with the simultaneous rarity interval. For the other 35 rows the
JSON deliberately records `all_estimated_factors_band: null`: aggregate means
cannot identify a valid play-cost interval. Calling the rarity-only band a full
danger interval would be false.

To satisfy REVIEW5's literal “every empirical curve” criterion, rerun and
version paired `(J_truth, J_blind, J_random)` episode triples for the other
cells, then let this script consume them. This is CPU-only but is a separate
measurement campaign. No paper prose should claim full factor propagation
until that campaign is complete.

## Verification

```bash
PYTHONPATH=src .venv/bin/python scripts/danger_law_h4.py
PYTHONPATH=src .venv/bin/pytest -q tests/test_danger_law_h4.py
```

The tests independently exercise the adaptive chain rule on an enumerated
binary tree, sharp adaptive bounds, exponent addition, all admissible two-mode
couplings, interval corner propagation, point reproduction, gap accounting,
and exact freshness of the versioned JSON.

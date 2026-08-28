# Paper 3 — campaign log

Process record for the T1–T8 proof campaign: which routes were tried, in what
order, and what the wrong turns cost. **Nothing here is paper content.** The
mathematics — statements, proofs, refutations with their evidence labels —
lives in `THEORY.md`; paper prose lives in `main.tex` under the claim contract
in `.claude/skills/paper-claims`.

The reason to keep this separately rather than not at all: several routes were
attempted more than once because their earlier failure was not recorded, and
three of the campaign's false positives came from the same two testing
mistakes.

## The two recurring testing mistakes

1. **A censored zero is an interval, and its width is set by UNITS, not
   samples.** Two "0 violations" results fell to more power once the
   experimental unit was counted correctly. In T3's variant route the unit is
   the *entering pair* (only a pair whose γ₁ copy enters can falsify pathwise
   M1), which is ~2 orders of magnitude below the rollout count: 0/517 units
   became 13/30 764 once the sample was grown.
2. **Coverage, not just power.** T2's argmax-angle dominance held on 278 dirty
   steps and failed in 11 of 16 cells once *hidden* channels were included —
   the first check had sampled only facing channels. Test the claim over the
   configuration space it is stated on, not the one that was convenient.

Both now have permanent guards, and the working rule is: stress-test a new
claim over power *and* coverage **before** attempting to prove it.

## Restatements that look like reductions but are not

Four times a decomposition was proposed as progress and turned out to be
logically equivalent to the statement it was meant to reduce. The pattern in
T3 is that any split of the entry event into "get into position" × "finish"
recovers the entry event, because position is defined by the finish.

| proposed reduction | why it is a restatement |
|---|---|
| c = r·κ, so "prove κ ≤ 32" | the only free bound on κ is 1/r_int, returning c ≤ r/r_int |
| "d's rise beats f's drop" | logically equivalent to M1 itself |
| f ≤ d(2π) − d(γ) | logically equivalent to M2 itself |
| "bound P(prefix)" | a launch state is *defined* by finishing, so P(reach one) = d |

The check that catches these: state the candidate bound, then ask what the
*freest* available bound on the new quantity is. If it returns the original
statement, it is a rename.

## Mechanisms proposed and refuted

Recorded because each was intuitive enough to be worth attempting twice.

- **T2's tail as a freeze transient.** 0/556 freezes across both continuations:
  after a dirty step both branches follow π_T, which knows the mode.
- **T2's tail as route commitment.** Tail events split the two routes *less*
  often than the bulk (0.190 vs 0.299) — the correlation runs backwards. It
  was attractive because it would have tied the planner analysis to the
  paper's own topology, which is a reason for suspicion rather than belief.
- **T2's delay as a contact cost.** π_B freezes 0 times in the facing
  configuration; the delay is an aim-point cost.
- **T3's freeze as a handicap to entry.** Freezing *boosts* entry 3.7–5.8× —
  it selects for trajectories that already reached the ring's neighbourhood.
- **T3's throughput as a tangential-speed condition.** The median tangential
  speed at channel arrival is ≈0.45 independent of γ, and at γ ≥ 0.4 the
  criterion is met by 100% of arrivals while T is still 0.28.
- **T5's Bernstein-on-Z₁ route.** Computes 2.5·10⁻⁵ at n = 8 against a
  measured 2.4·10⁻³ — invalid, and the invalidity localises the error to the
  wrong tail (the cone event is a small-ball event for the perpendicular
  mass).
- **T5's σ_i comparability as "a routine estimate".** Hoeffding's union is
  vacuous; Bernstein's is 0.4–0.5; multiplicative Chernoff caps near 3.

## Claims that were stated too strongly and then corrected

- **Cor T5-U**, first written as "per-dimension rate ≤ 0.7783 with no
  probabilistic input whatever". q(u) < 1 for every u gives each coordinate a
  factor below 1, which is not an exponential rate; a rate needs
  sup_i q(u_i) < 1, hence comparable σ_i. What ρ ≥ 1 buys is a very wide
  window, not the absence of one.
- **T2's play-cost bound**, first called "the first non-vacuous bound". True
  only with a measured constant: the proved chain gives 48 and the
  competence-hypothesis chain 1.21, both vacuous against the trivial pc ≤ 1.
- **T3's f ≤ r**, first described as "loose" at small γ. It is *vacuous* for
  M1 wherever r > r_int, i.e. at every γ ≤ 0.9.

## Ledger hygiene

Twice the `RESULTS-TO-PROVE` list in `THEORY.md` contradicted the detailed
sections below it, because later passes updated the sections and not the list.
When a T-item's state changes, both places change.

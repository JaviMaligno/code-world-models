# Paper 2 review — hardening plan

Date: 2026-08-17. This review supersedes the compression recommendations in the conversational
review that preceded it. It does **not** supersede `REVIEW-RESPONSE.md` through
`REVIEW4-RESPONSE.md`; those files are the historical record of earlier external reviews and
their resolutions.

## Governing rule

The paper's contributions form a coherent chain:

1. gate miss quantifies the uncovered event;
2. identifiability states what cannot be recovered from a sample that misses it;
3. the localization budget distinguishes bounded-Lipschitz error from discontinuous modes;
4. the instruments expose the planning consequence;
5. LLM synthesis separates missing evidence from failed induction;
6. the 2D campaigns delimit the 1D repair result;
7. the independent gate, coverage certificates, second planner and mitigation test remedies and
   their limits.

Do not remove a link merely because the compilation is long or the paper has many contributions.
Strengthen vulnerable links with proofs, measurements, independent experimental units, baselines
or explicit bridge statements. Move or delete material only after showing that it is duplicative,
unused, contradictory, or forbidden by a target venue.

## Findings and routes to the strongest defensible version

### H1 — Make the disc-identifiability claim a theorem relative to a named class

**Issue.** The abstract says the disc is identifiable within the finitely parameterized families
inhabited by the artifacts and controls. Section `sec:arity` says something narrower: population
support reaches both sides; finite samples recover a circle in 12/20 baseline blocks and 20/20
high-coverage blocks; uniqueness over the broader artifact template library is not proved.

**Do not merely hedge the abstract. First try to earn it:**

1. Define a hypothesis class `H_region` explicitly (circle predicates first; then the finite
   template library actually observed in the artifact audit).
2. State and prove the finite-sample separation condition for circles. In the noiseless setting,
   three non-collinear boundary landings identify a unique circle; the proof must connect the
   observed entry transitions and the contract's integrator to those landings.
3. Add a per-seed certificate script that records rank/non-collinearity, fitted parameters and
   whether every alternative in `H_region` is separated by the sample.
4. Report identifiability at the seed-block level. If the finite template library is not
   enumerable or separable, retain the strong theorem for the circle class and name the exact
   unresolved extension instead of implying it is proved.

**Acceptance criterion.** Every use of “identified” names `(sample, hypothesis class, criterion)`;
the abstract and `sec:arity` state the same theorem and the same measured block counts.

### H2 — Generalize the localization budget at domain boundaries

**Issue.** The abstract quotes `vol(E_eps) >= ((eta-eps)/L)^(d+m)` without the corollary's premise
that the guaranteed ball is not clipped by the domain boundary.

**Earn the unconditional-looking statement instead of deleting the result:**

1. Prove the always-valid form
   `vol(E_eps) >= vol(B_infty(z0, (eta-eps)/(2L)) intersect (S x A))`.
2. Add a domain-regularity corollary: if the domain has a uniform interior-volume constant
   `kappa`, the lower bound is `kappa ((eta-eps)/L)^(d+m)`.
3. Instantiate `kappa` for the box domains used by the instruments, including face and corner
   cases. Keep the unclipped formula as the `kappa=1` interior case.
4. Scope “no finite local constant” to the discontinuous reset modes studied here; do not imply
   that every hybrid boundary is non-Lipschitz.

**Acceptance criterion.** The abstract cites a theorem valid at boundary points, and every volume
constant in prose is generated or checked by the formal/numeric audit.

### H3 — Make synthesis statistics block-first without discarding draw-level evidence

**Issue.** `105/111 draws`, `64/70 blocks`, and `0/156 attempts` describe different units. Shared
rollout samples make the draw-level observations dependent.

**Strengthening work:**

1. Add a canonical table with campaign, model, distinct seed blocks, draws per block, exact repair,
   phantom repair, refusal and blindness.
2. Keep draw-level counts as artifact census results, but make block-level results primary for
   inference.
3. Use a cluster bootstrap or a hierarchical binomial model with seed block as the cluster; version
   the script and its output JSON.
4. Where affordable, repeat the same model several times on identical samples. This identifies
   synthesizer variability separately from evidence variability.
5. Preserve the 0/156 result as a complete artifact census; do not attach an independence-based
   interval to 156.

**Acceptance criterion.** No interval treats synthesis draws sharing a rollout block as independent,
and the abstract gives both the artifact census and the independent block count.

### H4 — Strengthen the “danger law” beyond the Bernoulli identity

**Issue.** `(1-r)^N` is exact but elementary under i.i.d. sampling. The paper's novelty is the full
chain from coverage failure to planner-mediated loss.

**Strengthening work:**

1. Present the law as a tuple: critical-event miss, conditional shipped cost, distribution shift,
   and the hypotheses under which they factor.
2. Add uncertainty propagation for measured rarity and accepted-artifact play cost to every danger
   curve; retain point estimates but accompany them with simultaneous or clearly pointwise bands.
3. State a non-i.i.d. extension or failure theorem. Useful targets are beta-mixing rollouts,
   stratified gates, or adaptive gates whose conditional miss factors multiply as
   `prod_i (1-r_i(history))`.
4. Make the independent-gate exponent and the multi-mode Frechet bracket corollaries of this common
   formulation.

**Acceptance criterion.** “Danger law” refers to the pipeline-risk result, not only to a Bernoulli
miss identity, and each empirical curve carries uncertainty from all estimated factors.

### H5 — Test the representational claim against a mode-capable learned baseline

**Issue.** The sentence saying code creates an exact-repair capability “that learned models lack”
is not earned by a linear fit and an `h=8` MLP; the related-work section itself lists learned event
functions and switching models.

**Strengthening work:**

1. Add at least one baseline whose hypothesis class contains the true mode: a switching linear
   model, mixture-of-experts with a hard/temperature-controlled gate, or a learned event function.
2. Train it on exactly the same wall-free, wall-containing and 2D samples.
3. Measure off-mode error, mode-rule recovery, gate acceptance, planner play cost and sensitivity to
   the number/angular coverage of contacts.
4. Separate three conclusions: expressibility, induction from finite evidence and float-level exact
   agreement. Code may retain a strong advantage on the third even if the hybrid learner succeeds
   on the first two.

**Acceptance criterion.** The code-versus-learned conclusion quantifies the strongest mode-capable
baseline tested; if code still wins, the claim becomes stronger rather than narrower.

### H6 — Convert the 2D ablation collection into an explicit exclusion matrix

**Issue.** The eight interventions are valuable but several change more than one variable and are
post-hoc. They show that tested changes did not suffice; they do not uniquely identify an internal
LLM mechanism.

**Strengthening work:**

1. For every intervention record: target hypothesis, changed variables, unavoidable co-changes,
   pre-run prediction, experimental unit, positive control, result and strongest licensed inference.
2. Add bridge statements explaining how each negative result narrows the surviving mechanism class.
3. Design factorial follow-ups for any pair of confounded variables whose separation would change
   the headline conclusion.
4. Reserve “identified mechanism” for a design that separates the remaining alternatives; until
   then use the positive statement already supported: located-rule induction failed despite
   samples on which the explicit circle fit succeeds.

**Acceptance criterion.** A reader can reconstruct exactly which mechanism classes survive all
eight interventions, and no causal exclusion relies on a one-factor description of a multi-change
treatment.

### H7 — Generalize beyond designed deterministic instruments

**Issue.** The three instruments establish existence and mechanism, but prevalence and robustness
under noisy or externally specified dynamics remain open.

**Strengthening work, in increasing cost:**

1. Add observation/process noise while preserving a mode-aware statistical acceptance criterion;
   determine which exact statements become high-probability statements.
2. Add an externally defined contact or saturation benchmark not designed around the law.
3. Pre-specify the critical event and analysis before running that benchmark.
4. Run the same gate/planner/synthesis/held-out evaluation chain and report failures as well as
   confirmations.

**Acceptance criterion.** Either the law survives on an external benchmark, supporting a broader
claim, or the paper gains a measured boundary condition instead of a generic “toy” caveat.

## Historical review-bias audit

Files inspected: `REVIEW-RESPONSE.md`, `REVIEW2-RESPONSE.md`,
`REVIEW3-RESPONSE.md`, `REVIEW4-RESPONSE.md`, and `STRONGER-STATEMENTS.md`.

- Review 1 point 22 requested a 12--16 page main paper and complained of too many contributions.
  The response correctly rejected contribution-counting as a criterion, built a dependency audit
  showing 13/13 numbered body results support measurements, improved hierarchy, and declined the
  destructive page target.
- Review 2 point 7.1 again requested reduction. The response correctly declined it for the same
  evidence-backed reason.
- No unresolved reduction-first recommendation was found in reviews 3 or 4.
- `STRONGER-STATEMENTS.md` consistently records how weakened claims can be earned back and already
  embodies the correct policy.

Therefore no historical response text should be rewritten: it accurately records reviews and
already resists the bias. The persistent correction belongs in repository instructions and in this
forward-looking hardening plan.

## Instructions for the implementing agent

Work H1--H7 in dependency order, one claim at a time. Before changing prose, read
`.claude/skills/paper-claims/SKILL.md`. For each item:

1. write the proposed strong claim and its statement contract;
2. inspect whether existing results already prove or measure it;
3. implement the cheapest decisive proof or experiment;
4. version generated evidence under `results/` and add it to the audits;
5. update prose only after the evidence exists;
6. if the strong version cannot be earned, record the exact blocker and route in
   `STRONGER-STATEMENTS.md` rather than silently deleting the contribution.

Do not use page count as an optimization objective unless a target venue and its hard limit are
provided. Do not move a result to the supplement merely because it is technical; first check
whether a main-text measurement depends on it.

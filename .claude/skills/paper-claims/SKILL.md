---
name: paper-claims
description: >
  The statement contract for this repo's papers: how to scope a claim, when to
  strengthen instead of hedge, and how to keep research process out of the prose.
  Use whenever writing or editing docs/paper2/main.tex, docs/paper/main.tex or
  any paper-facing text; whenever a review, self-check or audit says a claim is
  too strong; and before answering "should I weaken this sentence?" (usually:
  no — earn it first). Also use when adding a heading, a bolded lead-in, an
  abstract sentence, or any number to prose.
---

# Paper claims: scope, strength, and narrative

Three rules. The linter mechanises the parts that are mechanisable
(`scripts/audit_paper_claims.py`); this file is the part it cannot express.

## 1. The statement contract

Every claim in a paper carries three things. If you cannot supply all three, the
sentence is not ready.

1. **Quantifier and scope.** Over what does it hold — all pairs, or
   bounded-Lipschitz pairs? At every knob, or at the knobs swept? Universally, or
   for the models tested? "Exactly", or "up to $C\varepsilon^2$"?
2. **Experimental unit.** The unit is almost never the thing you counted. In this
   repo the gate rollout stream ignores knob, shape and prompt, so **the unit is
   the seed block**: a pooled $k/N$ whose $N$ counts synthesis draws rather than
   blocks is not $N$ independent observations, and a Wilson interval over it is
   wrong. Say which one you mean, per claim.
3. **An evidence label, from exactly this set:**

   | label | obligation |
   |---|---|
   | **proved** | name the proposition *and* its hypotheses (`Proposition~\ref{prop:...}`) |
   | **measured** | name the JSON under `results/` and give $n$ **and** the unit |
   | **consistent-with** | say that the mechanism is *not* identified, and name the alternative you cannot exclude |

   `consistent-with` is a real label, not a softened `measured`. The template-prior
   reading of the 2D repair collapse is `consistent-with`: three campaigns agree,
   no mechanism is isolated. Say so in those words.

A claim labelled **proved** that does not name a proposition, or **measured** that
does not name a JSON, is a claim with no evidence label at all.

## 2. Strengthen first; weaken as the fallback

When a review or a self-check shows a claim is too strong, the **first** move is
to look for the experiment or the proof that earns the strong version. Hedging the
wording is the fallback, not the reflex.

The order to work in:

1. **Is there a cheap experiment?** More rollouts, a disjoint seed block, a
   non-destructive variant into a sibling JSON. Most of this repo's weakened
   claims were CPU-only to recover: censored zeros → 30k rollouts; the pooled
   0.84 → a `--seed-offset` block; "below random at every knob" → a narrowed
   phantom plateau. Costly scripts must checkpoint per unit and skip done units.
2. **Is there a proof?** Turning an assumption into a theorem is usually cheaper
   than measuring around it, and it comes out *stronger* than the original. The
   independence assumption in the joint gate-miss factor became a sharp
   Fréchet–Hoeffding bracket plus an exact sign rule — no compute at all.
   A threshold that would not converge became a *rate*, which holds at every
   $\varepsilon$ instead of below an unstable cutoff.
3. **Only then weaken** — and when you do, **record what would have earned it
   back** in `docs/paper2/STRONGER-STATEMENTS.md`: the was/now pair, the concrete
   route, its cost, and its payoff. A weakening with no route recorded is how the
   claim stays weak forever.
4. **Some weakenings are permanent, by design.** "No learner can infer it" →
   "…from the sample" is not recoverable and should not be: a prior *can* supply
   the mode. When the caveat is the content, say that in the paper.

Never let a *search* stand in for evidence ("we looked and found none" is not
"none exists"). Never state a censored zero as a zero: a printed `0` means no
occurrence in the sample, and its content is the interval.

## 3. The narrative contract

**The paper states what is true, not how the authors got there.** No "we got this
wrong before", no draft archaeology, no debugging narrative, no self-congratulation,
no ops diary. Corrections history goes in a changelog file (and the recoverable
weaknesses in `STRONGER-STATEMENTS.md`). Two tests: would this sentence survive if
someone else had written the paper? Does the reader need it to check the claim?

Rewrites from the current `docs/paper2/main.tex`:

> **Before:** "Two details in that display are easy to get wrong in the loosening
> direction, and we got both wrong first."
> **After:** "Two details tighten the display. The cardinality that enters is the
> *packing* number, which dominates the covering number, so an upper bound on it is
> what the union bound needs; and the ball mass must be intersected with $U$."

> **Before:** "Our first attempt to recover the rest was wrong in a way worth
> recording, because the error was invisible in the direction that flatters the gate.
> We argued that conditioning on a rollout's *entire* state trajectory leaves the
> action indicators independent … That is false: …"
> **After:** "Conditioning on a rollout's entire state trajectory does *not* leave
> the action indicators independent: under this plant $a_t = ((v_{t+1}-v_t)/dt +
> \mathrm{drag}\,v_t)/\mathrm{gain}$, so the trajectory determines every action and
> the conditional law is degenerate. The gate policy gives $a_t \perp s_t$, not
> $a_t \perp (s_0,\dots,s_T)$."

> **Before:** "…measuring it per episode settles a claim we had got wrong twice. The
> distinct fence count never exceeds $2/5/6$ …, not the ``about two thirds'' an
> earlier draft inferred."
> **After:** "Measured per episode, the distinct fence count never exceeds $2/5/6$ at
> knobs $(2,6)/(3,7)/(4,8)$ — at most a quarter of the $24$-fence budget. The bound
> is per-episode and must be compared against a per-episode count: raw violations are
> dominated by duplicates (two episodes record $28$ while placing at most $6$ distinct
> fences; medians $1/1/2$ against means $1.05/2.65/4.25$)."

> **Before:** "A third family (Qwen) was launched on this cell and **aborted after its
> three full-arm cells** when that provider's inference credits ran out, so it
> contributes a translation control and nothing else."
> **After:** "The Qwen arm covers the full (translation) arm only: 3/3 gate 1.000 at
> zero refinement iterations, both discs written exactly on the landing position,
> per-patch blindness 0.0. It carries no incomplete-arm evidence."

Same rule for headings: `\paragraph{The nonlinear case is not a separate case: the
constant is universal.}` → `\paragraph{The nonlinear case reuses the constant:
$c = 5/6$ at step 1 on both plants.}`

## How to check

```bash
PYTHONPATH=src .venv/bin/python scripts/audit_paper_claims.py            # ratcheted
PYTHONPATH=src .venv/bin/python scripts/audit_paper_claims.py --census   # per-pattern hits
PYTHONPATH=src .venv/bin/python scripts/audit_paper_claims.py --strict   # + hand constants
PYTHONPATH=src .venv/bin/python scripts/audit_paper2_numbers.py          # tables vs JSONs
```

The audit fails only when a rule goes **above** `results/paper_claims_baseline.json`.
Re-run `--baseline` after a cleanup pass so the ratchet tightens; never raise a
number in it. Legitimate exceptions go in `docs/paper2/claims-allowlist.txt`, each
with a one-line justification above it (an entry without one is a hard error).

Then the reviewer's-eye pass, which no linter does:

- **For each heading and each bolded lead-in, ask: what is the quantifier, and does
  the cited proposition or measurement carry it?** A heading is the unit a reader
  quotes out of context, so it must carry its own scope — it may not borrow one from
  the paragraph beneath it. The last review flagged four headings.
- For each "sound"/"certif*", finish the sentence "…sound relative to ___".
- For each interval, name the unit it is over, and check that $N$ counts units and
  not draws.
- For each number in prose, ask which script wrote it to `results/`. If none did,
  that is the finding: make the script emit it. Every peer-review arithmetic error
  in paper 2 was in a hand-computed constant the numeric audit did not cover.

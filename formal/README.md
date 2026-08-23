# formal/ — machine-checked statements for paper 2

Why this exists: two review rounds found errors in hand-written proofs while the 700-value
numeric audit passed. The weak class is hand-proved implications, and it has two guards now:

* **cheap** — `tests/test_proposition_falsification.py`: exact-arithmetic counterexample
  search over finite probability spaces, ~1 s, runs with the suite. It re-finds the second
  review's counterexamples by construction, so a false "in particular" of that shape dies
  in CI.
* **expensive** — this directory: Lean 4 + Mathlib formalizations. Under a checker, a false
  clause does not compile at all.

`Paper2Props/Paper2Props/Basic.lean` covers `prop:risk`:

| result | statement |
|---|---|
| `risk_factorizes_iff` | the factored form `D = E[X]·P(G)` ⟺ `Cov(X, 1_G) = 0` |
| `factored_of_const` | the corrected sufficient condition (globally constant cost) |
| `old_clause_is_false` | the PRE-correction clause refuted: the reviewer's fair-coin counterexample as a theorem |

## Build

```bash
brew install elan-init && elan-init -y     # once; ~/.elan
cd formal/Paper2Props
lake exe cache get                          # Mathlib binary cache, several GB
lake build                                  # compiles the proofs
```

Notes from the first install on this machine: use Apple's git (`/usr/bin/git`) if
`/usr/local`'s old Homebrew git errors on clone templates, and never run two
`lake exe cache get` concurrently (partial builds produce undefined-symbol link errors;
`rm -rf .lake/packages/mathlib/.lake/build` and re-run once).

## Scope, honestly

Formalized: `prop:risk` (probability-pure). Formalizable at days-per-proposition:
`prop:gatemiss`, `prop:twofactor`, `prop:jointmiss`. Not worth it now: `prop:epsrate`
(censored laws, pushforwards over a process) and `prop:entryclass` (needs the rollout
process modeled) — weeks each. The falsification suite covers all of the probability-level
statements regardless.

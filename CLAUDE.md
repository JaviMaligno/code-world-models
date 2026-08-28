# Paper work

Before reviewing or editing either paper, follow `.claude/skills/paper-claims/SKILL.md`.
In particular, use the strengthen-before-weaken rule and the contribution-preservation test.
The current actionable review for paper 2 is `docs/paper2/REVIEW5-HARDENING.md`.

Paper 3 mathematics is formalized in Lean as it lands: when a THEORY.md item's
proof lands or changes, formalize it in `formal/Paper2Props/Paper3Ring/` in the
same session, or record in `docs/paper3/FORMALIZATION.md` why not. That ledger
maps THEORY.md items to Lean declarations and carries the triage of what is next.

**Paper 3 is the active work: read `docs/paper3/STATE.md` first.** It says what
is open, what is decided, and how to run things here — and it is a pointer
layer, so follow it to the document that holds the detail rather than trusting
a restatement.

Paper 2 is published (arXiv:2608.17956). `results/` is shared between the
papers, so anything that globs it states which instruments it covers; do not
widen paper 2's analyses to pick up paper 3's campaigns.

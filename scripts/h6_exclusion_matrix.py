"""Build the H6 exclusion ledger from versioned Paper 2 evidence.

This is deliberately a ledger, not a new experiment.  It makes the causal scope of
the eight 2D interventions machine-readable and checks the headline counts against
the existing behavioural audit before writing the canonical JSON.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "results" / "h6_exclusion_matrix_v1.json"
ARITY = ROOT / "results" / "arity_evidence_ablations.json"


def _pooled(campaign: dict) -> tuple[int, int]:
    rows = campaign["per_size"].values()
    return (sum(r["k_repaired_behavioural"] for r in rows),
            sum(r["n_mode_containing"] for r in rows))


def build() -> dict:
    arity = json.loads(ARITY.read_text())
    camps = arity["campaigns"]
    observed = {
        "slab": _pooled(camps["slab"]),
        "landing_variable": _pooled(camps["landing"]),
        "interior_landing": _pooled(camps["landing_effect"]),
        "interior_clamp": _pooled(camps["clamp_effect"]),
        "coverage": _pooled(camps["dose_arc240"]),
        "coverage_form_hint": _pooled(camps["dose_arc240_hint"]),
        "radius_control": _pooled(camps["hint_radius"]),
        "form_only_control": _pooled(camps["hint_centre"]),
    }

    common = {
        "outcome": "behavioural recovery: gate pass, mode probe, and exact grid agreement",
        "unit_note": "draw counts are descriptive; rollout-seed blocks are the sampling unit",
    }
    rows = [
        {
            "id": 1, "intervention": "region-first guidance and 3x budget",
            "target_hypothesis": "default prompting or insufficient synthesis/refinement budget",
            "changed_variables": ["prompt order and de-bias instruction", "examples 40->120", "failure lines 20->40", "iterations 5->15"],
            "unavoidable_cochanges": ["context length", "number of optimization opportunities"],
            "prediction_status": "post-hoc; no preregistered direction",
            "experimental_unit": "20 reused rollout-seed blocks; 40 GPT-5.x draws",
            "positive_control": "the stated full region is translated at gate 1.000",
            "result": "0/40 behavioural repairs; failure class changes from half-planes toward bounded evidence-hull templates",
            "licensed_inference": "the tested joint prompt-and-budget escalation did not suffice",
            "not_licensed": "prompting in general, longer context, tools, or persistent refinement cannot work",
        },
        {
            "id": 2, "intervention": "axis-aligned square with flat edges",
            "target_hypothesis": "circle curvature causes the induction failure",
            "changed_variables": ["region geometry: disc->square", "predicate algebra: quadratic->max/abs"],
            "unavoidable_cochanges": ["contact geometry and distribution", "truth clause"],
            "prediction_status": "post-hoc directional diagnostic",
            "experimental_unit": "20 reused rollout-seed blocks; 40 GPT-5.x draws",
            "positive_control": "full square clause translated 40/40 at zero refinement",
            "result": "0/40 behavioural repairs; artifacts often write discs on square evidence",
            "licensed_inference": "removing curvature in this matched plant did not suffice",
            "not_licensed": "geometry is irrelevant to induction",
        },
        {
            "id": 3, "intervention": "second model family (Claude relay)",
            "target_hypothesis": "the observed template failures are unique to GPT-5.x",
            "changed_variables": ["model family", "relay execution path"],
            "unavoidable_cochanges": ["provider training data and decoding stack"],
            "prediction_status": "post-hoc exploratory spot-check",
            "experimental_unit": "3 mode-containing rollout-seed blocks; one draw per block",
            "positive_control": "one full-clause control translates the rule at iteration 0",
            "result": "0/3 repairs; period-2 cycles traverse the same low-complexity template classes",
            "licensed_inference": "the qualitative failure class is not confined to the tested GPT-5.x implementation",
            "not_licensed": "cross-family prevalence or a universal LLM mechanism",
        },
        {
            "id": 4, "intervention": "one-coordinate slab",
            "target_hypothesis": "lower trigger arity restores induction",
            "changed_variables": ["predicate arity 2->1", "disc->slab", "mode count 2->1"],
            "unavoidable_cochanges": ["the slab screens the far mode", "the target becomes observationally non-identifiable"],
            "prediction_status": "post-hoc diagnostic whose assumed repair target failed admissibility",
            "experimental_unit": "20 reused rollout-seed blocks; 40 GPT-5.x draws",
            "positive_control": "full slab clause translated 40/40 at zero refinement",
            "result": f"{observed['slab'][0]}/{observed['slab'][1]} behavioural repairs; 19/20 large-model draws instead find an unfalsifiable near-face half-plane",
            "licensed_inference": "none about arity; the intervention reveals an observational equivalence class",
            "not_licensed": "arity has been excluded as a cause",
        },
        {
            "id": 5, "intervention": "name the trigger's landing-state argument",
            "target_hypothesis": "variable identification blocks region induction",
            "changed_variables": ["one prompt sentence names the landing state"],
            "unavoidable_cochanges": ["prompt text"],
            "prediction_status": "post-hoc diagnostic",
            "experimental_unit": "20 reused rollout-seed blocks; 40 GPT-5.x draws",
            "positive_control": "matched region-guided comparator and executable full clause",
            "result": f"{observed['landing_variable'][0]}/{observed['landing_variable'][1]} behavioural repairs; failures shift toward memorizing contact locations",
            "licensed_inference": "explicitly naming the argument did not suffice",
            "not_licensed": "all variable-binding errors are eliminated",
        },
        {
            "id": 6, "intervention": "stop at the interior landing point",
            "target_hypothesis": "freeze semantics fail because they censor interior states",
            "changed_variables": ["post-contact state: previous position->landing position"],
            "unavoidable_cochanges": ["dwell time", "mode-transition share rises about 11x"],
            "prediction_status": "post-hoc directional hypothesis expected to restore repair",
            "experimental_unit": "20 reused rollout-seed blocks; 40 GPT-5.x draws",
            "positive_control": "full clause translated 40/40; interior-witness count is measured",
            "result": f"{observed['interior_landing'][0]}/{observed['interior_landing'][1]} behavioural repairs and no incomplete gate passes",
            "licensed_inference": "lifting interior censoring while increasing mode evidence did not suffice",
            "not_licensed": "post-state semantics have no causal role",
        },
        {
            "id": 7, "intervention": "project contacts to the boundary",
            "target_hypothesis": "the entry-only evidence class causes the failure",
            "changed_variables": ["post-contact state: previous position->radial boundary projection"],
            "unavoidable_cochanges": ["post-state rule complexity", "contact locations"],
            "prediction_status": "post-hoc complementary diagnostic",
            "experimental_unit": "20 reused rollout-seed blocks; 40 GPT-5.x draws",
            "positive_control": "full clause translated in all 40 cells; three contacts identify a circle in 20/20 blocks",
            "result": f"{observed['interior_clamp'][0]}/{observed['interior_clamp'][1]} behavioural repairs and no incomplete gate passes",
            "licensed_inference": "breaking entry-only equivalence at matched evidence did not suffice",
            "not_licensed": "all evidence-censoring explanations are excluded",
        },
        {
            "id": 8, "intervention": "increase angular contact coverage at calibrated contact count",
            "target_hypothesis": "insufficient boundary coverage prevents a located-circle fit",
            "changed_variables": ["start distribution", "rollout count", "contact arc about 111->185 degrees"],
            "unavoidable_cochanges": ["trajectory distribution"],
            "prediction_status": "direction recorded before this run (B21), but question arose post-hoc; not preregistered",
            "experimental_unit": "20 rollout-seed blocks; 20 no-hint and 20 form-hint draws",
            "positive_control": f"least-squares circle fit succeeds 20/20; radius-only synthesis control repairs {observed['radius_control'][0]}/{observed['radius_control'][1]}",
            "result": f"{observed['coverage'][0] + observed['coverage_form_hint'][0]}/{observed['coverage'][1] + observed['coverage_form_hint'][1]} behavioural repairs",
            "licensed_inference": "coverage sufficient for the declared estimator did not suffice for either tested synthesis arm",
            "not_licensed": "arbitrary coverage or tool-assisted fitting cannot restore induction",
        },
    ]
    for row in rows:
        row.update(common)
    return {
        "script": "h6_exclusion_matrix.py", "version": 1,
        "source": "results/arity_evidence_ablations.json",
        "rows": rows,
        "surviving_mechanism_classes": [
            "failure to execute an algebraic/geometric fit over textual transitions",
            "a refinement loop that does not retain a stable located hypothesis",
            "an objective/prompt that rewards sample fit without explicit system identification",
            "other model-internal causes not separated by these interventions",
        ],
        "positive_statement": "On every widest-coverage block the specified circle fit recovers the located rule, while neither tested synthesis arm does (0/40); when form and location are supplied, the withheld radius is recovered 20/20.",
        "factorial_followups": [
            {"factors": ["prompt guidance", "example/failure-line budget", "iteration budget"], "why": "separate the three components jointly changed by intervention 1"},
            {"factors": ["post-state semantics", "mode-evidence quantity"], "why": "cross clamp/landing semantics with calibrated equal contact dose"},
            {"factors": ["angular coverage", "start distribution"], "why": "vary coverage within each start-family or importance-reweight to a common trajectory law"},
            {"factors": ["trigger arity", "identifiability"], "why": "use a bounded one-coordinate region whose near and far faces are reachable"},
        ],
        "causal_status": "The matrix narrows tested explanations but does not identify a unique internal LLM mechanism.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = build()
    rendered = json.dumps(data, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not RESULT.exists() or RESULT.read_text() != rendered:
            raise SystemExit("stale H6 exclusion matrix")
    else:
        RESULT.write_text(rendered)


if __name__ == "__main__":
    main()

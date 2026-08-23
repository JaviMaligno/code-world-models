"""Held-out (three-way split) scoring of already-synthesized artifacts.

Review point #1 against paper 2: the "gate score 1.000" reported for every
accepted artifact was computed on the SAME sample the artifact was synthesized
and refined on, so it is training-set consistency, not verification. Because
every cell of ``results/continuous_synthesis_*.json`` stores its source
``code`` together with the truth-env knobs and the rollout ``seed`` that
generated its training sample, the split can be built after the fact at zero
LLM cost:

  D_train  = collect_transitions(env, cell["n_rollouts"], seed=cell["seed"])
             -- the exact sample the artifact was synthesized/refined on
  D_gate   = collect_transitions(env, N_GATE, seed=cell["seed"] + 5_000_000)
             -- the INDEPENDENT acceptance gate
  D_eval   = collect_transitions(env, n_eval,  seed=cell["seed"] + 7_000_000)
             -- the independent out-of-sample exactness probe

``collect_transitions`` seeds rollout *i* with ``random.Random(seed + i)``, so a
call with ``n`` rollouts consumes the contiguous integer block ``[seed,
seed+n)``.  Disjointness of the three families of blocks is therefore a
statement about integer intervals, and :func:`disjointness_report` proves it by
brute-force set intersection over every block any committed campaign uses (no
interval arithmetic, no clever argument).

Nothing in this module makes a network call.
"""
import math
import random
from dataclasses import asdict, dataclass, field, fields as _dc_fields

from .contract import (_compare_transitions, _run_contract_cases,
                       collect_transitions, contract_accuracy)
from .envs import CartWall, PatchField2D, PendulumStop
from .instruments import spec_for

# --- the split ---------------------------------------------------------------
# Offsets are large enough that no gate/eval block can collide with a training
# block (training rollout seeds are 10_000*(i+1+offset) <= 400_000) and the two
# held-out families cannot collide with each other.  Both facts are *proved*
# by disjointness_report(), not asserted here.
GATE_SEED_OFFSET = 5_000_000
EVAL_SEED_OFFSET = 7_000_000
N_GATE = 40                       # never reduce this (it is the danger-law N)
N_EVAL_DEFAULT = 100

# Training-sample seed grid used by scripts/continuous_danger_synthesis.py:
#   rollout_seed = 10_000 * (seed_index + 1 + seed_offset),  seed_index < 20
TRAIN_SEED_STRIDE = 10_000
TRAIN_N_SEED_INDEX = 20
TRAIN_SEED_OFFSETS = (0, 20)
TRAIN_N_ROLLOUTS = 40             # every committed campaign used --n-rollouts 40


def train_rollout_seeds(n_seed_index: int = TRAIN_N_SEED_INDEX,
                        offsets=TRAIN_SEED_OFFSETS) -> list[int]:
    """Every training rollout seed any committed campaign can have used."""
    return [TRAIN_SEED_STRIDE * (i + 1 + off)
            for off in offsets for i in range(n_seed_index)]


def seed_block(seed: int, n_rollouts: int) -> set[int]:
    """The literal set of integers ``random.Random`` is constructed from when
    ``collect_transitions(env, n_rollouts, seed=seed)`` runs."""
    return set(range(seed, seed + n_rollouts))


def disjointness_report(n_train: int = TRAIN_N_ROLLOUTS, n_gate: int = N_GATE,
                        n_eval: int = N_EVAL_DEFAULT,
                        gate_offset: int = GATE_SEED_OFFSET,
                        eval_offset: int = EVAL_SEED_OFFSET,
                        train_seeds=None) -> dict:
    """Brute-force proof that the three block families never share a rollout
    seed.  Builds the actual integer sets and intersects them; also checks the
    gate blocks are mutually disjoint and the eval blocks are mutually
    disjoint (a within-family collision would make two artifacts share a
    held-out sample by accident rather than by design)."""
    train_seeds = list(train_rollout_seeds() if train_seeds is None
                       else train_seeds)
    train_union: set[int] = set()
    for s in train_seeds:
        train_union |= seed_block(s, n_train)
    gate_blocks = {s: seed_block(s + gate_offset, n_gate) for s in train_seeds}
    eval_blocks = {s: seed_block(s + eval_offset, n_eval) for s in train_seeds}
    gate_union: set[int] = set()
    eval_union: set[int] = set()
    gate_self_overlaps, eval_self_overlaps = [], []
    for s, blk in gate_blocks.items():
        if gate_union & blk:
            gate_self_overlaps.append(s)
        gate_union |= blk
    for s, blk in eval_blocks.items():
        if eval_union & blk:
            eval_self_overlaps.append(s)
        eval_union |= blk
    return {
        "n_train_seeds": len(train_seeds),
        "train_seed_min": min(train_seeds), "train_seed_max": max(train_seeds),
        "n_train": n_train, "n_gate": n_gate, "n_eval": n_eval,
        "gate_seed_offset": gate_offset, "eval_seed_offset": eval_offset,
        "train_union_size": len(train_union),
        "gate_union_size": len(gate_union),
        "eval_union_size": len(eval_union),
        "train_gate_overlap": sorted(train_union & gate_union),
        "train_eval_overlap": sorted(train_union & eval_union),
        "gate_eval_overlap": sorted(gate_union & eval_union),
        "gate_within_family_overlap_seeds": gate_self_overlaps,
        "eval_within_family_overlap_seeds": eval_self_overlaps,
        "all_disjoint": not (train_union & gate_union)
                        and not (train_union & eval_union)
                        and not (gate_union & eval_union)
                        and not gate_self_overlaps and not eval_self_overlaps,
    }


def split_for_cell(env, cell: dict, n_eval: int = N_EVAL_DEFAULT,
                   n_gate: int = N_GATE):
    """(D_train, D_gate, D_eval) for one artifact, reproduced exactly."""
    seed = cell["seed"]
    n_train = cell.get("n_rollouts", TRAIN_N_ROLLOUTS)
    d_train = collect_transitions(env, n_train, seed=seed)
    d_gate = collect_transitions(env, n_gate, seed=seed + GATE_SEED_OFFSET)
    d_eval = collect_transitions(env, n_eval, seed=seed + EVAL_SEED_OFFSET)
    return d_train, d_gate, d_eval


# --- truth-env reconstruction ------------------------------------------------
# Params whose name differs from the env field they set.
_PARAM_ALIASES = {"start_arc": "start_arc_deg"}
# Params that describe the CAMPAIGN, not the truth env, and so must not reach it.
# Listed explicitly because env_from_params refuses to silently drop anything else.
_PARAMS_NOT_ENV = frozenset({
    "arm", "size", "seed_offset", "n_seeds", "n_rollouts", "play_episodes",
    "max_iters", "eps", "prompt_variant", "mode_hint", "instrument",
    "compat_model", "compat_base_url", "k1", "k2", "th_stop", "x_wall",
    "out_tag",   # a FILENAME tag for split-provenance re-runs; never touches the env
})


def env_from_params(params: dict):
    """Rebuild the truth env from a synthesis file's top-level ``params``,
    exactly as scripts/continuous_danger_synthesis.py builds it.  Older
    committed files predate some flags, so the defaults here must be the
    argparse defaults of that script (instrument=cart, patch_shape=disc,
    th_stop=1.4, k1=3.0, k2=7.0)."""
    instrument = params.get("instrument", "cart")
    if instrument == "pendulum":
        return PendulumStop(th_stop=params.get("th_stop", 1.4))
    if instrument == "patch2d":
        # Pass through EVERY param that names a field of the env rather than an
        # enumerated few. Enumerating is how `mode_effect` and `start_arc` came to be
        # dropped: the landing, clamp and evidence-dose campaigns were rebuilt as
        # `freeze` boxes and therefore scored against the wrong truth. A knob added to
        # the env in future is carried here automatically or not at all.
        fields = {f.name for f in _dc_fields(PatchField2D)}
        kwargs, unknown = {}, []
        for k, v in params.items():
            if k in _PARAMS_NOT_ENV:
                continue
            name = _PARAM_ALIASES.get(k, k)
            if name in fields:
                if v is not None:
                    kwargs[name] = v
            else:
                unknown.append(k)
        if unknown:
            # A param that is neither a field, an alias, nor declared irrelevant is a
            # knob this function would DROP. Dropping `start_arc` (the field is
            # `start_arc_deg`) rebuilt the dose campaigns as their own controls, which
            # is a wrong answer rather than a missing one. So it raises.
            raise ValueError(
                f"env_from_params does not know what to do with {sorted(unknown)}: add "
                f"each to _PARAM_ALIASES (it names an env field under another name) or "
                f"to _PARAMS_NOT_ENV (it does not describe the truth env)")
        kwargs.pop("p1", None)
        kwargs.pop("p2", None)
        return PatchField2D(p1=(params.get("k1", 3.0), 0.0),
                            p2=(params.get("k2", 7.0), 0.0), **kwargs)
    if instrument == "cart":
        return CartWall(x_wall=params["x_wall"])
    raise ValueError(f"unknown instrument {instrument!r}")


# The shape tag inside env_key.  "sq" is kept for the square because 625 already-audited
# artifacts carry keys built with it; anything new gets its own unambiguous tag.
_SHAPE_TAG = {"square": "sq", "slab": "slab"}


def env_key(params: dict) -> str:
    """A stable name for the truth env: the identity of the rollout stream.
    Two artifacts with the same env_key AND the same seed share their D_train /
    D_gate / D_eval samples bit-for-bit (the streams depend on the env and the
    seed only -- not on the arm, the model, or the prompt variant), so this is
    the key any independence-respecting count must deduplicate on."""
    instrument = params.get("instrument", "cart")
    if instrument == "pendulum":
        return f"pendulum_thstop{params.get('th_stop', 1.4):g}"
    if instrument == "patch2d":
        # Every field the ROLLOUT STREAM depends on has to be in this key, or two
        # different instruments deduplicate onto one sample.  The original form
        # mapped any non-disc shape to "sq", so the SLAB collided with the SQUARE:
        # at a shared knob it would silently have been scored against the square's
        # rarity.  It was caught only because the slab's calibrated knob (5.5) has no
        # R_SOURCES entry and the guard refused to run -- luck, not design.  The
        # mode's post-state and the start arc change the stream too.  Defaults are
        # omitted so every key computed before this fix is unchanged.
        shape = params.get("patch_shape", "disc")
        key = f"patch2d{'' if shape == 'disc' else _SHAPE_TAG[shape]}_"
        key += f"k{params.get('k1', 3.0):g}_{params.get('k2', 7.0):g}"
        effect = params.get("mode_effect", "freeze")
        if effect != "freeze":
            key += f"_{effect}"
        arc = params.get("start_arc")
        if arc is not None:
            key += f"_arc{arc:g}"
        n_roll = params.get("n_rollouts", 40)
        if n_roll != 40:
            key += f"_n{n_roll}"
        return key
    return f"cart_xwall{params['x_wall']:g}"


# --- rarity constants used for the two-factor prediction ---------------------
# Every entry names the JSON and the exact key it is read from; the audit
# script RE-READS each source at run time and refuses to run if a value drifted
# (no hand-copied constant is ever trusted).
R_SOURCES = {
    "cart_xwall8": {
        "r": 0.011433333333333334, "kind": "firing",
        "source": "results/continuous_reach.json",
        "path": "rows[x_wall==8.0].rarity",
        "note": "30k-rollout mode-firing rarity (paper Table tab:danger)"},
    "cart_xwall4": {
        "r": 0.13516666666666666, "kind": "firing",
        "source": "results/continuous_reach.json",
        "path": "rows[x_wall==4.0].rarity",
        "note": "30k-rollout mode-firing rarity (paper Table tab:danger)"},
    "pendulum_thstop1.4": {
        "r": 0.0196, "kind": "firing",
        "source": "results/continuous_pendulum.json",
        "path": "rows[th_stop==1.4].rarity",
        "note": "30k-rollout mode-firing rarity"},
    "pendulum_thstop1": {
        "r": 0.12703333333333333, "kind": "firing",
        "source": "results/continuous_pendulum.json",
        "path": "rows[th_stop==1.0].rarity",
        "note": "30k-rollout mode-firing rarity"},
    "patch2d_k3_7": {
        "r": 0.15, "kind": "firing_union",
        "source": "results/continuous_patch2d.json",
        "path": "rows[k1==3.0,k2==7.0].r_either",
        "per_mode": {"patch1": 0.14166666666666666,
                     "patch2": 0.008333333333333333},
        "per_mode_path": {"patch1": "rows[k1==3.0,k2==7.0].r1",
                          "patch2": "rows[k1==3.0,k2==7.0].r2"},
        "note": "600-rollout union rarity r_either (disc)"},
    "patch2dsq_k3_7": {
        "r": None, "kind": "firing_union_unavailable",
        "source": "results/continuous_patch2d_square.json",
        "path": "rows[k1==3.0,k2==7.0]: r_either NOT stored for the square "
                "ablation; only r1/r2 are",
        "per_mode": {"patch1": 0.185, "patch2": 0.008333333333333333},
        "per_mode_path": {"patch1": "rows[k1==3.0,k2==7.0].r1",
                          "patch2": "rows[k1==3.0,k2==7.0].r2"},
        "note": "union rarity not calibrated for the square ablation; the "
                "independence surrogate r1+r2-r1*r2 is reported separately "
                "and clearly labelled as derived, never as a measured r"},
    "patch2d_k5_9": {
        "r": None, "kind": "uncalibrated",
        "source": None,
        "path": "no committed calibration: continuous_patch2d.json sweeps "
                "k1 in {2,3,4} x k2 in {6,7,8} only",
        "per_mode": None, "per_mode_path": None,
        "note": "the (5,9) disc cell has no calibrated rarity in results/; "
                "the two-factor prediction is reported as null for it"},
    "patch2dslab_k5.5_7": {
        "r": None, "kind": "firing_union_unavailable",
        "source": "results/patch2d_slab_calibration.json",
        "path": "units.rarity_imperm.measure: r1 only; the slab campaign's "
                "calibration measured patch-1 contact rarity, not the union",
        "per_mode": {"patch1": 0.12816666666666668, "patch2": None},
        "per_mode_path": {"patch1": "units.rarity_imperm.measure.r1",
                          "patch2": "not measured for the slab"},
        "note": "the ARITY ablation (2026-07-29), rarity-matched to the disc's "
                "r1 = 0.1417 by MOVING the mode to k1 = 5.5, at 30k rollouts. "
                "Its own repair target is identified only up to prop:entryclass "
                "(results/mode_identifiability.json), so the two-factor "
                "prediction is reported for it but the repair count is not read "
                "as an exclusion"},
    "patch2d_k3_7_landing": {
        "r": 0.15266666666666667, "kind": "firing_union",
        "source": "results/mode_effect_calibration.json",
        "path": "variants.landing.rarity",
        "per_mode": None, "per_mode_path": None,
        "note": "1500 rollouts only (CI 0.135-0.172), against the disc's 600-"
                "rollout 0.15 -- a wider interval than the headline instruments. "
                "The value is IDENTICAL to freeze's and clamp's to every digit, "
                "and that is correct rather than a copy error: whether a rollout "
                "contains an entry is settled by the trajectory UP TO the first "
                "entry, which the three post-states share"},
    "patch2d_k3_7_clamp": {
        "r": 0.15266666666666667, "kind": "firing_union",
        "source": "results/mode_effect_calibration.json",
        "path": "variants.clamp.rarity",
        "per_mode": None, "per_mode_path": None,
        "note": "see patch2d_k3_7_landing: same sample size, same value, same "
                "reason it is the same value"},
    "patch2d_k3_7_arc120_n15": {
        "r": None, "kind": "uncalibrated",
        "source": "results/evidence_dose_calibration.json",
        "path": "arms.arc120: the dose calibration measured CONTACT COUNT and "
                "angular coverage per seed block, and blocks_with_a_contact "
                "(20/20) -- none of which is a per-rollout union rarity",
        "per_mode": None, "per_mode_path": None,
        "note": "the evidence-dose arm's rarity was never measured at a sample "
                "size that would support it, so the two-factor prediction is "
                "reported as null here rather than computed from a surrogate"},
    "patch2d_k3_7_arc240_n15": {
        "r": None, "kind": "uncalibrated",
        "source": "results/evidence_dose_calibration.json",
        "path": "arms.arc240: as arc120 -- contacts and coverage, not rarity",
        "per_mode": None, "per_mode_path": None,
        "note": "as arc120. Note the ring start raises the contact SHARE of the "
                "sample by construction, so the disc's r cannot be borrowed"},
    "patch2dsq_k5_9": {
        "r": None, "kind": "firing_union_unavailable",
        "source": "results/continuous_patch2d_square.json",
        "path": "rows[k1==5.0,k2==9.0]: r_either NOT stored",
        "per_mode": {"patch1": 0.056666666666666664, "patch2": 0.005},
        "per_mode_path": {"patch1": "rows[k1==5.0,k2==9.0].r1",
                          "patch2": "rows[k1==5.0,k2==9.0].r2"},
        "note": "square ablation, union rarity not calibrated"},
}


def independence_surrogate(r1: float, r2: float) -> float:
    """P(at least one of two independent modes fires) = r1 + r2 - r1*r2.
    Only used where a measured union rarity is absent, and always labelled."""
    return r1 + r2 - r1 * r2


# --- scoring ------------------------------------------------------------------
def _case_err(t: dict, got: dict) -> float:
    """Sup-norm error of one sandbox result against the truth transition, using
    the SAME formula _compare_transitions uses.  Reporting only: the pass/fail
    decision always comes from _compare_transitions itself."""
    if "error" in got:
        return math.inf
    if len(got["ns"]) != len(t["next_state"]):
        return math.inf
    return max(max(abs(g - e) for g, e in zip(got["ns"], t["next_state"])),
               abs(got["r"] - t["reward"]))


@dataclass
class ScoreResult:
    """Held-out score of one artifact on one sample."""
    n: int
    n_correct: int
    accuracy: float
    n_fail: int
    n_mode_contact: int              # transitions where the truth mode fired
    n_fail_mode_contact: int         # failures that ARE mode contacts
    n_fail_off_mode: int             # failures that are NOT mode contacts
    max_err_off_mode_fail: float | None
    max_err_all: float | None
    max_err_off_mode_all: float | None
    exact_outside_mode: bool | None   # every failure is a mode contact
    infra_error: str | None = None
    fail_source_indices: list[int] = field(default_factory=list)

    def to_json(self) -> dict:
        d = asdict(self)
        for k in ("max_err_off_mode_fail", "max_err_all", "max_err_off_mode_all"):
            if d[k] is not None and not math.isfinite(d[k]):
                d[k] = "inf"
        return d


def score_transitions(code: str, transitions: list[dict], eps: float,
                      timeout: float = 300.0) -> ScoreResult:
    """Score `code` on `transitions` and break the failures down by whether
    the truth's mode fired on that transition.

    The accuracy is derived from the same two primitives ``contract_accuracy``
    is built from (``_run_contract_cases`` + ``_compare_transitions``) so that
    it is numerically identical to ``contract_accuracy(code, transitions,
    eps)[0]`` -- tested in tests/test_heldout_gate.py, which asserts equality
    on both a passing and a failing artifact.  We cannot simply call
    ``contract_accuracy``: it discards WHICH transitions failed, and the
    mode-contact vs off-mode split of the failures is the load-bearing part of
    this audit (a held-out failure on off-mode float noise is a different
    finding from a held-out failure on the mode)."""
    n = len(transitions)
    n_contact = sum(1 for t in transitions if t["contact"])
    if n == 0:
        return ScoreResult(0, 0, 0.0, 0, 0, 0, 0, None, None, None, None,
                           "no transitions provided")
    produced, err = _run_contract_cases(code, transitions, timeout=timeout)
    if produced is None:
        # mirrors contract_accuracy's infra-failure convention (accuracy 0.0)
        return ScoreResult(n, 0, 0.0, n, n_contact, n_contact, n - n_contact,
                           None, None, None, None, err,
                           [t["source_index"] for t in transitions])
    n_correct, _failures, failed_positions = _compare_transitions(
        transitions, produced, eps)
    errs = [_case_err(t, g) for t, g in zip(transitions, produced)]
    fail_contact = [i for i in failed_positions if transitions[i]["contact"]]
    fail_off = [i for i in failed_positions if not transitions[i]["contact"]]
    off_all = [errs[i] for i in range(min(len(errs), n))
               if not transitions[i]["contact"]]
    return ScoreResult(
        n=n, n_correct=n_correct, accuracy=n_correct / n,
        n_fail=len(failed_positions), n_mode_contact=n_contact,
        n_fail_mode_contact=len(fail_contact),
        n_fail_off_mode=len(fail_off),
        max_err_off_mode_fail=(max(errs[i] for i in fail_off)
                               if fail_off else None),
        max_err_all=(max(errs) if errs else None),
        max_err_off_mode_all=(max(off_all) if off_all else None),
        exact_outside_mode=(len(fail_off) == 0),
        infra_error=None,
        fail_source_indices=[transitions[i]["source_index"]
                             for i in failed_positions[:50]])


# --- mode presence ------------------------------------------------------------
def mode_presence(env, transitions: list[dict]) -> dict:
    """Whether (and how often) the truth's mode fired in `transitions`.

    ``any`` is the union event ("the sample contains a mode contact"), the same
    event ``contract.sample_contains_mode`` reports.  ``per`` is the per-mode
    breakdown from the instrument spec's ``sample_modes`` (patch2d only; None
    elsewhere).  ``n_rollouts_with_contact`` counts *rollouts*, which is the
    unit the rarity r is defined on."""
    spec = spec_for(env)
    n_contact = sum(1 for t in transitions if t["contact"])
    h = env.h_episode
    rollouts_with = {t["source_index"] // h for t in transitions if t["contact"]}
    n_rollouts = (len(transitions) + h - 1) // h
    out = {
        "any": n_contact > 0,
        "n_contact_transitions": n_contact,
        "n_transitions": len(transitions),
        "n_rollouts": n_rollouts,
        "n_rollouts_with_contact": len(rollouts_with),
        "per": None,
    }
    if spec.sample_modes is not None:
        out["per"] = spec.sample_modes(env, transitions)
    return out


def blind_from_cell(cell: dict) -> bool | None:
    """The paper's probe-based mode-blindness event for one artifact: fully
    blind on EVERY mode.  None when the original run never computed it (it is
    only computed for artifacts whose in-sample gate reached 1.0)."""
    per = cell.get("mode_blindness")
    if isinstance(per, dict):
        if not per:
            return None
        return all(v == 1.0 for v in per.values())
    wb = cell.get("wall_blindness")
    if wb is None:
        return None
    return wb == 1.0


# --- aggregation --------------------------------------------------------------
def wilson(k: int, n: int) -> list[float] | None:
    """Wilson 95% interval, imported lazily so this module stays importable
    without the law helpers."""
    if n == 0:
        return None
    from ..law import wilson_ci
    _point, lo, hi = wilson_ci(k, n)
    return [lo, hi]


def contingency(records: list[dict], *, row_key, col_key) -> dict:
    """2x2 table {rowvalue: {colvalue: count}} plus the off-diagonal detail."""
    table = {"gate_mode_absent": {"accepted": 0, "rejected": 0},
             "gate_mode_present": {"accepted": 0, "rejected": 0}}
    off_diagonal = []
    for rec in records:
        row = ("gate_mode_absent" if not row_key(rec) else "gate_mode_present")
        col = "accepted" if col_key(rec) else "rejected"
        table[row][col] += 1
        if (row == "gate_mode_absent") != (col == "accepted"):
            off_diagonal.append({
                "file": rec["file"], "arm": rec["arm"], "seed": rec["seed"],
                "row": row, "col": col,
                "gate_accuracy_heldout": rec["gate"]["accuracy"],
                "gate_n_fail_mode_contact": rec["gate"]["n_fail_mode_contact"],
                "gate_n_fail_off_mode": rec["gate"]["n_fail_off_mode"]})
    n = len(records)
    agree = table["gate_mode_absent"]["accepted"] + \
        table["gate_mode_present"]["rejected"]
    return {"n": n, "table": table,
            "coincides_exactly": n > 0 and agree == n,
            "n_agree": agree, "n_disagree": n - agree,
            "off_diagonal": off_diagonal}


def failure_class(score: dict) -> str:
    if score["infra_error"]:
        return "infra_error"
    if score["n_fail"] == 0:
        return "no_failures"
    if score["n_fail_off_mode"] == 0:
        return "mode_only"
    if score["n_fail_mode_contact"] == 0:
        return "off_mode_only"
    return "mixed"

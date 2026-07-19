"""Guard-only AST/MDL feature characterization of a synthesized artifact.

`guard_features(code, integrator_reward_ast)` parses a candidate `step`
program and computes structural complexity features on the GUARD
condition(s) only -- the boolean `test` expressions of `If`/`IfExp` branches
that decide whether the reset/freeze outcome fires -- and explicitly EXCLUDES:

  - auxiliary branches (e.g. action clamping: `if a > 1: a = 1`), identified
    heuristically as conditionals whose test references only the action
    parameter (the 2nd positional arg of the `step`/entry function) and not
    the state parameter;
  - the shared integrator/reward code fragment (`integrator_reward_ast`, a
    representative snippet of the physics update all candidates share, e.g.
    `vx2 = vx + (gain*cos(phi) - drag*vx)*dt`), matched structurally via
    `ast.dump` fingerprints and treated as an opaque (degree-0) leaf if a
    guard test happens to embed it.

This matters because a naive whole-program AST scan for `Mult`/`Pow` nodes
picks up the integrator's `state_var * constant` products and reports
`guard_poly_degree >= 2` for nearly every artifact, even ones with a purely
linear guard (e.g. `x2 >= 8.0`). Scoping the scan to just the branch test
node(s) -- which never include the integrator's own assignment statement --
already avoids most of this; the fingerprint exclusion is a defensive
second layer for guards that happen to inline shared code.

Degree bookkeeping treats `var * const` and `var ** const` as NOT increasing
degree beyond the variable's own degree scaled by the constant exponent
(`Pow` with a numeric exponent multiplies degree by that exponent), while
`var * var` (two non-constant operands) sums degrees, matching ordinary
multivariate polynomial degree.
"""
from __future__ import annotations

import ast
from typing import Optional


_INVALID_RESULT = {
    "n_comparisons": 0,
    "boolean_depth": 0,
    "n_literals": 0,
    "guard_poly_degree": 0,
    "uses_hypot_sqrt": False,
    "n_conjuncts": 0,
    "n_disjuncts": 0,
    "guard_ast_size": 0,
    "approx_mdl": 0,
    "invalid": True,
}


def guard_features(code: str, integrator_reward_ast: str) -> dict:
    """Compute guard-only AST/MDL features for a candidate `step` program.

    Returns a dict with keys `n_comparisons, boolean_depth, n_literals,
    guard_poly_degree, uses_hypot_sqrt, n_conjuncts, n_disjuncts,
    guard_ast_size, approx_mdl, invalid`. On unparseable `code`, returns the
    same keys with `invalid=True` and zeroed/False numeric fields.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return dict(_INVALID_RESULT)

    fingerprints = _integrator_fingerprints(integrator_reward_ast)
    guard_tests = _find_guard_tests(tree, fingerprints)

    stats = {
        "n_comparisons": 0,
        "n_literals": 0,
        "guard_ast_size": 0,
        "uses_hypot_sqrt": False,
        "n_conjuncts": 0,
        "n_disjuncts": 0,
    }
    max_degree = 0
    max_bool_depth = 0
    for test in guard_tests:
        _accumulate_stats(test, fingerprints, stats)
        max_degree = max(max_degree, _poly_degree(test, fingerprints))
        max_bool_depth = max(max_bool_depth, _boolop_depth(test))

    approx_mdl = stats["guard_ast_size"] + stats["n_literals"]

    return {
        "n_comparisons": stats["n_comparisons"],
        "boolean_depth": max_bool_depth,
        "n_literals": stats["n_literals"],
        "guard_poly_degree": max_degree,
        "uses_hypot_sqrt": stats["uses_hypot_sqrt"],
        "n_conjuncts": stats["n_conjuncts"],
        "n_disjuncts": stats["n_disjuncts"],
        "guard_ast_size": stats["guard_ast_size"],
        "approx_mdl": approx_mdl,
        "invalid": False,
    }


# --------------------------------------------------------------------------
# Fingerprinting the shared integrator/reward fragment
# --------------------------------------------------------------------------

def _integrator_fingerprints(integrator_reward_ast: str) -> set:
    """ast.dump fingerprints of every subexpression of the shared fragment.

    Used to treat any guard-test subtree that structurally matches a piece
    of the shared integrator/reward code as an opaque, degree-0 leaf --
    i.e. explicitly "subtracted" from the guard's own polynomial degree.
    """
    try:
        frag_tree = ast.parse(integrator_reward_ast)
    except SyntaxError:
        return set()
    fingerprints = set()
    for node in ast.walk(frag_tree):
        if isinstance(node, (ast.Module, ast.Load, ast.Store, ast.Expr, ast.Assign)):
            continue
        try:
            fingerprints.add(ast.dump(node, annotate_fields=False))
        except Exception:
            continue
    return fingerprints


def _is_fingerprinted(node: ast.AST, fingerprints: set) -> bool:
    if not fingerprints:
        return False
    try:
        return ast.dump(node, annotate_fields=False) in fingerprints
    except Exception:
        return False


# --------------------------------------------------------------------------
# Locating guard test expressions (excluding auxiliary/clamp branches)
# --------------------------------------------------------------------------

def _get_entry_params(tree: ast.AST) -> tuple:
    """Positional parameter names of the first function def (state, action)."""
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            args = node.args.args
            state_param = args[0].arg if len(args) >= 1 else None
            action_param = args[1].arg if len(args) >= 2 else None
            return state_param, action_param
    return None, None


def _refs_name(node: ast.AST, name: Optional[str]) -> bool:
    if name is None:
        return False
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and n.id == name:
            return True
    return False


def _branch_reset_shaped(branch) -> bool:
    """True if a branch looks like it constructs/returns a (new) state
    vector -- the hallmark of a reset/freeze outcome -- rather than a bare
    scalar reassignment (the hallmark of an auxiliary clamp)."""
    if branch is None:
        return False
    if isinstance(branch, list):  # If.body / If.orelse: list of statements
        for stmt in branch:
            if isinstance(stmt, ast.Return) and isinstance(stmt.value, (ast.List, ast.Tuple)):
                return True
        return False
    if isinstance(branch, ast.expr):  # IfExp.body / IfExp.orelse
        return isinstance(branch, (ast.List, ast.Tuple, ast.Call))
    return False


def _find_guard_tests(tree: ast.AST, fingerprints: set) -> list:
    """Return the highest-priority group of If/IfExp `test` expressions.

    Priority order (highest wins, ties keep all): a test that references the
    state parameter (directly or via a derived local) AND whose branch is
    reset-shaped > a test that references the state parameter only > any
    other non-auxiliary test. Tests classified as action-only clamps, or
    tests that are themselves exactly the shared integrator/reward fragment,
    are excluded outright.
    """
    state_param, action_param = _get_entry_params(tree)
    candidates = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test, body, orelse = node.test, node.body, node.orelse
        elif isinstance(node, ast.IfExp):
            test, body, orelse = node.test, node.body, node.orelse
        else:
            continue

        # The shared integrator/reward fragment itself is not a guard.
        if _is_fingerprinted(test, fingerprints):
            continue

        refs_state = _refs_name(test, state_param)
        refs_action = _refs_name(test, action_param)
        # Auxiliary/clamp branch: references only the action var, not state.
        if refs_action and not refs_state and action_param is not None:
            continue

        priority = 1 if refs_state else 0
        if _branch_reset_shaped(body) or _branch_reset_shaped(orelse):
            priority += 1
        candidates.append((priority, test))

    if not candidates:
        return []
    best = max(p for p, _ in candidates)
    return [t for p, t in candidates if p == best]


# --------------------------------------------------------------------------
# Feature accumulation over a guard test sub-AST
# --------------------------------------------------------------------------

_HYPOT_SQRT_NAMES = {"hypot", "sqrt"}


def _call_name(node: ast.Call) -> Optional[str]:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _accumulate_stats(node: ast.AST, fingerprints: set, stats: dict) -> None:
    """Walk a guard-test subtree, stopping (opaquely) at fingerprinted
    (shared-integrator) subtrees, tallying size/literal/comparison/call
    stats and flattened conjunct/disjunct counts."""
    stats["guard_ast_size"] += 1
    if _is_fingerprinted(node, fingerprints):
        return  # opaque leaf: do not descend, do not count as guard's own complexity

    if isinstance(node, ast.Constant):
        stats["n_literals"] += 1
    elif isinstance(node, ast.Compare):
        stats["n_comparisons"] += len(node.ops)
    elif isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            stats["n_conjuncts"] += len(node.values)
        elif isinstance(node.op, ast.Or):
            stats["n_disjuncts"] += len(node.values)
    elif isinstance(node, ast.Call):
        name = _call_name(node)
        if name in _HYPOT_SQRT_NAMES:
            stats["uses_hypot_sqrt"] = True

    for child in ast.iter_child_nodes(node):
        _accumulate_stats(child, fingerprints, stats)


def _boolop_depth(node: ast.AST, current: int = 0) -> int:
    """Max nesting depth of BoolOp (And/Or) nodes; 0 if none present."""
    depths = [current]
    if isinstance(node, ast.BoolOp):
        current += 1
        depths.append(current)
        for v in node.values:
            depths.append(_boolop_depth(v, current))
    else:
        for child in ast.iter_child_nodes(node):
            depths.append(_boolop_depth(child, current))
    return max(depths)


# --------------------------------------------------------------------------
# Polynomial degree of a guard-test expression
# --------------------------------------------------------------------------

def _is_pure_constant(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return True
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        return _is_pure_constant(node.operand)
    return False


def _const_value(node: ast.AST):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_const_value(node.operand)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd):
        return _const_value(node.operand)
    return None


def _poly_degree(node: Optional[ast.AST], fingerprints: set) -> int:
    """Structural polynomial degree of a guard (sub)expression.

    `var * const` / `var ** const` scale the variable's own degree rather
    than summing as if both operands were independent variables; `var *
    var` (two non-constant operands) sums degrees. A subtree that matches
    the shared integrator/reward fingerprint is treated as an opaque,
    degree-0 constant-like term (explicitly excluded from the guard's own
    complexity)."""
    if node is None:
        return 0
    if _is_fingerprinted(node, fingerprints):
        return 0

    if isinstance(node, ast.Constant):
        return 0
    if isinstance(node, (ast.Name, ast.Subscript, ast.Attribute)):
        return 1
    if isinstance(node, ast.UnaryOp):
        return _poly_degree(node.operand, fingerprints)
    if isinstance(node, ast.BinOp):
        left = _poly_degree(node.left, fingerprints)
        right = _poly_degree(node.right, fingerprints)
        if isinstance(node.op, (ast.Add, ast.Sub)):
            return max(left, right)
        if isinstance(node.op, ast.Mult):
            if _is_pure_constant(node.left):
                return right
            if _is_pure_constant(node.right):
                return left
            return left + right
        if isinstance(node.op, ast.Div):
            if _is_pure_constant(node.right):
                return left
            return left + right
        if isinstance(node.op, ast.Pow):
            exp = _const_value(node.right)
            if isinstance(exp, (int, float)) and left > 0:
                return int(left * exp)
            if isinstance(exp, (int, float)) and exp == 0:
                return 0
            return left
        # unknown operator: conservative fallback
        return max(left, right)
    if isinstance(node, ast.Call):
        arg_degrees = [_poly_degree(a, fingerprints) for a in node.args]
        base = max(arg_degrees) if arg_degrees else 0
        return max(1, base)
    if isinstance(node, ast.Compare):
        degrees = [_poly_degree(node.left, fingerprints)]
        degrees.extend(_poly_degree(c, fingerprints) for c in node.comparators)
        return max(degrees)
    if isinstance(node, ast.BoolOp):
        return max(_poly_degree(v, fingerprints) for v in node.values)
    if isinstance(node, ast.IfExp):
        return max(
            _poly_degree(node.test, fingerprints),
            _poly_degree(node.body, fingerprints),
            _poly_degree(node.orelse, fingerprints),
        )
    # generic fallback: max over children
    children = list(ast.iter_child_nodes(node))
    if not children:
        return 0
    return max(_poly_degree(c, fingerprints) for c in children)

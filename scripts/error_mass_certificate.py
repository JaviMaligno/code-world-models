"""Enumeration-free error-mass certificate (companion to the coverage bound).

Unlike scripts/coverage_bound_constants.py, which enumerates the reachable
info-sets and their exact reach probabilities, this certificate needs NO
enumeration: no |I|, no pi_min, no reach probabilities. Its only inputs are

  N       gate size (i.i.d. games checked, detectability as in Theorem 1)
  delta   confidence level
  b       max branching at player info-sets   (rule-level constant)
  bar_d   player-move horizon: max number of player-action edges on any
          complete history (rule-level constant, bar_d >= d_max)

b and bar_d are boundable by inspection of the rules; we verify them here
with a cheap tree walk only because Kuhn/Leduc make that free. Nothing else
about the game is touched, so the certificate applies verbatim to games far
too large to enumerate.

Certified quantities (Theorem 2 + reach-ratio corollary in the paper):
  (held-out gate, fixed candidate)  mu_rho(E_f) <= ln(1/delta)/N
  (transfer, any profile sigma)     P_sigma(hit E_f) <= b^bar_d * ln(1/delta)/N
  (mixture gate, weight lambda)     P_planner(hit E_f) <= ln(1/delta)/(lambda*N)
                                    P_sigma(hit E_f)   <= b^bar_d * ln(1/delta)/((1-lambda)*N)
  (Occam / class-uniform)           N needed so that ANY gate-passing program of
                                    <= ell bits has mass <= eps:
                                    N >= ((ell+1)ln2 + ln(1/delta)) / eps

Run: PYTHONPATH=src python scripts/error_mass_certificate.py
"""
import math
from cwm.groundtruth import kuhn_poker as kuhn
from cwm.groundtruth import leduc_poker as leduc


def structural_constants(model):
    """Verify (b, bar_d) by tree walk. Both are rule-level constants that can be
    bounded by inspection without any traversal; this walk is a convenience check
    and reads NO reach probabilities and counts NO info-sets."""
    b = 0
    bar_d = 0

    def rec(state, depth):
        nonlocal b, bar_d
        if model.is_terminal(state):
            bar_d = max(bar_d, depth)
            return
        legal = model.legal_actions(state)
        b = max(b, len(legal))
        for a in legal:
            rec(model.apply_action(state, a), depth + 1)

    for d in model.initial_states():
        rec({"board": list(d["board"]), "current_player": d["current_player"]}, 0)
    return b, bar_d


def certify(name, model, N_used, delta=0.05, lam=0.5, ell_bits=10_000, enum_note=""):
    b, bar_d = structural_constants(model)
    eps = math.log(1.0 / delta) / N_used                 # held-out gate, fixed candidate
    ratio = float(b) ** bar_d                            # reach-ratio bound b^bar_d
    transfer = min(1.0, ratio * eps)                     # any profile, pure-random gate
    mix_planner = min(1.0, eps / lam)                    # mixture gate: deployed planner
    mix_any = min(1.0, ratio * eps / (1.0 - lam))        # mixture gate: any profile
    # Occam / class-uniform: N needed for mass <= eps_target over <= ell-bit programs
    eps_target = 0.01
    N_occam = ((ell_bits + 1) * math.log(2.0) + math.log(1.0 / delta)) / eps_target
    print(f"=== {name} ===", flush=True)
    print(f"  inputs: N = {N_used}, delta = {delta}, b = {b}, bar_d = {bar_d} "
          f"(no |I|, no pi_min, no reach probabilities)", flush=True)
    print(f"  certified sampling-mass of undetected error region: "
          f"mu_rho(E_f) <= ln(1/delta)/N = {eps:.4g}", flush=True)
    print(f"  transfer to ANY profile (pure-random gate, ratio b^bar_d = {ratio:.0f}): "
          f"P_sigma(hit E_f) <= {transfer:.4g}"
          f"{'  [VACUOUS]' if ratio * eps >= 1.0 else ''}", flush=True)
    print(f"  mixture gate (lambda = {lam}, same N): deployed planner <= {mix_planner:.4g}; "
          f"any profile <= {mix_any:.4g}"
          f"{'  [any-profile VACUOUS]' if ratio * eps / (1 - lam) >= 1.0 else ''}", flush=True)
    print(f"  Occam/class-uniform note: mass <= {eps_target} for every gate-passing "
          f"program of <= {ell_bits} bits needs N >= {N_occam:,.0f} "
          f"(demanding: N must exceed the artifact description length; "
          f"prefer a held-out gate in practice)", flush=True)
    if enum_note:
        print(f"  vs enumeration route: {enum_note}", flush=True)
    print("", flush=True)


certify("Kuhn", kuhn, N_used=80,
        enum_note="coverage bound certifies FULL coverage at N=80 (N_suff=66) -- "
                  "stronger where enumeration is feasible")
certify("Leduc", leduc, N_used=8000,
        enum_note="coverage bound needs N~27k (tight) / 7.4M (loose) and does NOT "
                  "certify N=8000; the mixture error-mass certificate holds at N=8000 "
                  "with no enumeration")
print("DONE", flush=True)

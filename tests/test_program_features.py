"""Guard-only AST/MDL feature extraction (excludes the shared integrator)."""
from cwm.continuous.program_features import guard_features

INTEG = "vx2 = vx + (gain*math.cos(phi) - drag*vx)*dt"  # representative shared-code fragment


def test_guard_degree_excludes_integrator():
    # a purely linear guard must read as degree 1 even though the integrator multiplies vars
    lin = "def step(s,a):\n    x2=s[0]+s[2]*0.1\n    return [8.0,0.0] if x2>=8.0 else [x2,s[1],s[2],s[3]]\n"
    assert guard_features(lin, INTEG)["guard_poly_degree"] == 1
    quad = "def step(s,a):\n    x2=s[0]+s[2]*0.1\n    return list(s) if (x2-3)**2+s[1]**2<=1 else [x2,s[1],s[2],s[3]]\n"
    assert guard_features(quad, INTEG)["guard_poly_degree"] >= 2


def test_invalid_flag():
    assert guard_features("def step(:\n", INTEG)["invalid"] is True

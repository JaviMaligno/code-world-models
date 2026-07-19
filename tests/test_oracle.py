import math, random
from cwm.continuous.shapes import Circle, Parabola, RegularPolygon
from cwm.continuous.shapes import HalfPlane, Strip, Wedge
from cwm.continuous.oracle import (fit_family, operational_reconstructs_vs_truth,
                                   operational_heldout_accuracy, tangent_baseline, SUFFICIENCY_UNCERTIFIED)
import math
BOX = ((-8.0,14.0),(-6.0,6.0))

def _labeled(shape, seed=0, n=1500):
    rng = random.Random(seed)
    pts = [(rng.uniform(0,6), rng.uniform(-3,3)) for _ in range(n)]
    return [(p, shape.contains(p)) for p in pts]

def test_fit_recovers_true_circle_R1():
    fit = fit_family("circle", _labeled(Circle(3.0,0.0,1.0)), BOX)
    assert abs(fit.cx-3.0) < 0.15 and abs(fit.R-1.0) < 0.15  # R=1 reachable (box bounds, not observed range)

def test_oracle_vs_truth_all_families():
    for fam, shp in (("halfplane", HalfPlane(3.0)), ("strip", Strip(3.0,1.0)),
                     ("circle", Circle(3.0,0.0,1.0)), ("parabola", Parabola(3.0,2.0)),
                     ("wedge", Wedge((3.0,0.0), math.radians(30), 0.0)),
                     ("polygon", RegularPolygon(3.0,0.0,1.0,5,0.0))):
        assert operational_reconstructs_vs_truth(fam, _labeled(shp), shp, BOX, iou_thresh=0.85)

def test_oracle_heldout_accuracy():
    shp = Circle(3.0,0.0,1.0)
    assert operational_heldout_accuracy("circle", _labeled(shp, seed=0), _labeled(shp, seed=1)) > 0.9

def test_tangent_baseline_classifies_with_side_and_offset():
    shp = Circle(3.0,0.0,1.0)
    hp = tangent_baseline(_labeled(shp, n=400))
    # a clear interior point is classified inside, a clear exterior point outside
    assert hp.contains((3.0,0.0)) and not hp.contains((7.0,0.0))

def test_sufficiency_uncertified_sentinel():
    assert SUFFICIENCY_UNCERTIFIED is True

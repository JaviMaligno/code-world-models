from cwm.cost_meter import CostMeter, extrapolate, PRICES
from cwm.llm.provider import Usage

def test_prices_have_three_roles():
    assert {"large", "mini", "nano"} <= set(PRICES)

def test_cost_accumulates_by_role():
    m = CostMeter()
    m.add("nano", Usage(prompt_tokens=1_000_000, completion_tokens=0))
    m.add("large", Usage(prompt_tokens=0, completion_tokens=1_000_000))
    assert m.by_role["nano"] > 0 and m.by_role["large"] > 0
    assert abs(m.total_usd() - (m.by_role["nano"] + m.by_role["large"])) < 1e-9

def test_extrapolate_linear():
    assert extrapolate(0.5, 10) == 5.0

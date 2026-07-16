"""InstrumentSpec: the env-specific parts of the synthesis contract. The cart
spec must reproduce the pre-refactor prompt byte-for-byte (golden fixtures) so
the committed §6 cart results stay reproducible."""
import pathlib

from cwm.continuous.envs import CartWall, PendulumStop
from cwm.continuous.instruments import CART_SPEC, PENDULUM_SPEC, spec_for

FIX = pathlib.Path(__file__).parent / "fixtures"


def _contract(spec, env, include_mode):
    return spec.api_text + "\n" + spec.rules_text(env, include_mode)


def test_cart_spec_is_byte_identical_to_golden():
    env = CartWall(x_wall=8.0)
    assert _contract(CART_SPEC, env, True) == (FIX / "cart_contract_full.txt").read_text()
    assert _contract(CART_SPEC, env, False) == (FIX / "cart_contract_incomplete.txt").read_text()


def test_spec_for_dispatches_by_type():
    assert spec_for(CartWall(x_wall=8.0)) is CART_SPEC
    assert spec_for(PendulumStop(th_stop=1.4)) is PENDULUM_SPEC


def test_pendulum_rules_text_has_gravity_and_stop():
    env = PendulumStop(th_stop=1.4)
    full = _contract(PENDULUM_SPEC, env, True)
    assert "grav = 2.0" in full
    assert "math.sin(th)" in full
    assert "th_stop" in full or "1.4" in full
    incomplete = _contract(PENDULUM_SPEC, env, False)
    assert "1.4" not in incomplete.split("Reward")[0] or "stop" not in incomplete.lower()


def test_pendulum_mode_probes_fire_the_stop_in_truth():
    env = PendulumStop(th_stop=1.4)
    probes = PENDULUM_SPEC.mode_probes(env)
    assert list(probes) == ["stop"]
    for state, action in probes["stop"]:
        _s2, _r, contact = env.step(state, action)
        assert contact, f"probe {state},{action} must fire the stop in truth"


def test_mode_probes_are_dicts_and_fire():
    from cwm.continuous.envs import PatchField2D
    from cwm.continuous.instruments import PATCH2D_SPEC, spec_for
    env = PatchField2D()
    assert spec_for(env) is PATCH2D_SPEC
    probes = PATCH2D_SPEC.mode_probes(env)
    assert set(probes) == {"patch1", "patch2"}
    for name, plist in probes.items():
        for s, a in plist:
            c1, c2 = env.contact_modes(s, a)
            assert (c1, c2) == ((name == "patch1"), (name == "patch2"))


def test_cart_probes_dict_single_mode():
    from cwm.continuous.instruments import CART_SPEC
    env = CartWall(x_wall=8.0)
    probes = CART_SPEC.mode_probes(env)
    assert list(probes) == ["wall"] and len(probes["wall"]) == 3

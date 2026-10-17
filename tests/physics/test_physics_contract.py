"""Contract equivalence: the numpy physics against sympy.lambdify of theory/contract.yaml.

The contract arrives on this branch only through integration, so the file-based tests
skip with an explicit reason when theory/contract.yaml is absent from the working tree or
is a different contract version from the one the registry implements
(nacre.physics.contract.CONTRACT_VERSION). Until integration brings that version,
nacre.physics.devtools.check_contract_equivalence runs the same checks against the theory
lane's branch and records the commit (configs/preprint/contract_check.json). The detection tests at the end
run always: they prove the checker rejects a sign-slipped implementation.
"""
from pathlib import Path

import pytest

from nacre.physics import contract as registry
from nacre.physics.devtools import equivalence as eq

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "theory" / "contract.yaml"
SYMBOLS = ROOT / "theory" / "symbols.yaml"
ABSENT = "theory/contract.yaml is not on this branch yet (it arrives with integration of lane p0-w3)"


@pytest.fixture(scope="module")
def contract():
    if not (CONTRACT.exists() and SYMBOLS.exists()):
        pytest.skip(ABSENT)
    c = eq.Contract(CONTRACT.read_text(encoding="utf-8"), SYMBOLS.read_text(encoding="utf-8"))
    if c.doc.get("version") != registry.CONTRACT_VERSION:
        pytest.skip("theory/contract.yaml on this branch is version %s; the implementation targets version %s, "
                    "checked against the theory lane's commit in configs/preprint/contract_check.json"
                    % (c.doc.get("version"), registry.CONTRACT_VERSION))
    return c


@pytest.mark.parametrize("name", sorted(registry.FUNCTIONS))
def test_implementation_matches_contract_expression(contract, name):
    if name not in contract.functions:
        pytest.fail("%s is registered but not in the contract" % name)
    for res in (eq.check_function(contract, name), eq.check_limits(contract, name),
                eq.check_monotonicity(contract, name)):
        assert res.ok, res.messages


def test_every_contract_function_is_implemented(contract):
    assert sorted(set(contract.functions) - set(registry.FUNCTIONS)) == []


def test_template_barrier_matches_contract_composite(contract):
    res = eq.check_composite(contract)
    assert res.ok, res.messages


def test_constant_relations_hold():
    assert eq.check_constants()


def test_recorded_check_is_a_pass_for_the_implemented_version():
    import json
    rec = json.loads((ROOT / "configs" / "preprint" / "contract_check.json").read_text(encoding="utf-8"))
    assert rec["status"] == "PASS" and rec["rtol"] == 1e-12
    assert rec.get("contract_version") == registry.CONTRACT_VERSION
    assert sorted(rec["functions"]) == sorted(set(registry.FUNCTIONS) | {"DG_het_template"})


# ------------------------------------------------------------------ the checker catches slips
MINI_SYMBOLS = """
symbols:
  - {id: gamma_sl, unit: J m^-2, interval: '(-oo, oo)'}
  - {id: gamma_sn0, unit: J m^-2, interval: '(-oo, oo)'}
  - {id: Delta_gamma_w, unit: J m^-2, interval: '(-oo, oo)'}
  - {id: gamma_nl, unit: J m^-2, interval: '(0, oo)'}
"""
MINI_CONTRACT = """
functions:
  - name: cos_theta_young
    unit: '1'
    expression: (gamma_sl - gamma_sn0 - Delta_gamma_w)/gamma_nl
"""


def test_checker_accepts_the_registered_young_relation():
    c = eq.Contract(MINI_CONTRACT, MINI_SYMBOLS)
    assert eq.check_function(c, "cos_theta_young").ok


def test_checker_rejects_a_sign_slipped_young_relation(monkeypatch):
    def slipped(gamma_sl, gamma_sn0, Delta_gamma_w, gamma_nl):
        return (gamma_sl - gamma_sn0 + Delta_gamma_w) / gamma_nl

    entry = registry.FUNCTIONS["cos_theta_young"]
    monkeypatch.setitem(registry.FUNCTIONS, "cos_theta_young", registry.Entry(slipped, entry.args))
    res = eq.check_function(eq.Contract(MINI_CONTRACT, MINI_SYMBOLS), "cos_theta_young")
    assert not res.ok and "relative error" in res.messages[0]


def test_checker_rejects_a_wrong_argument_set(monkeypatch):
    entry = registry.FUNCTIONS["cos_theta_young"]
    monkeypatch.setitem(registry.FUNCTIONS, "cos_theta_young",
                        registry.Entry(lambda a, b, c: a, entry.args[:3]))
    assert not eq.check_function(eq.Contract(MINI_CONTRACT, MINI_SYMBOLS), "cos_theta_young").ok


ILL = """
functions:
  - name: x_bind
    unit: '1'
    expression: log(1 + gamma_nl) - gamma_nl
"""
ILL_SYMBOLS = """
symbols:
  - {id: gamma_nl, unit: '1', interval: '(0, 1e-6)'}
"""


def test_conditioning_allowance_never_excuses_a_less_accurate_implementation(monkeypatch):
    # log(1 + x) - x for tiny x cancels badly: an accurate log1p form passes, a single-
    # precision evaluation (worse than the contract's own double-precision formula) fails.
    import numpy as np
    c = eq.Contract(ILL, ILL_SYMBOLS)
    monkeypatch.setitem(registry.FUNCTIONS, "x_bind", registry.Entry(lambda g: np.log1p(g) - g, ("gamma_nl",)))
    assert eq.check_function(c, "x_bind").ok
    sloppy = lambda g: (np.log1p(np.float32(g)) - np.float32(g)).astype(float)
    monkeypatch.setitem(registry.FUNCTIONS, "x_bind", registry.Entry(sloppy, ("gamma_nl",)))
    assert not eq.check_function(c, "x_bind").ok

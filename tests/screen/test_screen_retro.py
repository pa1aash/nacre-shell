"""Retrodiction entry point (W2.3): interface mappings, intervals, swap check and permutation null.

Every case here is synthetic, built so that its verdict is known by construction; the frozen
preprint/retrodiction/cases.yaml is never run in this suite.
"""
import numpy as np
import pytest
import yaml

from nacre.physics.constants import GAS_CONSTANT
from nacre.screen import retro

SHARED = {"gamma_nl": {"symbol": "gamma_nl", "distribution": {"type": "uniform", "low": 0.10, "high": 0.12},
                       "unit": "J m^-2"},
          "V_m": {"symbol": "V_m", "value": 3.7e-5, "unit": "m^3 mol^-1"},
          "water": {"symbol": "gamma_w", "value": {"gamma_w": 72.0, "gamma_w_polar": 50.0, "gamma_w_dispersive": 22.0},
                    "unit": "mJ m^-2"}}
COMMON = [{"symbol": "Omega", "role": "shared", "distribution": {"type": "uniform_log", "low_sigma": 4.0, "high_sigma": 5.0},
           "unit": "1"},
          {"symbol": "T", "role": "shared", "value": 298.0, "unit": "K"}]


def _case(cid, inputs, relation="test_higher_barrier", study="S-A"):
    return {"id": cid, "study": study, "termination": "thiol", "negative": False, "status": "usable",
            "outcome": {"relation": relation}, "inputs": COMMON + inputs}


def _dupre(cid, test, ref, unit="kcal mol^-1", relation="test_higher_barrier", study="S-A"):
    return _case(cid, [
        {"symbol": "dG_bind", "role": "test", "distribution": {"type": "normal", "mean": test, "sd": 0.1}, "unit": unit},
        {"symbol": "dG_bind", "role": "reference", "distribution": {"type": "normal", "mean": ref, "sd": 0.1}, "unit": unit},
        {"symbol": "A_c", "role": "shared", "distribution": {"type": "uniform", "low": 0.3, "high": 0.4}, "unit": "nm^2"}],
        relation, study)


def _write(tmp_path, cases, shared=SHARED):
    p = tmp_path / "cases.yaml"
    p.write_text(yaml.safe_dump({"schema": "retro-cases/v1", "shared_priors": shared, "cases": cases}), encoding="utf-8")
    return p


def test_dupre_maps_adhesion_to_gamma_sn_and_weaker_adhesion_raises_the_barrier(tmp_path):
    # W = |dG|/(N_A A_c) ~ 0.08 J/m^2 against W ~ 0.16: cos theta -0.3 against +0.5 on the reference
    rec = retro.run_cases(_write(tmp_path, [_dupre("RC01", -4.0, -8.0)]), draws=4000, n_perm=0)
    c = rec["cases"][0]
    assert c["interface"] == "gamma_sn" and c["mapping"] == "dupre"
    assert c["delta"]["q05"] > 0 and c["verdict"] == "correct"
    assert c["barrier_test"]["median"] > c["barrier_reference"]["median"] > 0
    assert c["swap_check"]["holds"]
    rec = retro.run_cases(_write(tmp_path, [_dupre("RC01", -4.0, -8.0, relation="test_lower_barrier")]), draws=4000,
                          n_perm=0)
    assert rec["cases"][0]["verdict"] == "incorrect"
    rec = retro.run_cases(_write(tmp_path, [_dupre("RC01", -6.0, -6.0)]), draws=4000, n_perm=0)
    assert rec["cases"][0]["verdict"] == "inconclusive"


def test_kt_units_resolve_with_the_pair_temperature(tmp_path):
    kcal = retro.run_cases(_write(tmp_path, [_dupre("RC01", -4.0, -8.0)]), draws=2000, n_perm=0, seed=3)
    from nacre.screen.units import factor
    kt = factor("kcal mol^-1", "J mol^-1") / (GAS_CONSTANT * 298.0)   # one kcal/mol in units of R T
    rec = retro.run_cases(_write(tmp_path, [_dupre("RC01", -4.0 * kt, -8.0 * kt, unit="kT")]), draws=2000, n_perm=0,
                          seed=3)
    assert rec["cases"][0]["delta"]["median"] == pytest.approx(kcal["cases"][0]["delta"]["median"], rel=0.02)


def test_ca_binding_maps_to_gamma_sl_through_gibbs_langmuir(tmp_path):
    # stronger binding (higher c_local) lowers gamma_sl, lowers cos theta and RAISES the barrier (SF2)
    case = _case("RC11", [
        {"symbol": "c_local", "role": "test", "distribution": {"type": "normal", "mean": 4.9, "sd": 0.05}, "unit": "mM"},
        {"symbol": "c_local", "role": "reference", "distribution": {"type": "normal", "mean": 2.0, "sd": 0.05}, "unit": "mM"},
        {"symbol": "c_bulk", "role": "shared", "value": 1.0, "unit": "mM"},
        {"symbol": "Gamma_s", "role": "shared", "value": 5.0e-6, "unit": "mol m^-2"},
        {"symbol": "delta_s", "role": "shared", "value": 1.0e-9, "unit": "m"},
        {"symbol": "cos_theta", "role": "shared", "distribution": {"type": "uniform", "low": -0.2, "high": 0.2}, "unit": "1"}])
    c = retro.run_cases(_write(tmp_path, [case]), draws=4000, n_perm=0)["cases"][0]
    assert c["interface"] == "gamma_sl" and c["mapping"] == "gibbs_langmuir"
    assert c["verdict"] == "correct" and c["swap_check"]["holds"]


def test_owrk_and_net_mappings_and_label_symmetry(tmp_path):
    owrk = _case("RC07", [
        {"symbol": "gamma_s_owrk", "role": "test", "value": {"polar": 80.0, "dispersive": 3.0}, "unit": "mJ m^-2"},
        {"symbol": "gamma_s_owrk", "role": "reference", "value": {"polar": 28.0, "dispersive": 11.0}, "unit": "mJ m^-2"},
        {"symbol": "cos_theta_ref", "role": "shared", "distribution": {"type": "uniform", "low": -0.5, "high": 0.5},
         "unit": "1"}])
    net = _case("RC06", [
        {"symbol": "gamma_net_sim", "role": "test", "distribution": {"type": "normal", "mean": 100.0, "sd": 2.0},
         "unit": "mJ m^-2"},
        {"symbol": "gamma_net_sim", "role": "reference", "distribution": {"type": "normal", "mean": 50.0, "sd": 2.0},
         "unit": "mJ m^-2"}])
    rec = retro.run_cases(_write(tmp_path, [owrk, net]), draws=4000, n_perm=0)
    by = {c["id"]: c for c in rec["cases"]}
    assert by["RC07"]["interface"] == "gamma_sl" and by["RC06"]["interface"] == "f_theta"
    assert by["RC06"]["verdict"] == "correct"
    assert rec["summary"]["swap_check"]["holds"] and rec["summary"]["swap_check"]["max_abs_sum"] == 0.0


def test_local_omega_mappings_are_refused(tmp_path):
    case = _case("RC11", [
        {"symbol": "c_local", "role": "test", "value": 2.0, "unit": "mM", "maps_to": "Omega_local = E_enr Omega_bulk"},
        {"symbol": "c_local", "role": "reference", "value": 4.0, "unit": "mM"}])
    with pytest.raises(retro.CaseError, match="Omega_local"):
        retro.run_cases(_write(tmp_path, [case]), draws=100, n_perm=0)


def test_unknown_inputs_and_missing_keys_are_refused(tmp_path):
    bad = _case("RC01", [{"symbol": "mystery", "role": "test", "value": 1.0, "unit": "1"},
                         {"symbol": "mystery", "role": "reference", "value": 1.0, "unit": "1"}])
    with pytest.raises(retro.CaseError, match="no interface mapping"):
        retro.run_cases(_write(tmp_path, [bad]), draws=100, n_perm=0)
    shared = dict(SHARED, gamma_nl={"symbol": "gamma_nl", "params_key": "gamma_calcite_water"})
    table = tmp_path / "params.yaml"
    table.write_text(yaml.safe_dump({"mock": True, "params": {}}), encoding="utf-8")
    with pytest.raises(retro.CaseError, match="BLOCKED"):
        retro.run_cases(_write(tmp_path, [_dupre("RC01", -4.0, -8.0)], shared), params_path=table, draws=100, n_perm=0)


def test_pass_threshold_and_permutation_null(tmp_path):
    assert retro.pass_threshold(12) == 10
    cases = [_dupre("RC%02d" % i, -2.0 - 0.3 * i, -8.0 - 0.3 * i, study="S-%d" % (i % 3)) for i in range(1, 7)]
    rec = retro.run_cases(_write(tmp_path, cases), draws=2000, n_perm=50, seed=1)
    s = rec["summary"]
    assert s["N"] == 6 and s["correct"] == 6 and s["k"] == retro.pass_threshold(6) and s["pass"]
    null = s["permutation_null"]
    assert null["descriptive"] and sum(null["counts"]) == 50 and 0.0 <= null["p_value_ge_observed"] <= 1.0
    assert s["study_level"]["studies"] == 3 and rec["cases_sha256"].startswith("sha256:")


def test_an_undetermined_prediction_counts_as_a_miss():
    assert retro.verdict(None, "test_higher_barrier") == "undetermined"

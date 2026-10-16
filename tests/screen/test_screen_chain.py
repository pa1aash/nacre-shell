"""The screen chain reproduces the contract functions draw by draw; clipping only in the screen."""
from pathlib import Path

import numpy as np
import pytest

from nacre.physics import nucleation, template
from nacre.physics import supersaturation as sat
from nacre.screen import chain, params_adapter, propagate

ROOT = Path(__file__).resolve().parents[2]
MOCK = ROOT / "configs" / "preprint" / "mock_params.yaml"


@pytest.fixture(scope="module")
def draws():
    rp = params_adapter.regime_priors(MOCK, "R-slurry", allow_mock=True)
    x = rp.joint.sample(np.random.default_rng(11), 20_000)
    return {s: x[:, j] for j, s in enumerate(rp.joint.symbols)}


def test_all_three_links_are_evaluable_from_the_mock_table(draws):
    assert chain.evaluable_links(draws) == ["anchor", "sequester", "nucleate"]
    assert chain.evaluable_links({"T": 1.0}) == []


def test_template_barrier_equals_the_contract_composite_on_in_domain_draws(draws):
    out, _ = chain.evaluate(draws)
    nuc, seq = out["nucleate"], out["sequester"]
    ratio = (draws["gamma_sl"] - draws["gamma_sn0"] - draws["Delta_gamma_w"]) / draws["gamma_nl"]
    ok = (np.abs(ratio) < 1) & (nuc["Omega_local"] > 1)
    assert ok.sum() > 1000
    args = {k: draws[k][ok] for k in template.COMPOSITE_ARGS if k != "Delta_G_seq"}
    args["Delta_G_seq"] = seq["Delta_G_seq"][ok]
    want = template.template_heterogeneous_barrier(*[args[k] for k in template.COMPOSITE_ARGS])
    kt = nucleation.barrier_in_kT(want, draws["T"][ok])
    assert np.allclose(nuc["barrier_het_template_kT"][ok], kt, rtol=1e-12, atol=0)


def test_bulk_barrier_uses_the_bulk_saturation_and_no_template(draws):
    out, _ = chain.evaluate(draws)
    nuc = out["nucleate"]
    om = sat.saturation_ratio_bulk(draws["a_Ca"], draws["a_CO3"], draws["K_sp"])
    ok = om > 1
    hom = nucleation.homogeneous_barrier_from_saturation(draws["gamma_nl"][ok], draws["V_m"][ok], om[ok], draws["T"][ok])
    assert np.allclose(nuc["barrier_hom_bulk_kT"][ok], nucleation.barrier_in_kT(hom, draws["T"][ok]), rtol=1e-12)
    assert np.all(np.isnan(nuc["barrier_hom_bulk_kT"][~ok]))        # Omega <= 1: no barrier


def test_young_ratio_outside_the_domain_is_clipped_and_counted(draws):
    out, masses = chain.evaluate(draws)
    nuc = out["nucleate"]
    ratio = (draws["gamma_sl"] - draws["gamma_sn0"] - draws["Delta_gamma_w"]) / draws["gamma_nl"]
    m = masses["nucleate"]["cos_theta"]
    assert m.n_spread == int((ratio > 1).sum()) > 0
    assert m.n_nonwetting == int((ratio < -1).sum()) > 0
    assert np.all(nuc["f_theta"][ratio > 1] == 0.0)
    assert np.all(nuc["f_theta"][ratio < -1] == 1.0)
    assert np.all(np.abs(nuc["cos_theta"]) <= 1.0)


def test_sequestration_follows_the_cycle_with_the_protonation_correction(draws):
    from nacre.physics.sequestration import sequestration_free_energy
    out, _ = chain.evaluate(draws)
    want = sequestration_free_energy(draws["Delta_G_site"], draws["pKa"], draws["pH"], draws["T"])
    assert np.allclose(out["sequester"]["Delta_G_seq"], want, rtol=1e-12)
    assert np.all(out["sequester"]["c_local"] <= out["sequester"]["E_enr"] * draws["c_bulk"] * (1 + 1e-12))


def test_chunked_propagation_is_reproducible_and_counts_boundary_mass_over_chunks():
    rp = params_adapter.regime_priors(MOCK, "R-slurry", allow_mock=True)
    a, ma = propagate.propagate_chain(chain.evaluate, rp.joint, 5000, seed=3, chunk=1024)
    b, mb = propagate.propagate_chain(chain.evaluate, rp.joint, 5000, seed=3, chunk=1024)
    assert np.array_equal(a["nucleate"]["f_theta"], b["nucleate"]["f_theta"])
    assert ma["nucleate"]["cos_theta"].n_finite == 5000
    assert ma["nucleate"]["cos_theta"] == mb["nucleate"]["cos_theta"]

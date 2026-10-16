"""Enrichment, its saturation bound and Omega with enrichment (contract C2 and supersaturation)."""
import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from nacre.physics.constants import GAS_CONSTANT
from nacre.physics.sequestration import (
    binding_layer_saturation_concentration,
    enrichment_factor,
    local_calcium_concentration,
    sequestration_free_energy,
)
from nacre.physics.supersaturation import saturation_ratio_bulk, saturation_ratio_local

pos = st.floats(min_value=1e-6, max_value=1e6)
temps = st.floats(min_value=1.0, max_value=2000.0)
reals = st.floats(min_value=-1e5, max_value=1e5)


@given(pos, pos, pos)
def test_local_concentration_never_exceeds_saturation_or_the_dilute_value(e, cb, cm):
    c = local_calcium_concentration(e, cb, cm)
    assert c <= cm * (1 + 1e-15)
    assert c <= e * cb * (1 + 1e-15)


@given(pos, pos, pos)
def test_local_concentration_is_harmonic_combination(e, cb, cm):
    assert 1 / local_calcium_concentration(e, cb, cm) == pytest.approx(1 / (e * cb) + 1 / cm, rel=1e-12)


def test_local_concentration_limits():
    assert local_calcium_concentration(0.0, 1.0, 1.0) == 0.0
    assert local_calcium_concentration(3.0, 2.0, 1e300) == pytest.approx(6.0, rel=1e-12)
    assert local_calcium_concentration(3.0, 1e300, 5.0) == pytest.approx(5.0, rel=1e-12)


@given(reals, temps)
def test_enrichment_is_boltzmann_factor(dg, t):
    x = -dg / (GAS_CONSTANT * t)
    if abs(x) < 700:
        assert enrichment_factor(dg, t) == pytest.approx(math.exp(x), rel=1e-12)


def test_no_transfer_free_energy_means_no_enrichment():
    assert enrichment_factor(0.0, 300.0) == 1.0


@given(reals, st.floats(min_value=-20, max_value=20), st.floats(min_value=-20, max_value=20), temps)
def test_protonation_correction_never_favours_binding(g, pka, ph, t):
    assert sequestration_free_energy(g, pka, ph, t) >= g


def test_protonation_correction_at_pka_is_rt_ln2():
    assert sequestration_free_energy(0.0, 7.0, 7.0, 300.0) == pytest.approx(GAS_CONSTANT * 300.0 * math.log(2), rel=1e-12)


@given(pos, pos, pos, pos)
def test_omega_local_in_the_dilute_limit_is_enrichment_times_bulk(e, a, b, k):
    cb = 1.0
    cl = local_calcium_concentration(e, cb, 1e300)
    assert saturation_ratio_local(cl, cb, a, b, k) == pytest.approx(e * saturation_ratio_bulk(a, b, k), rel=1e-12)


def test_omega_local_equals_bulk_without_enrichment():
    assert saturation_ratio_local(2.0, 2.0, 0.1, 0.2, 1e-3) == pytest.approx(saturation_ratio_bulk(0.1, 0.2, 1e-3))


def test_saturation_concentration_is_site_density_over_thickness():
    assert binding_layer_saturation_concentration(6.0, 3.0) == 2.0


@pytest.mark.parametrize("args", [(-1.0, 1.0, 1.0), (1.0, 0.0, 1.0), (1.0, 1.0, 0.0)])
def test_unphysical_layer_inputs_are_rejected(args):
    with pytest.raises(ValueError):
        local_calcium_concentration(*args)

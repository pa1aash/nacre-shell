"""The screen's units module: exact conversions, round trips, dimension checks and refusals (R7(3))."""
import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from nacre.physics.constants import FARADAY
from nacre.screen import units as u

PAIRS = [("kJ mol^-1", "J mol^-1", 1e3), ("kJ/mol", "J mol^-1", 1e3), ("kcal mol^-1", "J mol^-1", 4184.0),
         ("eV/atom", "J mol^-1", FARADAY), ("eV/f.u.", "kJ/mol", FARADAY / 1e3), ("mN m^-1", "J m^-2", 1e-3),
         ("mJ m^-2", "J m^-2", 1e-3), ("nm^2", "m^2", 1e-18), ("mM", "mol m^-3", 1.0),
         ("mol dm^-3", "mol m^-3", 1e3), ("mol L^-1", "M", 1.0), ("cm^3 mol^-1", "m^3 mol^-1", 1e-6),
         ("V vs Li+/Li", "V", 1.0), ("J/C", "V", 1.0), ("ohm m", "Ohm m", 1.0), ("mOhm cm^2", "Ohm m^2", 1e-7),
         ("h", "s", 3600.0), ("1", "", 1.0), ("Angstrom", "nm", 0.1), ("m^-2 s^-1", "cm^-2 s^-1", 1e-4),
         ("kg m^-3", "g cm^-3", 1e-3), ("mol kg^-1", "mmol g^-1", 1.0)]


@pytest.mark.parametrize("a,b,k", PAIRS)
def test_known_conversion_factors(a, b, k):
    assert u.factor(a, b) == pytest.approx(k, rel=1e-14)


@settings(max_examples=100, deadline=None)
@given(i=st.integers(0, len(PAIRS) - 1), x=st.floats(-1e6, 1e6, allow_nan=False))
def test_round_trip_returns_the_value(i, x):
    a, b, _ = PAIRS[i]
    assert u.convert(u.convert(x, a, b), b, a) == pytest.approx(x, rel=1e-13, abs=1e-300)


def test_arrays_convert_elementwise():
    np.testing.assert_allclose(u.convert(np.array([1.0, 2.0]), "kJ/mol", "J mol^-1"), [1e3, 2e3], rtol=1e-15)


@pytest.mark.parametrize("bad", ["kT", "furlong", "degC", "°C", "J m^-x", "J m^^2", "eV/atomz", "kk J", None])
def test_unknown_or_malformed_units_are_refused(bad):
    with pytest.raises(u.UnitError):
        u.parse(bad)


@pytest.mark.parametrize("a,b", [("J m^-2", "J mol^-1"), ("eV", "V"), ("m^-2", "m^2"), ("mol m^-3", "1"),
                                 ("eV/atom", "eV"), ("s", "Hz-less")])
def test_conversion_between_dimensions_is_refused(a, b):
    with pytest.raises(u.UnitError):
        u.factor(a, b)


def test_dimensions_are_si_base_vectors():
    assert u.dimension("J m^-2") == u.dimension("N m^-1") == u.dimension("kg s^-2")
    assert u.dimension("V") == u.dimension("J C^-1")
    assert u.same_dimension("eV/atom", "kJ/mol")

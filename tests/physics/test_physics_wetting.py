"""Property tests of the shape factor f(theta) (exact mathematics, no data)."""
import math

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from nacre.physics.wetting import shape_factor, shape_factor_from_cos

angles = st.floats(min_value=0.0, max_value=math.pi, allow_nan=False)
cosines = st.floats(min_value=-1.0, max_value=1.0, allow_nan=False)


def test_complete_wetting_has_no_barrier():
    assert shape_factor(0.0) == 0.0


def test_complete_non_wetting_recovers_the_homogeneous_barrier():
    assert shape_factor(math.pi) == pytest.approx(1.0, abs=1e-15)


def test_right_angle_gives_one_half():
    assert shape_factor(math.pi / 2) == pytest.approx(0.5, abs=1e-15)


@given(angles)
def test_bounded_between_zero_and_one(theta):
    f = shape_factor(theta)
    assert 0.0 <= f <= 1.0


@given(angles, angles)
def test_monotone_increasing_in_theta(a, b):
    lo, hi = min(a, b), max(a, b)
    assert shape_factor(lo) <= shape_factor(hi) + 1e-15


@given(cosines)
def test_factored_and_expanded_forms_agree(c):
    # (2 + c)(1 - c)^2 / 4 and (2 - 3c + c^3) / 4 are the same polynomial in cos(theta).
    assert shape_factor_from_cos(c) == pytest.approx((2 - 3 * c + c ** 3) / 4, abs=1e-14)


def test_derivative_is_non_negative_on_the_whole_interval():
    # df/dtheta = (3/4) sin^3(theta) >= 0 on [0, pi]; check against a dense grid.
    theta = np.linspace(0.0, math.pi, 10001)
    f = shape_factor(theta)
    assert np.all(np.diff(f) >= -1e-15)
    mid = theta[1:-1]
    numeric = (f[2:] - f[:-2]) / (theta[2:] - theta[:-2])
    assert np.allclose(numeric, 0.75 * np.sin(mid) ** 3, atol=1e-6)


@settings(max_examples=50)
@given(st.lists(angles, min_size=1, max_size=20))
def test_vectorised_matches_scalar(thetas):
    arr = shape_factor(np.array(thetas))
    # vectorised and scalar paths may differ at the last bit
    assert np.allclose(arr, [shape_factor(t) for t in thetas], rtol=1e-12, atol=0)


@pytest.mark.parametrize("bad", [-1e-9, math.pi + 1e-9, float("nan"), float("inf")])
def test_angles_outside_zero_to_pi_are_rejected(bad):
    with pytest.raises(ValueError):
        shape_factor(bad)


@pytest.mark.parametrize("bad", [-1.0 - 1e-12, 1.0 + 1e-12, float("nan")])
def test_cosines_outside_unit_interval_are_rejected(bad):
    with pytest.raises(ValueError):
        shape_factor_from_cos(bad)

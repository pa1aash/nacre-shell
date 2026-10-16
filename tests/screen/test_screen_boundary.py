"""Screen-layer clipping of the Young ratio and the boundary mass (lane note N2)."""
import numpy as np
import pytest

from nacre.physics.wetting import shape_factor_from_cos
from nacre.screen.boundary import EMPTY, BoundaryMass, clip_cos_theta


def test_inside_values_pass_unchanged_and_are_not_counted():
    r = np.array([-1.0, -0.3, 0.0, 0.7, 1.0])
    c, m = clip_cos_theta(r)
    assert np.array_equal(c, r)
    assert (m.n_finite, m.n_spread, m.n_nonwetting) == (5, 0, 0)


def test_spreading_clips_to_theta_zero_and_nonwetting_to_theta_180():
    c, m = clip_cos_theta([1.5, -2.0, 0.2, 1.0 + 1e-15])
    assert c.tolist() == [1.0, -1.0, 0.2, 1.0]
    assert shape_factor_from_cos(c[0]) == 0.0      # theta = 0: f = 0
    assert shape_factor_from_cos(c[1]) == 1.0      # theta = 180 deg: f = 1
    assert (m.n_finite, m.n_spread, m.n_nonwetting) == (4, 2, 1)
    assert m.total_fraction == pytest.approx(3 / 4)


def test_non_finite_ratios_are_neither_clipped_nor_counted():
    c, m = clip_cos_theta([np.nan, np.inf, 2.0])
    assert np.isnan(c[0]) and np.isnan(c[1]) and c[2] == 1.0
    assert (m.n_finite, m.n_spread, m.n_nonwetting) == (1, 1, 0)


def test_masses_add_across_chunks_and_serialise():
    a = clip_cos_theta([2.0, 0.0])[1]
    b = clip_cos_theta([-3.0, 0.5, 0.1])[1]
    total = EMPTY + a + b
    assert total == BoundaryMass(5, 1, 1)
    d = total.as_dict()
    assert d["fraction_total"] == pytest.approx(0.4)
    assert set(d) == {"n_finite", "n_clipped_theta_0", "n_clipped_theta_180", "fraction_theta_0",
                      "fraction_theta_180", "fraction_total"}


def test_physics_still_raises_where_the_screen_clips():
    with pytest.raises(ValueError):
        shape_factor_from_cos(1.5)

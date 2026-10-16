"""Input validation against physical domains (internal)."""
import numpy as np


def as_float_array(name, value):
    arr = np.asarray(value, dtype=float)
    if not np.all(np.isfinite(arr)):
        raise ValueError("%s must be finite" % name)
    return arr


def real(name, value):
    return as_float_array(name, value)


def positive(name, value):
    arr = as_float_array(name, value)
    if np.any(arr <= 0):
        raise ValueError("%s must be strictly positive" % name)
    return arr


def non_negative(name, value):
    arr = as_float_array(name, value)
    if np.any(arr < 0):
        raise ValueError("%s must be non-negative" % name)
    return arr


def closed_interval(name, value, low, high):
    arr = as_float_array(name, value)
    if np.any((arr < low) | (arr > high)):
        raise ValueError("%s must lie in [%r, %r]" % (name, low, high))
    return arr


def open_interval(name, value, low, high):
    arr = as_float_array(name, value)
    if np.any((arr <= low) | (arr >= high)):
        raise ValueError("%s must lie in (%r, %r)" % (name, low, high))
    return arr


def scalar_or_array(arr):
    arr = np.asarray(arr)
    return arr.item() if arr.ndim == 0 else arr

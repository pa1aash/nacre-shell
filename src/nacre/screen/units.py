"""One dimension-checked units module for the screen (cp3 ruling R7(3)).

Every unit string the screen reads (the parameter table's ``unit`` fields, W5's stability
documents, the retrodiction cases) is converted here and nowhere else. A unit string is a
product of factors separated by spaces, ``*`` or ``/`` (everything after a ``/`` is in the
denominator), each a known unit with an optional SI prefix and an optional integer power:
``J m^-2``, ``kJ/mol``, ``m^3 mol^-1``, ``eV/atom``, ``mN m^-1``, ``mol dm^-3``. ``1`` (or an
empty string) is dimensionless.

Dimensions are vectors over the SI base quantities (kg, m, s, A, K, mol). A conversion
between strings of different dimension is refused, and so is any token this module does
not know: a unit is never guessed. Counting units (``atom``, ``f.u.``, ``molecule``) are
one entity each, 1/N_A mol, so eV per atom converts to J mol^-1 exactly.

The only numbers here are exact definitions: the SI prefixes, the SI-defined constants
(elementary charge and Avogadro constant, from nacre.physics.constants), the litre, the
thermochemical calorie (4.184 J by definition), the angstrom, the minute and the hour. No
temperature offset is supported: degrees Celsius are refused, kelvin only.
"""
import re

import numpy as np

from nacre.physics.constants import AVOGADRO, ELEMENTARY_CHARGE

BASE = ("kg", "m", "s", "A", "K", "mol")


class UnitError(ValueError):
    """An unknown unit token, a malformed unit string, or a conversion between dimensions."""


def _dim(**powers):
    return tuple(int(powers.get(b, 0)) for b in BASE)


_ZERO = _dim()
_J = _dim(kg=1, m=2, s=-2)
_C = _dim(A=1, s=1)
_V = tuple(a - b for a, b in zip(_J, _C))

#: token -> (factor to SI, dimension). Prefixable units take SI prefixes.
UNITS = {
    "m": (1.0, _dim(m=1)), "g": (1e-3, _dim(kg=1)), "s": (1.0, _dim(s=1)), "A": (1.0, _dim(A=1)),
    "K": (1.0, _dim(K=1)), "mol": (1.0, _dim(mol=1)),
    "J": (1.0, _J), "W": (1.0, _dim(kg=1, m=2, s=-3)), "N": (1.0, _dim(kg=1, m=1, s=-2)),
    "Pa": (1.0, _dim(kg=1, m=-1, s=-2)), "C": (1.0, _C), "V": (1.0, _V),
    "Ohm": (1.0, tuple(a - b for a, b in zip(_V, _dim(A=1)))),
    "eV": (ELEMENTARY_CHARGE, _J), "cal": (4.184, _J), "L": (1e-3, _dim(m=3)),
    "M": (1e3, _dim(mol=1, m=-3)),                         # molar, mol dm^-3
    "atom": (1.0 / AVOGADRO, _dim(mol=1)), "f.u.": (1.0 / AVOGADRO, _dim(mol=1)),
    "fu": (1.0 / AVOGADRO, _dim(mol=1)), "molecule": (1.0 / AVOGADRO, _dim(mol=1)),
    "Angstrom": (1e-10, _dim(m=1)), "min": (60.0, _dim(s=1)), "h": (3600.0, _dim(s=1)),
}
ALIASES = {"ohm": "Ohm", "Ω": "Ohm", "Å": "Angstrom", "angstrom": "Angstrom", "l": "L", "atoms": "atom"}
PREFIXABLE = {"m", "g", "s", "A", "K", "mol", "J", "W", "N", "Pa", "C", "V", "Ohm", "eV", "cal", "L", "M"}
PREFIXES = {"G": 1e9, "M": 1e6, "k": 1e3, "h": 1e2, "d": 1e-1, "c": 1e-2, "m": 1e-3, "u": 1e-6, "µ": 1e-6,
            "n": 1e-9, "p": 1e-12, "f": 1e-15}
_FACTOR = re.compile(r"^(?P<tok>[A-Za-zµΩÅ.]+)(?:\^(?P<pow>[+-]?\d+))?$")
#: Qualifiers that name a reference electrode or scale; the factor is the potential in volts.
_QUALIFIERS = re.compile(r"\s+vs\.?\s+.*$")


def _token(tok):
    tok = ALIASES.get(tok, tok)
    if tok in UNITS:
        return UNITS[tok]
    for p in sorted(PREFIXES, key=len, reverse=True):
        if tok.startswith(p) and tok[len(p):] in PREFIXABLE:
            f, d = UNITS[tok[len(p):]]
            return PREFIXES[p] * f, d
    raise UnitError("unknown unit token %r" % tok)


def parse(unit):
    """(factor to SI, dimension vector) of a unit string; UnitError if any token is unknown."""
    if unit is None:
        raise UnitError("no unit given")
    text = _QUALIFIERS.sub("", str(unit).strip())
    if text in ("", "1", "-", "dimensionless"):
        return 1.0, _ZERO
    factor, dim, sign = 1.0, [0] * len(BASE), 1
    for part in re.split(r"(\s+|\*|/)", text):
        if part is None or not part.strip() or part == "*":
            continue
        if part == "/":
            sign = -1
            continue
        if part == "1":
            continue
        m = _FACTOR.match(part.strip())
        if not m:
            raise UnitError("malformed unit factor %r in %r" % (part, unit))
        f, d = _token(m.group("tok"))
        power = sign * int(m.group("pow") or 1)
        factor *= f ** power
        dim = [a + power * b for a, b in zip(dim, d)]
    return factor, tuple(dim)


def dimension(unit):
    return parse(unit)[1]


def factor(from_unit, to_unit):
    """Multiplier taking a value in from_unit to to_unit; UnitError if the dimensions differ."""
    f1, d1 = parse(from_unit)
    f2, d2 = parse(to_unit)
    if d1 != d2:
        raise UnitError("cannot convert %r (dimension %s) to %r (dimension %s)"
                        % (from_unit, _show(d1), to_unit, _show(d2)))
    return f1 / f2


def convert(value, from_unit, to_unit):
    """value (scalar or array) in from_unit, expressed in to_unit."""
    k = factor(from_unit, to_unit)
    v = np.asarray(value, dtype=float) * k
    return float(v) if v.ndim == 0 else v


def same_dimension(a, b):
    return dimension(a) == dimension(b)


def _show(d):
    parts = ["%s^%d" % (b, p) if p != 1 else b for b, p in zip(BASE, d) if p]
    return " ".join(parts) or "1"

"""Prior-file loader.

Prior-file format (YAML), the contract between the parameter table and the screen:

    mock: false                    # true only for synthetic test priors
    regimes:
      <regime id>:                 # R-slurry | R-cell (charter/regimes.yaml)
        parameters:
          <name>:
            symbol: <str>
            units: <str>
            distribution: uniform | loguniform | normal | fixed
            # uniform, loguniform: low, high (loguniform needs 0 < low < high)
            # normal: mean, sd (sd > 0); fixed: value
            transform: none | log10   # optional; log10: the distribution is of log10 of the quantity
            source: <str>          # provenance of the prior (evidence-table key)

Production priors are read from lit/params.yaml, written by the parameter-table lane, in
its own layout (lit/corpus/params_README.md); nacre.screen.params_adapter reads that layout
into the same Prior objects. Neither loader invents a value.

Mock files (``mock: true``) carry synthetic numbers for exercising the code. They are
refused unless the caller passes ``allow_mock=True`` (the ``--mock`` flag of the CLI).
"""
import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml
from scipy import special

PRODUCTION_PRIORS = Path("lit") / "params.yaml"
REGIMES = ("R-slurry", "R-cell")
_PARAMS = {"uniform": ("low", "high"), "loguniform": ("low", "high"), "normal": ("mean", "sd"),
           "fixed": ("value",)}
TRANSFORMS = ("none", "log10")


class MockPriorsRefused(RuntimeError):
    """A mock prior file was offered without the explicit mock flag."""


class PriorFileError(ValueError):
    """The prior file does not follow the prior-file format."""


@dataclass(frozen=True)
class Prior:
    """Prior distribution of one physical input of the screen.

    ``distribution`` and ``params`` describe the stated variable; with ``transform: log10``
    that variable is log10 of the physical quantity (solubility products, binding
    constants), and sample() and ppf() return the physical quantity 10**y.
    """
    name: str
    symbol: str
    units: str
    distribution: str
    params: dict
    source: str = ""
    transform: str = "none"

    @property
    def is_fixed(self):
        return self.distribution == "fixed"

    def _stated_ppf(self, u):
        p = self.params
        if self.distribution == "uniform":
            return p["low"] + u * (p["high"] - p["low"])
        if self.distribution == "loguniform":
            return np.exp(np.log(p["low"]) + u * (np.log(p["high"]) - np.log(p["low"])))
        if self.distribution == "normal":
            return p["mean"] + p["sd"] * special.ndtri(u)
        if self.distribution == "fixed":
            return np.full(np.shape(u), p["value"], dtype=float)
        raise PriorFileError("unknown distribution %r" % self.distribution)

    def ppf(self, u):
        """Physical value at cumulative probability u in (0, 1) (inverse CDF, SI units)."""
        y = self._stated_ppf(np.asarray(u, dtype=float))
        return 10.0 ** y if self.transform == "log10" else y

    def sample(self, rng, n):
        """Draw n independent samples of the physical quantity (SI units, as in ``units``)."""
        return self.ppf(rng.random(n))


@dataclass(frozen=True)
class PriorSet:
    """All priors of one prior file, per regime, with the file's identity."""
    path: str
    sha256: str
    mock: bool
    regimes: dict = field(default_factory=dict)

    def parameters(self, regime):
        return self.regimes[regime]

    def names(self, regime):
        return [p.name for p in self.regimes[regime]]


def _prior(name, spec, where):
    if not isinstance(spec, dict):
        raise PriorFileError("%s: parameter spec must be a mapping" % where)
    dist = spec.get("distribution")
    if dist not in _PARAMS:
        raise PriorFileError("%s: distribution must be one of %s" % (where, sorted(_PARAMS)))
    params = {}
    for key in _PARAMS[dist]:
        if key not in spec:
            raise PriorFileError("%s: %s prior needs %r" % (where, dist, key))
        value = float(spec[key])
        if not np.isfinite(value):
            raise PriorFileError("%s: %r must be finite" % (where, key))
        params[key] = value
    if dist in ("uniform", "loguniform") and not params["low"] < params["high"]:
        raise PriorFileError("%s: needs low < high" % where)
    if dist == "loguniform" and params["low"] <= 0:
        raise PriorFileError("%s: loguniform needs low > 0" % where)
    if dist == "normal" and params["sd"] <= 0:
        raise PriorFileError("%s: normal needs sd > 0" % where)
    for key in ("symbol", "units"):
        if not isinstance(spec.get(key), str):
            raise PriorFileError("%s: %r is required" % (where, key))
    transform = spec.get("transform", "none")
    if transform not in TRANSFORMS:
        raise PriorFileError("%s: transform must be one of %s" % (where, TRANSFORMS))
    return Prior(name, spec["symbol"], spec["units"], dist, params, str(spec.get("source", "")),
                 transform)


def load_priors(path, allow_mock=False):
    """Load a prior file into a PriorSet.

    Raises MockPriorsRefused when the file is marked ``mock: true`` and allow_mock is
    False, and PriorFileError when the file does not follow the format above.
    """
    path = Path(path)
    raw = path.read_bytes()
    doc = yaml.safe_load(raw) or {}
    if not isinstance(doc, dict):
        raise PriorFileError("%s: top level must be a mapping" % path)
    mock = doc.get("mock")
    if not isinstance(mock, bool):
        raise PriorFileError("%s: 'mock' must be stated explicitly as true or false" % path)
    if mock and not allow_mock:
        raise MockPriorsRefused("%s is a mock prior file; pass --mock (allow_mock=True) to use "
                                "it, and never for production results" % path)
    regimes = doc.get("regimes")
    if not isinstance(regimes, dict) or not regimes:
        raise PriorFileError("%s: 'regimes' must be a non-empty mapping" % path)
    out = {}
    for regime, block in regimes.items():
        if regime not in REGIMES:
            raise PriorFileError("%s: unknown regime %r" % (path, regime))
        params = (block or {}).get("parameters")
        if not isinstance(params, dict) or not params:
            raise PriorFileError("%s: regime %s has no parameters" % (path, regime))
        out[regime] = tuple(_prior(n, s, "%s:%s.%s" % (path, regime, n)) for n, s in params.items())
    return PriorSet(str(path), "sha256:" + hashlib.sha256(raw).hexdigest(), mock, out)

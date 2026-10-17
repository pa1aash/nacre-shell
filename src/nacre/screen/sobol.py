"""Variance-based (Sobol) sensitivity indices for independent inputs, with bootstrap CIs.

Sobol indices decompose Var(Y) into contributions of independent inputs: the first-order
index S_i = Var(E[Y | X_i]) / Var(Y) is the share of the output variance explained by X_i
alone, and the total-order index ST_i = E[Var(Y | X_~i)] / Var(Y) the share that would
remain if every input except X_i were known (X_i alone and through all its interactions).
They are defined for independent inputs only; for the correlated priors of the screen the
dependent-input method is nacre.screen.shapley, and Sobol indices are reported for the
same marginals sampled independently.

Saltelli design with N base rows and k varying inputs: matrices A and B of independent
draws and, for each input i, A_B^(i) (A with column i taken from B), giving N (k + 2)
model evaluations. Estimators, on outputs centred by the pooled mean of A and B:

    S_i  = mean(f_B (f_AB_i - f_A)) / Var(f)          (Saltelli et al. 2010)
    ST_i = mean((f_A - f_AB_i)^2) / (2 Var(f))        (Jansen 1999)

with Var(f) from the pooled A and B evaluations. Confidence intervals are percentile
bootstrap intervals over the N base rows, computed for all inputs at once as products of a
resampling count matrix with the per-row terms. Rows where an evaluation is non-finite
are dropped for that input. Fixed inputs are constants: they are not part of the design.

Sizing (size_and_verify): a target CI half-width is stated before sizing; a pilot run
estimates the half-width, the base size is scaled by (h_pilot / target)^2 to the next power
of two, and convergence is verified by doubling the base size: converged when the doubled
run's largest half-width is within the target and no index moves by more than the target.
"""
import warnings

import numpy as np

from nacre.screen.sampling import JointPrior

METHOD = ("Saltelli design; Saltelli 2010 first order, Jansen total order; percentile bootstrap "
          "over base rows; independent marginals")


def _as_joint(priors):
    if isinstance(priors, JointPrior):
        return priors.independent()
    return JointPrior.independent_of(tuple(priors))


def saltelli_design(priors, n_base, rng):
    """Return (A, B, names): two (n_base, k) matrices of independent draws of the varying inputs."""
    joint = _as_joint(priors)
    var = [p for p in joint.priors if not p.is_fixed]
    a = np.column_stack([p.sample(rng, n_base) for p in var])
    b = np.column_stack([p.sample(rng, n_base) for p in var])
    return a, b, [p.name for p in var]


def _evaluate(model, mat, cols, fixed, chunk):
    """Evaluate model on the rows of mat in chunks; cols are the input keys of mat's columns."""
    n = mat.shape[0]
    step = chunk or n
    parts = []
    for s in range(0, n, step):
        x = {c: mat[s:s + step, j] for j, c in enumerate(cols)}
        x.update({c: np.full(min(step, n - s), v) for c, v in fixed.items()})
        parts.append(model(x))
    return {k: np.concatenate([np.asarray(p[k], float) for p in parts]) for k in parts[0]}


_BOOT_CHUNK = 50


def _bootstrap_count_chunks(seed_seq, n_base, n_bootstrap):
    """Yield (<= 50, n_base) resampling-count blocks (rows drawn with replacement).

    The blocks are regenerated from their seeds on every call, so each output sees the
    same resamples without holding the whole (n_bootstrap, n_base) matrix in memory.
    """
    seqs = seed_seq.spawn((n_bootstrap + _BOOT_CHUNK - 1) // _BOOT_CHUNK) if n_bootstrap else []
    for c, sq in enumerate(seqs):
        m = min(_BOOT_CHUNK, n_bootstrap - c * _BOOT_CHUNK)
        rng = np.random.default_rng(sq)
        counts = np.empty((m, n_base))
        for r in range(m):
            counts[r] = np.bincount(rng.integers(0, n_base, n_base), minlength=n_base)
        yield counts


def _index_terms(fa, fb, fab_list):
    """Per-row terms (n, 7 k) whose weighted sums give S_i and ST_i for every input."""
    pooled = np.concatenate([fa, fb])
    centre = np.nanmean(np.where(np.isfinite(pooled), pooled, np.nan)) if np.any(np.isfinite(pooled)) else 0.0
    a, b = fa - centre, fb - centre
    cols = []
    for fab in fab_list:
        ab = fab - centre
        ok = np.isfinite(a) & np.isfinite(b) & np.isfinite(ab)
        z = lambda v: np.where(ok, v, 0.0)
        cols += [ok.astype(float), z(a), z(b), z(a * a), z(b * b), z(b * (ab - a)), z((a - ab) ** 2)]
    return np.column_stack(cols)


def _indices_from_sums(s):
    """S and ST from weighted sums (..., 7 k) of the per-row terms."""
    s = s.reshape(s.shape[:-1] + (-1, 7))
    n, sa, sb, saa, sbb, s1, st = (s[..., j] for j in range(7))
    m = 2 * n
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = (sa + sb) / m
        var = ((saa + sbb) - m * mean ** 2) / (m - 1)
        first = (s1 / n) / var
        total = (st / n) / (2 * var)
    bad = ~(var > 0) | (n < 2)
    first = np.where(bad, np.nan, first)
    total = np.where(bad, np.nan, total)
    return first, total


def _design_and_evaluate(model, joint, n_base, rng, key, chunk):
    var = [p for p in joint.priors if not p.is_fixed]
    cols = [getattr(p, key) for p in var]
    fixed = {getattr(p, key): float(p.ppf(0.5)) for p in joint.priors if p.is_fixed}
    a, b, names = saltelli_design(joint, n_base, rng)
    ya, yb = _evaluate(model, a, cols, fixed, chunk), _evaluate(model, b, cols, fixed, chunk)
    yab = []
    for j in range(len(cols)):
        ab = a.copy()
        ab[:, j] = b[:, j]
        yab.append(_evaluate(model, ab, cols, fixed, chunk))
    return names, ya, yb, yab


def _compute(names, ya, yb, yab, outputs, rows, rng, n_bootstrap, confidence):
    boot_seq = np.random.SeedSequence(int(rng.integers(0, 2 ** 63)))
    alpha = (1.0 - confidence) / 2.0
    result = {}
    for out in outputs:
        terms = _index_terms(ya[out][:rows], yb[out][:rows], [y[out][:rows] for y in yab])
        first, total = _indices_from_sums(terms.sum(axis=0))
        if n_bootstrap:
            bf, bt = [], []
            for counts in _bootstrap_count_chunks(boot_seq, rows, n_bootstrap):
                f_, t_ = _indices_from_sums(counts @ terms)
                bf.append(f_)
                bt.append(t_)
            bf, bt = np.vstack(bf), np.vstack(bt)
            with np.errstate(all="ignore"), warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)     # an index with no finite resample stays NaN
                lo1, hi1 = np.nanquantile(bf, [alpha, 1 - alpha], axis=0)
                lot, hit = np.nanquantile(bt, [alpha, 1 - alpha], axis=0)
        else:
            lo1 = hi1 = first
            lot = hit = total
        result[out] = {
            name: {"first_order": {"estimate": float(first[j]), "ci_low": float(lo1[j]), "ci_high": float(hi1[j])},
                   "total_order": {"estimate": float(total[j]), "ci_low": float(lot[j]), "ci_high": float(hit[j])}}
            for j, name in enumerate(names)}
    design = {"method": METHOD, "base_samples": int(rows), "evaluations": int(rows * (len(names) + 2)),
              "bootstrap_resamples": int(n_bootstrap), "confidence_level": float(confidence)}
    return result, design


def sobol_indices(model, priors, outputs, n_base, rng, n_bootstrap=200, confidence=0.95,
                  key="name", chunk=None):
    """Sobol first- and total-order indices of each output with respect to each varying input.

    model: dict of input arrays -> dict of output arrays. priors: a JointPrior or a
    sequence of Prior (sampled independently either way). key: "name" or "symbol", the
    input key the model expects. Returns ({output: {input: {"first_order": {...},
    "total_order": {...}}}}, design) where each index dict is {"estimate", "ci_low",
    "ci_high"} and design records the sample sizes (schema $defs/regime.sobol_design).
    """
    if n_base < 2:
        raise ValueError("Sobol design needs at least 2 base rows")
    if not 0 < confidence < 1:
        raise ValueError("confidence must lie in (0, 1)")
    joint = _as_joint(priors)
    names, ya, yb, yab = _design_and_evaluate(model, joint, n_base, rng, key, chunk)
    return _compute(names, ya, yb, yab, outputs, n_base, rng, n_bootstrap, confidence)


def max_half_width(indices):
    """Largest CI half-width over all outputs, inputs and both orders (NaN entries ignored)."""
    hw = [(d[o]["ci_high"] - d[o]["ci_low"]) / 2.0 for per in indices.values() for d in per.values()
          for o in ("first_order", "total_order")]
    hw = [h for h in hw if np.isfinite(h)]
    return max(hw) if hw else float("nan")


def max_shift(a, b):
    """Largest absolute change of any index estimate between two runs."""
    d = [abs(a[q][i][o]["estimate"] - b[q][i][o]["estimate"]) for q in a for i in a[q]
         for o in ("first_order", "total_order")]
    d = [x for x in d if np.isfinite(x)]
    return max(d) if d else float("nan")


def _next_pow2(x):
    return int(2 ** int(np.ceil(np.log2(max(x, 1)))))


def size_and_verify(model, priors, outputs, target_half_width, seed, pilot=1024, n_bootstrap=200,
                    confidence=0.95, key="name", chunk=None, max_base=2 ** 20, on_cap="raise"):
    """Size the Saltelli base sample for a target CI half-width and verify it by doubling.

    The target is an input stated before sizing. A pilot of `pilot` rows gives the largest
    CI half-width h0; the base size is n = pilot (h0 / target)^2 rounded up to a power of
    two. The verification run has 2n rows and contains the n-row run as its first half
    (doubling adds rows), so the shift of every index from n to 2n rows measures the
    remaining sampling error. Converged when the 2n run's largest half-width and the
    largest shift are both within the target. Returns (indices, design, convergence) of
    the 2n run. When 2n would exceed max_base: on_cap="raise" raises ValueError;
    on_cap="cap" runs at 2n = max_base and records capped = true (then converged is
    whatever the capped run achieves, and the shortfall is reported, never hidden).
    """
    if not target_half_width > 0:
        raise ValueError("target half-width must be positive")
    joint = _as_joint(priors)
    pilot_seq, run_seq, boot_seq = np.random.SeedSequence(seed).spawn(3)
    idx0, _ = sobol_indices(model, joint, outputs, pilot, np.random.default_rng(pilot_seq),
                            n_bootstrap, confidence, key, chunk)
    h0 = max_half_width(idx0)
    n = max(pilot, _next_pow2(pilot * (h0 / target_half_width) ** 2)) if np.isfinite(h0) else max_base
    capped = 2 * n > max_base
    if capped:
        if on_cap != "cap":
            raise ValueError("target half-width %.3g needs %d base rows (doubled), above %d"
                             % (target_half_width, 2 * n, max_base))
        n = max_base // 2
    names, ya, yb, yab = _design_and_evaluate(model, joint, 2 * n, np.random.default_rng(run_seq), key, chunk)
    b1, b2 = np.random.default_rng(boot_seq).spawn(2)
    idx1, _ = _compute(names, ya, yb, yab, outputs, n, b1, n_bootstrap, confidence)
    idx2, design2 = _compute(names, ya, yb, yab, outputs, 2 * n, b2, n_bootstrap, confidence)
    h2, shift = max_half_width(idx2), max_shift(idx1, idx2)
    conv = {"target_ci_half_width": float(target_half_width), "base_samples": int(n),
            "base_samples_doubled": int(2 * n), "max_ci_half_width": float(h2),
            "max_estimate_shift": float(shift),
            "converged": bool(h2 <= target_half_width and shift <= target_half_width),
            "capped": bool(capped)}
    return idx2, design2, conv

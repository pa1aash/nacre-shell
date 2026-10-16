# Parameter table: format and prior-construction rule

`lit/params.yaml` holds one entry per input of the P0 screen and of the two regimes. This file
states how every entry, and in particular every prior, is built from the evidence table. The rule
was committed before any value was entered in `lit/params.yaml` and before any screen output existed
(standing rule R7 of the track). It lives under `lit/corpus/` because that is the lane's ownership; the
session prompt named `lit/params_README.md`, which the lane-ownership hook refuses for lane p0-w1. The loader `src/nacre/lit/params.py` checks each entry against it.
After tag `p0-cp3` the file `lit/params.yaml` changes only through a dated entry in
`ops/tracks/p0_deviations.md`.

## 1. File layout

```yaml
mock: false                 # the screen loader refuses mock files without --mock
meta: {...}                 # session, rule version, evidence-table sha256, date
params:
  <key>:                    # lower-case slug, unique
    symbol: <id>            # theory/symbols.yaml id where one exists, else a descriptive id
    transform: none | log10 # log10: value, range and prior are in log10 of the symbol's quantity
    unit: <SI unit>         # parses with pint; "1" for dimensionless and for log10 values
    regimes: [R-slurry | R-cell | shared]
    status: sourced | single-source | gap | computed | registered | design-input | definitional
    value: <number> | null  # central value (section 4)
    range: {min: <number>, max: <number>} | null
    range_reason: <text>    # required when range is null
    prior: {family: normal | uniform | loguniform | fixed | categorical | none, ...parameters}
    rule: <clause id>       # the clause of section 3 that produced the prior (N1, U1, ...)
    sources: [<row_id>, ...]  # evidence-table row ids; every one must exist
    best_grade: A | B | C | D | null
    method: <text>          # how the value, range and prior were obtained from the rows
    conditions: <text>      # conditions of the sources that matter for the screen
    correlation_group: <group id> | null
    notes: <text>
correlation_groups:
  <group id>:
    members: [<key>, ...]
    kind: rank | assumed independent
    matrix: [[...], ...]    # Spearman rank correlation, in member order; identity when assumed independent
    sources: [<row_id>, ...] # rows that support a non-zero entry
    reason: <text>
```

Values are converted from the source unit to the SI unit stated in `unit`. A conversion is
arithmetic on printed numbers and is stated in `method`; no conversion constant is typed from memory
beyond the exact SI definitions (k_B, N_A, e, and the exact prefixes). Quantities that sources print
on a logarithmic scale (solubility products, binding constants, pKa, pH) are stored on that scale
(`transform: log10`, or the quantity itself for pH and pKa); a uniform prior on such a key is
log-uniform in the underlying quantity, and a normal prior is log-normal in it.

Keys are read by the screen through the loader (`prior`, `priors`, `prior_set`) and by the stability
code through dotted paths: `params.<key>` resolves to `value`, and `params.<key>.range.min` to a
bound.

## 2. Evidence admitted to a prior

E1. Only rows of `lit/evidence_table.csv` are admitted, by `row_id`. A value that is not in a row is
    not in the table.

E2. A row is admitted for a key only when it measures or computes the quantity the key defines, under
    the key's conditions or conditions stated as different in `conditions`. A proxy (a different
    quantity used in place of the target, as listed in `lit/corpus/coverage_notes.yaml`, for example a
    surface enthalpy for an interfacial free energy, or adhesion on mica for adhesion on alumina) is
    never admitted. It may be named in `notes`.

E3. Rows that cite the same original determination count once. The original is used when it was read;
    otherwise the compilation row with the highest grade stands for it.

E4. Each admitted value carries an interval:
    - a stated standard deviation, standard error or standard uncertainty u gives the interval x ± 2u;
    - a stated `±x` whose meaning the source does not give is treated as a standard uncertainty u = x;
    - a stated `lo..hi` range, spread or bound is used as printed;
    - a value with no uncertainty is a point.

E5. Grade D rows (abstract only or unchecked secondary citations) are admitted only when no grade A
    to C row exists for the key, and then never with a normal prior.

## 3. Choice of prior family

The clauses are applied in order; the first that applies decides the family.

**X1 (no prior).** No admitted row: `prior: {family: none}`, `range: null`, `range_reason` says why
(gap, proxy only, computed in the study, registered at G2). Such a key is not sampled; the screen
lane decides how a link that needs it is treated.

**X2 (computed or registered).** The input is computed by the study itself (a potential of mean force,
a slab energy, a materials-database energy) or is a registration input set at a gate (for example
`R_A_max`, `j_req`): `status: computed` or `registered`, `prior: {family: none}`, `range: null`,
unless literature comparators exist, which are then listed in `notes` and never become the prior.

**X3 (definitional or categorical).** A value fixed by a definition (an SI-defined constant, the
standard-state temperature of a thermochemical table, the reference of a potential scale):
`prior: {family: fixed, value: x}`. A categorical input (salt or solvent identity): `prior:
{family: categorical, options: [...]}`, each option carrying its source rows; it is not sampled.

**N1 (normal).** At least two independent admitted values (E3), every one of grade A or B, every one
with a stated uncertainty, and concordant: for every pair, |x_i − x_j| ≤ 2 (u_i² + u_j²)^½.
`prior: {family: normal, mean: m, sd: s}` with m the inverse-variance weighted mean and
s = max(u_w, s_x), where u_w = (Σ u_i⁻²)^−½ and s_x is the sample standard deviation of the values,
so that the prior is never narrower than the scatter of the sources.

**N2 (normal from one grade-A source).** Exactly one independent admitted value, of grade A, with a
stated uncertainty u: `prior: {family: normal, mean: x, sd: u}`.

**N3 (normal must respect the physical domain).** A normal prior from N1 or N2 is kept only if
[m − 4s, m + 4s] lies inside the admissible interval of the symbol (`theory/symbols.yaml`), or, for a
log10 key, always. Otherwise clause U1 applies with the bounds [m − 2s, m + 2s] cut to the admissible
interval.

**U1 (uniform over the sourced span).** Every other case with at least two distinct admitted values or
at least one interval: the sources disagree beyond their uncertainties, or give only bounds or
ranges, or lack uncertainties, or the best contributing grade is C or D, or there is a single source
of grade B to D with an interval. `prior: {family: uniform, low: a, high: b}` where a and b are the
smallest and largest ends of the intervals of E4 (points count as their own ends), cut to the
admissible interval of the symbol.

**L1 (log-uniform when the span exceeds a decade).** If clause U1 applies, both bounds are positive,
the key is not already on a log scale, and b/a > 10: `prior: {family: loguniform, low: a, high: b}`.

**P1 (single point).** Exactly one admitted value, a point (no uncertainty, no interval):
`prior: {family: fixed, value: x}` with `status: single-source` and a note that the width is not
sourced. The key is listed as outstanding in the session report; no width is invented.

Grades limit the family as follows: a normal prior needs grade A or B throughout (N1) or a single
grade-A source (N2); grade C (fits through a model, derivations, compilations) and grade D rows give
uniform or log-uniform priors only; grade D rows enter only under E5. `best_grade` is the best grade
among the admitted rows.

## 4. Central value and range

- `range` is the sourced span: the smallest and largest ends of the admitted intervals (E4). For
  uniform and log-uniform priors it equals the prior support. For a normal prior it is reported
  alongside the prior and is not its support.
- `value` is the prior mean for a normal prior; for uniform and log-uniform priors, the median of the
  admitted point values (of the interval midpoints when only intervals exist; the geometric midpoint
  for log-uniform); for a fixed prior, the fixed value.
- `range` must contain `value`. A null range needs `range_reason`.
- Regime inputs (`charter/regimes.yaml`) take their range from sources only. A bound quoted in the
  charter from the deck enters only if an admitted row supports it.

## 5. Correlation groups

C1. Keys whose admitted values come from the same determination or the same fit (for example an
    effective interfacial energy and a kinetic prefactor from one classical-nucleation fit, or two
    solubility products and the free-energy offset derived from them) form a group.

C2. Keys that the physics ties together without a joint source form a group as well: the three
    interfacial free energies of Young's relation and the water-displacement term (lane note N2), the
    solubility products of the polymorphs and the ACC offset, the carbonate-system inputs at the
    regime pH.

C3. The group's `kind` is `rank` with a Spearman matrix only where a source reports a correlation or a
    covariance between members (the rows are listed in `sources`). Otherwise `kind: assumed
    independent` with the identity matrix, and the group exists so that the screen can test the
    sensitivity of its results to that assumption.

C4. Each key belongs to at most one group; a key in no group has `correlation_group: null`. A group
    lists exactly the keys that name it. The matrix is square in member order, symmetric, with unit
    diagonal, entries in [−1, 1], and positive semi-definite.

## 6. What the loader checks

`src/nacre/lit/params.py` (`load_params`, `validate`, `prior`, `priors`, `prior_set`):

1. every unit parses with pint and is the SI unit of the symbol where the symbol is registered;
2. `range` contains `value`, and a null range has a reason;
3. every source `row_id` exists in `lit/evidence_table.csv`, and `best_grade` is the best grade among
   them;
4. the prior parameters are valid for the family (low < high, low > 0 for log-uniform, sd > 0) and
   consistent with the clause named in `rule` (a normal prior only under N1 or N2 with grade A or B
   rows; uniform bounds equal to the range; log-uniform only when the span exceeds a decade; fixed
   equal to `value`);
5. correlation groups satisfy C4.

`prior(key)` returns a distribution object that is a `nacre.screen.priors.Prior` (same `sample(rng, n)`),
extended with the key's grade, sources and correlation group; `priors(keys)` returns them as a tuple
with the rank-correlation matrix over the requested keys, and `prior_set(regime)` returns a
`nacre.screen.priors.PriorSet` for one regime.

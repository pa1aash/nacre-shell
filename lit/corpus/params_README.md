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

## 7. Additions at cp3 (rule version 2, P0-W1.3, 2026-10-17)

Sections 1 to 6 are unchanged. The clauses below were added on day 3 to apply the cp2 and cp3
rulings: the cp2 gap policy (decision D15), the cp2 conventions (D14), and the cp3 rulings R2, R8
and R10 of 2026-10-17. Some values already existed when they were written; each clause therefore
names the ruling it applies, and none of them selects or moves a value by judgement. The builder
(`src/nacre/lit/build_params.py`) applies them from the specification, and the loader checks them.

### 7.1 Roles

Every entry has a `role`:

- `primary`: the key the screen samples;
- `sensitivity`: a labelled alternative to the primary key named in `of`, which is reported beside it
  and never decides a verdict;
- `analog`: a flagged analog prior for the key named in `of` (below);
- `design-axis`: an input the study varies over named classes, not a quantity with one prior.

`prior_set(regime)` returns primary keys only. Sensitivity and analog keys are read by name.

Entries may also carry `flags`, a list of `single_source`, `analog`, `truncated`, `widened`,
`ionic_strength` and `registered`, which the SI table prints.

### 7.2 Clauses

**T1 (truncation by ruling).** A ruling that requires a physical bound the sourced span crosses
cuts the span at that bound: the prior is U1 (or L1) on the cut span, and `truncation` names the
bound, the side, the ruling and the key that keeps the uncut prior as a `sensitivity`. The value
is the median of the admitted points inside the cut span. Applied to `gamma_sl0_template` (cp3 R8:
gamma >= 0; a negative template-water energy is a van Oss artifact).

**W1 (single-source widening).** This applies to a Ca2+ binding or transfer free energy, or to a
log10 binding constant, whose status is `single-source` (gap policy (iii); `theory/ignorance_priors.md`
Section 4). The sourced span is widened symmetrically about its midpoint until its half-width is at
least the method error m, where m is the value of `m_seq_method_error`. For a log10 constant, m is
divided by R T ln 10 at the standard temperature 298.15 K, with R = N_A k_B taken from the exact SI
constants. The prior is uniform over the widened span. `widening` records m, the key that supplies
it and the unwidened span, and the entry carries the flags `single_source` and `widened`. A verdict
whose band would change under the unwidened span is marked as resting on a single source. The flag
`single_source` is carried even when the sourced span already exceeds m and nothing is widened.

**A1 (analog prior).** Rows that measure a different but physically analogous quantity (E2 proxies)
are admitted to a separate key with role `analog`, `of` naming the unmeasured key, and the flag
`analog`. Clauses N1 to L1 then apply to them unchanged. An analog prior runs side by side with the
ignorance prior of its key. It never replaces that prior, and its verdict is reported as
conditional on the analog (`theory/ignorance_priors.md` Section 3, item 4).

**I1 (ignorance prior).** An unmeasured interfacial or geometric quantity whose admissible range
follows from physics (`theory/ignorance_priors.md`) carries `ignorance`. This records the lower and
upper bounds as expressions in other keys, the input keys, and the section of the authority. The
family is `none`, because the bounds move with the draws of their inputs, and the screen draws
from the expressions. `range` is the envelope of the bounds over the input ranges (below), shown
for information.

**D1 (derived key).** A key fixed by a stated formula from other keys (a margin, a derived physical
quantity) carries `derived`, which records the formula, the input keys and their roles. The value
is the formula at the input values. The range is the envelope over the input ranges: the formula
is evaluated at every corner of the input box, which is exact for formulas monotone in each input,
and every formula used here is. A margin used as a fixed edge has family `fixed`. A derived
quantity that moves with sampled inputs has family `none`, and the screen computes it per draw. An
input of a D1 formula may be a row's printed uncertainty (`take: uncertainty`, the printed ±x as a
number) or one unit of the last printed decimal place of a row's value (`take: last_digit`, for tables
whose stated uncertainty convention is a number of last-digit units). Both are read from the row's
text and are not typed.

**R1 (registered convention).** A convention set at a gate is read, not typed, from the
machine-readable block of its authority (`theory/thresholds.md`, block `thresholds`). `registered`
names the file, the block path and the ruling. The value is the registered primary value, and any
registered sweep is copied beside it. The family is `fixed`, and the status is `registered`. A
registration whose ruling has not been recorded keeps rule X2 and says so in `range_reason`.

**G1 (design axis by class).** An input that a ruling makes a design axis keyed to named classes
(cp3 R2: `E_cell_max` by cathode class) is a categorical entry. Each option names its class and
the per-class key, which is built from that class's rows by clauses N1 to P1. The screen reports
one verdict per class, and no class is preferred.

**P1, extended.** Several independent sources that print the identical point without an uncertainty
give a fixed prior under P1 with all of them as sources; the width is still not sourced.

### 7.3 Margins of the thresholds (theory/thresholds.md, conventions m_W, m_S, m_E)

For each of m_W, m_S and m_E, the entry states one of two cases in `notes` and in `margin_case`:
`evidence`, a value derived (D1) from fetched method-error rows; or `zero`, because the prior
already carries the method error, with the reason.

## 8. Post-cp3 supplements (rule version 3, P0-W1.4, 2026-10-19)

Sections 1 to 7 are unchanged. After tag `p0-cp3` the parameter table changes only by addition
(standing rule R7 of the track, decision D30): new evidence rows and new keys, each covered by a
dated entry in `ops/tracks/p0_deviations.md` with "Re-audit: cp4". The production screens read the
table at the tag and never see the additions.

- **New keys** carry `added_in` (the session that added them). They follow sections 2 to 7 unchanged.
- **A gap at the tag is never edited.** When new evidence supplies a prior for a key that was a gap at
  `p0-cp3`, the prior goes to a new key that names the gap key in `fills`. The gap key keeps its entry
  as it was at the tag, so a reader of the tag and a reader of the supplemented table agree on every
  key the tag holds. `fills` must name a gap key with the same unit and transform, and the filling
  key must have admitted evidence. Whether a consumer reads the filling key in place of the gap key
  is decided at cp4, not here.
- **One edit of an existing key is mandated:** `n_req` becomes N_req = ln(1/q_0)/A_patch with
  q_0 = 1 - p_cred (cp3 R5), in place of 1/A_patch. Its value stays null while `patch_area` is a gap,
  so no screen value changes; the edit is named in the deviation entry.
- **Loader check.** `tests/lit/test_lit_params_post_cp3.py` compares every key of the tag's table with
  the current table and fails if any differs, except `n_req` and the alias that copies it.

## 9. Conversion rules (P0-W1.PH-W1.7, 2026-10-22)

Sections 1 to 8 are unchanged. The rules below are documentation for consumers of the table; no key value is changed by them.

**9.1 Transfer free energies not on the TATB scale.** The transfer free-energy keys are on the TATB (tetraphenylarsonium tetraphenylborate) extrathermodynamic scale. A transfer free energy from a source on another scale (a single-ion scale fixed by another assumption, or a conventional scale with the proton as zero) is not admitted on the strength of its printed number. It is converted only when the source itself prints the offset between its scale and TATB for the same solvent pair, by adding that printed offset (arithmetic on printed numbers, the offset is read, not typed). When no offset is printed, the source is excluded and named in `notes` of the key as a comparator (E2: a different scale is a different quantity). The same rule applies to hydration energies on the absolute and conventional proton scales (see the per-key interval of PH-W1.6).

**9.2 Molal to molar binding constants.** A binding constant K read from a source in molal units is converted to the molar scale only when the source prints the solution density for the conditions, through c = m rho / (1 + m M); with no printed density the molal number stays a comparator. The dimensionless thermodynamic constant used for a free energy is K_P = K c0, with c0 = 1 mol dm^-3 for a molar K (K in dm^3 mol^-1) and K_P = K m0 with m0 = 1 mol kg^-1 for a molal K. For a log10 key, log10 K_P = log10 (K / (dm^3 mol^-1)), and the free energy is Delta_G = -R T ln K_P with R = N_A k_B from the exact SI constants. Stoichiometry is read from the source's own reaction: K for 1:1 binding has units dm^3 mol^-1; a source printing a stepwise or overall constant is not mixed with the other.

**9.3 Solubility-product formula units.** A solubility product is stated for one stated formula unit, and the exponents of the ion product follow that unit. Moving between formula units that differ by an integer factor n multiplies log10 K_sp by n: log10 K(unit B) = n log10 K(unit A) when unit B is n times unit A. Applied here: Tung et al. 1988 print IP(OCP) = (Ca2+)^4 (H+)(PO4 3-)^3 (pdf p. 3, read from the page image) and name the phase Ca8H2(PO4)6.5H2O, so the printed pKsp 48.4 belongs to the half unit Ca4H(PO4)3 (with 2.5 H2O), and the Ca8H2(PO4)6 basis is log10 K = 2 x (-48.4) = -96.8. The factor is supported by the printed expression, not by a second source. The same rule relates the Ca5 hydroxyapatite key to a Ca10 literature value (TR-057, factor 2).

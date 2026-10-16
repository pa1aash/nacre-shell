# Required precision: operational definition

Written in P0-W4.2, before any production screen output exists (rule R7). P0-W4.4 applies it on
Day 4 to the production screens. Implementation: `src/nacre/screen/precision.py`. Tests on the
analytic benchmark: `tests/screen/test_screen_precision.py`.

## 1. Question

The screen reports which parameters govern each link's verdict. For each governing parameter the
paper also states the **required precision**: the prior width the parameter must be narrowed to for
the verdict to be decided, with every other input left at its prior. This number tells a
first-principles calculation how accurate it has to be to matter.

## 2. Definitions

- **Decisive quantity Q and verdict statistic.** For each link these come from the frozen decision
  rule in `configs/preprint/thresholds.yaml`, the copy of `theory/thresholds.md`. The statistic is
  the credible interval of Q under the propagated prior, `[q_lo, q_hi]`, at the level the decision
  rule registers. The default is the equal-tailed 95 % interval; the rule's own level and form
  replace it when frozen.
- **Band edges.** These are the thresholds that separate the verdict bands of Q (feasible,
  inconclusive, falsified), including an absolute-barrier bound where the rule has one.
- **Decided.** The verdict is decided when no band edge lies inside the open interval
  `(q_lo, q_hi)`, so that the whole interval lies in one band. The **nearest threshold** is the band
  edge closest to the interval's centre. When the verdict is undecided, it is the edge the interval
  straddles.
- **Stated variable v of a parameter.** This is the variable in which its prior is stated:
  - the quantity itself for normal and uniform priors;
  - its natural logarithm for log-uniform priors;
  - log10 of the quantity for keys stored with `transform: log10`.
- **Prior width W.** This is the width of the prior's central 95 % interval in v.
- **Narrowed prior.** The prior of parameter i is contracted about its median `m_i` by a factor
  `s` in [0, 1] in its stated variable: `v' = m_i + s (v - m_i)`.
  - Every central interval becomes `s` times as wide.
  - The median and the shape of the distribution are kept.
  - The map is monotone, so the Gaussian-copula rank correlations with the other inputs are
    unchanged.
  - `s = 1` is the prior and `s = 0` fixes the parameter at its median.
- **Required precision.** This is the largest `s*` at which the verdict is decided, holding every
  other input at its prior. It is reported as:
  - `width_ratio` = `s*`;
  - `required_width` = `s* W`, in the parameter's stated variable and units;
  - `nearest_threshold`, the edge that the narrowed interval clears.

Each parameter's status is one of three values.

| Status | Condition | What is reported |
|---|---|---|
| `already_clears` | Decided at `s = 1` | ratio 1, required width = prior width |
| `ok` | Undecided at `s = 1`, decided at some `s` in [0, 1) | `s*` and `s* W` |
| `unreachable` | Undecided even at `s = 0` | null ratio and width. No narrowing of this parameter alone decides the verdict; the report names the parameters that must improve together. |

## 3. Algorithm

1. Draw one set of `n` joint prior samples, including the copula correlations, from a fixed seed.
   These **common random numbers** are reused at every `s`, so the statistic `g(s)` is a smooth
   function of `s` and differences between values of `s` are not sampling noise.
2. Evaluate `g(1)`. If it is decided, the status is `already_clears`.
3. Evaluate `g(0)`. If it is undecided, the status is `unreachable`.
4. Scan `s` on an 11-point grid from 0 to 1 and record whether each point is decided. A decided
   region that does not form a single interval `[0, s*]` is flagged `monotone = false` in the
   record, and the largest decided grid point is used.
5. Bisect between the largest decided grid point and the next one until the bracket is narrower
   than `1e-4` in `s`. The lower end of the bracket is `s*`.
6. Record `s*`, `s* W`, the nearest threshold and the interval at the prior. The record goes into
   the results document under `required_precision/<regime>/<parameter>` (schema
   `$defs/required_precision`, results schema v2).

**Which parameters.** The governing parameters of a link are those whose Shapley effect on the
decisive quantity has a lower 95 % bound above 0.05 under the stated correlations, together with
the top-ranked parameter under independence if it differs (the dependence check, Task 4e). Under
the stated correlations a correlated partner can carry variance without entering the model. Its
required precision is then reported with the note "acts through its correlation".

**Sample size.** `n` = 2^20 per parameter in production, the same as the Monte Carlo draws. A
result is accepted only if the bootstrap standard error of `q_lo` and `q_hi` at `s*` is smaller
than a tenth of the distance from `g(1)` to the nearest edge. Otherwise `n` is doubled.

## 4. Analytic benchmark

Take `Y = beta^T X` with Gaussian `X`. Narrowing parameter i by `s` scales its standard deviation by
`s`, so the upper credible bound is

    q_hi(s) = mu + z sqrt(beta^T Sigma(s) beta),   Sigma(s) = Sigma with row and column i scaled by s,

where `z` is the standard-normal quantile of the level. With one edge `t > mu`, the verdict is
decided when `q_hi(s) <= t`. The largest such `s` is the root of a quadratic in `s`
(`precision.linear_gaussian_ratio`). These results are in the tests, with `beta = (1, 2, 0.5)`,
unit standard deviations and `n = 2^18`.

| Case | Parameter, edge | Estimated `s*` | Exact `s*` |
|---|---|---|---|
| independent | x2, t = 4.0 | 0.8543 | 0.8537 |
| corr(x1, x2) = 0.5 | x2, t = 4.5 | 0.7812 | 0.7834 |
| independent | x2, t = 6.0 | `already_clears` | `already_clears` |
| independent | x1, t = 4.0 | `unreachable` | no real root (unreachable) |

The contraction itself is tested on uniform, log-uniform and log10-normal priors: it keeps the
median and scales the central 95 % width by `s`.

## 5. What it is not

The required precision says how narrow one parameter's prior must be for the screen's statistic to
leave the inconclusive straddle. It does not say that a calculation at that precision exists, and
it does not say that a decided verdict would be feasible: the band that is reached depends on where
the narrowed distribution sits. It is computed under the frozen thresholds and the cp3 parameter
table. A change to either after cp3 goes through `ops/tracks/p0_deviations.md` (rule R-thr) and
invalidates the numbers.

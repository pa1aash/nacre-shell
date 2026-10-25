# Caption drafts for W6 (PH-W8.9, cp6 re-audit G1 and G4)

The paper captions of fig2, fig15 and fig17 are the translation (`nacre.preprint.captions.to_tex`) of these drafts.
W6 writes them, verbatim, as the `**Fig. N**` paragraph of `figures/src/captions/<fig>.md`; the caption equality test
then holds again (until then it is an expected failure, `W6_PENDING` in tests/preprint/test_preprint_captions.py).

## fig2

```text
Illustrative construction of the four links of the mechanism chain; the brown strip is the hydroxylated aluminium oxide (red discs, surface oxygens). (a) Catechol units (nitrogen blue) displace interfacial water; (b) Ca²⁺ (green) bound in the catechol layer (beige); (c) amorphous CaCO₃ nucleus (pale blue) on the template; (d) coalesced film, with the template–nucleus and template–film contacts in vermillion. Oxygen red, hydrogen white, carbon at line vertices.
```

## fig15

```text
Regime map (rows: slurry phases, cell phases, silicates, carbonates); columns: K2 in processing and acid-adjusted (by pH) slurries, K1 per cutoff class (nominal \NumClassLo), crystalline left, amorphous right. Dots: suitable against dissolution (vertical lines: lowest passing dose at least \NumRegHighDose); plain: undetermined; single hatching: open (K1) or inconclusive (K2); cross: excluded (K2: every cell dissolves; K1: thermodynamically excluded†). Brushite at \NumClassHiLow–\NumClassHiHigh is excluded only above \NumRegCrossBrushiteHi.
```

## fig17

```text
(a) K2 stability map by slurry pH, rows ordered upward by K1 upper bound E_ub (calcite, α-TCP, ACP, β-TCP, HAp, brushite). Circle area: passing fraction, filled below a lowest passing dose of \NumRegHighDose and open above; cross: excluded (K2: every cell dissolves; K1: thermodynamically excluded†); plus: open; dot: undetermined. (b) K1 upper bounds only, bars open below; crossed hatching with dashed edges: incomplete budget; grey: cutoff classes; \NumRegNoKOneBound phases without a bound omitted.
```

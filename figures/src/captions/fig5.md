# Fig. 5 caption draft

Built from W4's production run `ignorance` (`results/preprint/screen/ignorance/summary.json`, P0-W4.3), pinned in `figures/src/schemas/upstream.yaml` (`screen_ignorance`): the barrier prefactor (schema v3 reference fields) and the θ and Ω_bulk quantiles. Thresholds from `configs/preprint/thresholds.yaml`, parameter rows from `lit/params.yaml`. Numbers in the draft are macro names only (rule R5).

## Draft

**Fig. 5** Heterogeneous barrier ΔG*_het/k_BT over contact angle θ and bulk supersaturation Ω_bulk at the screen's reference inputs. Vertical line: the C3a edge, cos θ = \NumMcos; outlines: central \NumFigFiveOutlineMass of ignorance-prior draws (slurry solid, drying dashed). The absolute-barrier bound is not drawn because A_patch is a registered gap.

## Checklist (R4, R5, R6, R7)

- Physical claim: the template acts on the barrier only through θ; only angles on the wetting side of the C3a edge halve it; the screen's ignorance prior sits on the non-wetting side.
- The θ outline and the boundary mass are properties of the ignorance prior, never a finding (`theory/ignorance_priors.md` §3).
- The clip at θ = 0 is empty in this run (\NumBoundaryMassThetaZero); the caption names only the non-wetting clip.
- When A_patch receives a value, the generator draws the C3b bound as a black contour without further change; the caption sentence then changes.

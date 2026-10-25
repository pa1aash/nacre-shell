# Fig. 3 caption draft

Source of the states and arrows: `theory/derivation_body.tex`, Section 7 ("Where the template acts: bookkeeping and the no-double-counting proof"), lane p0-w3, commit in `figures/tikz/schematics.yaml` (`fig3.w3_commit`). The default figure contains no text (Palaash's decision, P0-W6.3); every identification below is by position. The symbol variant is no longer a deliverable; `uv run nacre figs --only fig3_symbols` still builds it (`figures/out/variants/fig3_symbols.pdf`) if the SI asks for it. Numbers in the draft are macro names only (rule R5); this caption needs none.

## Draft

**Fig. 3** Illustrative construction of where Ca²⁺ binding enters the nucleation barrier: bulk solution, template–liquid interface with bound Ca²⁺, and a partially wetting CaCO₃ cap, left to right. Blue arrow: sequestration, ΔG_seq; black arrow: cap formation; top route: carbonate from the bulk at k_BT ln Ω_bulk; short arrows: Young's balance. Vermillion: the template–nucleus contact, γ_sn, including bridging Ca²⁺.

## Checklist (R4, R6, R7)

- Physical claim: Ca²⁺ binding enters the barrier once, through γ_sl; the nucleus is fed from the bulk at k_BT ln Ω_bulk; the template helps only through how well the nucleus wets it (γ_sn below γ_sl).
- Layout: one row of three states with straight horizontal arrows between them; the carbonate route runs along the top with right-angle bends and enters the cap vertically. Every cycle arrow is horizontal or vertical (checked in each build, `nacre.figs.schematic.arrow_problems`); only the three force vectors keep their physical directions, at the same line weight.
- The cap's contact angle is 55° (partial wetting, clearly below a right angle and not zero).
- Nothing depicts a raised driving force: two bound ions, no enriched cloud, no arrow from the bound layer to the nucleus.
- Ion bridging is drawn inside the template–nucleus contact (vermillion), as the contact excess Γ_Ca,sn inside γ_sn.
- No text, legend or label; the checker verifies that the PDF contains no text.
- The full identification of pictogram colours (oxygen red, nitrogen blue, Ca²⁺ green, hydrogen white) and the Γ_Ca,sn − Γ_Ca,sl difference rule move to the model section text, to keep the caption near the length target.

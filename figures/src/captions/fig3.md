# Fig. 3 caption draft

Source of the states and arrows: `theory/derivation_body.tex`, Section 7 ("Where the template acts: bookkeeping and the no-double-counting proof"), lane p0-w3, commit in `figures/tikz/schematics.yaml` (`fig3.w3_commit`). The default figure contains no text; every identification below is by position. The symbol variant (`figures/out/variants/fig3_symbols.pdf`) is the same drawing with ΔG_seq, γ_sl, γ_sn and γ_nl set on their arrows; whether it replaces the default is the operator's decision.

## Draft

**Fig. 3** Where the template's Ca²⁺ binding enters the nucleation barrier. *Top left (grey box):* the bulk solution at the regime activities, a hydrated Ca²⁺ ion (green disc with six water molecules, oxygen towards the ion) and a carbonate ion; every ion here carries its bulk electrochemical potential. *Lower middle:* the template–liquid interface at the regime Ca²⁺ activity. The catechol-bearing layer (beige band) on the hydroxylated oxide (brown strip, red discs the surface oxygens) carries catecholate and carboxylate sites; two of them hold a Ca²⁺ ion. *Blue curved arrow, top left to lower middle:* transfer of Ca²⁺ from the hydrated bulk to a site, ΔG_seq. Through the Gibbs–Langmuir adsorption term it changes only the template–liquid interfacial energy, γ_sl = γ_sl⁽⁰⁾ + Δγ_ads (blue line). *Black arrow, lower middle to lower right:* a nucleus forms on the template. *Lower right:* the amorphous CaCO₃ nucleus as a spherical cap (pale blue) at a small contact angle. Three interfaces meet at its edge:

- the template–nucleus contact under the cap (vermillion), where Ca²⁺ ions of the nucleus sit at the sites (ion bridging) as part of that contact and its energy γ_sn;
- the nucleus–liquid surface of the cap (bold black outline), γ_nl;
- the template–liquid interface outside the cap (blue), γ_sl, still carrying its adsorbed Ca²⁺.

*Three short arrows at the right edge of the cap:* the interfacial energies as line tensions in Young's relation, cos θ = (γ_sl − γ_sn)/γ_nl: blue γ_sl outward along the template, vermillion γ_sn inward along the template, black γ_nl along the cap surface. *Black curved arrow, top left to the cap:* the formula units of the nucleus come from the bulk solution at the bulk chemical potentials, so the driving force is k_BT ln Ω_bulk; none comes from the bound layer.

The binding therefore enters the barrier once, through γ_sl. It cannot raise the driving force, because at equilibrium the bound ion carries the bulk chemical potential. At fixed γ_sl⁽⁰⁾ and γ_sn, stronger binding lowers γ_sl and raises θ and the barrier: the bound ions must be removed from the area the nucleus covers. The template lowers the barrier only if the template–nucleus contact, including any ion bridging, lowers γ_sn by more than the adsorption lowers γ_sl, so that the nucleus wets the template well. Structures are drawn from their SMILES as pictograms (bonds as lines; oxygen red, nitrogen blue, Ca²⁺ green, hydrogen white; carbon at line vertices; charges not drawn). This is an illustrative construction, not a simulated structure.

## Checklist (R4, R7)

- Physical claim: Ca²⁺ binding enters the barrier once, through γ_sl. The nucleus is fed from the bulk at k_BT ln Ω_bulk. The template helps only through how well the nucleus wets it.
- Nothing in the figure depicts a raised driving force. The template carries only two bound ions, not an enriched cloud. The nucleus is fed by the arrow from the bulk, and no arrow runs from the bound layer to the nucleus.
- Ion bridging is drawn inside the template–nucleus contact (vermillion), as part of γ_sn.
- No text, legend or label in the default figure; the checker verifies that the PDF contains no text.

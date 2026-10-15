# Claim numbering reconciliation (design flag 8)

The deck (`nacre_talk.pdf`, 29 slides) counts the mechanism three ways: three linked
claims on slide 13, "four sequential links" on slide 28, and five rows in the kill table
on slide 21. This file maps every one of those deck items onto the single register
C1-C5 in `charter/claim_register.yaml`, so the numbering is fixed across deck, paper and
code. From here on, paper sections, result files, figure IDs and code modules use C1-C5
and nothing else.

| Register id | Name | Mechanistic role |
|---|---|---|
| C1 | Anchoring | link 1, anchor |
| C2 | Sequestration | link 2, sequester |
| C3 | Nucleation (crux) | link 3, nucleate |
| C4 | Conformality | outcome condition |
| C5 | Thermodynamic stability | outcome condition (regime-dependent) |

Rules for the tables below: each row is one deck item; the "Maps to" cell holds exactly
one register id, or `dropped:` followed by the reason. `tests/charter/test_charter.py`
parses every table row whose first cell is a deck-item id (`S<slide>-<tag>`).

## Deck items

### Slide 13: "The mechanism as three linked claims"

The three numbered boxes are the three mechanistic links; the fourth box ("Outcome") and
the four "killed if" captions under the arrows are the same slide.

| Deck item | Deck text (abridged) | Maps to | Note |
|---|---|---|---|
| S13-1 | 1. Anchor: PDA catechol and quinone bind hydroxylated Al2O3/AlOOH | C1 | |
| S13-2 | 2. Sequester: PDA and chitosan concentrate Ca2+ against aqueous reference | C2 | |
| S13-3 | 3. Nucleate: thin interfacial CaCO3 forms in situ, likely stabilised ACC | C3 | |
| S13-O | Outcome: conformal barrier against high-voltage Al dissolution | C4 | The slide's outcome is conformality; its thermodynamic-stability half is not drawn on the slide and is carried by C5 (from slide 21, row S21-K5). |
| S13-k1 | killed if adhesion does not beat the water displacement penalty | C1 | |
| S13-k2 | killed if binding is unfavourable versus solvated Ca2+ | C2 | |
| S13-k3 | killed if the nucleation barrier stays too high | C3 | |
| S13-k4 | killed if the favoured morphology is porous, not conformal | C4 | |

### Slide 28: "four sequential links, any one of which can kill it"

Slide 28 asserts four links but does not list them. The only slide that draws four
killable links is slide 13 (three claims plus the outcome, each with a "killed if"
caption), so the four links are read as those. Slide 12's four-row transplant table is
the other four-item list in the deck and is reconciled separately below.

| Deck item | Deck text (abridged) | Maps to | Note |
|---|---|---|---|
| S28-L1 | link 1 (anchor; per slide 13) | C1 | |
| S28-L2 | link 2 (sequester; per slide 13) | C2 | |
| S28-L3 | link 3 (nucleate; per slide 13) | C3 | |
| S28-L4 | link 4 (conformal outcome; per slide 13) | C4 | C5 is a fifth condition the slide does not count; see S21-K5. |

### Slide 12: "The transplant" (four mappings)

| Deck item | Deck text (abridged) | Maps to | Note |
|---|---|---|---|
| S12-T1 | chitin scaffold -> chitosan binder | C2 | Chitosan enters the register as a Ca2+ sequestering phase (link 2) and as a control elsewhere. |
| S12-T2 | acidic proteins that bind Ca2+ -> polydopamine catechol and quinone groups | C2 | Design flag 4: tested against carboxylate controls; if they win, this row of the transplant table changes. |
| S12-T3 | shell nacre surface -> hydroxylated Al2O3 and AlOOH on the collector | C1 | |
| S12-T4 | aragonite platelet -> thin interfacial CaCO3, plausibly stabilised ACC | C3 | Polymorph framing (ACC or calcite) is registered at G2 (design flag 1). |

### Slide 21: "Pre-registered thresholds and kill criteria" (five-row kill table and bands)

| Deck item | Deck text (abridged) | Maps to | Note |
|---|---|---|---|
| S21-K1 | Anchoring: adhesion does not exceed the water displacement penalty | C1 | |
| S21-K2 | Sequestration: Ca2+ binding is unfavourable against the solvated reference | C2 | |
| S21-K3 | Nucleation: f(theta) >= 0.8 | C3 | Recorded as proposed (deck), status pending G2. |
| S21-K4 | Conformality: favoured morphology is a porous scale | C4 | Needs its own criterion (design flag 2). |
| S21-K5 | Stability: the phase sits far above the Pourbaix hull at operating pH and potential | C5 | Aqueous screen covers R-slurry only; R-cell uses a Li-referenced window (design flag 7). |
| S21-B1 | f(theta) <= 0.5 feasible | C3 | Proposed (deck), pending G2; design flag 2 objection attached. |
| S21-B2 | 0.5 < f(theta) < 0.8 inconclusive | C3 | Proposed (deck), pending G2. |
| S21-B3 | f(theta) >= 0.8 falsified | C3 | Proposed (deck), pending G2. |
| S21-S1 | Current standing, borderline near 0.5 under crystalline calcite assumptions | C3 | Seen before registration; disclosure D-flag1 (design flag 1), formal text in S22. |
| S21-S2 | Moves clearly into the supported region under the ACC framing | C3 | Primary framing fixed at G2 with literature-only justification. |
| S21-S3 | That sensitivity is itself a reportable result | C3 | Reported as the Phase 7 item 11 sensitivity analysis. |
| S21-F | "The thresholds were set before the calculation, not after seeing it." | dropped: a statement about process, not a claim; contradicted by S21-S1 and superseded by the timestamped registration at G2 | |

## Related deck definitions superseded by the register

These are not counted claims, but each is pinned to one claim so the deck's wording does
not reappear in the paper unchanged.

| Deck item | Deck text (abridged) | Maps to | Note |
|---|---|---|---|
| S18-W | W_adh = (E_oxide + E_polymer - E_interface)/A | C1 | Static vacuum energy; replaced as the decisive observable by the PMF-derived W_adh,wet. Kept only as the item-1 comparator. |
| S18-G | Delta_G_seq = G(Ca2+@site) + n G(H2O) - G(site) - G(Ca2+aq) | C2 | Becomes a thermodynamic cycle with protonation and ionic-strength corrections. |
| S18-P | Pourbaix analysis as a mechanistic proxy | C5 | Must not be satisfiable by construction (Phase 7 item 21). |
| S20-E | gamma_eff = gamma_nuc,liq - Delta_gamma_water | C3 | OPEN (design flag 3): sign and use in Young owned by S20/S21. |

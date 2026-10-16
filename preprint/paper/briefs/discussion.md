# Brief: Discussion

- **File:** `sections/discussion.tex`.
- **Written:** after checkpoint cp4.
- **Length target:** 800 to 1000 words, six paragraphs.

## Purpose

Say plainly what the results license and what they do not. Weigh the contrary evidence. State the limits of the model, the proxy nature of the Pourbaix result and the breadth of the priors.

## Physical argument, in order

1. **What the results license.**
   - A statement that the sequence is, or is not, thermodynamically possible under the stated priors.
   - The ranking of the governing quantities.
   - The precision targets for first-principles work.
   - Claims: CL-G01 and CL-P01.
2. **What they do not license.** The does-not-claim sentences are used verbatim, because they are the only sentences the scope linter exempts. They are about function, rates and cycling, optimality and experiment. Claims: CL-N01, CL-N02, CL-N04 and CL-N05.
3. **Contrary evidence.**
   - The literature that cuts against the chain, including Osorio-Celestino and co-workers (2020).
   - It is weighed link by link: which link it bears on, and whether it moves a prior or a criterion.
   - Its content is taken from p0-w2's record in `lit/contrary.md`, not from memory. The reference enters through `nacre bib add <doi>` with the DOI recorded there.
   - Claim: CL-L05.
4. **Limits of the model.**
   - Classical nucleation with a spherical-cap nucleus of one registered polymorph; amorphous precursors and non-classical pathways lie outside it (CL-L03).
   - The insulating-film limitation: film thickness is bounded above by electronic resistance, and that bound is reported only as a limitation (CL-L04, from `charter/scope_guard.md`).
5. **The Pourbaix proxy.** Phase stability is not kinetics: the Pourbaix result says which phases are stable, not how fast any forms or dissolves. Claim: CL-L01.
6. **The breadth of the priors.**
   - Every conclusion is conditional on them, and narrower priors could reorder the ranking.
   - This is why the required-precision result is the transferable output.
   - Claim: CL-L02.

## Figures and tables

- Figs 5, 6 and 7 and Table 1 are referred back to; no new figure.

## Macros needed

None new. It reuses Results macros only where a number is essential.

## Claims carried

CL-G01, CL-P01, CL-N01, CL-N02, CL-N04, CL-N05, CL-L05, CL-L03, CL-L04, CL-L01 and CL-L02.

## Supplying lanes

- p0-w2: `lit/contrary.md` and `lit/novelty.md`.
- p0-w1: prior breadth (`lit/params.yaml`).
- p0-w5: Pourbaix.
- p0-w8: text.

## Cautions

- The branch rule applies (`charter/branches.md`): the Discussion must read correctly whether the screen comes out favourable, inconclusive or unfavourable.
- No softening of a miss in the retrodiction; it is discussed where it bears on a link.

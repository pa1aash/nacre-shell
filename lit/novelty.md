# Novelty audit, track p0

Session P0-W2.1 (master-plan trace S13). This file supports the novelty wording of the P0 preprint and nothing else. Its scope is set by the scope guard (`charter/scope_guard.md`, "No novelty wording beyond what the Phase 1 novelty audit supports"; patterns SG13 and SG14), and the chain it audits is the claim register C1 to C5 (`charter/claim_register.yaml`). The charter is under the G0 audit (cp1 open), so this file depends on register version 1 as drafted in S02; a change to the chain after G0 means this audit has to be re-checked against it.

The sections are written in order: the query design was fixed and committed before any query was run, and the query log follows it.

## Query design

Fixed before searching. Nothing in this section was changed after any result was seen.

### Question

Has the combined thermodynamic chain been reported before, for an aluminium current collector in water-processed (alkaline slurry) electrode manufacture? The chain is:

1. wet adhesion of a catechol or polysaccharide template to the hydroxylated native oxide (C1);
2. Ca2+ sequestration and local enrichment by that template (C2);
3. heterogeneous, templated CaCO3 nucleation on it (C3);
4. stability of the resulting film (C4, C5).

A secondary question is which parts of the chain have been reported separately, and by whom, so that the paper can credit them.

### Concept blocks and synonyms

Each block is the OR of its terms. Spellings (aluminium/aluminum, mineralisation/mineralization) are both searched. Formulae are written as the search engines index them.

| Block | Concept | Terms (OR within the block) |
|---|---|---|
| S | substrate | "aluminium current collector", "aluminum current collector", "Al current collector", "aluminium foil", "aluminum foil", "Al foil", alumina, boehmite, Al2O3, AlOOH |
| O | organic layer | polydopamine, catechol, "mussel-inspired", chitosan, alginate, "carboxymethyl chitosan" |
| M | mineral | "calcium carbonate", CaCO3, "amorphous calcium carbonate", biomineralization, biomineralisation, nacre |
| P | process | "aqueous processing", "water-based", "aqueous binder", "aqueous slurry", "water-processed", "fluorine-free", "PVDF-free", binder |

### Combinations

All eleven combinations of two or more blocks are searched: the six pairs SO, SM, SP, OM, OP and MP, the four triples SOM, SOP, SMP and OMP, and the quadruple SOMP. A combination is the AND of its blocks.

**Battery-context variants.** The S, M and P blocks have large literatures outside batteries: alumina ceramics and catalysts, CaCO3 scale and cement, and binders in construction. Each of the eleven combinations is therefore also run once with a context block C ANDed on: (battery OR "lithium-ion" OR "Li-ion" OR cathode OR electrode OR "current collector"). These variants only rank and narrow the screen. The unconstrained run stays the record of coverage. This gives 22 boolean query strings.

### Routes and query forms

The routes are the repository retrieval toolkit (`src/nacre/retrieval`, sources Crossref, Semantic Scholar, OpenAIRE, arXiv and ChemRxiv, all through its rate-limited HTTP session). They are used in the form each route accepts:

| Route | Boolean support | Form used |
|---|---|---|
| Semantic Scholar (bulk search endpoint) | yes (`+`, `\|`, quoted phrases, parentheses) | the 22 boolean strings |
| arXiv API | yes (`AND`, `OR`, field `all:`) | the 22 boolean strings |
| OpenAIRE Graph API | tested on the first query; if boolean operators are not honoured, keyword form as for Crossref | the 22 boolean strings, or the keyword form |
| Crossref works API | no (relevance-ranked bag of words) | keyword form, below |
| ChemRxiv public API | no | keyword form, below |
| OpenAlex works API (supplementary route, not part of the toolkit, called through the toolkit's HTTP session) | yes (`title_and_abstract.search`, with `AND`, `OR` and quoted phrases) | the 22 boolean strings |

**Keyword form.** For each of the eleven combinations, three strings are built. String k (k = 1, 2, 3) takes the k-th representative term of each block in the combination:

| Block | Representative terms 1, 2, 3 |
|---|---|
| S | "aluminium current collector", "aluminum foil", boehmite |
| O | polydopamine, catechol, chitosan |
| M | "calcium carbonate", "amorphous calcium carbonate", biomineralization |
| P | "aqueous binder", "water-based", "fluorine-free" |

This gives 33 keyword strings per keyword-only route. They are run unconstrained, because those routes rank by relevance and the S and P terms already carry the battery context.

**Patents.** Patent search goes through the toolkit's Lens client (`LENS_TOKEN` in `.env`), and through any other patent route keyed in `.env`. Without a working route, the patent side is recorded as an instrument gap and the novelty wording is weakened to match.

### Screening protocol

1. **Record.** For every query: the route, the exact string, the date, the reported total hits, and the number screened.
2. **Screen.** Titles and abstracts of the top 25 results per query and route, in the route's relevance order, are screened. The union is deduplicated by DOI, or by title where there is no DOI.
3. **Retention criteria.** A record is retained if it reports any of the following:
   - (a) any part of the chain on aluminium or alumina, or on a battery current collector;
   - (b) templated CaCO3 or ACC nucleation on polydopamine, catechol, chitosan, alginate or carboxymethyl-chitosan layers on any substrate;
   - (c) catechol or polysaccharide binders, or coatings, used against aluminium current-collector corrosion in aqueous or fluorine-free processing;
   - (d) CaCO3 or other mineral layers on aluminium for corrosion protection, or as an observed cause of corrosion;
   - (e) a computational treatment of any link (adhesion in water, Ca2+ binding, templated nucleation, film stability) for these materials.
4. **Full text.** The closest hits, those covering three or more blocks or two links of the chain, are read in full where an open copy exists. Copies are kept only under `.local/lit/novelty/` and are never committed.
5. **Closest prior art.** Each closest hit enters the table with: its DOI; what it shows, with a locator; the blocks it covers; the physical question it answers; and how P0 differs.

### Decision rule for the novelty wording

- A combined-chain novelty sentence is written only if no retained record evaluates adhesion, sequestration, templated nucleation and film stability together for an aluminium current collector in the aqueous processing regime.
- If the search finds such a record, the sentence is withdrawn and the record is credited.
- Each sentence is limited to what was searched (routes, dates, blocks). No "first" wording is used.
- The patent gap, if it remains, is stated in the wording itself, or in the sentence's qualifier.

## Execution notes and deviations from the design

The design above was run unchanged on 2026-10-16, with these differences, all of them forced by the routes. Each was decided before the results it affects were seen.

1. **OpenAIRE.** The Graph API refused the first boolean string with HTTP 400 ("Too many logical operators found. Max allowed is 4"). OpenAIRE was therefore run in the keyword form (33 strings), as the design allowed. The refused attempt is kept in the log (Q67).
2. **Semantic Scholar.** The boolean form needs the bulk search endpoint, which has no relevance ordering. The 25 records screened per query are the 25 most cited (`sort=citationCount:desc`). The reported hit count is the full boolean total.
3. **arXiv.** Some strings got HTTP 429 and were re-run after a pause. The log shows the final attempt and the number of attempts. Every arXiv string completed. arXiv indexes little chemistry of this kind: 17 of the 22 strings returned zero hits.
4. **ChemRxiv.** The public API returned HTTP 403 to all 33 keyword strings, so ChemRxiv was not searched (instrument gap). Preprints from ChemRxiv that carry a DOI (10.26434/…) are still reached through Crossref, OpenAlex and Semantic Scholar, which index them, but ChemRxiv's own search was not available.
5. **Patents.** The toolkit's only patent client is Lens, and `LENS_TOKEN` is empty in `.env`. All 33 patent strings were skipped and logged as `no_token`. No other patent route is keyed in `.env`. **The patent literature was not searched** (instrument gap).
6. **OpenAlex** (supplementary route) was queried with `title_and_abstract.search`, so its hit counts are title-and-abstract matches.
7. **Follow-up queries.** After screening, targeted follow-up queries (tags N1 and N2) checked the nearest neighbours that screening had surfaced: polydopamine on Al foil; CaCO3 coatings for Al corrosion protection; biomineral interphases in batteries; bio-derived binders against Al collector corrosion; computational treatments of the links. They are logged separately (table T) and are not part of the designed coverage record.
8. **Full text.** Open copies were reached for 5 records: 4 through Europe PMC and 2 as repository or journal PDFs (the PDA-treated Cu-collector paper came both ways). Publisher-hosted open copies (ACS, MDPI, Wiley, APS, IOP) refused headless clients. Where no full text was reached, the locator is the abstract, and a record is credited only for what its abstract states.

Raw responses, screening files and full texts are local-only under `.local/lit/novelty/`.

## Query log

**Designed queries.**
- **Attempted.** 199 strings were attempted:
  - Semantic Scholar 22, OpenAlex 22, arXiv 22 (boolean form, with and without the context block C);
  - OpenAIRE 33 + 1 refused, Crossref 33, ChemRxiv 33 (keyword form);
  - Lens 33 (patents).
- **Executed.** 133 strings returned results, across five routes: Semantic Scholar, OpenAlex, arXiv, OpenAIRE and Crossref.
- **Screened.** 1917 result rows were screened. After deduplication by DOI or title, 1158 unique records remained. They were first ranked by how many blocks their title and abstract matched, and then read.

`Hits reported` is the total the route returned for the string. For keyword-only routes (Crossref, OpenAIRE), this is a relevance-ranked match count, not a boolean count, and it is not comparable across routes. `Screened` is the number of title and abstract records read for that string. `Retained DOIs` are the records from that string that entered the retained set (criteria (a) to (e)) or the closest-prior-art table.

| # | Route | Combination | Query string | Date | Hits reported | Screened | Retained DOIs | Status |
|---|---|---|---|---|---|---|---|---|
| Q1 | semanticscholar | SO | `("aluminium current collector" \| "aluminum current collector" \| "Al current collector" \| "aluminium foil" \| "aluminum foil" \| "Al foil" \| alumina \| boehmite \| Al2O3 \| AlOOH) + (polydopamine \| catechol \| "mussel-inspired" \| chitosan \| alginate \| "carboxymethyl chitosan")` | 2026-10-16 | 1104 | 25 | — | ok |
| Q2 | semanticscholar | SO+C | `("aluminium current collector" \| "aluminum current collector" \| "Al current collector" \| "aluminium foil" \| "aluminum foil" \| "Al foil" \| alumina \| boehmite \| Al2O3 \| AlOOH) + (polydopamine \| catechol \| "mussel-inspired" \| chitosan \| alginate \| "carboxymethyl chitosan") + (battery \| "lithium-ion" \| "Li-ion" \| cathode \| electrode \| "current collector")` | 2026-10-16 | 72 | 25 | 10.1021/acsami.8b03657 | ok |
| Q3 | semanticscholar | SM | `("aluminium current collector" \| "aluminum current collector" \| "Al current collector" \| "aluminium foil" \| "aluminum foil" \| "Al foil" \| alumina \| boehmite \| Al2O3 \| AlOOH) + ("calcium carbonate" \| CaCO3 \| "amorphous calcium carbonate" \| biomineralization \| biomineralisation \| nacre)` | 2026-10-16 | 2080 | 25 | — | ok |
| Q4 | semanticscholar | SM+C | `("aluminium current collector" \| "aluminum current collector" \| "Al current collector" \| "aluminium foil" \| "aluminum foil" \| "Al foil" \| alumina \| boehmite \| Al2O3 \| AlOOH) + ("calcium carbonate" \| CaCO3 \| "amorphous calcium carbonate" \| biomineralization \| biomineralisation \| nacre) + (battery \| "lithium-ion" \| "Li-ion" \| cathode \| electrode \| "current collector")` | 2026-10-16 | 31 | 25 | — | ok |
| Q5 | semanticscholar | SP | `("aluminium current collector" \| "aluminum current collector" \| "Al current collector" \| "aluminium foil" \| "aluminum foil" \| "Al foil" \| alumina \| boehmite \| Al2O3 \| AlOOH) + ("aqueous processing" \| "water-based" \| "aqueous binder" \| "aqueous slurry" \| "water-processed" \| "fluorine-free" \| "PVDF-free" \| binder)` | 2026-10-16 | 7805 | 25 | — | ok |
| Q6 | semanticscholar | SP+C | `("aluminium current collector" \| "aluminum current collector" \| "Al current collector" \| "aluminium foil" \| "aluminum foil" \| "Al foil" \| alumina \| boehmite \| Al2O3 \| AlOOH) + ("aqueous processing" \| "water-based" \| "aqueous binder" \| "aqueous slurry" \| "water-processed" \| "fluorine-free" \| "PVDF-free" \| binder) + (battery \| "lithium-ion" \| "Li-ion" \| cathode \| electrode \| "current collector")` | 2026-10-16 | 652 | 25 | 10.1016/j.jpowsour.2013.10.039 | ok |
| Q7 | semanticscholar | OM | `(polydopamine \| catechol \| "mussel-inspired" \| chitosan \| alginate \| "carboxymethyl chitosan") + ("calcium carbonate" \| CaCO3 \| "amorphous calcium carbonate" \| biomineralization \| biomineralisation \| nacre)` | 2026-10-16 | 2326 | 25 | 10.1002/adfm.200902347 | ok |
| Q8 | semanticscholar | OM+C | `(polydopamine \| catechol \| "mussel-inspired" \| chitosan \| alginate \| "carboxymethyl chitosan") + ("calcium carbonate" \| CaCO3 \| "amorphous calcium carbonate" \| biomineralization \| biomineralisation \| nacre) + (battery \| "lithium-ion" \| "Li-ion" \| cathode \| electrode \| "current collector")` | 2026-10-16 | 45 | 25 | 10.1021/jacs.4c03943 | ok |
| Q9 | semanticscholar | OP | `(polydopamine \| catechol \| "mussel-inspired" \| chitosan \| alginate \| "carboxymethyl chitosan") + ("aqueous processing" \| "water-based" \| "aqueous binder" \| "aqueous slurry" \| "water-processed" \| "fluorine-free" \| "PVDF-free" \| binder)` | 2026-10-16 | 2054 | 25 | — | ok |
| Q10 | semanticscholar | OP+C | `(polydopamine \| catechol \| "mussel-inspired" \| chitosan \| alginate \| "carboxymethyl chitosan") + ("aqueous processing" \| "water-based" \| "aqueous binder" \| "aqueous slurry" \| "water-processed" \| "fluorine-free" \| "PVDF-free" \| binder) + (battery \| "lithium-ion" \| "Li-ion" \| cathode \| electrode \| "current collector")` | 2026-10-16 | 586 | 25 | — | ok |
| Q11 | semanticscholar | MP | `("calcium carbonate" \| CaCO3 \| "amorphous calcium carbonate" \| biomineralization \| biomineralisation \| nacre) + ("aqueous processing" \| "water-based" \| "aqueous binder" \| "aqueous slurry" \| "water-processed" \| "fluorine-free" \| "PVDF-free" \| binder)` | 2026-10-16 | 2585 | 25 | — | ok |
| Q12 | semanticscholar | MP+C | `("calcium carbonate" \| CaCO3 \| "amorphous calcium carbonate" \| biomineralization \| biomineralisation \| nacre) + ("aqueous processing" \| "water-based" \| "aqueous binder" \| "aqueous slurry" \| "water-processed" \| "fluorine-free" \| "PVDF-free" \| binder) + (battery \| "lithium-ion" \| "Li-ion" \| cathode \| electrode \| "current collector")` | 2026-10-16 | 24 | 24 | — | ok |
| Q13 | semanticscholar | SOM | `("aluminium current collector" \| "aluminum current collector" \| "Al current collector" \| "aluminium foil" \| "aluminum foil" \| "Al foil" \| alumina \| boehmite \| Al2O3 \| AlOOH) + (polydopamine \| catechol \| "mussel-inspired" \| chitosan \| alginate \| "carboxymethyl chitosan") + ("calcium carbonate" \| CaCO3 \| "amorphous calcium carbonate" \| biomineralization \| biomineralisation \| nacre)` | 2026-10-16 | 17 | 17 | — | ok |
| Q14 | semanticscholar | SOM+C | `("aluminium current collector" \| "aluminum current collector" \| "Al current collector" \| "aluminium foil" \| "aluminum foil" \| "Al foil" \| alumina \| boehmite \| Al2O3 \| AlOOH) + (polydopamine \| catechol \| "mussel-inspired" \| chitosan \| alginate \| "carboxymethyl chitosan") + ("calcium carbonate" \| CaCO3 \| "amorphous calcium carbonate" \| biomineralization \| biomineralisation \| nacre) + (battery \| "lithium-ion" \| "Li-ion" \| cathode \| electrode \| "current collector")` | 2026-10-16 | 1 | 1 | — | ok |
| Q15 | semanticscholar | SOP | `("aluminium current collector" \| "aluminum current collector" \| "Al current collector" \| "aluminium foil" \| "aluminum foil" \| "Al foil" \| alumina \| boehmite \| Al2O3 \| AlOOH) + (polydopamine \| catechol \| "mussel-inspired" \| chitosan \| alginate \| "carboxymethyl chitosan") + ("aqueous processing" \| "water-based" \| "aqueous binder" \| "aqueous slurry" \| "water-processed" \| "fluorine-free" \| "PVDF-free" \| binder)` | 2026-10-16 | 40 | 25 | 10.1021/acsami.8b03657 | ok |
| Q16 | semanticscholar | SOP+C | `("aluminium current collector" \| "aluminum current collector" \| "Al current collector" \| "aluminium foil" \| "aluminum foil" \| "Al foil" \| alumina \| boehmite \| Al2O3 \| AlOOH) + (polydopamine \| catechol \| "mussel-inspired" \| chitosan \| alginate \| "carboxymethyl chitosan") + ("aqueous processing" \| "water-based" \| "aqueous binder" \| "aqueous slurry" \| "water-processed" \| "fluorine-free" \| "PVDF-free" \| binder) + (battery \| "lithium-ion" \| "Li-ion" \| cathode \| electrode \| "current collector")` | 2026-10-16 | 11 | 11 | 10.1021/acsami.8b03657 | ok |
| Q17 | semanticscholar | SMP | `("aluminium current collector" \| "aluminum current collector" \| "Al current collector" \| "aluminium foil" \| "aluminum foil" \| "Al foil" \| alumina \| boehmite \| Al2O3 \| AlOOH) + ("calcium carbonate" \| CaCO3 \| "amorphous calcium carbonate" \| biomineralization \| biomineralisation \| nacre) + ("aqueous processing" \| "water-based" \| "aqueous binder" \| "aqueous slurry" \| "water-processed" \| "fluorine-free" \| "PVDF-free" \| binder)` | 2026-10-16 | 106 | 25 | — | ok |
| Q18 | semanticscholar | SMP+C | `("aluminium current collector" \| "aluminum current collector" \| "Al current collector" \| "aluminium foil" \| "aluminum foil" \| "Al foil" \| alumina \| boehmite \| Al2O3 \| AlOOH) + ("calcium carbonate" \| CaCO3 \| "amorphous calcium carbonate" \| biomineralization \| biomineralisation \| nacre) + ("aqueous processing" \| "water-based" \| "aqueous binder" \| "aqueous slurry" \| "water-processed" \| "fluorine-free" \| "PVDF-free" \| binder) + (battery \| "lithium-ion" \| "Li-ion" \| cathode \| electrode \| "current collector")` | 2026-10-16 | 0 | 0 | — | ok |
| Q19 | semanticscholar | OMP | `(polydopamine \| catechol \| "mussel-inspired" \| chitosan \| alginate \| "carboxymethyl chitosan") + ("calcium carbonate" \| CaCO3 \| "amorphous calcium carbonate" \| biomineralization \| biomineralisation \| nacre) + ("aqueous processing" \| "water-based" \| "aqueous binder" \| "aqueous slurry" \| "water-processed" \| "fluorine-free" \| "PVDF-free" \| binder)` | 2026-10-16 | 42 | 25 | — | ok |
| Q20 | semanticscholar | OMP+C | `(polydopamine \| catechol \| "mussel-inspired" \| chitosan \| alginate \| "carboxymethyl chitosan") + ("calcium carbonate" \| CaCO3 \| "amorphous calcium carbonate" \| biomineralization \| biomineralisation \| nacre) + ("aqueous processing" \| "water-based" \| "aqueous binder" \| "aqueous slurry" \| "water-processed" \| "fluorine-free" \| "PVDF-free" \| binder) + (battery \| "lithium-ion" \| "Li-ion" \| cathode \| electrode \| "current collector")` | 2026-10-16 | 1 | 1 | — | ok |
| Q21 | semanticscholar | SOMP | `("aluminium current collector" \| "aluminum current collector" \| "Al current collector" \| "aluminium foil" \| "aluminum foil" \| "Al foil" \| alumina \| boehmite \| Al2O3 \| AlOOH) + (polydopamine \| catechol \| "mussel-inspired" \| chitosan \| alginate \| "carboxymethyl chitosan") + ("calcium carbonate" \| CaCO3 \| "amorphous calcium carbonate" \| biomineralization \| biomineralisation \| nacre) + ("aqueous processing" \| "water-based" \| "aqueous binder" \| "aqueous slurry" \| "water-processed" \| "fluorine-free" \| "PVDF-free" \| binder)` | 2026-10-16 | 0 | 0 | — | ok |
| Q22 | semanticscholar | SOMP+C | `("aluminium current collector" \| "aluminum current collector" \| "Al current collector" \| "aluminium foil" \| "aluminum foil" \| "Al foil" \| alumina \| boehmite \| Al2O3 \| AlOOH) + (polydopamine \| catechol \| "mussel-inspired" \| chitosan \| alginate \| "carboxymethyl chitosan") + ("calcium carbonate" \| CaCO3 \| "amorphous calcium carbonate" \| biomineralization \| biomineralisation \| nacre) + ("aqueous processing" \| "water-based" \| "aqueous binder" \| "aqueous slurry" \| "water-processed" \| "fluorine-free" \| "PVDF-free" \| binder) + (battery \| "lithium-ion" \| "Li-ion" \| cathode \| electrode \| "current collector")` | 2026-10-16 | 0 | 0 | — | ok |
| Q23 | openalex | SO | `("aluminium current collector" OR "aluminum current collector" OR "Al current collector" OR "aluminium foil" OR "aluminum foil" OR "Al foil" OR alumina OR boehmite OR Al2O3 OR AlOOH) AND (polydopamine OR catechol OR "mussel-inspired" OR chitosan OR alginate OR "carboxymethyl chitosan")` | 2026-10-16 | 1254 | 25 | — | ok |
| Q24 | openalex | SO+C | `("aluminium current collector" OR "aluminum current collector" OR "Al current collector" OR "aluminium foil" OR "aluminum foil" OR "Al foil" OR alumina OR boehmite OR Al2O3 OR AlOOH) AND (polydopamine OR catechol OR "mussel-inspired" OR chitosan OR alginate OR "carboxymethyl chitosan") AND (battery OR "lithium-ion" OR "Li-ion" OR cathode OR electrode OR "current collector")` | 2026-10-16 | 100 | 25 | 10.1002/app.53530, 10.1021/acsami.8b03657 | ok |
| Q25 | openalex | SM | `("aluminium current collector" OR "aluminum current collector" OR "Al current collector" OR "aluminium foil" OR "aluminum foil" OR "Al foil" OR alumina OR boehmite OR Al2O3 OR AlOOH) AND ("calcium carbonate" OR CaCO3 OR "amorphous calcium carbonate" OR biomineralization OR biomineralisation OR nacre)` | 2026-10-16 | 2097 | 25 | — | ok |
| Q26 | openalex | SM+C | `("aluminium current collector" OR "aluminum current collector" OR "Al current collector" OR "aluminium foil" OR "aluminum foil" OR "Al foil" OR alumina OR boehmite OR Al2O3 OR AlOOH) AND ("calcium carbonate" OR CaCO3 OR "amorphous calcium carbonate" OR biomineralization OR biomineralisation OR nacre) AND (battery OR "lithium-ion" OR "Li-ion" OR cathode OR electrode OR "current collector")` | 2026-10-16 | 34 | 25 | — | ok |
| Q27 | openalex | SP | `("aluminium current collector" OR "aluminum current collector" OR "Al current collector" OR "aluminium foil" OR "aluminum foil" OR "Al foil" OR alumina OR boehmite OR Al2O3 OR AlOOH) AND ("aqueous processing" OR "water-based" OR "aqueous binder" OR "aqueous slurry" OR "water-processed" OR "fluorine-free" OR "PVDF-free" OR binder)` | 2026-10-16 | 8133 | 25 | 10.1016/j.jpowsour.2013.10.039, 10.1149/06418.0013ecst | ok |
| Q28 | openalex | SP+C | `("aluminium current collector" OR "aluminum current collector" OR "Al current collector" OR "aluminium foil" OR "aluminum foil" OR "Al foil" OR alumina OR boehmite OR Al2O3 OR AlOOH) AND ("aqueous processing" OR "water-based" OR "aqueous binder" OR "aqueous slurry" OR "water-processed" OR "fluorine-free" OR "PVDF-free" OR binder) AND (battery OR "lithium-ion" OR "Li-ion" OR cathode OR electrode OR "current collector")` | 2026-10-16 | 847 | 25 | 10.1007/s10853-014-8028-3, 10.1016/j.electacta.2019.05.141, 10.1016/j.jpowsour.2013.10.039 | ok |
| Q29 | openalex | OM | `(polydopamine OR catechol OR "mussel-inspired" OR chitosan OR alginate OR "carboxymethyl chitosan") AND ("calcium carbonate" OR CaCO3 OR "amorphous calcium carbonate" OR biomineralization OR biomineralisation OR nacre)` | 2026-10-16 | 2541 | 25 | 10.1002/adfm.200902347, 10.1021/cg301759t, 10.1021/la803541m | ok |
| Q30 | openalex | OM+C | `(polydopamine OR catechol OR "mussel-inspired" OR chitosan OR alginate OR "carboxymethyl chitosan") AND ("calcium carbonate" OR CaCO3 OR "amorphous calcium carbonate" OR biomineralization OR biomineralisation OR nacre) AND (battery OR "lithium-ion" OR "Li-ion" OR cathode OR electrode OR "current collector")` | 2026-10-16 | 62 | 25 | 10.1002/cssc.201700616 | ok |
| Q31 | openalex | OP | `(polydopamine OR catechol OR "mussel-inspired" OR chitosan OR alginate OR "carboxymethyl chitosan") AND ("aqueous processing" OR "water-based" OR "aqueous binder" OR "aqueous slurry" OR "water-processed" OR "fluorine-free" OR "PVDF-free" OR binder)` | 2026-10-16 | 2664 | 25 | — | ok |
| Q32 | openalex | OP+C | `(polydopamine OR catechol OR "mussel-inspired" OR chitosan OR alginate OR "carboxymethyl chitosan") AND ("aqueous processing" OR "water-based" OR "aqueous binder" OR "aqueous slurry" OR "water-processed" OR "fluorine-free" OR "PVDF-free" OR binder) AND (battery OR "lithium-ion" OR "Li-ion" OR cathode OR electrode OR "current collector")` | 2026-10-16 | 831 | 25 | 10.1021/acsami.8b03657 | ok |
| Q33 | openalex | MP | `("calcium carbonate" OR CaCO3 OR "amorphous calcium carbonate" OR biomineralization OR biomineralisation OR nacre) AND ("aqueous processing" OR "water-based" OR "aqueous binder" OR "aqueous slurry" OR "water-processed" OR "fluorine-free" OR "PVDF-free" OR binder)` | 2026-10-16 | 2831 | 25 | — | ok |
| Q34 | openalex | MP+C | `("calcium carbonate" OR CaCO3 OR "amorphous calcium carbonate" OR biomineralization OR biomineralisation OR nacre) AND ("aqueous processing" OR "water-based" OR "aqueous binder" OR "aqueous slurry" OR "water-processed" OR "fluorine-free" OR "PVDF-free" OR binder) AND (battery OR "lithium-ion" OR "Li-ion" OR cathode OR electrode OR "current collector")` | 2026-10-16 | 33 | 25 | — | ok |
| Q35 | openalex | SOM | `("aluminium current collector" OR "aluminum current collector" OR "Al current collector" OR "aluminium foil" OR "aluminum foil" OR "Al foil" OR alumina OR boehmite OR Al2O3 OR AlOOH) AND (polydopamine OR catechol OR "mussel-inspired" OR chitosan OR alginate OR "carboxymethyl chitosan") AND ("calcium carbonate" OR CaCO3 OR "amorphous calcium carbonate" OR biomineralization OR biomineralisation OR nacre)` | 2026-10-16 | 20 | 20 | — | ok |
| Q36 | openalex | SOM+C | `("aluminium current collector" OR "aluminum current collector" OR "Al current collector" OR "aluminium foil" OR "aluminum foil" OR "Al foil" OR alumina OR boehmite OR Al2O3 OR AlOOH) AND (polydopamine OR catechol OR "mussel-inspired" OR chitosan OR alginate OR "carboxymethyl chitosan") AND ("calcium carbonate" OR CaCO3 OR "amorphous calcium carbonate" OR biomineralization OR biomineralisation OR nacre) AND (battery OR "lithium-ion" OR "Li-ion" OR cathode OR electrode OR "current collector")` | 2026-10-16 | 0 | 0 | — | ok |
| Q37 | openalex | SOP | `("aluminium current collector" OR "aluminum current collector" OR "Al current collector" OR "aluminium foil" OR "aluminum foil" OR "Al foil" OR alumina OR boehmite OR Al2O3 OR AlOOH) AND (polydopamine OR catechol OR "mussel-inspired" OR chitosan OR alginate OR "carboxymethyl chitosan") AND ("aqueous processing" OR "water-based" OR "aqueous binder" OR "aqueous slurry" OR "water-processed" OR "fluorine-free" OR "PVDF-free" OR binder)` | 2026-10-16 | 66 | 25 | 10.1021/acsami.8b03657, 10.1149/ma2014-02/1/16 | ok |
| Q38 | openalex | SOP+C | `("aluminium current collector" OR "aluminum current collector" OR "Al current collector" OR "aluminium foil" OR "aluminum foil" OR "Al foil" OR alumina OR boehmite OR Al2O3 OR AlOOH) AND (polydopamine OR catechol OR "mussel-inspired" OR chitosan OR alginate OR "carboxymethyl chitosan") AND ("aqueous processing" OR "water-based" OR "aqueous binder" OR "aqueous slurry" OR "water-processed" OR "fluorine-free" OR "PVDF-free" OR binder) AND (battery OR "lithium-ion" OR "Li-ion" OR cathode OR electrode OR "current collector")` | 2026-10-16 | 26 | 25 | 10.1021/acsami.8b03657, 10.1149/ma2014-02/1/16 | ok |
| Q39 | openalex | SMP | `("aluminium current collector" OR "aluminum current collector" OR "Al current collector" OR "aluminium foil" OR "aluminum foil" OR "Al foil" OR alumina OR boehmite OR Al2O3 OR AlOOH) AND ("calcium carbonate" OR CaCO3 OR "amorphous calcium carbonate" OR biomineralization OR biomineralisation OR nacre) AND ("aqueous processing" OR "water-based" OR "aqueous binder" OR "aqueous slurry" OR "water-processed" OR "fluorine-free" OR "PVDF-free" OR binder)` | 2026-10-16 | 107 | 25 | — | ok |
| Q40 | openalex | SMP+C | `("aluminium current collector" OR "aluminum current collector" OR "Al current collector" OR "aluminium foil" OR "aluminum foil" OR "Al foil" OR alumina OR boehmite OR Al2O3 OR AlOOH) AND ("calcium carbonate" OR CaCO3 OR "amorphous calcium carbonate" OR biomineralization OR biomineralisation OR nacre) AND ("aqueous processing" OR "water-based" OR "aqueous binder" OR "aqueous slurry" OR "water-processed" OR "fluorine-free" OR "PVDF-free" OR binder) AND (battery OR "lithium-ion" OR "Li-ion" OR cathode OR electrode OR "current collector")` | 2026-10-16 | 3 | 3 | — | ok |
| Q41 | openalex | OMP | `(polydopamine OR catechol OR "mussel-inspired" OR chitosan OR alginate OR "carboxymethyl chitosan") AND ("calcium carbonate" OR CaCO3 OR "amorphous calcium carbonate" OR biomineralization OR biomineralisation OR nacre) AND ("aqueous processing" OR "water-based" OR "aqueous binder" OR "aqueous slurry" OR "water-processed" OR "fluorine-free" OR "PVDF-free" OR binder)` | 2026-10-16 | 49 | 25 | — | ok |
| Q42 | openalex | OMP+C | `(polydopamine OR catechol OR "mussel-inspired" OR chitosan OR alginate OR "carboxymethyl chitosan") AND ("calcium carbonate" OR CaCO3 OR "amorphous calcium carbonate" OR biomineralization OR biomineralisation OR nacre) AND ("aqueous processing" OR "water-based" OR "aqueous binder" OR "aqueous slurry" OR "water-processed" OR "fluorine-free" OR "PVDF-free" OR binder) AND (battery OR "lithium-ion" OR "Li-ion" OR cathode OR electrode OR "current collector")` | 2026-10-16 | 2 | 2 | — | ok |
| Q43 | openalex | SOMP | `("aluminium current collector" OR "aluminum current collector" OR "Al current collector" OR "aluminium foil" OR "aluminum foil" OR "Al foil" OR alumina OR boehmite OR Al2O3 OR AlOOH) AND (polydopamine OR catechol OR "mussel-inspired" OR chitosan OR alginate OR "carboxymethyl chitosan") AND ("calcium carbonate" OR CaCO3 OR "amorphous calcium carbonate" OR biomineralization OR biomineralisation OR nacre) AND ("aqueous processing" OR "water-based" OR "aqueous binder" OR "aqueous slurry" OR "water-processed" OR "fluorine-free" OR "PVDF-free" OR binder)` | 2026-10-16 | 1 | 1 | — | ok |
| Q44 | openalex | SOMP+C | `("aluminium current collector" OR "aluminum current collector" OR "Al current collector" OR "aluminium foil" OR "aluminum foil" OR "Al foil" OR alumina OR boehmite OR Al2O3 OR AlOOH) AND (polydopamine OR catechol OR "mussel-inspired" OR chitosan OR alginate OR "carboxymethyl chitosan") AND ("calcium carbonate" OR CaCO3 OR "amorphous calcium carbonate" OR biomineralization OR biomineralisation OR nacre) AND ("aqueous processing" OR "water-based" OR "aqueous binder" OR "aqueous slurry" OR "water-processed" OR "fluorine-free" OR "PVDF-free" OR binder) AND (battery OR "lithium-ion" OR "Li-ion" OR cathode OR electrode OR "current collector")` | 2026-10-16 | 0 | 0 | — | ok |
| Q45 | arxiv | SO | `(all:"aluminium current collector" OR all:"aluminum current collector" OR all:"Al current collector" OR all:"aluminium foil" OR all:"aluminum foil" OR all:"Al foil" OR all:alumina OR all:boehmite OR all:Al2O3 OR all:AlOOH) AND (all:polydopamine OR all:catechol OR all:"mussel-inspired" OR all:chitosan OR all:alginate OR all:"carboxymethyl chitosan")` | 2026-10-16 | 0 | 0 | — | ok |
| Q46 | arxiv | SO+C | `(all:"aluminium current collector" OR all:"aluminum current collector" OR all:"Al current collector" OR all:"aluminium foil" OR all:"aluminum foil" OR all:"Al foil" OR all:alumina OR all:boehmite OR all:Al2O3 OR all:AlOOH) AND (all:polydopamine OR all:catechol OR all:"mussel-inspired" OR all:chitosan OR all:alginate OR all:"carboxymethyl chitosan") AND (all:battery OR all:"lithium-ion" OR all:"Li-ion" OR all:cathode OR all:electrode OR all:"current collector")` | 2026-10-16 | 0 | 0 | — | ok |
| Q47 | arxiv | SM | `(all:"aluminium current collector" OR all:"aluminum current collector" OR all:"Al current collector" OR all:"aluminium foil" OR all:"aluminum foil" OR all:"Al foil" OR all:alumina OR all:boehmite OR all:Al2O3 OR all:AlOOH) AND (all:"calcium carbonate" OR all:CaCO3 OR all:"amorphous calcium carbonate" OR all:biomineralization OR all:biomineralisation OR all:nacre)` | 2026-10-16 | 4 | 4 | — | ok |
| Q48 | arxiv | SM+C | `(all:"aluminium current collector" OR all:"aluminum current collector" OR all:"Al current collector" OR all:"aluminium foil" OR all:"aluminum foil" OR all:"Al foil" OR all:alumina OR all:boehmite OR all:Al2O3 OR all:AlOOH) AND (all:"calcium carbonate" OR all:CaCO3 OR all:"amorphous calcium carbonate" OR all:biomineralization OR all:biomineralisation OR all:nacre) AND (all:battery OR all:"lithium-ion" OR all:"Li-ion" OR all:cathode OR all:electrode OR all:"current collector")` | 2026-10-16 | 0 | 0 | — | ok |
| Q49 | arxiv | SP | `(all:"aluminium current collector" OR all:"aluminum current collector" OR all:"Al current collector" OR all:"aluminium foil" OR all:"aluminum foil" OR all:"Al foil" OR all:alumina OR all:boehmite OR all:Al2O3 OR all:AlOOH) AND (all:"aqueous processing" OR all:"water-based" OR all:"aqueous binder" OR all:"aqueous slurry" OR all:"water-processed" OR all:"fluorine-free" OR all:"PVDF-free" OR all:binder)` | 2026-10-16 | 12 | 12 | — | ok |
| Q50 | arxiv | SP+C | `(all:"aluminium current collector" OR all:"aluminum current collector" OR all:"Al current collector" OR all:"aluminium foil" OR all:"aluminum foil" OR all:"Al foil" OR all:alumina OR all:boehmite OR all:Al2O3 OR all:AlOOH) AND (all:"aqueous processing" OR all:"water-based" OR all:"aqueous binder" OR all:"aqueous slurry" OR all:"water-processed" OR all:"fluorine-free" OR all:"PVDF-free" OR all:binder) AND (all:battery OR all:"lithium-ion" OR all:"Li-ion" OR all:cathode OR all:electrode OR all:"current collector")` | 2026-10-16 | 2 | 2 | — | ok |
| Q51 | arxiv | OM | `(all:polydopamine OR all:catechol OR all:"mussel-inspired" OR all:chitosan OR all:alginate OR all:"carboxymethyl chitosan") AND (all:"calcium carbonate" OR all:CaCO3 OR all:"amorphous calcium carbonate" OR all:biomineralization OR all:biomineralisation OR all:nacre)` | 2026-10-16 | 1 | 1 | — | ok |
| Q52 | arxiv | OM+C | `(all:polydopamine OR all:catechol OR all:"mussel-inspired" OR all:chitosan OR all:alginate OR all:"carboxymethyl chitosan") AND (all:"calcium carbonate" OR all:CaCO3 OR all:"amorphous calcium carbonate" OR all:biomineralization OR all:biomineralisation OR all:nacre) AND (all:battery OR all:"lithium-ion" OR all:"Li-ion" OR all:cathode OR all:electrode OR all:"current collector")` | 2026-10-16 | 0 | 0 | — | ok |
| Q53 | arxiv | OP | `(all:polydopamine OR all:catechol OR all:"mussel-inspired" OR all:chitosan OR all:alginate OR all:"carboxymethyl chitosan") AND (all:"aqueous processing" OR all:"water-based" OR all:"aqueous binder" OR all:"aqueous slurry" OR all:"water-processed" OR all:"fluorine-free" OR all:"PVDF-free" OR all:binder)` | 2026-10-16 | 2 | 2 | — | ok |
| Q54 | arxiv | OP+C | `(all:polydopamine OR all:catechol OR all:"mussel-inspired" OR all:chitosan OR all:alginate OR all:"carboxymethyl chitosan") AND (all:"aqueous processing" OR all:"water-based" OR all:"aqueous binder" OR all:"aqueous slurry" OR all:"water-processed" OR all:"fluorine-free" OR all:"PVDF-free" OR all:binder) AND (all:battery OR all:"lithium-ion" OR all:"Li-ion" OR all:cathode OR all:electrode OR all:"current collector")` | 2026-10-16 | 0 | 0 | — | ok |
| Q55 | arxiv | MP | `(all:"calcium carbonate" OR all:CaCO3 OR all:"amorphous calcium carbonate" OR all:biomineralization OR all:biomineralisation OR all:nacre) AND (all:"aqueous processing" OR all:"water-based" OR all:"aqueous binder" OR all:"aqueous slurry" OR all:"water-processed" OR all:"fluorine-free" OR all:"PVDF-free" OR all:binder)` | 2026-10-16 | 0 | 0 | — | ok |
| Q56 | arxiv | MP+C | `(all:"calcium carbonate" OR all:CaCO3 OR all:"amorphous calcium carbonate" OR all:biomineralization OR all:biomineralisation OR all:nacre) AND (all:"aqueous processing" OR all:"water-based" OR all:"aqueous binder" OR all:"aqueous slurry" OR all:"water-processed" OR all:"fluorine-free" OR all:"PVDF-free" OR all:binder) AND (all:battery OR all:"lithium-ion" OR all:"Li-ion" OR all:cathode OR all:electrode OR all:"current collector")` | 2026-10-16 | 0 | 0 | — | ok |
| Q57 | arxiv | SOM | `(all:"aluminium current collector" OR all:"aluminum current collector" OR all:"Al current collector" OR all:"aluminium foil" OR all:"aluminum foil" OR all:"Al foil" OR all:alumina OR all:boehmite OR all:Al2O3 OR all:AlOOH) AND (all:polydopamine OR all:catechol OR all:"mussel-inspired" OR all:chitosan OR all:alginate OR all:"carboxymethyl chitosan") AND (all:"calcium carbonate" OR all:CaCO3 OR all:"amorphous calcium carbonate" OR all:biomineralization OR all:biomineralisation OR all:nacre)` | 2026-10-16 | 0 | 0 | — | ok |
| Q58 | arxiv | SOM+C | `(all:"aluminium current collector" OR all:"aluminum current collector" OR all:"Al current collector" OR all:"aluminium foil" OR all:"aluminum foil" OR all:"Al foil" OR all:alumina OR all:boehmite OR all:Al2O3 OR all:AlOOH) AND (all:polydopamine OR all:catechol OR all:"mussel-inspired" OR all:chitosan OR all:alginate OR all:"carboxymethyl chitosan") AND (all:"calcium carbonate" OR all:CaCO3 OR all:"amorphous calcium carbonate" OR all:biomineralization OR all:biomineralisation OR all:nacre) AND (all:battery OR all:"lithium-ion" OR all:"Li-ion" OR all:cathode OR all:electrode OR all:"current collector")` | 2026-10-16 | 0 | 0 | — | ok |
| Q59 | arxiv | SOP | `(all:"aluminium current collector" OR all:"aluminum current collector" OR all:"Al current collector" OR all:"aluminium foil" OR all:"aluminum foil" OR all:"Al foil" OR all:alumina OR all:boehmite OR all:Al2O3 OR all:AlOOH) AND (all:polydopamine OR all:catechol OR all:"mussel-inspired" OR all:chitosan OR all:alginate OR all:"carboxymethyl chitosan") AND (all:"aqueous processing" OR all:"water-based" OR all:"aqueous binder" OR all:"aqueous slurry" OR all:"water-processed" OR all:"fluorine-free" OR all:"PVDF-free" OR all:binder)` | 2026-10-16 | 0 | 0 | — | ok |
| Q60 | arxiv | SOP+C | `(all:"aluminium current collector" OR all:"aluminum current collector" OR all:"Al current collector" OR all:"aluminium foil" OR all:"aluminum foil" OR all:"Al foil" OR all:alumina OR all:boehmite OR all:Al2O3 OR all:AlOOH) AND (all:polydopamine OR all:catechol OR all:"mussel-inspired" OR all:chitosan OR all:alginate OR all:"carboxymethyl chitosan") AND (all:"aqueous processing" OR all:"water-based" OR all:"aqueous binder" OR all:"aqueous slurry" OR all:"water-processed" OR all:"fluorine-free" OR all:"PVDF-free" OR all:binder) AND (all:battery OR all:"lithium-ion" OR all:"Li-ion" OR all:cathode OR all:electrode OR all:"current collector")` | 2026-10-16 | 0 | 0 | — | ok |
| Q61 | arxiv | SMP | `(all:"aluminium current collector" OR all:"aluminum current collector" OR all:"Al current collector" OR all:"aluminium foil" OR all:"aluminum foil" OR all:"Al foil" OR all:alumina OR all:boehmite OR all:Al2O3 OR all:AlOOH) AND (all:"calcium carbonate" OR all:CaCO3 OR all:"amorphous calcium carbonate" OR all:biomineralization OR all:biomineralisation OR all:nacre) AND (all:"aqueous processing" OR all:"water-based" OR all:"aqueous binder" OR all:"aqueous slurry" OR all:"water-processed" OR all:"fluorine-free" OR all:"PVDF-free" OR all:binder)` | 2026-10-16 | 0 | 0 | — | ok |
| Q62 | arxiv | SMP+C | `(all:"aluminium current collector" OR all:"aluminum current collector" OR all:"Al current collector" OR all:"aluminium foil" OR all:"aluminum foil" OR all:"Al foil" OR all:alumina OR all:boehmite OR all:Al2O3 OR all:AlOOH) AND (all:"calcium carbonate" OR all:CaCO3 OR all:"amorphous calcium carbonate" OR all:biomineralization OR all:biomineralisation OR all:nacre) AND (all:"aqueous processing" OR all:"water-based" OR all:"aqueous binder" OR all:"aqueous slurry" OR all:"water-processed" OR all:"fluorine-free" OR all:"PVDF-free" OR all:binder) AND (all:battery OR all:"lithium-ion" OR all:"Li-ion" OR all:cathode OR all:electrode OR all:"current collector")` | 2026-10-16 | 0 | 0 | — | ok |
| Q63 | arxiv | OMP | `(all:polydopamine OR all:catechol OR all:"mussel-inspired" OR all:chitosan OR all:alginate OR all:"carboxymethyl chitosan") AND (all:"calcium carbonate" OR all:CaCO3 OR all:"amorphous calcium carbonate" OR all:biomineralization OR all:biomineralisation OR all:nacre) AND (all:"aqueous processing" OR all:"water-based" OR all:"aqueous binder" OR all:"aqueous slurry" OR all:"water-processed" OR all:"fluorine-free" OR all:"PVDF-free" OR all:binder)` | 2026-10-16 | 0 | 0 | — | ok |
| Q64 | arxiv | OMP+C | `(all:polydopamine OR all:catechol OR all:"mussel-inspired" OR all:chitosan OR all:alginate OR all:"carboxymethyl chitosan") AND (all:"calcium carbonate" OR all:CaCO3 OR all:"amorphous calcium carbonate" OR all:biomineralization OR all:biomineralisation OR all:nacre) AND (all:"aqueous processing" OR all:"water-based" OR all:"aqueous binder" OR all:"aqueous slurry" OR all:"water-processed" OR all:"fluorine-free" OR all:"PVDF-free" OR all:binder) AND (all:battery OR all:"lithium-ion" OR all:"Li-ion" OR all:cathode OR all:electrode OR all:"current collector")` | 2026-10-16 | 0 | 0 | — | ok |
| Q65 | arxiv | SOMP | `(all:"aluminium current collector" OR all:"aluminum current collector" OR all:"Al current collector" OR all:"aluminium foil" OR all:"aluminum foil" OR all:"Al foil" OR all:alumina OR all:boehmite OR all:Al2O3 OR all:AlOOH) AND (all:polydopamine OR all:catechol OR all:"mussel-inspired" OR all:chitosan OR all:alginate OR all:"carboxymethyl chitosan") AND (all:"calcium carbonate" OR all:CaCO3 OR all:"amorphous calcium carbonate" OR all:biomineralization OR all:biomineralisation OR all:nacre) AND (all:"aqueous processing" OR all:"water-based" OR all:"aqueous binder" OR all:"aqueous slurry" OR all:"water-processed" OR all:"fluorine-free" OR all:"PVDF-free" OR all:binder)` | 2026-10-16 | 0 | 0 | — | ok |
| Q66 | arxiv | SOMP+C | `(all:"aluminium current collector" OR all:"aluminum current collector" OR all:"Al current collector" OR all:"aluminium foil" OR all:"aluminum foil" OR all:"Al foil" OR all:alumina OR all:boehmite OR all:Al2O3 OR all:AlOOH) AND (all:polydopamine OR all:catechol OR all:"mussel-inspired" OR all:chitosan OR all:alginate OR all:"carboxymethyl chitosan") AND (all:"calcium carbonate" OR all:CaCO3 OR all:"amorphous calcium carbonate" OR all:biomineralization OR all:biomineralisation OR all:nacre) AND (all:"aqueous processing" OR all:"water-based" OR all:"aqueous binder" OR all:"aqueous slurry" OR all:"water-processed" OR all:"fluorine-free" OR all:"PVDF-free" OR all:binder) AND (all:battery OR all:"lithium-ion" OR all:"Li-ion" OR all:cathode OR all:electrode OR all:"current collector")` | 2026-10-16 | 0 | 0 | — | ok (2 attempts; last shown) |
| Q67 | openaire | SO | `("aluminium current collector" OR "aluminum current collector" OR "Al current collector" OR "aluminium foil" OR "aluminum foil" OR "Al foil" OR alumina OR boehmite OR Al2O3 OR AlOOH) AND (polydopamine OR catechol OR "mussel-inspired" OR chitosan OR alginate OR "carboxymethyl chitosan")` | 2026-10-16 | — | 0 | — | HTTP 400 (boolean form refused) |
| Q68 | openaire | SO/k1 | `aluminium current collector polydopamine` | 2026-10-16 | 0 | 0 | — | ok |
| Q69 | openaire | SO/k2 | `aluminum foil catechol` | 2026-10-16 | 2 | 2 | 10.1002/app.53530 | ok |
| Q70 | openaire | SO/k3 | `boehmite chitosan` | 2026-10-16 | 24 | 24 | — | ok |
| Q71 | openaire | SM/k1 | `aluminium current collector calcium carbonate` | 2026-10-16 | 0 | 0 | — | ok |
| Q72 | openaire | SM/k2 | `aluminum foil amorphous calcium carbonate` | 2026-10-16 | 0 | 0 | — | ok |
| Q73 | openaire | SM/k3 | `boehmite biomineralization` | 2026-10-16 | 4 | 4 | — | ok |
| Q74 | openaire | SP/k1 | `aluminium current collector aqueous binder` | 2026-10-16 | 8 | 8 | — | ok |
| Q75 | openaire | SP/k2 | `aluminum foil water-based` | 2026-10-16 | 241 | 25 | 10.1016/j.jpowsour.2013.10.039 | ok |
| Q76 | openaire | SP/k3 | `boehmite fluorine-free` | 2026-10-16 | 6 | 6 | — | ok |
| Q77 | openaire | OM/k1 | `polydopamine calcium carbonate` | 2026-10-16 | 36 | 25 | 10.1002/cssc.201700616, 10.1007/s11998-016-9898-x, 10.1021/cg301759t, 10.3390/coatings13020306 | ok |
| Q78 | openaire | OM/k2 | `catechol amorphous calcium carbonate` | 2026-10-16 | 2 | 2 | 10.1002/cssc.201700616 | ok |
| Q79 | openaire | OM/k3 | `chitosan biomineralization` | 2026-10-16 | 350 | 25 | — | ok |
| Q80 | openaire | OP/k1 | `polydopamine aqueous binder` | 2026-10-16 | 17 | 17 | — | ok |
| Q81 | openaire | OP/k2 | `catechol water-based` | 2026-10-16 | 994 | 25 | — | ok |
| Q82 | openaire | OP/k3 | `chitosan fluorine-free` | 2026-10-16 | 40 | 25 | — | ok |
| Q83 | openaire | MP/k1 | `calcium carbonate aqueous binder` | 2026-10-16 | 41 | 25 | — | ok |
| Q84 | openaire | MP/k2 | `amorphous calcium carbonate water-based` | 2026-10-16 | 130 | 25 | — | ok |
| Q85 | openaire | MP/k3 | `biomineralization fluorine-free` | 2026-10-16 | 3 | 3 | — | ok |
| Q86 | openaire | SOM/k1 | `aluminium current collector polydopamine calcium carbonate` | 2026-10-16 | 0 | 0 | — | ok |
| Q87 | openaire | SOM/k2 | `aluminum foil catechol amorphous calcium carbonate` | 2026-10-16 | 0 | 0 | — | ok |
| Q88 | openaire | SOM/k3 | `boehmite chitosan biomineralization` | 2026-10-16 | 0 | 0 | — | ok |
| Q89 | openaire | SOP/k1 | `aluminium current collector polydopamine aqueous binder` | 2026-10-16 | 0 | 0 | — | ok |
| Q90 | openaire | SOP/k2 | `aluminum foil catechol water-based` | 2026-10-16 | 0 | 0 | — | ok |
| Q91 | openaire | SOP/k3 | `boehmite chitosan fluorine-free` | 2026-10-16 | 0 | 0 | — | ok |
| Q92 | openaire | SMP/k1 | `aluminium current collector calcium carbonate aqueous binder` | 2026-10-16 | 0 | 0 | — | ok |
| Q93 | openaire | SMP/k2 | `aluminum foil amorphous calcium carbonate water-based` | 2026-10-16 | 0 | 0 | — | ok |
| Q94 | openaire | SMP/k3 | `boehmite biomineralization fluorine-free` | 2026-10-16 | 0 | 0 | — | ok |
| Q95 | openaire | OMP/k1 | `polydopamine calcium carbonate aqueous binder` | 2026-10-16 | 0 | 0 | — | ok |
| Q96 | openaire | OMP/k2 | `catechol amorphous calcium carbonate water-based` | 2026-10-16 | 0 | 0 | — | ok |
| Q97 | openaire | OMP/k3 | `chitosan biomineralization fluorine-free` | 2026-10-16 | 0 | 0 | — | ok |
| Q98 | openaire | SOMP/k1 | `aluminium current collector polydopamine calcium carbonate aqueous binder` | 2026-10-16 | 0 | 0 | — | ok |
| Q99 | openaire | SOMP/k2 | `aluminum foil catechol amorphous calcium carbonate water-based` | 2026-10-16 | 0 | 0 | — | ok |
| Q100 | openaire | SOMP/k3 | `boehmite chitosan biomineralization fluorine-free` | 2026-10-16 | 0 | 0 | — | ok |
| Q101 | crossref | SO/k1 | `aluminium current collector polydopamine` | 2026-10-16 | 1589967 | 25 | 10.1038/srep30945, 10.1149/ma2016-03/2/589 | ok |
| Q102 | crossref | SO/k2 | `aluminum foil catechol` | 2026-10-16 | 199991 | 25 | — | ok |
| Q103 | crossref | SO/k3 | `boehmite chitosan` | 2026-10-16 | 99600 | 25 | — | ok |
| Q104 | crossref | SM/k1 | `aluminium current collector calcium carbonate` | 2026-10-16 | 1928492 | 25 | 10.2139/ssrn.4698483 | ok |
| Q105 | crossref | SM/k2 | `aluminum foil amorphous calcium carbonate` | 2026-10-16 | 650634 | 25 | — | ok |
| Q106 | crossref | SM/k3 | `boehmite biomineralization` | 2026-10-16 | 7073 | 25 | — | ok |
| Q107 | crossref | SP/k1 | `aluminium current collector aqueous binder` | 2026-10-16 | 1908705 | 25 | — | ok |
| Q108 | crossref | SP/k2 | `aluminum foil water-based` | 2026-10-16 | 8684965 | 25 | — | ok |
| Q109 | crossref | SP/k3 | `boehmite fluorine-free` | 2026-10-16 | 891875 | 25 | — | ok |
| Q110 | crossref | OM/k1 | `polydopamine calcium carbonate` | 2026-10-16 | 361589 | 25 | — | ok |
| Q111 | crossref | OM/k2 | `catechol amorphous calcium carbonate` | 2026-10-16 | 472738 | 25 | — | ok |
| Q112 | crossref | OM/k3 | `chitosan biomineralization` | 2026-10-16 | 102868 | 25 | — | ok |
| Q113 | crossref | OP/k1 | `polydopamine aqueous binder` | 2026-10-16 | 339386 | 25 | — | ok |
| Q114 | crossref | OP/k2 | `catechol water-based` | 2026-10-16 | 8517392 | 25 | — | ok |
| Q115 | crossref | OP/k3 | `chitosan fluorine-free` | 2026-10-16 | 987112 | 25 | — | ok |
| Q116 | crossref | MP/k1 | `calcium carbonate aqueous binder` | 2026-10-16 | 680074 | 25 | — | ok |
| Q117 | crossref | MP/k2 | `amorphous calcium carbonate water-based` | 2026-10-16 | 8940212 | 25 | — | ok |
| Q118 | crossref | MP/k3 | `biomineralization fluorine-free` | 2026-10-16 | 895199 | 25 | — | ok |
| Q119 | crossref | SOM/k1 | `aluminium current collector polydopamine calcium carbonate` | 2026-10-16 | 1937461 | 25 | 10.1038/srep30945, 10.2139/ssrn.4698483 | ok |
| Q120 | crossref | SOM/k2 | `aluminum foil catechol amorphous calcium carbonate` | 2026-10-16 | 660497 | 25 | — | ok |
| Q121 | crossref | SOM/k3 | `boehmite chitosan biomineralization` | 2026-10-16 | 104736 | 25 | — | ok |
| Q122 | crossref | SOP/k1 | `aluminium current collector polydopamine aqueous binder` | 2026-10-16 | 1917622 | 25 | — | ok |
| Q123 | crossref | SOP/k2 | `aluminum foil catechol water-based` | 2026-10-16 | 8693901 | 25 | — | ok |
| Q124 | crossref | SOP/k3 | `boehmite chitosan fluorine-free` | 2026-10-16 | 988941 | 25 | — | ok |
| Q125 | crossref | SMP/k1 | `aluminium current collector calcium carbonate aqueous binder` | 2026-10-16 | 2253360 | 25 | — | ok |
| Q126 | crossref | SMP/k2 | `aluminum foil amorphous calcium carbonate water-based` | 2026-10-16 | 9114642 | 25 | — | ok |
| Q127 | crossref | SMP/k3 | `boehmite biomineralization fluorine-free` | 2026-10-16 | 897044 | 25 | — | ok |
| Q128 | crossref | OMP/k1 | `polydopamine calcium carbonate aqueous binder` | 2026-10-16 | 688956 | 25 | — | ok |
| Q129 | crossref | OMP/k2 | `catechol amorphous calcium carbonate water-based` | 2026-10-16 | 8949119 | 25 | — | ok |
| Q130 | crossref | OMP/k3 | `chitosan biomineralization fluorine-free` | 2026-10-16 | 992228 | 25 | — | ok |
| Q131 | crossref | SOMP/k1 | `aluminium current collector polydopamine calcium carbonate aqueous binder` | 2026-10-16 | 2262205 | 25 | — | ok |
| Q132 | crossref | SOMP/k2 | `aluminum foil catechol amorphous calcium carbonate water-based` | 2026-10-16 | 9123537 | 25 | — | ok |
| Q133 | crossref | SOMP/k3 | `boehmite chitosan biomineralization fluorine-free` | 2026-10-16 | 994057 | 25 | — | ok |
| Q134 | chemrxiv | SO/k1 | `aluminium current collector polydopamine` | 2026-10-16 | — | 0 | — | HTTP 403 (2 attempts; last shown) |
| Q135 | chemrxiv | SO/k2 | `aluminum foil catechol` | 2026-10-16 | — | 0 | — | HTTP 403 |
| Q136 | chemrxiv | SO/k3 | `boehmite chitosan` | 2026-10-16 | — | 0 | — | HTTP 403 |
| Q137 | chemrxiv | SM/k1 | `aluminium current collector calcium carbonate` | 2026-10-16 | — | 0 | — | HTTP 403 |
| Q138 | chemrxiv | SM/k2 | `aluminum foil amorphous calcium carbonate` | 2026-10-16 | — | 0 | — | HTTP 403 |
| Q139 | chemrxiv | SM/k3 | `boehmite biomineralization` | 2026-10-16 | — | 0 | — | HTTP 403 |
| Q140 | chemrxiv | SP/k1 | `aluminium current collector aqueous binder` | 2026-10-16 | — | 0 | — | HTTP 403 |
| Q141 | chemrxiv | SP/k2 | `aluminum foil water-based` | 2026-10-16 | — | 0 | — | HTTP 403 |
| Q142 | chemrxiv | SP/k3 | `boehmite fluorine-free` | 2026-10-16 | — | 0 | — | HTTP 403 |
| Q143 | chemrxiv | OM/k1 | `polydopamine calcium carbonate` | 2026-10-16 | — | 0 | — | HTTP 403 |
| Q144 | chemrxiv | OM/k2 | `catechol amorphous calcium carbonate` | 2026-10-16 | — | 0 | — | HTTP 403 |
| Q145 | chemrxiv | OM/k3 | `chitosan biomineralization` | 2026-10-16 | — | 0 | — | HTTP 403 |
| Q146 | chemrxiv | OP/k1 | `polydopamine aqueous binder` | 2026-10-16 | — | 0 | — | HTTP 403 |
| Q147 | chemrxiv | OP/k2 | `catechol water-based` | 2026-10-16 | — | 0 | — | HTTP 403 |
| Q148 | chemrxiv | OP/k3 | `chitosan fluorine-free` | 2026-10-16 | — | 0 | — | HTTP 403 |
| Q149 | chemrxiv | MP/k1 | `calcium carbonate aqueous binder` | 2026-10-16 | — | 0 | — | HTTP 403 |
| Q150 | chemrxiv | MP/k2 | `amorphous calcium carbonate water-based` | 2026-10-16 | — | 0 | — | HTTP 403 |
| Q151 | chemrxiv | MP/k3 | `biomineralization fluorine-free` | 2026-10-16 | — | 0 | — | HTTP 403 |
| Q152 | chemrxiv | SOM/k1 | `aluminium current collector polydopamine calcium carbonate` | 2026-10-16 | — | 0 | — | HTTP 403 |
| Q153 | chemrxiv | SOM/k2 | `aluminum foil catechol amorphous calcium carbonate` | 2026-10-16 | — | 0 | — | HTTP 403 |
| Q154 | chemrxiv | SOM/k3 | `boehmite chitosan biomineralization` | 2026-10-16 | — | 0 | — | HTTP 403 |
| Q155 | chemrxiv | SOP/k1 | `aluminium current collector polydopamine aqueous binder` | 2026-10-16 | — | 0 | — | HTTP 403 |
| Q156 | chemrxiv | SOP/k2 | `aluminum foil catechol water-based` | 2026-10-16 | — | 0 | — | HTTP 403 |
| Q157 | chemrxiv | SOP/k3 | `boehmite chitosan fluorine-free` | 2026-10-16 | — | 0 | — | HTTP 403 |
| Q158 | chemrxiv | SMP/k1 | `aluminium current collector calcium carbonate aqueous binder` | 2026-10-16 | — | 0 | — | HTTP 403 |
| Q159 | chemrxiv | SMP/k2 | `aluminum foil amorphous calcium carbonate water-based` | 2026-10-16 | — | 0 | — | HTTP 403 |
| Q160 | chemrxiv | SMP/k3 | `boehmite biomineralization fluorine-free` | 2026-10-16 | — | 0 | — | HTTP 403 |
| Q161 | chemrxiv | OMP/k1 | `polydopamine calcium carbonate aqueous binder` | 2026-10-16 | — | 0 | — | HTTP 403 |
| Q162 | chemrxiv | OMP/k2 | `catechol amorphous calcium carbonate water-based` | 2026-10-16 | — | 0 | — | HTTP 403 |
| Q163 | chemrxiv | OMP/k3 | `chitosan biomineralization fluorine-free` | 2026-10-16 | — | 0 | — | HTTP 403 |
| Q164 | chemrxiv | SOMP/k1 | `aluminium current collector polydopamine calcium carbonate aqueous binder` | 2026-10-16 | — | 0 | — | HTTP 403 |
| Q165 | chemrxiv | SOMP/k2 | `aluminum foil catechol amorphous calcium carbonate water-based` | 2026-10-16 | — | 0 | — | HTTP 403 |
| Q166 | chemrxiv | SOMP/k3 | `boehmite chitosan biomineralization fluorine-free` | 2026-10-16 | — | 0 | — | HTTP 403 |
| Q167 | lens | SO | `aluminium current collector polydopamine` | 2026-10-16 | — | 0 | — | no LENS_TOKEN: skipped |
| Q168 | lens | SO | `aluminum foil catechol` | 2026-10-16 | — | 0 | — | no LENS_TOKEN: skipped |
| Q169 | lens | SO | `boehmite chitosan` | 2026-10-16 | — | 0 | — | no LENS_TOKEN: skipped |
| Q170 | lens | SM | `aluminium current collector calcium carbonate` | 2026-10-16 | — | 0 | — | no LENS_TOKEN: skipped |
| Q171 | lens | SM | `aluminum foil amorphous calcium carbonate` | 2026-10-16 | — | 0 | — | no LENS_TOKEN: skipped |
| Q172 | lens | SM | `boehmite biomineralization` | 2026-10-16 | — | 0 | — | no LENS_TOKEN: skipped |
| Q173 | lens | SP | `aluminium current collector aqueous binder` | 2026-10-16 | — | 0 | — | no LENS_TOKEN: skipped |
| Q174 | lens | SP | `aluminum foil water-based` | 2026-10-16 | — | 0 | — | no LENS_TOKEN: skipped |
| Q175 | lens | SP | `boehmite fluorine-free` | 2026-10-16 | — | 0 | — | no LENS_TOKEN: skipped |
| Q176 | lens | OM | `polydopamine calcium carbonate` | 2026-10-16 | — | 0 | — | no LENS_TOKEN: skipped |
| Q177 | lens | OM | `catechol amorphous calcium carbonate` | 2026-10-16 | — | 0 | — | no LENS_TOKEN: skipped |
| Q178 | lens | OM | `chitosan biomineralization` | 2026-10-16 | — | 0 | — | no LENS_TOKEN: skipped |
| Q179 | lens | OP | `polydopamine aqueous binder` | 2026-10-16 | — | 0 | — | no LENS_TOKEN: skipped |
| Q180 | lens | OP | `catechol water-based` | 2026-10-16 | — | 0 | — | no LENS_TOKEN: skipped |
| Q181 | lens | OP | `chitosan fluorine-free` | 2026-10-16 | — | 0 | — | no LENS_TOKEN: skipped |
| Q182 | lens | MP | `calcium carbonate aqueous binder` | 2026-10-16 | — | 0 | — | no LENS_TOKEN: skipped |
| Q183 | lens | MP | `amorphous calcium carbonate water-based` | 2026-10-16 | — | 0 | — | no LENS_TOKEN: skipped |
| Q184 | lens | MP | `biomineralization fluorine-free` | 2026-10-16 | — | 0 | — | no LENS_TOKEN: skipped |
| Q185 | lens | SOM | `aluminium current collector polydopamine calcium carbonate` | 2026-10-16 | — | 0 | — | no LENS_TOKEN: skipped |
| Q186 | lens | SOM | `aluminum foil catechol amorphous calcium carbonate` | 2026-10-16 | — | 0 | — | no LENS_TOKEN: skipped |
| Q187 | lens | SOM | `boehmite chitosan biomineralization` | 2026-10-16 | — | 0 | — | no LENS_TOKEN: skipped |
| Q188 | lens | SOP | `aluminium current collector polydopamine aqueous binder` | 2026-10-16 | — | 0 | — | no LENS_TOKEN: skipped |
| Q189 | lens | SOP | `aluminum foil catechol water-based` | 2026-10-16 | — | 0 | — | no LENS_TOKEN: skipped |
| Q190 | lens | SOP | `boehmite chitosan fluorine-free` | 2026-10-16 | — | 0 | — | no LENS_TOKEN: skipped |
| Q191 | lens | SMP | `aluminium current collector calcium carbonate aqueous binder` | 2026-10-16 | — | 0 | — | no LENS_TOKEN: skipped |
| Q192 | lens | SMP | `aluminum foil amorphous calcium carbonate water-based` | 2026-10-16 | — | 0 | — | no LENS_TOKEN: skipped |
| Q193 | lens | SMP | `boehmite biomineralization fluorine-free` | 2026-10-16 | — | 0 | — | no LENS_TOKEN: skipped |
| Q194 | lens | OMP | `polydopamine calcium carbonate aqueous binder` | 2026-10-16 | — | 0 | — | no LENS_TOKEN: skipped |
| Q195 | lens | OMP | `catechol amorphous calcium carbonate water-based` | 2026-10-16 | — | 0 | — | no LENS_TOKEN: skipped |
| Q196 | lens | OMP | `chitosan biomineralization fluorine-free` | 2026-10-16 | — | 0 | — | no LENS_TOKEN: skipped |
| Q197 | lens | SOMP | `aluminium current collector polydopamine calcium carbonate aqueous binder` | 2026-10-16 | — | 0 | — | no LENS_TOKEN: skipped |
| Q198 | lens | SOMP | `aluminum foil catechol amorphous calcium carbonate water-based` | 2026-10-16 | — | 0 | — | no LENS_TOKEN: skipped |
| Q199 | lens | SOMP | `boehmite chitosan biomineralization fluorine-free` | 2026-10-16 | — | 0 | — | no LENS_TOKEN: skipped |

**Follow-up queries** (not part of the designed coverage). The N tags are novelty follow-ups. The B and X tags are the contrary-evidence searches for `lit/contrary.md`, logged here so that every search of this session is in one place.

| # | Tag | Route | Query string | Date | Hits reported | Screened | Retained DOIs |
|---|---|---|---|---|---|---|---|
| T1 | B1 | openalex | `Osorio-Celestino calcium carbonate aluminium corrosion` | 2026-10-16 | 0 | 0 | — |
| T2 | B1 | openalex | `"calcium carbonate" AND aluminum AND corrosion AND scaling` | 2026-10-16 | 13 | 13 | 10.1021/acsomega.0c01538 |
| T3 | B1 | crossref | `Osorio-Celestino calcium carbonate scaling aluminium corrosion 2020` | 2026-10-16 | 9291196 | 25 | 10.1021/acsomega.0c01538 |
| T4 | B2 | openalex | `"Pourbaix" AND (limitations OR kinetics OR metastable) AND (corrosion OR stability)` | 2026-10-16 | 116 | 25 | — |
| T5 | B2 | openalex | `"Pourbaix diagram" AND aluminum` | 2026-10-16 | 44 | 25 | — |
| T6 | B2 | openalex | `"electrochemical stability" AND "Pourbaix" AND metastable AND "first-principles"` | 2026-10-16 | 0 | 0 | — |
| T7 | B3 | openalex | `catechol AND calcium AND (binding OR complexation) AND (pKa OR "stability constant")` | 2026-10-16 | 2 | 2 | — |
| T8 | B3 | openalex | `(catecholate OR catechol) AND calcium AND carboxylate AND binding` | 2026-10-16 | 0 | 0 | — |
| T9 | B3 | openalex | `catechol AND calcium AND complex AND pH` | 2026-10-16 | 7 | 7 | — |
| T10 | B3 | openalex | `(DOPA OR catechol) AND (Ca2+ OR calcium) AND (binding OR coordination) AND (mussel OR adhesive)` | 2026-10-16 | 11 | 11 | — |
| T11 | B3 | openalex | `polydopamine AND calcium AND (adsorption OR binding OR chelation)` | 2026-10-16 | 50 | 25 | 10.3390/coatings13020306 |
| T12 | B4 | openalex | `polydopamine AND (oxidation OR "oxidative stability" OR "electrochemical stability") AND (cathode OR "high voltage")` | 2026-10-16 | 108 | 25 | — |
| T13 | B4 | openalex | `polydopamine AND "high voltage" AND cathode AND binder` | 2026-10-16 | 1 | 1 | — |
| T14 | B3 | openalex | `catechol AND ("acid dissociation" OR pKa OR "acidity constant") AND (determination OR spectrophotometric OR potentiometric)` | 2026-10-16 | 20 | 20 | — |
| T15 | B3 | openalex | `"catechol" AND "calcium" AND "stability constant"` | 2026-10-16 | 2 | 2 | — |
| T16 | B5 | openalex | `"amorphous calcium carbonate" AND (crystallization OR transformation) AND (kinetics OR lifetime) AND (vaterite OR calcite)` | 2026-10-16 | 52 | 25 | — |
| T17 | B5 | openalex | `"amorphous calcium carbonate" AND dehydration AND crystallization` | 2026-10-16 | 35 | 25 | — |
| T18 | B7 | openalex | `"prenucleation clusters" AND "calcium carbonate"` | 2026-10-16 | 47 | 25 | — |
| T19 | B7 | openalex | `"classical nucleation theory" AND ("calcium carbonate" OR CaCO3) AND (non-classical OR limitations OR validity)` | 2026-10-16 | 10 | 10 | — |
| T20 | B7 | openalex | `"crystallization by particle attachment"` | 2026-10-16 | 50 | 25 | — |
| T21 | B8 | openalex | `polydopamine AND structure AND (elucidating OR "never-ending" OR "self-assembly" OR controversy)` | 2026-10-16 | 273 | 25 | — |
| T22 | B7 | crossref | `Gebauer Volkel Colfen 2008 stable prenucleation calcium carbonate clusters Science` | 2026-10-16 | 315703 | 25 | — |
| T23 | B7 | crossref | `Nielsen Aloni De Yoreo 2014 in situ TEM imaging of CaCO3 nucleation direct and indirect pathways` | 2026-10-16 | 629763 | 25 | — |
| T24 | B7 | crossref | `Hu Nielsen De Yoreo thermodynamics of calcite nucleation at organic interfaces classical vs non-classical` | 2026-10-16 | 605735 | 25 | — |
| T25 | B6 | openalex | `"calcium carbonate" AND ("band gap" OR "electronic structure") AND (insulator OR insulating)` | 2026-10-16 | 2 | 2 | — |
| T26 | B6 | openalex | `"current collector" AND coating AND ("contact resistance" OR "interfacial resistance") AND aluminum` | 2026-10-16 | 23 | 23 | — |
| T27 | X1 | openalex | `(aqueous OR water-based) AND (cathode OR NMC OR LiNi) AND "aluminum" AND corrosion AND (slurry OR processing)` | 2026-10-16 | 147 | 25 | 10.1002/maco.201608843, 10.1007/s10853-014-8028-3, 10.1016/j.electacta.2019.05.141, 10.1016/j.jpowsour.2013.10.039, 10.1021/acsami.8b03657, 10.1149/06418.0013ecst |
| T28 | X1 | openalex | `("aqueous processing" OR "water-based") AND "current collector" AND corrosion AND (pH OR alkaline)` | 2026-10-16 | 35 | 25 | 10.1002/celc.202500327, 10.1007/s10853-014-8028-3 |
| T29 | X2 | openalex | `(LiTFSI OR "fluorine-free" OR "imide") AND aluminum AND ("current collector") AND (corrosion OR "anodic dissolution")` | 2026-10-16 | 110 | 25 | 10.1016/j.ensm.2025.104569 |
| T30 | N1 | openalex | `polydopamine AND ("aluminum foil" OR "aluminium foil" OR "Al foil" OR "aluminum current collector" OR "aluminium current collector")` | 2026-10-16 | 4 | 4 | 10.1002/app.53530 |
| T31 | N1 | openalex | `"calcium carbonate" AND (coating OR film OR "conversion coating") AND (aluminum OR aluminium) AND "corrosion protection"` | 2026-10-16 | 7 | 7 | — |
| T32 | N1 | openalex | `(nacre OR biomineralization OR "calcium carbonate") AND ("current collector" OR interphase OR "solid electrolyte interphase") AND battery` | 2026-10-16 | 13 | 13 | 10.1016/j.nanoen.2022.107830, 10.1557/s43581-025-00131-8 |
| T33 | N1 | openalex | `(alginate OR chitosan OR polydopamine OR catechol) AND binder AND ("aluminum current collector" OR "aluminium current collector" OR "Al current collector") AND corrosion` | 2026-10-16 | 4 | 4 | 10.1021/acsami.8b03657, 10.1149/ma2014-02/1/16 |
| T34 | N2 | openalex | `(catechol OR dopamine OR DOPA OR polydopamine) AND (alumina OR Al2O3 OR boehmite OR "aluminum oxide") AND ("density functional" OR DFT OR "molecular dynamics" OR "first-principles")` | 2026-10-16 | 14 | 14 | 10.1021/acs.jpcb.9b04473, 10.1021/acs.langmuir.5c02791, 10.1021/jp512780s |
| T35 | N2 | openalex | `("calcium carbonate" OR calcite OR "amorphous calcium carbonate") AND (polydopamine OR catechol OR chitosan OR alginate) AND ("molecular dynamics" OR "density functional" OR "free energy")` | 2026-10-16 | 24 | 24 | 10.1016/j.carbpol.2019.115054, 10.1016/j.gca.2006.04.023, 10.3390/coatings13020306 |
| T36 | N2 | openalex | `(polydopamine OR dopamine) AND "calcium carbonate" AND (mineralization OR nucleation) AND (film OR surface OR substrate)` | 2026-10-16 | 5 | 5 | 10.1002/cssc.201700616, 10.1007/s11998-016-9898-x |

## Screening result

- **Depth of screening.**
  - **Screened in full.** On the two boolean routes with abstracts (Semantic Scholar and OpenAlex), every record was screened for every combination that returned at most 25 hits:
    - the quadruple SOMP and SOMP+C (Semantic Scholar 0 and 0; OpenAlex 1 and 0, Q21–Q22 and Q43–Q44);
    - SOM (17 and 20) and SOM+C (1 and 0);
    - SMP+C (0 and 3) and OMP+C (1 and 2);
    - on Semantic Scholar also SOP+C (11) and MP+C (24).
  - **Screened in part.** For larger combinations, the 25 top-ranked records per route were screened.
- **Quadruple and S-O-M triple.** No record in either set concerns an aluminium current collector:
  - the single OpenAlex SOMP hit is a ceramics-forming paper (10.1016/j.jeurceramsoc.2016.07.020, abstract);
  - the SOM hits are nacre-like structural composites, alumina-platelet films and immobilisation supports (Q13–Q14 and Q35–Q36).
- **No combined chain.** No retained record evaluates, or reports experimentally, the combined chain (C1 → C2 → C3 → C4/C5) on aluminium or on any battery current collector, in either regime.
- **Separate links.** The links have been reported separately. The table below gives the closest of those reports.

## Closest prior art

Ranked by closeness to P0: the number of blocks covered, then how much of the chain is treated. The top five come first. The locator is "abstract" wherever no open full text was reached (see execution note 8), and a record is credited only for what that locator states.

| # | DOI | What it shows (locator) | Blocks | Physical question it answers | How P0 differs |
|---|---|---|---|---|---|
| 1 | 10.1007/s11998-016-9898-x (Li, Peng, Deng et al., J. Coat. Technol. Res. 14, 1095, 2017) | PDA dip-coated on silicon wafers at pH 8.5 acts as the organic matrix. ACC forms on the PDA (with poly(acrylic acid) in solution, CO2-diffusion method) and transforms into a continuous calcite film, whose thickness is set by mineralisation time (abstract) | O, M | Can a PDA layer template a macroscopically continuous CaCO3 film, via ACC, under mild aqueous conditions? | Substrate is Si, not the hydroxylated Al oxide. No processing regime and no corrosion question. Experimental synthesis, needing a soluble polyanion. P0 evaluates the thermodynamics of each link (wet adhesion, Ca2+ sequestration, templated nucleation barrier, film stability) for Al in the alkaline slurry |
| 2 | 10.1002/cssc.201700616 (Ko, Son, Park, ChemSusChem 10, 2585, 2017) | Catechol-rich PDA as a biomimetic mediator yields nanostructured CaCO3 films of amorphous hemispheres. These are then converted into metal-oxide electrocatalyst films (abstract) | O, M | Can PDA-mediated CaCO3 mineralisation serve as a green templating route to nanostructured films? | The CaCO3 is a sacrificial template, not a barrier. No Al, no current collector, no stability analysis |
| 3 | 10.1002/celc.202500327 (Maffre, Liu, Markowski et al., ChemElectroChem 13, e202500327, 2025) | LiH2PO4 buffer in aqueous processing of NMC622 and LNMO: reduced Al pitting, and XPS phosphorus species consistent with a thin phosphate passivation layer (abstract) | S, P (inorganic layer formed in situ) | Does pH buffering and phosphate passivation suppress Al collector corrosion during aqueous processing? | Phosphate, not carbonate. No organic template and no Ca2+ chemistry. An empirical additive study; P0 is a thermodynamic screen of a templated carbonate film |
| 4 | 10.1149/06418.0013ecst (Soeda, Yamagata, Ishikawa, ECS Trans. 64, 13, 2015); 10.1149/ma2014-02/1/16 (meeting abstract) | Alginic acid as an aqueous cathode binder: the acid–base reaction with the active-material surface gives a pH-controlled slurry, which is reported to avoid Al current-collector corrosion. The meeting abstract estimates slurry pH 8.4 (both abstracts) | S, O, P | Can a polysaccharide binder's own acidity keep the slurry outside the Al corrosion regime? | The mechanism is pH control by the binder. There is no Ca2+ sequestration, no mineral layer and no thermodynamic chain |
| 5 | 10.1021/jacs.4c03943 (Ai, Yang, Yin et al., J. Am. Chem. Soc. 146, 15496, 2024) | Nacre-like "brick-and-mortar" interphase built from mesoporous PDA platelets on a Zn anode for aqueous Zn-ion batteries (abstract) | O, nacre motif (architecture only, no mineral), battery | Does a nacre-architecture artificial interphase regulate Zn2+ flux and deposition? | An anode, not an Al collector. Nacre as a structural motif, not as a biomineralisation mechanism. No CaCO3 |
| 6 | 10.1002/adfm.200902347 (Ryu, Ku, Lee et al., Adv. Funct. Mater. 20, 2132, 2010) | Surface-anchored catecholamine in PDA enriches the interface with Ca2+ and drives hydroxyapatite crystallisation on ceramics, metals, semiconductors and polymers (abstract) | O, M (calcium phosphate) | Does a PDA layer enrich Ca2+ and template a calcium mineral on any substrate? | Calcium phosphate in a biomedical setting. The closest experimental analogue of links C2 to C3, but not carbonate, not Al collectors, not computed |
| 7 | 10.1021/cg301759t (Wang, Xu, Cryst. Growth Des. 13, 1937, 2013) | PDA shells stabilise ACC nanoparticles for at least one year in the solid state. The stabilisation is attributed partly to Ca2+ complexation by PDA (abstract) | O, M | Does PDA retard ACC dissolution and transformation? | Particles, not a film on an oxide. Relevant to C4 and C5 and to contrary entry B5 |
| 8 | 10.1021/jp512780s (Yeh, Lenhart, Rinderspacher et al., J. Phys. Chem. C 119, 7721, 2015); 10.1021/acs.jpcb.9b04473 (Yeh et al., J. Phys. Chem. B 123, 7024, 2019); 10.1021/acs.langmuir.5c02791 (Shrestha, Kojio, Shiota et al., Langmuir 41, 23672, 2025) | Atomistic MD (2015, 2019) and periodic DFT (2025) of catechol and catechol polymers on alumina. In water, catechol adsorbs on hydroxylated alumina through cooperative hydrogen bonds (2015). Water competition significantly weakens adsorption of catechol oligomers (2019). On hydroxylated γ-Al2O3(110), the interaction is physisorption by hydrogen bonding, weaker than on the dehydroxylated surface (2025) (abstracts) | S, O (computational C1) | How strongly does catechol bind alumina, with and without water? | Link C1 only. No free-energy chain to sequestration, nucleation or stability. P0 credits these and builds on them; see contrary entry B9 |
| 9 | 10.1016/j.carbpol.2019.115054 (Zhu, Chen, He et al., Carbohydr. Polym. 223, 115054, 2019); 10.1016/j.gca.2006.04.023 (Perry, Cygan, Mitchell, Geochim. Cosmochim. Acta 70, 3508, 2006) | First-principles MD of chitosan monomers on calcite(104), with Ca–O coordination at the interface (2019, abstract). Molecular models of alginic acid interacting with Ca2+ and calcite surfaces (2006, title only) | O, M (computational) | How do polysaccharides bind calcite and Ca2+? | The organic–mineral interface only. No oxide substrate, no nucleation barrier, no regime |
| 10 | 10.1038/srep30945 (Cho, Gong, Song et al., Sci. Rep. 6, 30945, 2016) | PDA-treated Cu foil as an anode current collector. PDA (Tris buffer, pH 8.5) bonds the binder by condensation, and peel adhesion rises from 245.5 to 353.2 N m−1 (full text: Abstract; "Preparation of the Polydopamine-treated Cu Current Collector"; "Morphological changes of the Si electrodes") | O, current collector | Does a PDA primer improve electrode-to-collector adhesion? | Cu anode collector, adhesion only. No Al, no corrosion, no mineral |
| 11 | 10.1002/app.53530 (Xu, Xu, J. Appl. Polym. Sci. 140, e53530, 2022) | PDA on Ti-conversion-treated Al foil raises peel strength to a hot-melt adhesive in pouch-cell laminate film (abstract) | S, O | Can PDA replace chromate pretreatment of Al foil for adhesive bonding? | Packaging foil, dry adhesive joint. Not the collector, and no slurry or corrosion chain |
| 12 | 10.1016/j.jpowsour.2013.10.039 (Doberdò, Löffler, Laszczynski et al., J. Power Sources 248, 1000, 2014) | CMC-based aqueous NMC slurry causes serious Al corrosion during manufacture because of high pH. A thin carbon coating on the Al foil prevents direct contact (abstract) | S, P | Can a barrier coating on Al enable aqueous cathode processing? | A carbon barrier applied before casting, not a mineral grown in situ from the slurry. Empirical |
| 13 | 10.1002/maco.201608843 (Li, Church, Mater. Corros. 67, 978, 2016); 10.1007/s10853-014-8028-3 (Church, Kaminski, Jiang, J. Mater. Sci. 49, 3234, 2014; title only) | Slurry pH and immersion time are the principal factors in Al corrosion. The oxide passive film degrades to hydroxide, and localised corrosion initiates at intermetallic particles (2016, abstract) | S, P | What controls Al collector corrosion in aqueous slurries? | Defines the R-slurry problem that P0 screens against. See contrary entry B11 |
| 14 | 10.1016/j.electacta.2019.05.141 (Bauer, Çetinel, Müller et al., Electrochim. Acta 317, 112, 2019); 10.1021/acsami.8b03657 (Kazzazi, Bresser, Birrozzi et al., ACS Appl. Mater. Interfaces 10, 17214, 2018) | Li+/H+ exchange raises slurry pH and attacks Al; acid addition helps, but the best electrode properties were found at pH 9–10, outside the Al-stable region (2019, abstract). Aqueous binders including sodium alginate, with phosphoric acid to avoid Al corrosion (2018, abstract) | S, (O), P | How far can slurry pH be managed by acid or binder choice? | Mitigation by pH. No templated mineral |
| 15 | 10.1557/s43581-025-00131-8 (Thongklum, Chienwiboonsook, Limthongkul et al., MRS Energy Sustain. 12, 254, 2025); 10.1016/j.nanoen.2022.107830 (Zhang, Liao, Liu et al., Nano Energy 103, 107830, 2022; title only) | Acetylene black/CaCO3 coating as an artificial SEI on Zn anodes (2025, abstract). A "biomineralization-inspired" dendrite-free Zn electrode (2022, title) | M, battery | Can CaCO3 or biomineral-inspired coatings regulate Zn plating? | Zn anodes in aqueous electrolytes. Not an Al collector, not templated, no chain |
| 16 | 10.1016/j.ensm.2025.104569 (Du, Song, Ning et al., Energy Storage Mater. 82, 104569, 2025; title only) | A metal-oxide coating to suppress Al collector corrosion in high-voltage LiTFSI batteries (title) | S, R-cell coating | Can an inorganic coating protect Al against anodic dissolution in an imide electrolyte? | Not carbonate, not templated, not aqueous-processing. It shows that inorganic-coating protection of Al collectors in imide electrolytes is an active line, and the R-cell discussion must cite it |
| 17 | 10.1021/la803541m (Zhong, Chu, Langmuir 25, 3045, 2009) | Maleic chitosan, an acid polysaccharide, directs ACC films by self-organisation of colloidal nanoparticles under 10 nm (abstract) | O, M | How do acid polysaccharides form ACC films? | No substrate chemistry, no Al. Relevant to B5 and B7 (particle-based film formation) |

Records retained but judged further from P0 (no row): 10.1149/ma2016-03/2/589 (PDA-coated anode collector, meeting abstract, companion to row 10); 10.2139/ssrn.4698483 (effect of Cu and Al metals on CaCO3 scale, title only). Records retained as contrary evidence are in `lit/contrary.md`: 10.3390/coatings13020306, PDA coatings reduce CaCO3 deposition; and 10.1021/acsomega.0c01538, CaCO3 scaling raises Al-alloy corrosion.

### Full-text retry for rows 1, 3 and 5 (dated note, 2026-10-17, P0-W2.2)

Open routes were tried for each row: Unpaywall, OpenAlex, Europe PMC, Semantic Scholar, repository search, and archived copies of the open-access locations. The table rows above are left as written. This note records what each route returned and what the full text changes.

- **Row 1** (10.1007/s11998-016-9898-x): not retrieved.
  - Unpaywall and OpenAlex list no open copy.
  - The publisher page returns a bot-challenge shell, and no repository copy was found.
  - Crossref and OpenAlex carry no abstract, so the row still rests on the abstract read on day 1. It stays at "abstract".
- **Row 3** (10.1002/celc.202500327): read in full, from the typeset CC-BY version in the UCLouvain repository (9 pp.). The full text narrows what the row's abstract-based description implies.
  - **pH without additive.** In water alone the pH levels off at 10.8 (LNMO) and 12.3 (NMC622) (p. 3, Fig. 2A). In the full slurry it ends at 9.7 (LNMO) and 12.5 (NMC622) (p. 5, Fig. 3F).
  - **pH with LiH2PO4.** In the dilute test dispersion, LiH2PO4 holds the pH at 6.6 and 9.7 (p. 4, Fig. 2E).
  - **Al pitting.** The evidence on the Al is SEM only. Al from NMC622 + LiH2PO4 electrodes is "free of obvious pitting" (p. 6, Fig. 4D).
  - **Phosphate layer.** The XPS phosphate signal (P 2p) was measured on the cathode powders, not on the Al. The authors describe it as "a thin, largely inorganic phosphate layer forming on the active-material surface" and call their case "indirect yet coherent evidence" (p. 7).

  So the phosphate layer is shown on the active material, and the protection of the Al is attributed to pH buffering. No passivation layer on the collector is shown. The row's blocks and its difference from P0 are unchanged.
- **Row 5** (10.1021/jacs.4c03943): no open copy; the row stays at "abstract".
  - The abstract describes mesoporous PDA platelets in a nacre-like brick-and-mortar layer on Zn, with no mineral.
  - The row is unchanged.

**Effect on the wording.** N1 and N2 are unchanged. N2 credits "mitigation of Al corrosion in aqueous slurries" and row 3 still supports that credit, now as pH-buffering mitigation. No new evidence bears on the decision rule.

## Novelty wording supported by the evidence

**Wording N1 (for the Introduction or the end of the Abstract).**

> To our knowledge, based on a structured search of the indexed journal and preprint literature (Semantic Scholar, OpenAlex, arXiv, OpenAIRE and Crossref, October 2026; patent literature not searched), no previous study has evaluated, for an aluminium current collector in the alkaline aqueous-slurry regime, the combined thermodynamic chain of wet adhesion of a catechol or polysaccharide template to the native oxide, Ca2+ sequestration and enrichment by that template, templated CaCO3 nucleation on it, and the stability of the resulting film.

**Wording N2 (crediting the separate links; to follow N1).**

> Each link has precedent on its own: catechol adsorption on alumina in water has been simulated [10.1021/jp512780s; 10.1021/acs.jpcb.9b04473; 10.1021/acs.langmuir.5c02791]; polydopamine enriches interfaces with Ca2+ and templates calcium minerals, including continuous CaCO3 films, on other substrates [10.1002/adfm.200902347; 10.1007/s11998-016-9898-x; 10.1002/cssc.201700616] and stabilises amorphous CaCO3 [10.1021/cg301759t]; and aluminium corrosion in aqueous cathode slurries is mitigated by pH control, carbon coating, phosphate buffering or acidic binders [10.1002/maco.201608843; 10.1016/j.jpowsour.2013.10.039; 10.1002/celc.202500327; 10.1149/06418.0013ecst]. What has not been reported, within the searched literature, is the evaluation of these links as one chain for this interface and regime.

Conditions on N1 and N2:

1. **Required qualifiers.** "Within the searched literature" and "patent literature not searched" are part of the wording and may not be dropped while the patent gap stands (gap G1). If a patent search later finds a combined-chain disclosure, N1 is withdrawn.
2. **Regime.** N1 applies to R-slurry only. It is silent on the R-cell stability window (C5, item 20), which was not a designed combination.
3. **Non-claims.** N1 claims an evaluation, not a working barrier. It must not be paired with any verb that implies protection (scope guard SG02 and SG03).
4. **Scope-guard check.** Neither wording matches a scope-guard pattern (SG01 to SG14). The phrase "to our knowledge … no previous study" is limited by the search statement, and it contains no "first".

## Wording the evidence does not support

| # | Wording (or any paraphrase) | Why it is not supported |
|---|---|---|
| U1 | "the first report / study / demonstration of …" (any "first") | No search can establish priority. Patents (G1) and ChemRxiv's own search (G2) were not reached, and non-English literature was not targeted. Scope guard SG14 |
| U2 | "the intersection is unoccupied" / "no one has proposed nacre-inspired protection of aluminium collectors" | The searched literature supports only the narrower N1. Patents and grey literature were unsearched. Scope guard SG13 |
| U3 | "first nacre-inspired or biomineral-inspired battery interface" | Prior art: nacre-like PDA interphase on Zn (row 5); CaCO3 and biomineral-inspired Zn anode coatings (row 15) |
| U4 | "first use of polydopamine on a current collector or on aluminium foil in batteries" | Prior art: PDA-treated Cu collector (row 10); PDA on Al foil for pouch laminate (row 11) |
| U5 | "first templated CaCO3 film on polydopamine" or "first PDA-mediated CaCO3 mineralisation" | Prior art: rows 1 and 2; PDA-stabilised ACC (row 7) |
| U6 | "first protective inorganic layer formed during aqueous cathode processing" | Prior art: phosphate passivation layer from a LiH2PO4 buffer (row 3) |
| U7 | "first bio-derived binder that prevents aluminium corrosion in aqueous processing" | Prior art: alginic-acid binder (row 4) |
| U8 | "first computational study of catechol adhesion to alumina" | Prior art: row 8 (MD 2015 and 2019, DFT 2025) |
| U9 | "a CaCO3 layer protects aluminium" or "carbonate is known to passivate aluminium" | Contrary: CaCO3 scaling increased corrosion of Al alloys in hot brines (`lit/contrary.md` B1); PDA coatings reduce CaCO3 deposition (B10). Scope guard SG02 and SG03 in any case |
| U10 | Any novelty claim for the R-cell stability window (Li-referenced grand-potential screen of CaCO3 on Al in a fluorine-free electrolyte) | Not a designed combination and not searched as such. Inorganic coatings against Al dissolution in imide electrolytes are an active line (row 16). Needs its own search |
| U11 | "novel" in a patent or freedom-to-operate sense | Patents not searched (G1) |
| U12 | "unprecedented", "pioneering", "never before" | Same grounds as U1 |

## Gaps in this audit

- **G1 Patents.** No headless patent route: `LENS_TOKEN` is empty and no other key is present. Outstanding. YOU: a free Lens.org API token, added to `.env` as `LENS_TOKEN`, would let a later session rerun the 33 logged patent strings unchanged.
- **G2 ChemRxiv.** The search API returned HTTP 403 to every request. DOI-bearing ChemRxiv items are still partly covered through the indexing routes.
- **G3 Full text.** Publisher-hosted open copies refused headless clients. Only 5 full texts were reached, and the remaining locators are abstracts or titles. Rows 1 to 5 (the top five) were read from abstracts only. The full text of rows 1, 3 and 5 should be read before cp4, through an authenticated or library route by the operator. *Update 2026-10-17 (P0-W2.2): row 3 was read in full through an open repository copy (see the dated note under Closest prior art); rows 1 and 5 have no open copy and remain outstanding for an operator or library route.*
- **G4 Depth.** For combinations with more than 25 hits per route, only the top 25 records were screened. The decisive combinations (SOMP and the S-O-M triple, with and without the context block) were screened in full on both boolean routes.
- **G5 Language.** The query terms are English only.

## Phosphate redirect scan (PH-W2.1, 2026-10-20)

Scope: redirect to calcium-phosphate barriers on Al in fluorine-free cells (`ops/tracks/redirect_plan.md`). Fetched headless on 2026-10-20: Google Patents pages, Crossref, OpenAlex, HAL API, PMC, OSTI, web search. Patents were read as open full-text pages only. Values below are from those pages; "n.r." = not retrieved. Rows from search-result summaries are marked (S). Differences are stated against the target: templated biomimetic Ca-phosphate film + quantitative design rule + fluorine-free + aqueous slurry processing.

### P1. Incumbents

| ID | Identity | Assignee (verification) | Priority | Claim scope | How the target differs |
|---|---|---|---|---|---|
| I1 | US 6,485,866 B1 (parent of I2; CA 2,268,355) | Hydro-Québec original; Avestor LP / Bathium Canada listed as current (Google Patents header, verified) | 1999-04-07 | Claims 1, 12, 16: collector coated with a vitreous or partly vitreous binder of an alkaline-metal **phosphate or polyphosphate** plus an electronic-conduction additive; claim 12 is a process from an aqueous dispersion; carbon 2-20 vol % (claim 22) | Claims a glassy Li/K polyphosphate-plus-carbon binder, not a Ca-phosphate nucleated on a template; no design rule; no fluorine-free or Ca claim |
| I2 | US 6,844,114 B2 | Hydro-Québec original; Avestor / Bathium listed (verified) | 1999-04-07 (filed 2002-09-24) | Claims recite alkaline-metal **borate or polyborate** only; phosphate and (LiPO3)n, made by neutralising (HPO3)n to pH near 7, appear in the description only | Same as I1; borate claims leave phosphate described, not claimed, in this member |
| I3 | CA 2,268,355 A1 "LiPO3-based collector coating" | Hydro-Québec (original) | 1999-04-07 | Claim 2: coating based on phosphate, polyphosphate, borate or polyborate of an alkali metal; claims 19 and 30 repeat it for process and electrode | As I1 |
| I4 | US 8,221,915 B2 "High performance lithium or lithium ion cell" | Leyden Energy original; A123 Systems and Leyden ABC LLC listed later (verified) | 2010-11-12 | Al collector with conductive carbon/graphite coating; LiTFSI at 0.1-3 M; additive from LiBOB, LiF, LiFOB, LiPF6 and similar | Carbon coating plus fluorinated imide salt; no phosphate; not fluorine-free |
| I5 | US 9,263,731 B2 (same title) | Header names no assignee; legal events show Leyden Energy; A123 appears on some pages (unresolved) | 2010-11-12 (filed 2011-10-13) | Porous carbon/graphite-polymer coating leaving Al exposed; imide/methide salt; 0.01-1 M additive forms a film on exposed Al | As I4 |
| I6 | US 9,350,017 B2 (same title) | Unresolved: one fetch lists A123 Systems as original, the other none; legal events show Leyden | 2010-11-12 (CIP of US 13/273,114) | Claim 1: carbon/graphite coating 0.1-8 um, imide salt (C2F5SO2 or FSO2), additive LiBOB/LiF/LiPF6 and others. Page reports a 60 C hold at 4.2 V: bare Al corrodes at about 60 h, coated none in 1 week; at 3.65 V onset is delayed | As I4; the 60 C hold is a class A anchor for carbon coating |
| I7 | US 8,252,463 B2 and US 8,821,969 B2 (Modified current collector / method) | Tsinghua University and Hon Hai Precision (verified, both) | 2010-08-27 | Metal plate (example 20 um Al foil) with a protective film Al(x)M(y)PO4 or Al(x)M(y)(PO3)3, M = Cr, Zn, Mg, Zr, Mo, V, Nb or Ta; 10-200 nm; made from H3PO4 + Al(OH)3 + metal oxide (example CrO3) in water or NMP, dip coat, 100-350 C cure | **Closest incumbent: an Al-phosphate / Al-polyphosphate film on Al.** Film is cured aluminophosphate (Cr in the example), not a Ca-phosphate nucleated on a biomimetic template; no oxidation-limit rule; electrolyte salts listed include LiPF6 |
| I8 | Tolchard, Vullum, Arstad, Wagner, RSC Sustainability 1, 378 (2023), 10.1039/d3su00031a | Academic (SINTEF / NTNU) | 2023 | H3PO4 pH control for aqueous NMC622; needs tight acid stoichiometry and drying (Crossref abstract paraphrase); residual phosphate gave rapid cell death (S: 50-100 cycles) | Phosphate as a slurry additive on the active material, not a film on the foil |
| I9 | Chen et al., J. Mater. Chem. A 12, 25393 (2024), 10.1039/d4ta03592e | Academic (Uppsala) | 2024 | H3PO4 in water processing of Ni-rich cathodes gives a slightly thinner CEI and lower charge-transfer resistance (Crossref abstract) | As I8 |
| I10 | Carvalho et al., Polymers 8, 276 (2016), 10.3390/polym8080276 | Academic (Passerini group) | 2016 | LTO slurry pH 11.4 falls to about 6.7 with 1 wt % H3PO4; cavities and Al in cavity (EDX 66-88 at %) absent with acid; 144 vs 124 mAh/g at 5C | pH control for the slurry stage only |
| I11 | Xu et al., Electrochim. Acta 2022, 10.1016/j.electacta.2022.140970; further LTO/H3PO4 papers (S) | Academic (surfaced as Bresser-group LTO work; authorship n.r.) | 2022 | H3PO4 additive for water-processed LTO; phosphate anion matters beyond buffering; Li3PO4 and a Li1+xTi2(PO4)3 rod phase reported (S) | Phosphate forms on the active material; no barrier on Al designed |
| I12 | Bichon, Sotta, de Vito, Porcher, Lestriez, J. Power Sources 2021, 10.1016/j.jpowsour.2020.229097 (HAL-CEA, hal-03173352) | Academic / CEA-Liten | 2021 | Water-processed NMC532/graphite; Al corrosion avoided by H3PO4 buffering **or** a carbon-coated collector | Shows both incumbent routes at once |
| I13 | Long et al., Energy Environ. Sci. 18, 10306 (2025), 10.1039/d5ee06040k | Academic | 2025 | Interfacial strategy confining H+/OH- to suppress Al corrosion in aqueous storage (Crossref); an electrodeposited AlPO4 layer (S, n.r. in abstract) | Aqueous electrolytes, not Li-ion slurry or cell; needs full-text check |
| I14 | Gao, Ma et al., Mater. Today Energy 7, 18 (2018), 10.1016/j.mtener.2017.12.001 | Academic (Argonne) | 2017 | AlPO4 passivation layer on Al: corrosion peak absent and low leakage in CV and CA (S, via a 2023 review) | Class A anchor; see tier-2 table |

US 6,485,866 phosphate verdict: **yes**, phosphate and polyphosphate are claimed (claims 1, 12, 16), not only described. The continuation US 6,844,114 claims borate only. Search for phosphate conversion coatings on Al: the Tsinghua/Hon Hai films (I7) and AlPO4 on Al foil (I13, I14, Ma 2017) are what was found; no conventional conversion-coating paper for battery foil was found in 2 searches.

### P2. Template precedent

| Ref | What was shown |
|---|---|
| Ryu, Ku, Lee, Park, Adv. Funct. Mater. 20, 2132 (2010), 10.1002/adfm.200902347 | Polydopamine coating as a general route to hydroxyapatite crystallisation on ceramics, noble metals, semiconductors and polymers (abstract via search summary; Al and Li-ion cells not covered). Used as an optional qualitative consistency check |
| Surface-adhesive layer-by-layer PDA-hydroxyapatite on Ti, RSC Adv. 2014, 10.1039/c4ra07907h | Layer-by-layer PDA/HA films on titanium, repeatable, bioactive in cell tests (S) |
| Xiao et al., Nanosci. Nanotechnol. Lett. 2015, 10.1166/nnl.2015.1965 | PDA layer on Ti implants accelerates hydroxyapatite nucleation and growth (title and search summary) |
| Tapsir et al., Surf. Coat. Technol. 2016, 10.1016/j.surfcoat.2015.11.024; J. Biomater. Appl. 2017, 10.1177/0885328217744081 | Collagen-hydroxyapatite immobilised on PDA-grafted 316L stainless steel; adhesion and cell tests in the 2017 paper (titles only) |
| PDA-linked chitosan film on stainless steel, J. Mater. Sci. Mater. Med. 2022 (DOI n.r.) | Chitosan film bonded through PDA and glutaraldehyde, adhesion higher than PDA alone; no calcium phosphate (S) |
| HA-chitosan on 304 stainless steel by galvanic deposition (conference abstract, S) | HA-chitosan composite coating without external power; no Al, no battery |

No source found for PDA or chitosan templated calcium phosphate on **aluminium** or on a battery collector (3 searches). Absence in this scan does not establish priority.

### P3. Tier-2 hunt (for PH-W1.2 to extract; seed sources excluded)

Class: A hold or LSV on a coated Al collector; B coated cathode particle cycled to a stated cutoff; C bulk LSV. n.r. = not retrieved, to be fetched by W1.2.

| ID | Phase | Class | Electrolyte | Temp | Cutoff / potential | Duration as stated | DOI |
|---|---|---|---|---|---|---|---|
| T1 | AlPO4 coating on Al foil | A | 1.2 M LiPF6 EC/EMC 3:7 (fluorinated) | n.r. (not in main text) | Stepped holds; bare Al shows a corrosion window near 3.9 V; the window is absent with AlPO4 and peak parasitic current is about 50 % of uncoated (text states Fig. 4c, up to the 4.5 V step) | Holds up to 20 h | 10.1021/acs.jpclett.6b02933 (Ma et al., 2017; DOI from the SI record) |
| T2 | AlPO4 passivation layer on Al | A | n.r. | n.r. | CV and CA; corrosion peak disappeared (S) | n.r. | 10.1016/j.mtener.2017.12.001 |
| T3 | Li-Al-phosphate coating on LiCoO2 | B | n.r. | "room temperature and beyond" (title) | 4.6 V | n.r. | 10.1016/j.ensm.2021.01.031 |
| T4 | ALD AlPO4 on Li1.2Mn0.54Co0.13Ni0.13O2 | B | n.r. | n.r. | n.r. | n.r. | 10.1016/j.nanoen.2017.02.015 |
| T5 | ALD FePO4 on LiNi0.5Mn1.5O4 (analogue phase) | B | 1 M LiPF6 EC/DMC 1:1 | CV at room temperature; cycling n.r. | 5.0 V (3.5-5.0 V window) | 100 cycles at 0.5 C: 79.89 % retained bare, 100 % with 40 ALD cycles | 10.1002/advs.201500022 |
| T6 | Li3PO4 coating on LiNi0.8Co0.15Al0.05O2 for aqueous processing | B | n.r. | n.r. | n.r. | n.r. | 10.1002/cssc.202001907 |
| T7 | Li3PO4 and in situ LiPO3 (ALD thin film) | C, theoretical window | n.r. | n.r. | 0.69-4.21 V for Li3PO4; up to 5.00 V for LiPO3 (S) | n.r. | n.r. (record at kms.shanghaitech.edu.cn/handle/2MSLDSTB/345791; page unreadable) |
| T8 | LiPON, about 5 V window (S) | C, indirect | n.r. | n.r. | about 5 V (several records, one calculated) | n.r. | n.r. (Electrochim. Acta 2016 LiPON/B-LAGP record; not extracted) |

Counts: class A 2, B 4, C 2. **No tier-2 row exists for a calcium phosphate** (hydroxyapatite, ACP, OCP, beta-TCP, Ca pyrophosphate, Ca metaphosphate) and no Al(PO3)3 or Al-borate/oxalate row: 1 search for bulk Ca-phosphate LSV returned nothing. All A rows are in LiPF6 (fluorinated) electrolyte, so a fluorine-free reading is not available from them.

### P4. Fluorine-free phosphate-source survey

| ID | Source | What is sourced | Oxidation limit or film |
|---|---|---|---|
| S1 | Trimethyl phosphate (TMP) electrolyte on LNMO, Matsumoto et al., J. Power Sources 273 (2015), 10.1016/j.jpowsour.2014.09.018 | TMP-based electrolyte, abstract via search | Oxidation onset about 3.8 V vs Li/Li+, against about 4.6 V for EC:DEC; an oxidative polymer film limits further decomposition. No Al-phosphate film reported |
| S2 | TMP and TEP at 4.4 and 4.5 V, patent US 11,088,396 "Electrolyte formulations for electrochemical device" (S; assignee n.r.) | Patent text states superior stability at 4.4-4.5 V, to be shown by experiment | Conflicts with S1 (3.8 V onset); treat as unverified |
| S3 | Tornheim et al., J. Electrochem. Soc. 166 (2019), 10.1149/2.0951902jes (OSTI 1494582) | 1 wt % phosphate and phosphite additives incl. triethyl phosphate in 1.2 M LiPF6 EC/EMC, NMC532/LTO | Holds 4.6 V for 60 h and 4.3 V for 20 h: all phosphates slightly raised CE, none reduced the hold current, i.e. no passivated surface. Electrolyte is fluorinated |
| S4 | H3PO4 residue in slurries, Tolchard 2023 (I8) | Excess or unreacted orthophosphate remains on drying | Reacts with carbonate electrolyte, rapid failure (S: 50-100 cycles) |
| S5 | Li3PO4 and Li1+xTi2(PO4)3 from H3PO4 in LTO slurries (I11) | Phosphate forms on the active material in the slurry (S) | Not a source for the foil; a competing phase |
| S6 | Li3PO4 coating on NCA, Hofmann 2020 (T6) | Coating level trades water protection against electronic conduction | Cutoff n.r. |
| S7 | Hydro-Québec (LiPO3)n binder (I1, I3) | Phosphate-bearing binder is itself a collector coating; the background says earlier binders react with iron phosphate-type materials | Used at 3.1 V limit in polymer cells (plan); no high-voltage data |
| S8 | Tsinghua / Hon Hai aluminophosphate (I7) | Phosphate film built from H3PO4 + Al(OH)3 on Al foil | No oxidation limit stated in what was read |

Count: 8 sources. No source was found on a phosphate ester forming an Al phosphate film, or on TEP with Al corrosion (2 searches). **Phosphate supply at a pit from a co-solvent, additive, binder or film reservoir is a hypothesis**: nothing here shows delivery to a pit, in-situ AlPO4 formation in a cell, or the film's oxidation limit in a fluorine-free cell. Film properties can be screened; supply is not screened.

### P5. Novelty wording

Supported by this scan (acknowledge as prior art, or narrow claims):

| # | Wording | Support |
|---|---|---|
| NS1 | Phosphate and polyphosphate collector coatings from aqueous dispersion are prior art | I1 claims 1, 12, 16 (1999) |
| NS2 | Aluminophosphate films on Al collectors are prior art | I7 (2010); T1, T2 |
| NS3 | Phosphoric-acid pH control of aqueous electrodes is prior art, with residue risk | I8 to I12 |
| NS4 | Carbon-coated Al collectors are a prior route to the same benefit | I4 to I6, I12; Ma 2017 reports carbon raised parasitic current about 10-fold in LiPF6 |
| NS5 | Among the open sources scanned, none combines a PDA- or chitosan-templated Ca-phosphate film, a quantitative design rule, fluorine-free cells and aqueous-slurry processing | P1 to P3; narrow, search-limited, patent gap below |

Unsupported (do not write):

| # | Wording | Why |
|---|---|---|
| NU1 | "first" anything (first phosphate barrier, first bone-inspired, first templated film on Al) | No priority search possible (SG14) |
| NU2 | "novel" in any patent sense | Patent gap |
| NU3 | "no incumbent delivers the benefit" | I7, I8 to I12 deliver slurry-stage protection |
| NU4 | "outperforms phosphoric acid or carbon-coated collectors" | No comparison exists |
| NU5 | "a Ca phosphate is more oxidation-stable than carbonate" | No tier-2 row for any Ca phosphate |
| NU6 | "fluorine-free protection of Al is new" | Not searched as such |
| NU7 | "phosphate supply at a pit works" or "self-healing" | Hypothesis only |
| NU8 | "templated Ca phosphate has not been made on Al" | Only 3 searches; no Al/Ca-phosphate hit does not prove absence |
| NU9 | "the nucleation half is validated" | Retrodiction 7 of 12 |
| NU10 | Any claim that PDA-HA work on Ti or steel transfers to Al foil in alkaline slurry | Not shown |

Counts: supported 5, unsupported 10.

**Patent-search gap.** No keyword, classification or citation search of patent databases was possible (no Lens token). Only named Google Patents pages (I1 to I7) and incidental hits from web search were read. Not covered: other Hydro-Québec family members, JP/KR/CN filings beyond I7, phosphate conversion-coating patents for foil, claims text of I5 and I6 beyond claim 1.

## Route-layer prior art (PH-W2.2a, 2026-10-20)

Scope: routes R1 to R3 of the draft route layer (`ops/tracks/redirect_plan.md`, "ROUTE LAYER", draft, not ruled). Target of comparison: an in-situ, matrix-mediated, crosslinked, water-insoluble polyphosphate film on Al foil. Fetched headless on 2026-10-20: Google Patents pages, Crossref, OpenAlex, Europe PMC, NSF PAR, Nature PDF. Patents were read as open full-text pages only. "Abs." = abstract only (full text refused or blank); "Full" = full text read. Attempts per source are at most 3 (retrieval rule); refusals are listed under "Gaps".

### R-P1. Prior-art table

| ID | Identity | Assignee or authors | Year | What it shows | Route or K-test touched | How the target differs | Read |
|---|---|---|---|---|---|---|---|
| PA1 | EP1582608 A2 and US 8,163,105 B2, "Corrosion inhibition method" (EP B1 address returned 404; A2 and A3 pages open) | Kurita Water Industries (Yoneda, Iseri, Mori) | 2004 (priority 2004-03-31) | Pyrophosphate dosed into cooling water at initial pH 5 to <7 (end pH >=7) builds a two-layer film on carbon steel: iron pyrophosphate, then a Ca-phosphate layer needing 30 to 150 mg CaCO3/L hardness; the text says pyrophosphate hydrolyses to orthophosphate | R2 and R3 (Ca-phosphate film from dosed Ca and P-O-P phosphate); K2 hydrolysis | Iron substrate and dosed solution, not Al foil; first layer is substrate-derived Fe pyrophosphate; no matrix, no crosslinker, no battery, no fluorine-free test; insolubility not a design criterion | Full (patent text) |
| PA2a | Troutner, "Uniform aqueous corrosion of aluminum: effects of various ions", OSTI 4312114 | V. H. Troutner (Hanford) | 1957 | In distilled water, phosphate ion was one of two specific-ion effects on uniform Al corrosion: phosphate inhibited, citrate increased; 10 ppm phosphate inhibited at pH 4 to 7 with up to 2 ppm dichromate | Incumbent phosphate benefit on Al (K4 context) | Orthophosphate dosed to water; no film characterised, no polyphosphate, no battery | Abs. |
| PA2b | Zou, thesis "Corrosion inhibition of Al alloy with CaSiO3/gluconate based pigments", OhioLink ETD | Y. Zou | 2016 | CaSiO3/Ca-phosphate and Zn-phosphate pigment (heat treated 300 to 400 C) inhibits AA6061 in gluconic acid and 1 % NaCl; an adherent calcium-hydroxyl, glassy silicate/phosphate film forms; the effect needs oxygen | Ca-phosphate on an Al alloy | Orthophosphate pigment leachate, not polyphosphate; thesis; no crosslinking, no battery | Abs. |
| PA2c | Lu et al., Coatings 9, 649 (2019), 10.3390/coatings9100649 | X. Lu et al. | 2019 | Mg-rich primer with aluminium tripolyphosphate pigment gave about 49 days of cathodic protection of AZ91D in simulated acid rain; pigment releases phosphate and H+, giving Mg phosphate films | Polyphosphate pigment as inhibitor source | Mg alloy, galvanic primer, pigment leachate; not Al, not in situ crosslinking | Abs. |
| PA3 | Morsch et al., Sci. Rep. 8, 17450 (2018), 10.1038/s41598-018-35512-2 | Morsch, Emad, Farren, Goodall, Lyon, Gibbon | 2018 | Strontium aluminium polyphosphate (SAPP) on steel coupled to zinc in 3.5 % NaCl: a gel-like film within 1 h; film is zinc carbonate first, then (poly)phosphate after >6 h; polyP bands (1244, 1352 cm-1) at 24 h; polyP precipitates only after inhibition lowers local pH; hydrolysis to orthophosphate under alkaline cathode conditions (local pH >10) | K2 hydrolysis versus film formation (the race); R1 (insoluble Zn and Sr polyP forms from dissolved polyP plus cations) | Steel and zinc, pigment leachate; no matrix, no foil, no battery; film insolubility not tested | Full |
| PA4 | Wang et al., J. Mater. Chem. B 2024, 10.1039/d4tb01080a ("Liquid-liquid phase transition ... skin repair") | Wang, Neufurth, Schepler, Munoz-Espi, Ushijima, Schroder and others | 2024 | Na-polyP plus Ca2+ (from nacre aragonite in wound exudate) gives liquid-liquid phase separation into an aqueous Ca-polyP coacervate, a stronger porous gel; Ca-polyP nanoparticles enhance it | R2 (a Ca-polyP coacervate exists in physiological media) | Biomedical; coacervate made from aragonite in exudate, no metal, no wetting, no drying to a glass; no pH or binodal data in the abstract | Abs. |
| PA5 | Son et al., RSC Adv. 2017, 10.1039/c6ra28808a ("CaCO3 thin-film formation mediated by a synthetic protein-lysozyme coacervate") | Son, Kim, Bahn, Cha, Choi | 2017 | W1.2's reading is confirmed: the coacervate is a protein (synthetic protein plus lysozyme) complex coacervate; a planar, poorly crystalline CaCO3 film forms at the coacervate-phase interface | R2 precedent (coacervate-guided mineral film), carbonate not phosphate | Protein matrix, CaCO3, no polyphosphate, no metal substrate | Abs. |
| PA6 | US 12,478,560 B2, "Calcium coacervates for remineralization and for demineralization inhibition" (Google Patents page opened, HTTP 200, on retry) | Muhlbauer Technology GmbH (Paris, Gruber, Colfen, Bulgun, Prause) | 2019 (priority 2019-04-10; granted 2025-11-25) | Claim 1: caries method applying a Ca coacervate, made by mixing a polyanion solution with a Ca solution, to enamel; polyacrylic acid preferred; polyphosphates named once among possible polyanions | R2 (Ca coacervate as mineralising liquid precursor) | Dental enamel, polyacrylic acid not polyphosphate, no metal, no film, no battery | Full (claims and description) |
| PA7 | Wan, Huang, Diaz, Tang, Environ. Sci. Technol. 2019, 10.1021/acs.est.9b01876 (PAR 10109357) | Wan, Huang, Diaz, Tang | 2019 | polyP on gamma-Al2O3 (5, 35, 70 nm) at pH 6 to 8: all divalent cations speed hydrolysis, Ca2+ most; with Ca2+ the orthophosphate share rises about 3.5-fold (pH 6) and 8.5-fold (pH 8) after 9 d; with Ca2+ at pH 8 the main surface species is amorphous Ca phosphate; hydrolysis rate falls as particle size grows; Al polyphosphate precipitate was ruled out as the dominant species | K2 hydrolysis descriptor; R1 and R2 race; K1 amorphous Ca phosphate | Dilute mM suspensions of oxide nanoparticles, no film, no matrix, no crosslinking; rate-constant Table 1 not read (see Gaps) | Abs. plus results text (pdf pp. 5 to 11) |

Closest to the route among rows read: PA1 and PA3 for an in-situ polyphosphate film built from dosed polyP and Ca or other cations (both on steel, both show hydrolysis competing with film formation); PA7 for the same chemistry at an Al-oxide surface (it forms no film); I7 (US 8,252,463, section P1) remains the closest Al-foil phosphate film in a battery. No row shows a matrix-mediated, crosslinked, water-insoluble polyphosphate film on Al.

Polyphosphate corrosion inhibitors for Al components: 5 searches (OpenAlex, 2026-10-20) found only PA2a to PA2c (phosphate or polyphosphate pigments for Al or Mg alloys, abstract level) and steel-based work (SAPP and zinc aluminium polyphosphate on steel). No paper on an Al-foil polyphosphate film, and none in a battery. Absence in 5 searches does not establish priority.

### R-P2. Biomineralisation link (supports the bio-inspired framing only; no claim)

Result: found. Polyphosphate is documented in mineralising tissue as a hypothesised or co-located phosphate store and precursor. All rows are abstract level (OpenAlex or Crossref text); none was read in full.

| ID | Source | Sourced statement | Strength |
|---|---|---|---|
| BM1 | Omelon et al., PLoS ONE 4, e5634 (2009), 10.1371/journal.pone.0005634 | polyP co-located with mineralising cartilage and resorbing bone (DAPI); amorphous Ca-polyP complexes lower free Ca and phosphate; alkaline phosphatase cleaves orthophosphate from polyP, favouring apatite. The authors "hypothesize" this as the control mechanism | Hypothesis with co-location data |
| BM2 | Omelon et al., Acta Biomater. 2014, 10.1016/j.actbio.2014.06.008 | In elasmobranch tesserae, alkaline phosphatase activity is co-located with polyP at the mineralisation front; exogenous ALP removed polyP and produced orthophosphate in uncalcified cartilage; "proposed" regulated apatite mineralisation | Measured co-location in a cartilaginous skeleton |
| BM3 | Wang et al., BioMed Res. Int. 2019, 10.1155/2019/5141204 (review) | polyP exposure raises cytokines that drive mesenchymal-stem-cell differentiation to osteoblasts and "accelerates the osteoblast mineralization process" | Review statement |
| BM4 | Docampo et al., Phil. Trans. R. Soc. B 365 (2010), 10.1098/rstb.2009.0179 | Acidocalcisomes are acidic electron-dense organelles rich in polyP complexed with Ca and other cations (eukaryotic microbes) | Cell biology, not bone |
| BM5 | Boonrungsiman et al., PNAS 109 (2012), 10.1073/pnas.1208916109 | Calcium phosphate sits in osteoblast mitochondrial granules and vesicles that carry it to the matrix. The abstract does not name polyP, so a polyP precursor in bone is not shown by this source | Calcium phosphate transport; polyP not identified |
| BM6 | Wan 2019 (PA7) | Abiotic: polyP hydrolysis with Ca2+ at an Al oxide gives amorphous Ca phosphate, which the authors expect could age to hydroxyapatite over months (their inference) | Inference |
| BM7 | Wang 2024 (PA4) | Nacre aragonite plus Na-polyP in Ca-containing medium gives a Ca-polyP coacervate | Abstract result |

### R-P3. Baseline facts printed in the patents (for the baseline rows; no performance claim)

| Row | Patent | Composition as printed | Thickness as printed | Solubility as printed | Processing as printed |
|---|---|---|---|---|---|
| BL1 | US 6,485,866 B1 (Hydro-Quebec; priority 1999-04-07) | Vitreous or partly vitreous binder of an alkali-metal phosphate or polyphosphate (claims 1, 12, 16); example (LiPO3)n with Ketjenblack carbon at 8 vol % of the glass; a KOH-neutralised variant is mentioned | Example: about 3 um after drying on 13 um Al; mixed carbon plus iron phosphate coating about 4 um; "a few microns", preferably under 10 um, more preferably under 4 um | None stated for the coating. The binder is prepared and applied from aqueous solution and is described "in solution in water" | (HPO3)n neutralised with Li2O, LiOH or Li2CO3 to pH 4 to 9 (example near 7); coat; dry at 150 C; cell cycled at 60 C with a polyethylene-oxide electrolyte and LiTFSI |
| BL2 | US 6,844,114 B2 (same family, filed 2002-09-24) | Claims recite alkali-metal borate or polyborate with a conduction additive; phosphate and (LiPO3)n appear in the description only | Same description as BL1: about 3 um example; under 10 um, preferably under 4 um | None stated | Same description as BL1 |
| BL3 | US 8,252,463 B2 (Tsinghua University and Hon Hai Precision; priority 2010-08-27) | Claim 1: film consisting of AlxMyPO4, M one of Cr, Zn, Mg, Zr, Mo, V, Nb, Ta, 3x + ky = 3; the abstract also names AlxMy(PO3)3. Example: 85 % H3PO4 plus Al(OH)3 plus CrO3 in water | 10 to 200 nm; 50 to 60 nm preferred; example 52 nm on 20 um Al foil | Film solubility not stated. The background states AlPO4 particles are water-insoluble | Stir at 80 C, react 2 h each step; dilute with water and Triton; dip coat; dry 80 C for 0.5 h; heat treat 200 C for 1 h (range 100 to 350 C, reaction above 100 C); modifier solvent water or NMP |
| BL4 | US 8,821,969 B2 (same family; method claims) | Method: phosphate source, trivalent Al source and a metal oxide react to a clear solution; coat; heat treat to a protective film | Same description as BL3 | Same as BL3 | Same as BL3 |

Baseline facts: ok. Gap: neither family states the water solubility of the finished film, so the K2 baseline rows must carry "not stated in the patent" for the cured aluminophosphate and for the Li polyphosphate coating, and the "soluble Li polyphosphate" label in the plan rests on the plan's own description, not on a printed solubility value.

### R-P4. Novelty wording for the route layer

Supported by this scan (acknowledge as prior art, or narrow claims):

| # | Wording | Support |
|---|---|---|
| NS6 | In-situ phosphate or polyphosphate films from dosed solution plus Ca or other cations are prior art on steel, including the finding that polyphosphate precipitates and hydrolyses to orthophosphate in competition | PA1, PA3 |
| NS7 | Among the open sources scanned (patent keyword search not possible), none reports a crosslinked, water-insoluble polyphosphate film formed in situ on Al foil in a fluorine-free battery electrode context. The sentence stays true only with all four qualifiers; dropping "in situ" brings in I7 and BL3 (a baked Al(PO3)3-type film on Al foil, solubility not stated), dropping "fluorine-free" brings in I1 (Li polyphosphate on Al, polymer cells, imide salt) | P1 to P5; R-P1 to R-P3 |

Unsupported (do not write):

| # | Wording | Why |
|---|---|---|
| NU13 | "first" or "novel" in any form for the polyphosphate film, the coacervate route, or the combination (NS7 included) | No priority search possible (SG14); patent keyword search not possible |
| NU14 | "Polyphosphate films on aluminium are new" | I1 and I7 are prior Al-foil phosphate and polyphosphate films; PA2a to PA2c show phosphate inhibitors on Al alloys |
| NU15 | "A Ca-polyphosphate coacervate has not been applied to a metal" | Only 2 searches; PA6 shows Ca coacervates are patented for enamel; no metal search was run as such |
| NU16 | "The route avoids hydrolysis" or "a crosslinked film forms before hydrolysis" | PA3 and PA7 show hydrolysis competing with film formation; kinetics of gelation versus hydrolysis is a labelled hypothesis |
| NU17 | "Polyphosphate drives bone mineralisation" | BM1 and BM2 are hypotheses with co-location data; BM5 does not identify polyP |

Counts for this section: supported 2 (NS6, NS7), unsupported 5.

**NS7 verdict: supported only as a scan-limited negative.** It is a statement about what the scanned open sources contain, not about the world. It carries the patent-search gap.

**Patent-search gap (unchanged).** No keyword, classification or citation search of patent databases was possible (no Lens token, rule 3). Read as open full-text pages: EP1582608 A2 and A3, US 8,163,105, US 6,485,866, US 6,844,114, US 8,252,463, US 8,821,969, US 12,478,560. Not covered: other Hydro-Quebec members, Kurita family members beyond EP and US, JP, KR and CN filings, polyphosphate or coacervate coatings on metal foil, and any claim text beyond claim 1 of US 8,252,463 and US 8,821,969.

### R-P5. Gaps in this scan

| Gap | Detail |
|---|---|
| RSC full texts | PA4 and PA5: HTTP 403 on the article page, the pdf address and the DOI link (3 attempts each); abstract-level only. pH, Ca:polyP ratio, binodal data and any gamma_nl for the coacervate are therefore not extracted |
| Wan 2019 | NSF PAR PDF has blank pages 1 to 4 (abstract, methods, Table 1 not readable; 3 attempts: page text, image render, Europe PMC and OpenAlex abstracts). Rate constants (Table 1) and Table S2 are not read; only the text values quoted above |
| Patents | Keyword search impossible (see above); EP1582608 B1 address returned 404 |
| Al polyphosphate inhibitors | 5 searches; no Al-foil or battery polyphosphate film paper found; PA2a to PA2c are abstract level, PA2b is an unreviewed thesis |
| Biomineralisation | Abstract level only; no full text read |
| Chitosan oxidation limit | See `lit/contrary.md` B23; no numeric oxidation potential found in 3 searches |
| Li polyphosphate solubility | No numeric solubility of (LiPO3)n found in 1 search (PA-level); only the Hydro-Quebec text |

## Oxidation-limit related work and printed patent data (PH-W2.3, 2026-10-22)

Fetched headless on 2026-10-22: Google Patents pages (4), arXiv PDF, PMC page, Crossref. RSC pages returned HTTP 403 on 3 attempts each (article HTML, doi.org resolver, article PDF); RSC full text and SI were not read. "n.r." = not retrieved. "(S)" = Crossref abstract only. Values are as printed; none was recomputed.

### W-1. Related work for the oxidation-limit ladder (X7); to be cited, not claimed against

| ID | Source | Computes or measures | Method | Phases covered | Stability windows stated | Relation to our ladder |
|---|---|---|---|---|---|---|
| RW1 | Zhu, He, Mo, RSC J. Mater. Chem. A, 2016, 10.1039/c5ta08574h (SI n.r.; full text 403 x3) | (S) Ab initio electrochemical and chemical stability of solid-electrolyte/electrode interfaces in all-solid-state Li-ion batteries | n.r. (title and abstract only) | n.r.; Li-P-O compounds, LiPON, Li3PO4, Li4P2O7, LiPO3 not confirmed or excluded | n.r. | Ab initio window work on solid electrolytes; cite as method context. Cannot be read as covering or not covering Li-P-O until the full text is retrieved (gap RG1) |
| RW2 | Binninger, Marcolongo, Mottet, Weber, Laino, RSC J. Mater. Chem. A, 2020, 10.1039/c9ta09401f; read as arXiv 1901.02251v2 (same title and authors) | Compares ways to compute the electrochemical stability window of solid electrolytes; introduces the stoichiometry stability method against the phase stability method | DFT, PBE with SSSP Efficiency pseudopotentials; HSE06 tested on LATP, LLTO, LLZO | LGPS, LiPON (Li2PO2N, cell Li45P24O51N21, vacancy composition Li1.875PO2.125N0.875), LLZO, LLTO, LATP, LISICON, NASICON Na3Zr2Si2PO12. No Li3PO4, Li4P2O7 or LiPO3 (text search: no hit) | Stoichiometry stability vs Li, Table 2: LiPON 0.00 to 4.11 V; LATP 0.66 to 3.13 V; LGPS 1.08 to 2.85 V. Text cites measured LiPON windows 0.0 to about 5.0-5.5 V vs Li and XPS decomposition against Li metal | Computed Li-P-O oxynitride and phosphate-framework windows (LiPON, LATP); all Li-referenced, solid-electrolyte context; no Ca or Al orthophosphate or condensed phosphate, no experimental thermochemistry, no uncertainty budget |
| RW3 | Schwietert et al., JACS Au 1, 1488 (2021), PMC8479866, 10.1021/jacsau.1c00228 | Electrochemical stability and reaction mechanisms of solid electrolytes; decomposition window (Li grand-potential phase diagram) against intrinsic window (delithiation/lithiation redox) | DFT, PBE, VASP with PAW; 10 000 random Li configurations per composition, 10 lowest relaxed; reference energies from Materials Project | LPS, LPSB, LPSC, LGPS, LBH, LYB, LOC, LiPON (Li2PO2N), LLZO, LLTO, LATP (Li1.5Al0.5Ti1.5(PO4)3), LAGP (Li1.5Al0.5Ge1.5(PO4)3). Mentions metastable P-O phases in the Li2O-P2O5 range as a reason formation energies mislead; no Li3PO4, Li4P2O7 or LiPO3 computed | Decomposition / intrinsic, V vs Li/Li+: LiPON 0.68-2.64 / 0.00-4.12; LATP 2.17-3.86 / 2.74-3.77; LAGP 2.71-3.98 / 2.31-4.30. Text: LiPON oxidised around 4.3 V (cited experiment) | Computed Li-P-O and Al-containing phosphate (LATP, LAGP) windows; the intrinsic-window idea (kinetic route through delithiation) bears on tier-2 reading. Not a Ca or Al phosphate ladder from tabulated thermochemistry |

RW2 and RW3 both state that computed windows depend on the method (RW2: phase vs stoichiometry stability; RW3: decomposition vs intrinsic). RW3 text recorded for the tier-2 discussion (verbatim): "cyclic (CV) experiments overestimate the actual electrochemical stability window, whereas the prediction of the thermodynamic formation energy of the decomposition products often underestimates the actual electrochemical stability window." RW3 gives the reasons as small contact area and short time scale for CV, and unaccounted reaction mechanism and barrier for formation-energy predictions (cited there to its refs 7 to 10).

Related-work read: RW2 and RW3 in full text; RW1 abstract only (RW2 is the RSC version of arXiv 1901.02251, so the four requested items are three distinct papers). SI of RW1 not retrieved. Gap RG1.

### W-2. Candidate wording NS8 (narrowed), tested

> NS8: no scanned source gives a ladder from tabulated experimental thermochemistry, with uncertainty budgets, of Ca and Al phosphate oxidation limits across condensation states.

**Placement: unsupported list (NU18 below), not the supported list.** Reasons:

1. Ab initio window work for Li-P-O compounds exists and is cited: LiPON and LATP/LAGP in RW2 and RW3; computed Li3PO4 and LiPO3 windows in T7 (0.69-4.21 V and up to 5.00 V, record unreadable); LiPON about 5 V in T8. NS8 is at risk from this and must say so; it survives only as a statement that those windows are computed, Li-referenced, and not Ca or Al.
2. RW1 was not read beyond its abstract; "no scanned source" cannot be asserted while a scanned source is unread.
3. The wording depends on four qualifiers, each only partly checked: Ca and Al (none of RW2, RW3 covers Ca or Al orthophosphate or condensed phosphates, but LATP/LAGP contain Al), experimental thermochemistry (all read sources are DFT), uncertainty budgets (RW2 and RW3 give none for the windows; RW2 states a larger error margin for one literature value), condensation states (no source read spans ortho, pyro and meta).
4. The patent literature stays unsearched (gap G1; patent keyword search not possible).

**What would make NS8 supportable:** RW1 full text and SI read with no Ca or Al phosphate ladder in them; a stated scan-limited form ("among the open sources scanned, patent literature not searched"); and the sentence must name the computed Li-P-O windows as prior work in the same sentence or the one before. Status until then: candidate, not usable.

### W-3. F8: Al(x)M(y)PO4 and Al(x)M(y)(PO3)3 films on Al foil are claimed prior art

State plainly in the Introduction: films of Al(x)M(y)PO4 and Al(x)M(y)(PO3)3, M one of Cr, Zn, Mg, Zr, Mo, V, Nb or Ta, on aluminium foil are claimed in US 8,252,463 B2 and US 8,821,969 B2 (Tsinghua University and Hon Hai Precision; priority 2010-08-27). Our film is not claimed to be new as an aluminophosphate or polyphosphate film on Al; any differentiation rests on the stated hypotheses, not on performance.

Printed performance data and conditions (Google Patents full text, read 2026-10-22; facts only):

| Item | US 8,252,463 B2 | US 8,821,969 B2 | US 6,485,866 B1 (contrast) | US 6,844,114 B2 (contrast) |
|---|---|---|---|---|
| Test cells | None described for the foil. Examples: 1 modifier, 2 coated Al foil, 3 coated separator; no cell, no cycling, no capacity figure for the foil | Same description | Example 3: cathode of ethylene oxide copolymer (55 vol %) with LiTFSI (O/Li 30), V2O5 (40 vol %), Ketjenblack (5 vol %) on the (LiPO3)n-coated Al; 20 um EO-copolymer/LiTFSI separator; Li metal anode; reversible capacity 5.03 C/cm2. Example 4: KPO3 binder with FePO4 and carbon, same set-up | Same examples as US 6,485,866 |
| Electrolyte and salt | Listed generically for a cell: LiPF6, LiBF4 or LiBOB in EC, PC, EMC, DEC or DMC; none used in an example | Same | Solid polymer electrolyte, EO copolymer with LiTFSI (O/Li 30); the description also names LiBF4, LiPF6, ClO4- and TFSI salts in the background | Same |
| Potential or cutoff | None for the foil. Corrosion test is immersion in hydrochloric acid, concentration n.r. in the patent | Same | Recharge upper voltage limit 3.1 V, constant current, charge in 6 h (Example 3); iron phosphate discharge level 3.3 V (Example 4). Background: Al corrosion in TFSI above 4 V can lead to complete disintegration | Same |
| Temperature | Foil dried 80 C for 0.5 h; heat treated 200 C for 1 h; test temperature n.r. | Same | Cycling at 60 C (Example 3) | Same |
| Durations | Immersion in HCl 4 h; no bubbles on coated foil | Same | About 30 cycles (A.S.I. about 100 ohm after about 30 cycles); 6 h recharge | Same |
| Corrosion or capacity statement as printed | Conventional Al foil: "Bubbles are observed ... after a period of time, indicating that the conventional aluminum current collector has been eroding". Coated foil (Example 2): "no bubbles ... for 4 hours"; conductivity "still good"; no number. SEM: many defect holes on bare foil, smooth and dense coated foil. Background: capacity lost on cycling, especially at high temperature | Same text | Coated cell: "good maintenance of the capacity" and A.S.I. about 100 ohm after about 30 cycles; uncoated identical cell: initial capacity loss "about four times higher", high A.S.I. at the start, "confirming the protective role of the coating" | Same text |
| Film thickness | 10 to 200 nm; 50 to 60 nm preferred; example 52 nm | Same | About 3 um (example), under 10 um | Same |
| Cure range | Heat treatment 100 to 350 C, preferably 150 to 250 C, 1 to 3 h; example 200 C for 1 h | Same | Dry at 150 C (example 2); (LiPO3)n from (HPO3)n neutralised to pH 4 to 9 | Same |
| Claims | Film of AlxMyPO4 on metal plate | Method claims | Claims 1, 12, 16: alkali-metal phosphate or polyphosphate vitreous binder | Claims borate or polyborate only; phosphate in the description |

Not printed in any of the four: oxidation limit or window of the film; solubility of the finished film; fluorine-free electrolyte test; test on aluminophosphate in a lithium-ion cell. The two Tsinghua/Hon Hai patents print an acid-immersion bubble observation, not a cell result. The Hydro-Quebec cell result is for polymer electrolyte at 60 C with an upper limit of 3.1 V, below the 4.3 to 4.5 V cutoffs of our ladder. Patent family members and claims beyond these four were not read (gap G1).

### W-4. NS1 to NS5 and NU1 to NU10

Unchanged: the rows at "P5" (NS1 to NS5, NU1 to NU10) were not edited by this session; only new sections were appended (verified by diff).

### W-5. New unsupported-list row

| # | Wording (or any paraphrase) | Why it is not supported |
|---|---|---|
| NU18 | NS8 in any form: "no scanned source gives a ladder from tabulated experimental thermochemistry, with uncertainty budgets, of Ca and Al phosphate oxidation limits across condensation states" | RW2, RW3, T7 and T8 give computed Li-P-O windows (LiPON, LATP, LAGP, Li3PO4, LiPO3); RW1 unread beyond its abstract; patents unsearched (G1). Narrow form allowed only after RG1 closes, with the computed work named |

### W-6. Gaps

| ID | Gap |
|---|---|
| RG1 | RSC c5ta08574h and c9ta09401f full text and the c5 SI: HTTP 403 on 3 attempts each (article HTML, doi.org, PDF). c9 content read from arXiv 1901.02251; c5 not read beyond Crossref abstract |
| RG2 | Patent search remains a logged gap: only the four named patents were read; no keyword or classification search, no family or citation check |
| RG3 | HCl concentration and the date of the corrosion observation are not in the Tsinghua/Hon Hai text |

## Lineage support for "nacre-inspired" (PH-W2.4b, 2026-10-22)

Purpose: ruling C2 defines "nacre-inspired" in the Introduction as the biomineral lineage: an amorphous precursor (amorphous calcium carbonate, ACC) transforming under an organic matrix (chitin, silk-like proteins, polyelectrolytes), with chitin and chitosan as the structural polysaccharide. Each statement below is tested against open sources read on 2026-10-22 (Europe PMC full-text XML or the PMC article page, headless; one attempt each unless noted). "Full" = full text read; "Abs." = abstract only. Quoted text is as printed. No source here is a battery or aluminium source; the table says only what each source says about biominerals.

### L-1. Lineage table

| ID | Statement (Introduction wording to be) | Source (DOI; locator) | Read | What the source supports | Verdict |
|---|---|---|---|---|---|
| L1a | (a) Nacre is aragonite platelets within an organic matrix | Sedira et al., Biomimetics 11, 148 (2026), 10.3390/biomimetics11020148; section 1 Introduction ("brick-and-mortar arrangement of aragonite platelets"); section 3.2.1 ("Aragonite crystals ... are nucleated and grown in an organic matrix composed of proteins and chitin") | Full (review) | Nacre is a brick-and-mortar arrangement of aragonite platelets with an organic matrix of proteins and chitin | supported |
| L1a-2 | (a) same | Osuna-Mascaro et al., PLoS ONE 10, e0122934 (2015), 10.1371/journal.pone.0122934; Introduction, opening paragraph | Full | Mollusc shell is a biocomposite of calcium carbonate (aragonite, calcite or, rarely, vaterite) and a small quantity of organic matrix of proteins, polysaccharides and lipids; the organic fraction varies by microstructure and nacre is among the richer ones | supported (shell level; nacre-specific via L1a) |
| L1b | (b) ACC is a documented precursor in nacre | DeVol et al., J. Am. Chem. Soc. 137, 13325 (2015), 10.1021/jacs.5b07931; abstract (Europe PMC) | Abs. | Reports ACC precursors observed at the growth front of nacre in gastropod shells (red abalone, synchrotron spectromicroscopy). The abstract states that ACC precursors in nacre had stayed elusive before and that the phases seen are those of calcite precursors in sea urchin spicules, not proto-aragonite | supported (one direct observation, gastropod nacre, abstract level) |
| L1b-2 | (b) same | Sedira et al. 2026, 10.3390/biomimetics11020148; section 3.2.1 | Full (review) | "Amorphous calcium carbonate (ACC) acts as a precursor in the biomineralisation process, transforming into aragonite"; ACC precursors "observed at the growth front of nacre in gastropod shells" (cites DeVol); proteins and chitin "control the transformation of amorphous calcium carbonate to aragonite" (review statement, cites 183 and 195) | supported (secondary; restates DeVol) |
| L1b-3 | (b) in other biominerals | Gong et al., Proc. Natl. Acad. Sci. 109 (2012), 10.1073/pnas.1118085109; Introduction | Full (PMC page) | ACC is "an important precursor to geologic and biogenic" CaCO3 minerals; sea urchin spicules form via two ACC precursors, one hydrated and one not; formation proceeds through transient amorphous phases | supported (other biomineral: sea urchin spicule) |
| L1c | (c) Chitin is a component of the nacre organic matrix | Osuna-Mascaro et al. 2015, 10.1371/journal.pone.0122934; Abstract and Introduction | Full | Interlamellar membranes of bivalve nacre contain a minor chitin component of thin fibres with a protein coat, embedded in a proteinaceous matrix; the Introduction cites earlier work that the intercrystalline matrix of three mollusc classes is silk-fibroin proteins and beta-chitin | supported |
| L1c-2 | (c) same | Sedira et al. 2026, 10.3390/biomimetics11020148; section 3.2 | Full (review) | "The organic matrix in nacre consists of beta-chitin and silk fibroin-like proteins" | supported (secondary) |
| L1c-3 | (c) chitosan is the deacetylated derivative of chitin | Younes and Rinaudo, Mar. Drugs 13, 1133 (2015), 10.3390/md13031133; section 1 Introduction and "Chemical structure of chitin and chitosan" | Full | Chitin becomes chitosan "by partial deacetylation under alkaline conditions"; chitosan is a random copolymer of N-acetyl-D-glucosamine and D-glucosamine with a degree of acetylation DA | supported, with "partly deacetylated" as the exact wording |
| L1c-4 | (c) chitosan as a component of the nacre organic matrix | Sedira et al. 2026; Osuna-Mascaro et al. 2015 | Full | Chitosan appears in Sedira only as the polymer of nacre-inspired composites (chitosan-based and BNNS-chitosan films). Osuna-Mascaro has no mention of chitosan. No source read states chitosan occurs in natural nacre | unsupported (see flags) |
| L1d | (d) Amorphous calcium phosphate is a precursor in bone | Mahamid et al., Proc. Natl. Acad. Sci. 107, 6316 (2010), 10.1073/pnas.0914218107; abstract and Introduction | Full (PMC page) | In zebrafish fin rays, new mineral is delivered as packages of ACP nanospheres that transform into apatite platelets in the collagen matrix. The Introduction says ACP as precursor in bone had been debated for decades and that earlier studies were "consistent with" it but lacked direct in situ observation | supported for zebrafish fin bone; mammalian bone not covered by this source |
| L1d-2 | (d) polyphosphate in mineralising tissue | Omelon et al., PLoS ONE 4, e5634 (2009), 10.1371/journal.pone.0005634; Abstract, Introduction | Full | PolyP is located (fluorescent staining) in resorbing bone and calcifying cartilage; amorphous Ca-polyP complexes lower free Ca and phosphate; the authors "hypothesize" polyP formation and degradation as a mechanism controlling apatite saturation, and propose it as a regulator, not as a mineral precursor | partly (co-location and a hypothesis; polyP as precursor is not stated) |
| L1d-3 | (d) polyP and bone, other | BM2 to BM5 of section R-P2 | Abs. | Co-location, review statements, cell biology; BM5 does not name polyP | partly (abstract level, unchanged from PH-W2.2a) |

### L-2. Verdicts for the four statements

| Statement | Verdict | Basis |
|---|---|---|
| (a) Nacre is aragonite platelets within an organic matrix | supported | L1a, L1a-2 |
| (b) ACC is a documented precursor in nacre and other biominerals | supported (nacre: one direct observation in gastropod nacre, abstract level for DeVol; other biominerals: sea urchin spicule, full text) | L1b, L1b-2, L1b-3 |
| (c) Chitin is a component of the nacre organic matrix; chitosan is its deacetylated derivative | supported for chitin and for the chemistry ("partly deacetylated"); chitosan in the nacre matrix is unsupported | L1c to L1c-4 |
| (d) Polyphosphate or amorphous calcium phosphate as a precursor in bone and other biomineralisation | partly: ACP as a precursor is supported in zebrafish fin bone (Mahamid 2010); polyphosphate as a precursor is supported by no source, only as co-located and hypothesised (Omelon 2009, 2014) | L1d, L1d-2, L1d-3 |

### L-3. Flags for the Introduction wording

1. **Chitosan is not shown to be in nacre.** Write that chitin is a component of the nacre matrix and that chitosan is its partly deacetylated derivative, used here as the processable form; do not write that nacre contains chitosan. The phrase "chitin and chitosan as the structural polysaccharide" is supported for chitin only.
2. **Polyphosphate as a biomineral precursor is unsupported.** What is supported is ACP as a bone precursor (zebrafish fin) and polyP as a co-located, hypothesised regulator. Any sentence that makes polyP a precursor of bone mineral is the NU17 wording and stays unwritten.
3. **Polyelectrolytes** in the matrix were not tested against a source in this session. Osuna-Mascaro and Sedira name acidic proteins, which are polyelectrolytes, but neither calls the matrix a polyelectrolyte; the word should carry a source or be dropped.
4. **Scope of the ACC statement.** The nacre observation is one direct observation in gastropod (abalone) nacre; DeVol's abstract says earlier evidence was inferred from other shells. Write "documented" for the lineage, not "universal".
5. **Zebrafish fin is a bony fish skeleton**; the sentence should say fin bone, not bone in general.

### L-4. Gaps

| ID | Gap |
|---|---|
| LG1 | DeVol 2015 is abstract level (Europe PMC); no open full text found in one search. A primary full-text read of the nacre ACC observation is open |
| LG2 | Gong 2012 and Mahamid 2010 were read from the PMC article pages (author manuscripts); the Europe PMC full-text service returned HTTP 500 for them (1 attempt), so the PMC page was the second route. Mahamid 2008 (PMC2529085) returned a bot check page (1 attempt, recorded, not retried) |
| LG3 | No source read states chitosan occurs in nacre, and none covers polyelectrolytes as a matrix class (flags 1 and 3) |
| LG4 | No source read gives polyphosphate as a precursor in bone (flag 2); Omelon 2014 and the R-P2 rows remain abstract level |
| LG5 | Patent search remains a logged gap (RG2); this section needs no patent source |

## Coatings on aluminium and aragonite conditions (PH-W2.5, 2026-10-22)

Scope: decision D69. In-situ aragonite is a literature question and a hypothesis route; no screen change. Retrieval was headless (OpenAlex, Crossref, Europe PMC, publisher pages). "Full" = full text read; "Abs." = abstract only; "Title" = title and metadata only (full text refused, 3 attempts: Crossref, OpenAlex, doi.org HTTP 403). Searches run: OpenAlex free-text and title-and-abstract queries for CaCO3, calcium phosphate and hydroxyapatite on aluminium or its alloys, nacre-like, brick-and-mortar and layer-by-layer coatings on aluminium, and current-collector films (about 35 queries); the Semantic Scholar tool was rate-limited (3 attempts). The patent search stays a logged gap (RG2).

### A-1. Coatings table

| ID | DOI | System | Method | What the source shows (film; protection test; conditions) | What it does NOT show |
|---|---|---|---|---|---|
| CA1 | 10.1007/s44371-026-00673-x (Abs.) | CaCO3 scale on Al and Cu buttons, HEDP present | Heated aqueous solution, 100 C, bottom and suspended heating | XRD: scale on Al is calcite only; sludge is calcite plus vaterite; no corrosion test in the abstract | Not a coating made on purpose; no protection test; 100 C; no aragonite on Al |
| CA2 | 10.1016/j.matdes.2022.111073 (Abs.) | CaCO3 coating on Mg2Zn0.2Ca alloy (Mg, not Al) | Hydrothermal, MgSO4 0 to 20 mM in the bath | Coating with aragonite, vaterite and a calcite middle layer; corrosion resistance rises with MgSO4 up to 20 mM then falls; test not named in the abstract | Not aluminium; hydrothermal, not room temperature; pH not in the abstract |
| CA3 | 10.3390/jcs5100280 (Abs.) | CaCO3 and Ag particles inside an Al matrix composite | Stir casting; weight loss in neutral and acidic media | Corrosion rate fell with reinforcement content | A bulk composite, not a film on Al; no carbonate formation from solution |
| CA4 | none found | CaCO3 film on Al or Al alloy from solution, with a matrix, or by electrodeposition | About 12 queries (OpenAlex, 2 failed Semantic Scholar) | No source located for a deliberate CaCO3 film on Al | A negative from this search only; patents unsearched |
| CP1 | none found | Calcium phosphate or hydroxyapatite on Al or Al alloy | About 8 queries | No source located; hits are on Mg, Ti and steel | Same limit as CA4 |
| CP2 | 10.1038/s41598-017-16985-z (Abs.) | Electrodeposited hydroxyapatite on Ti64 (not Al) | Electrochemical deposition, electrolyte pH 5 and 6 | Protection efficiency about 89 % (pH 5) and about 93 % (pH 6) from corrosion tests in the abstract | Not Al; acidic bath; test medium not read |
| NL1 | 10.3389/fchem.2021.810886 (Full) | "Nacre" coating (pearl powder, NaH2PO4, Na2EDTA) on AZ91D Mg alloy | Hydrothermal, 363 K, 6 h, bath pH 5.5, 8.5, 11.5 | Coatings Ca- and P-rich; Ecorr and breakdown potential higher and icorr lower than bare AZ91D in simulated body fluid (polarization, EIS); pH 5.5 bath gave the thickest coating and lowest icorr | Not Al; not layered by design; phase identity not extracted here; not a battery medium |
| NL2 | 10.1038/s41529-023-00415-9 (Full) | Oriented graphene oxide in waterborne polyurethane, layered like pearl layers; steel (Q235) | Cast coating; EIS and SVET in 3.5 wt% NaCl | Impedance modulus one order of magnitude above the blank coating | Organic-GO lamellae, no mineral; steel, not Al |
| NL3 | 10.1016/j.porgcoat.2025.109778 (Title) | NH2-BNNS/epoxy lamellar coating, nacre-inspired by title | Not read | Title only | Substrate and test unknown |
| NL4 | 10.1016/j.electacta.2017.11.046 (Title) | Polymer-clay nanocomposite pretreatment on Al alloy 2024-T3 | Not read | Title shows a layered-silicate polymer coating on an Al alloy; nothing else read | Whether it is brick-and-mortar, and any test, unknown |
| NL5 | 10.1016/j.porgcoat.2026.110302 (Title) | Nacre-like polyelectrolyte coating for radiative cooling and corrosion | Not read | Title only | Substrate and test unknown |
| NL6 | none found | Nacre-like or brick-and-mortar mineral-polymer coating on Al, corrosion purpose | About 10 queries | Not located as a mineral-polymer film on Al; NL4 is the closest Al item and was not read | Same limit as CA4 |
| BC1 | 10.1038/s41529-024-00453-x (Full) | Al current collector, carbonate-ester Li-ion electrolytes | Electrochemical tests of bare Al | Passivation layer re-forms and Al is consumed; breakdown tied to ethylene carbonate adsorption at 4.4 V and 4.8 V | Bare foil only; no CaCO3 or Ca phosphate film |
| BC2 | none found | CaCO3 or Ca phosphate film on an Al collector | About 6 queries; earlier rows I1, I7 and row 3 (phosphate and polyphosphate on Al) stay the phosphate prior art | No carbonate collector film located | Same limit as CA4 |

Counts: rows 14; carbonate on Al as a deliberate film: none found (CA1 is scale; CA3 is bulk); phosphate on Al: none found in this scan (earlier phosphate rows unchanged); nacre-like on any metal: found (NL1 on Mg with mineral; NL2 on steel, organic); on Al: not read, NL4 title only; battery collector: none found.

### A-2. Polymorph conditions

Room temperature, aqueous. "Fraction" = what the source states. Compatibility with an alkaline electrode slurry (pH 10 to 13, Li+, Mg2+ absent unless added): yes, partly, no.

| ID | DOI | Conditions giving aragonite | Fraction reported | Compatible with a pH 10 to 13 slurry |
|---|---|---|---|---|
| PM1 | 10.1002/advs.202203759 (Full) | Mg2+: Ca2+ 10 mM, Mg2+ 50 mM (ratio 5), ammonium carbonate diffusion, pH about 9, glass substrate; mixtures at ratio below 5 | Pure aragonite at Mg:Ca = 5; calcite plus aragonite below that | No: needs Mg2+ at 5 times Ca2+; pH about 9, not 10 to 13 |
| PM2 | 10.1002/advs.202203759 (Full) | Polyamine (branched PEI) 1e-3 mg/mL, Ca2+ 10 mM, same method, no Mg2+ | Pure aragonite at that dose; calcite plus aragonite at 1e-5; calcite again at 0.1 mg/mL | Partly: no Mg2+ needed; pH about 9; cationic polymer, window is narrow |
| PM3 | 10.1073/pnas.1423898112 (Abs.) | Calculation: calcite nucleation barrier exceeds aragonite's in solutions with seawater-like Mg:Ca | Not an experiment | No for Mg2+-free; no pH 10 to 13 case |
| PM4 | 10.1021/acs.cgd.0c00152 (Abs.) | Inorganic seawater-type solutions with Mg2+; aragonite with a disordered core (Na, Mg, sulfate) | Not stated in the abstract | No: Mg2+ required; sulfate not required |
| PM5 | 10.1007/s44290-025-00291-z (Abs.) | Precipitation vs pH and temperature, below 50 C and at pH 7 to 12.5 | No aragonite at any pH; calcite 98 % at pH 12; vaterite 83 % at pH 8.4; aragonite appears 50 to 85 C, 96 % at 80 C | No: at pH 12 the product is calcite, and aragonite needs elevated temperature |
| PM6 | 10.1126/science.271.5245.67 (Abs.) | Aragonitic-shell macromolecules pre-adsorbed on beta-chitin and silk fibroin substrate | Aragonite induced; fraction not in the abstract | Not tested at pH 10 to 13; conditions not read |
| PM7 | 10.1021/acs.cgd.3c00102 (Full) | Mg/Ca 2 to 5 (Mg 20 to 40 mM), ammonium bicarbonate diffusion, aspartic and glutamic acid, chitin | High-Mg calcite and disordered dolomite; no aragonite claim | No: aragonite not the product |
| PM8 | 10.1002/advs.202203759 (Full), citing refs 48 to 52 | Review lines: additive-free narrow supersaturation window; gel column; nanopores; CO2/NH3 microbubbles at pH 9.7 to 10.5; constant composition at an optimal pH of 11 | Reported as high aragonite fractions; not read at source | Partly: pH 9.7 to 11 reported in two cited studies, not read, no Li+ |
| PM9 | 10.1021/jacs.5b07931 (Abs.) | ACC precursors at the growth front of gastropod nacre; ACC phases seen resemble those preceding calcite in sea urchin spicules; proto-aragonite found in coral | Direct observation in one gastropod | Not a solution condition |
| PM10 | 10.1021/acs.cgd.0c00152 (Abs.) | ACC core inside abiotically formed aragonite | Visualised; no fraction | Same as PM4 |
| PM11 | 10.1016/j.chemgeo.2012.12.014 (Title) | Carbonate accumulation rate, Mg2+, polyaspartic acid, 6 to 40 C | Not read | Not assessable |

Plain statement: the sources read give room-temperature aragonite from solution only with Mg2+ at about 5 times Ca2+ or with a cationic polyamine at low dose, both at pH about 9. The one source that scanned pH (PM5) found calcite at pH 12 and no aragonite at any pH. No source read gives aragonite at pH 10 to 13 with Li+ present and Mg2+ absent. PM8 cites pH 9.7 to 11 results that were not read. Compatibility with an alkaline slurry: **no, with one open lead (PM8, refs 51 and 52, unread)**.

### A-3. In-situ carbonate route (hypothesis route, D69)

**Route R4 (hypothesis, not a result).** The route would need amorphous calcium carbonate to form in the slurry or at the foil under an organic matrix, hold long enough to transform to aragonite on the Al surface, and leave an adherent film. The screen covers K2 (solubility at the processing pH) for aragonite and calcite, and nothing beyond that. The screen cannot say that aragonite forms, that a film forms, that anything resists corrosion, or that a layered structure results. Tests would be the experiment list: XRD or Raman phase fraction of the product from slurry-like solutions (pH 10 to 13, Li+, with and without Mg2+ and matrix); SEM of the foil surface and cross-section; electrochemical measurement of the foil in the slurry medium; and a time series for ACC. No claim is made that any of these succeed.

### A-4. Layering in nacre

Nacre is described as a lamellar composite of aragonite and organic sheets (DeVol et al., 10.1021/jacs.5b07931, abstract, read 2026-10-22). Polyamine-grown aragonite platelets are described as stacks comparable to structures in developing nacre (10.1002/advs.202203759, Full). The layering in nacre comes from organic interlayers between aragonite platelets; the word "thin" and the interlayer thickness are not in the abstracts read (gap LY1). **Statement (no source for it, and none sought):** alternating aragonite and calcite layers is not a nacre-like structure.

### A-5. Novelty effect

| ID | Finding | Effect on existing wording (no existing item edited) |
|---|---|---|
| NE1 | CA4, CP1, BC2: no deliberate CaCO3 or Ca phosphate film on Al located | Keeps N1 and NS7 narrow; adds nothing supported beyond "none located in about 35 queries"; a negative from search, not priority |
| NE2 | NL1: nacre-named Ca-P coating on Mg alloy with measured corrosion resistance | Reinforces U3 and the NU series: no "nacre-inspired protective coating" priority; NS items on nacre-like coatings must name Mg, steel and Al separately |
| NE3 | NL2, NL3 to NL5: nacre-like or layered coatings for corrosion exist on other metals (steel read; others by title) | Any NS item on layered corrosion coatings must be limited to "aluminium foil in a battery slurry"; NU1 to NU18 stand |
| NE4 | PM5: no aragonite at any pH including 12, calcite 98 % at pH 12 | NU18 and NS8 are unaffected (phosphate ladder); a new unsupported row is suggested: "aragonite forms in an alkaline slurry" |
| NE5 | CA1: scale on Al is calcite | "A CaCO3 layer on Al" stays unsupported for aragonite (U9) |

Suggested new unsupported rows (not inserted into the existing list):

| # | Wording | Why |
|---|---|---|
| NU19 | "Aragonite forms on Al foil in an alkaline electrode slurry" or "in-situ aragonite is expected at pH 10 to 13" | PM5 shows calcite at pH 12 and no aragonite; PM1 and PM2 are at pH about 9; PM8 leads unread |
| NU20 | "Alternating aragonite and calcite layers are nacre-like" | A-4: layering in nacre comes from organic interlayers; no source for the alternation |

### A-6. Gaps

| ID | Gap |
|---|---|
| CG1 | Full text refused (HTTP 403, 3 attempts each: Crossref, OpenAlex, doi.org): 10.1016/j.porgcoat.2026.110302, 10.1016/j.electacta.2017.11.046, 10.1016/j.porgcoat.2025.109778, 10.1016/j.corsci.2022.110812 (Title or none) |
| CG2 | 10.1007/s44371-026-00673-x and 10.1007/s44290-025-00291-z: publisher page empty or 403, PDF not served; abstract read via OpenAlex |
| CG3 | 10.1073/pnas.1423898112 and 10.1073/pnas.1811696115: PNAS 403; abstract only (the second returned no abstract); Mg:Ca threshold value not read |
| CG4 | Semantic Scholar tool rate-limited on 3 attempts; no citation chaining done |
| CG5 | Cited studies for aragonite at pH 9.7 to 10.5 and pH 11 (PM8 refs 51, 52) not identified or read |
| CG6 | Li+ effect on CaCO3 polymorph: one search, no relevant source |
| LY1 | Thickness and "thin" wording of nacre interlayers: no source read states it |
| RG2 | Patent search remains a logged gap |

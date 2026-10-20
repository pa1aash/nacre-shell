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

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

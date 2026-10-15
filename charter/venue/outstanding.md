# Outstanding items

Everything not reachable or not found, merged from the three retrieval passes (V1 manuscript, V2 artwork, V3 template). Every www.rsc.org request returned HTTP 403 to the headless client, so all RSC page content was read from Wayback snapshots (via: wayback in the data).

## Outstanding items, V1 (manuscript rules, RSC Advances)

Fields with value null in manuscript.yaml. For each, the pages searched were the RSC Advances author-guidelines page, the data-sharing page, the supplementary-information page, the experimental-reporting page, the author-responsibilities page and the article-templates page (final URLs in manuscript.yaml). Live fetches returned HTTP 403, so every page came from the Wayback Machine. Attempts: one fetch per page plus a text search of the fetched text.

| Field | Looked for | Result |
|---|---|---|
| title.max_characters | a title length limit | not stated; only "as short as possible" (recorded) |
| keywords.count | number of keywords | no keyword requirement on any page |
| keywords.separate_field_required | a separate keywords field or list | not stated |
| figures.max_count | cap on figures | not stated |
| tables.max_count | cap on tables | not stated |
| references.max_count | cap on references | not stated |
| esi.citation_in_main_text_format | how the SI is cited in the main text | not stated (only: refer to multimedia files in the paper; note SI references in the data availability statement) |
| esi.max_file_size | SI file size limit | only "large files may be hard to download" |
| section_headings.required_order_full | full required section order | only the order Conflicts of interest, Data availability, Acknowledgements is stated |
| units.si_required | SI units / nomenclature rule | no general rule; only technique-specific reporting forms |
| nomenclature.standard | IUPAC or other naming rule | not stated for the manuscript |
| line_numbers.required, font.required, spacing.required, page_size.required | layout rules | none stated; template use is optional |

## Pages not reached

- https://www.rsc.org/publishing/journals/guidelines/ : live HTTP 403; Wayback attempt hit a connection error (WinError 10061) while other fetches ran in parallel; not retried. It is only the journal list; the RSC Advances guideline page was reached via the link found in the cached rsc.org page.
- https://pubs.rsc.org/en/journals/journalissues/ra : reached via Wayback (snapshot 2026-06-18); it links to the guidelines list above, not to a journal-specific page.
- Other transient failures (parallel runs, connection refused) succeeded on a sequential retry for: publish-a-journal-article, preparing-supplementary-information, experimental-reporting, data-sharing, author-responsibilities, article-templates.
- All live rsc.org requests: HTTP 403 (bot block). Wayback fallback worked for every reached page.

## Notes

- Two RSC pages differ on SI references: the RSC Advances guidelines allow them in the main reference list; the general SI page asks for a separate list in the SI document. Both are recorded.
- The RSC Advances guideline page is a 2026-08-06 Wayback snapshot.
- The author-contributions section position within the end matter is not stated.
- Shared scratchpad: a script named gen.py in the shared scratchpad belongs to another subagent. It was run once by mistake and regenerated charter/venue/artwork.yaml (same content, new timestamps) and added fetch-log rows. Not otherwise harmful.

## Outstanding items (V2, RSC Advances artwork)

## Null fields (not stated on any reachable official page)

For every field below, the RSC Advances author guidelines page (section "Figures, graphics and images", "Table of contents entry", "Photographs", "Chemical structures"), the experimental-reporting page, the data-sharing page, the supplementary-information page and the journal landing page were read; none states the rule. URLs under https://www.rsc.org/publishing/publish-with-us/publish-a-journal-article/ (rsc-advances, experimental-reporting, data-sharing, preparing-supplementary-information) and https://www.rsc.org/publishing/journals/rsc-advances, plus the pubs.rsc.org journal page. No errors; each fetched once or twice.

- figure.min_font_size: looked for a general minimum text size. Only the structure-label size (7 pt) and a legibility statement exist; recorded as structure.label_font_size.
- figure.font_recommendation: looked for a general font. Only Arial/Helvetica for structure labels is stated (structure.label_font).
- figure.line_weight: looked for general line weights. Only ChemDraw bond widths are stated (structure.*).
- figure.colour_mode: looked for RGB/CMYK. Not stated; page only says colour is free.
- figure.min_resolution_line_art / _halftone / _combination: the page gives one 600 dpi figure for all artwork (figure.min_resolution), with no per-type split.
- figure.panel_label_convention: looked for panel letters, case, placement. Not stated.
- figure.caption_format_rules: looked for caption/legend layout rules. Only caption content items (numerical reference, permission, alteration notes) are stated.
- figure.min_height: not stated (only a maximum).
- table.formatting, table.placement, table.footnotes, table.width: no table-formatting page found. The linked Word template user guide (PDF, .../using-the-template.pdf) and the Word/LaTeX templates were not parsed (binary formats; V3 handles the LaTeX template). The author guidelines page says only that tables and figures should not duplicate data.

## Pages not reached live / notes

- Every www.rsc.org page returned HTTP 403 live (headless). All were read through the Wayback fallback (via: wayback). Snapshot dates are in each source_url (e.g. 20260806170935 for the RSC Advances guidelines page, 20260823224537 for experimental-reporting). Live equality is not verifiable headlessly.
- Wayback occasionally refused connections (WinError 10061) on a first attempt for https://www.rsc.org/publishing/publish-with-us/publish-a-journal-article; a retry succeeded.
- https://submission-checker.rsc.org: reached live (200) but is a JavaScript application with no usable static text; no alternative page found stating figure checks.
- Discovery note: https://www.rsc.org/ -> /publishing/publish-with-us/publish-a-journal-article (journal list is paginated, 12 of 57 shown, so the RSC Advances link was not in the fetched HTML). The RSC Advances guidelines URL was fetched by following the page's slug pattern (all other journals link as .../publish-a-journal-article/<slug>), and corroborated by https://pubs.rsc.org/en/journals/journalissues/ra, which links to https://www.rsc.org/publishing/journals/guidelines/ (reached via wayback).
- https://www.rsc.org/publishing/journals/processes-and-policies/author-responsibilities was fetched (wayback) but no artwork rules were found; not cited.

## Outstanding items (V3, RSC LaTeX template)

1. Live asset download blocked. URL: https://www.rsc.org/getContentAsset/5484c665-5d01-46eb-9b23-121b16e8ecd4/f4c91d86-ac3e-4675-bdf3-f8325ded9710/royal-society-of-chemistry-article-template.zip?language=en&v=638889698008795103 returned HTTP 403 (also without the query string). Wayback has no capture of the exact query-string URL (404); the capture of the query-less URL dated 20250909050504 was used (via wayback). Equality with the current live file cannot be confirmed. The operator may download the live zip and compare against sha256 e481548ff4c520b25e341dcf84a55bc58752064fd1e584a834f7c2767174b6c5.
2. Licence ambiguous. Only rsc.bst carries an explicit grant (LPPL 1.3c or later, author Joseph Wright, maintained by him). main.tex and the head_foot images carry an RSC copyright line only. No licence statement was found on the source page. Decision: local-only. Written confirmation from RSC would be needed to commit the template.
3. Archive inconsistencies: README.txt names rsc-articletemplate.tex and .pdf, but the archive holds main.tex and Royal_Society_of_Chemistry_article_template.pdf. head_foot/journal_name.pdf is generic; no RSC Advances-specific masthead found. The template has no graphical abstract or keywords placeholder.
4. Not fetched (out of scope for V3): the Supplementary Information preparation page and the RSC Advances journal page. Wayback worked for rsc.org pages; pubs.rsc.org returned 403 live on the one request logged.
5. The Wayback CDX endpoint refused one connection transiently; a retry worked.

## Operator and later-session actions

- Download the live template archive in a normal browser and compare its sha256 with charter/venue/template.yaml (the recorded copy is a 2025-09-09 Wayback capture).
- Ask RSC (or find explicit licence text) if committing the template is wanted; until then it stays local-only.
- Table rules, panel-label conventions, colour mode and a general minimum font size were not stated on any reachable page; the Word template user guide may hold them (not parsed).

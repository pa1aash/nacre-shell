# Venue constraints (RSC Advances)

Structured, sourced data for the journal the manuscript is built against. Nothing here is written from memory: each value was retrieved from an official Royal Society of Chemistry page by `nacre.report.fetch`.

| File | Content |
|---|---|
| `manuscript.yaml` | manuscript rules: article types, abstract, references, statements, data policy, ESI |
| `artwork.yaml` | figure, table-of-contents entry and table rules |
| `template.yaml` | provenance, file hashes and licence finding of the LaTeX template |
| `outstanding.md` | what could not be reached or was not stated, with the attempts made |
| `fetch_log.jsonl` | one row per request: utc, url, final_url, via, status, bytes, sha256, content_type, error |
| `_cache/` | raw responses (git-ignored, local only) |

## Field schema

`manuscript.yaml` and `artwork.yaml` hold a `fields` mapping. Every field has:

- `value`: transcribed as stated by the page, or `null` when no official page states it;
- `unit`: when the value has one;
- `source_url`: the official page;
- `locator`: section heading or anchor on that page (a locator, not prose);
- `retrieved_utc` and `via` (`live` or `wayback`);
- `snapshot_utc`: when `via` is `wayback`, the capture time of the snapshot that was read.

Values are never rounded or converted. A needed conversion is a separate `derived_*` field naming its source field. A `null` value has a matching entry in `outstanding.md`.

## Refreshing

- `uv run nacre venue fetch` re-fetches every source page and the template archive and reports pages whose hash changed, pages now unreachable, and recorded values no longer found in the page text. It writes no data file; update the yaml by hand-reviewed re-extraction if it reports a difference.
- `uv run nacre venue show [--file manuscript|artwork] [--prefix <name>]` prints the recorded values and the coverage counts.
- `uv run nacre venue check` runs the consistency checks (every value has a source and retrieval time; no long copied passages).

## Third-party material

Only short factual values with locators are committed. The template archive is local-only unless its licence explicitly permits redistribution; see `template.yaml` for the decision and its basis.

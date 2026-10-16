# Fetch log

Third-party canonical texts are downloaded, never typed. One row per fetch.

| Item | Source URL | Retrieved (UTC) | sha256 | HTTP |
|---|---|---|---|---|
| LICENSE (MIT; body field with [year] and [fullname] substituted) | https://api.github.com/licenses/mit | 2026-10-04T23:54:33Z | 73dbe6020aa3baac414a5eb68dab0668d6a7beb2010e0f4c46ae651211d239f8 | 200 |
| LICENSE-DATA (CC BY 4.0, verbatim) | https://creativecommons.org/licenses/by/4.0/legalcode.txt | 2026-10-04T23:54:34Z | 9ba9550ad48438d0836ddab3da480b3b69ffa0aac7b7878b5a0039e7ab429411 | 200 |
| Materials Project database 2026.04.13: thermo entries, 9 files (1 slurry system, 8 cell systems), 2,090 entries (P0-W5.1) | Materials Project API via mp-api 0.46.5 (`get_entries_in_chemsys`, thermo type GGA_GGA+U, compatible entries) | per file in `results/preprint/pourbaix/cache/manifest.json` (P0-W5.1 gives 2026-10-16) | per file in the same manifest; manifest sha256 `a0d055c72668051fd7568d7d0e689742a0b1a6aa8d4f9d772be8c6a210dbebb4` (P0-W5.1) | not recorded in P0-W5.1 |
| MPContribs `ion_ref_data`, 362 ion records (P0-W5.1) | Materials Project via `MPRester.get_ion_reference_data` | per file in `results/preprint/pourbaix/cache/manifest.json` | per file in the same manifest | not recorded in P0-W5.1 |
| NIST-JANAF tables O-029 (O2) and C-095 (CO2) (P0-W5.1) | URL stored in each of `janaf_O2.json` and `janaf_CO2.json` | per file in the manifest | per file in the manifest | not recorded in P0-W5.1 |
| Materials Project documentation export, licence search: no licence found (P0-W5.1) | not stated in P0-W5.1 | not stated in P0-W5.1 | not stated in P0-W5.1 | not stated in P0-W5.1 |
| Materials Project terms page (P0-W5.1): no content, licence text outstanding | https://materialsproject.org/about/terms | 2026-10-16 (P0-W5.1) | none | 403 |
| RSC article template archive, via `nacre paper template --ensure`; archive sha256 and 17 file hashes verified, unpacked to the local-only `paper/rsc_template/` (P0-W8.1) | https://web.archive.org/web/20250909050504id_/https://www.rsc.org/getContentAsset/5484c665-5d01-46eb-9b23-121b16e8ecd4/f4c91d86-ac3e-4675-bdf3-f8325ded9710/royal-society-of-chemistry-article-template.zip (pinned fallback URL of `charter/venue/template.yaml`; Wayback capture 20250909050504) | 2026-10-16 ~09:30Z (P0-W8.1) | e481548ff4c520b25e341dcf84a55bc58752064fd1e584a834f7c2767174b6c5 (match, P0-W8.1) | not recorded in P0-W8.1 |

The sha256 values are of the bytes written to the repository file.

Rows from P0-W5.1 and P0-W8.1 are copied from those reports and from the records they cite; a field the report does not state is marked as such and is not reconstructed.

# Requirements to re-check live before C2

Ruling B8 (`ops/tracks/p0.yaml`): Palaash re-checks the ChemRxiv and RSC policy pages live before C2. This file lists what to re-check and what to look at on each page.

## Why every point is on this list

Live chemrxiv.org and www.rsc.org return HTTP 403 to headless clients. Every requirement used by the package therefore comes from a Wayback capture:

- the ChemRxiv policy pages, T1 to T3 in `ops/policy/p0/index.yaml`, captured in 2025;
- the ChemRxiv browse page P1 in `preprint/package/fetch_index.yaml`, captured in December 2025;
- the RSC pages, T4 and T5, captured in 2026.

ChemRxiv appears to have moved to a new hosting platform during 2026 (`ops/policy/p0/requirements.md`, source caveat). No `/engage/` page has been captured since January 2026, and the captures of the new platform are challenge pages or assets. The ChemRxiv rules may therefore have been superseded in substance, not only in wording.

## Step 0: the platform move

- [ ] Open https://chemrxiv.org and note where the submission and author-information links now go. Record the new URLs beside the old ones below.
- [ ] Check whether ChemRxiv is still run by the same organisations, and whether the Terms of Submission have a new date or version.
- [ ] If an old `/engage/` URL redirects, re-check against the page it lands on. If it is gone, find the equivalent page from the site's submission or author-help menu.

## ChemRxiv

| Point | Captured source | Captured URL (2025) | What to look at live |
|---|---|---|---|
| Accepted content and status of the work | T1-2, T2-1 | `…/engage/assets/public/chemrxiv/term/author-faq.htm`, `…/term/policy.htm` | Is a working paper still accepted? Is it still excluded once accepted or published after peer review, or posted on another server? |
| Content type | T1-1 | `…/term/submission-guide.htm` | Is "Working Paper" still the type for an article with new results? |
| Form steps and order | T1-1 | same | Do the steps still run authors, then content, then supporting material and licence, then review? Are the per-author fields (name, email, institutions) and the institution limits unchanged? |
| ORCID login | T1-1, T2-1 | same; `…/term/policy.htm` | Is an ORCID iD still required for the submitting author? |
| Main file | T1-1, T1-2 | same | Is the main file still one PDF with figures embedded? Is there still no copyediting? Has the recommended figure resolution changed? |
| File size limit | T1-1 | same | None was stated in the capture. Look for one on the live form or help pages. |
| Abstract limit | T1-1 | same | Has the abstract word limit changed? |
| Categories and subcategories | T1-1, P1 | same; `…/engage/chemrxiv/browse-dashboard` | Compare the live main-category list with `metadata.yaml` `categories.offered`. Check the category limits and the rule that the top-listed main category is displayed. The subcategory list was never captured, so read it live. |
| Keywords | T1-1 | same | Is there a limit on the number of keywords, or a controlled vocabulary? |
| Supporting information | T1-1, T1-2 | same | Is SI still uploaded beside the main PDF in any format, with supplementary weblinks? |
| Licences | T1-1, T1-2 | same | Is CC BY 4.0 still offered? Is copyright still retained by the authors? |
| AI-use disclosure | T1-2 | `…/term/author-faq.htm` | Is it still "name of the tool(s) and method of use", placeable anywhere in the text? Does the new form have its own AI-use field? (requirements.md conflicts, item 3) |
| AI tools as authors | T1-1, T1-2, T2-1 | as above | Unchanged: never in the author list or the form? |
| Co-author consent | T3-1, T2-1 | `…/term/terms-of-submission.htm`, `…/term/policy.htm` | Is written notice of the terms to every co-author, with their authorisation, still required? Is any new form or confirmation needed? |
| Authorship criteria | T2-1 | `…/term/policy.htm` | Are the ICMJE criteria still the ones applied? |
| Competing interests | T2-1, T3-1, T1-1 | as above | Is a declaration covering all authors still required in the form and in the content? |
| Funding | T2-1, T1-1, T3-1 | as above | Is "Add Funder" still in the form? Must all grants still be declared? |
| Data availability | T2-1 | `…/term/policy.htm` | Is a Data Availability Statement still expected? Is a data or code deposit now required rather than encouraged? |
| Ethics | T2-1, T1-1 | as above | Is the ethics field still in the form, and is "not applicable" accepted? |
| Screening and decline grounds | T1-1, T1-2 | as above | Have the decline grounds changed (for example a new ground on AI-generated content)? Has the timing changed? |
| Versions and retraction | T1-1, T2-1 | as above | Is a correction still a new version with a short explanation? |

## RSC (later journal route, RSC Advances)

These do not gate C2, but the preprint must not close the journal route.

| Point | Captured source | Captured URL (2026) | What to look at live |
|---|---|---|---|
| Prior preprint posting | T4-5, T4-1 | `https://www.rsc.org/publishing/journals/processes-and-policies`, `…/author-responsibilities` | Is a ChemRxiv preprint still accepted? Is disclosure at submission still the rule? |
| RSC Advances guidelines | T4-3 | `https://www.rsc.org/publishing/publish-with-us/publish-a-journal-article/rsc-advances` | Is there still no preprint restriction of its own? Is the citation format for ChemRxiv preprints unchanged? |
| Licences | T4-2, T4-4 | `…/licences-copyright-and-permissions`, `…/publish-a-journal-article` | Is there any rule on the preprint's licence (the package proposes CC BY 4.0)? |
| AI tools | T4-1, T5-1, V-1 | `…/author-responsibilities`, `…/guiding-principles-for-artificial-intelligence` | Are the three disclosure locations (cover letter, Methods with prompts, Acknowledgements with model or version) unchanged? This is the open ruling in requirements.md conflicts, item 7. |

## Recording the re-check

For each row: the live URL, the date checked, and "unchanged" or the change. Changes that affect the package go into `metadata.yaml` or `submission_checklist.md` before C2.

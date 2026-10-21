# ChemRxiv submission checklist (C2)

What Palaash does at C2, in the order of the ChemRxiv submission form. Each item cites the requirement it comes from: `[T…]` ids are pages in `ops/policy/p0/index.yaml` (paraphrased in `ops/policy/p0/requirements.md`), `[P…]` ids are pages in `preprint/package/fetch_index.yaml`, and `[B…]` or `[D…]` ids are track decisions in `ops/tracks/p0.yaml`. Field values come from `preprint/package/metadata.yaml`.

Every `[T…]` and `[P…]` source is a Wayback capture from 2025 or 2026, not the live site. Items marked **re-check live** are confirmed on the live form or page before they are acted on; `requirements_recheck.md` says what to look at. The form order below is the order of the captured submission guide [T1-1]; if the live form differs, follow the live form and note the difference in the C2 record.

## Before opening the form

- [ ] cp5 has passed; C2 requires it [B3]. Not a policy item.
- [ ] The live policy re-check is done and recorded, using `requirements_recheck.md` [B8].
- [ ] Every co-author has received the Terms of Submission in writing (email suffices) and has authorised the submission, through the P0-W2.4 co-author pack. Keep the replies [T3-1, T2-1]. **re-check live**
- [ ] Everyone who meets the ICMJE authorship criteria is listed, and any authorship question is settled among the authors beforehand [T2-1]. **re-check live**
- [ ] The work is not accepted or published after peer review, and it is not posted on another preprint server [T1-2, T2-1]. **re-check live**
- [ ] The release files are ready from W8: the manuscript PDF with figures and tables embedded, and the SI (`metadata.yaml` `files`) [T1-1, T1-2]. **re-check live**
- [ ] The AI-use sentence is present in the PDF's Acknowledgements, built from `.local/p0/ai_ack.tex`, naming the tool and its method of use [T1-2, B4]. **re-check live**
- [ ] The contact details for every co-author are at hand from the local-only list `.local/p0/authors_contact.yaml` [T1-1]. **re-check live**
- [ ] No size limit was found in the captures. Check the live page for one and compare it with the PDF and SI [T1-1]. **re-check live**

## Log in

- [ ] Log in with the corresponding author's ORCID iD (`metadata.yaml` author Gang) and select "Submit Content" [T1-1, T2-1]. **re-check live**

## Step 1: author details

- [ ] Declare co-authorship, then enter every author in the order of `metadata.yaml` `authors`: given name, family name, email (from the local-only list) and institutions [T1-1]. **re-check live**
- [ ] Institutions: one per entry, within the per-author count and name-length limits stated in T1-1 [T1-1]. **re-check live**
- [ ] Check the fields that ORCID pre-fills for the corresponding author [T1-1]. **re-check live**
- [ ] Reorder the authors so that the form order matches the PDF byline [T1-1]. **re-check live**
- [ ] Do not enter any AI tool as an author [T1-1, T1-2]. **re-check live**

## Step 2: content

- [ ] Title: the final title from W8 (`metadata.yaml` `title.final`), identical to the PDF [T1-1]. **re-check live**
- [ ] Abstract: pasted from the final PDF, within the word limit stated in T1-1 (`metadata.yaml` `abstract`) [T1-1]. **re-check live**
- [ ] Categories: main categories and subcategories within the limits stated in T1-1; the top-listed main category is shown on the preprint page. Choose from the live list; the captured list and the lane's proposal are in `metadata.yaml` `categories` [T1-1, P1]. **re-check live**
- [ ] Keywords from `metadata.yaml` `keywords` [T1-1]. **re-check live**
- [ ] Content type: Working Paper [T1-1]. **re-check live**
- [ ] Upload the manuscript PDF and check the cover-page thumbnail [T1-1]. **re-check live**
- [ ] Funders: "Add Funder" with funder name and grant number, matching the funding statement in the PDF (`metadata.yaml` `funding`) [T1-1, T2-1, T3-1]. **re-check live**
- [ ] Competing interests for all authors, matching the PDF (`metadata.yaml` `competing_interests`) [T1-1, T2-1, T3-1]. **re-check live**
- [ ] Ethics approvals: not applicable (`metadata.yaml` `ethics`) [T1-1, T2-1]. **re-check live**
- [ ] If the live form has an AI-use field, which the captures do not describe, enter the same disclosure as the PDF [T1-2]. **re-check live**

## Step 3: supporting material and licence

- [ ] Upload the SI as supporting material beside the main PDF (`metadata.yaml` `files.supplementary`) [T1-1, T1-2]. **re-check live**
- [ ] Add supplementary weblinks to the repository and the Zenodo archive (`\nacreRepoURL`, `\nacreZenodoDOI`) if they exist at C2. They are filled at C3, so this item may move to a new version after posting [T1-1, T2-1]. **re-check live**
- [ ] Licence: CC BY 4.0 (`metadata.yaml` `licence`) [T1-1, T1-2]. **re-check live**

## Step 4: review and upload

- [ ] Review every field against `metadata.yaml` and the PDF [T1-1]. **re-check live**
- [ ] Read and accept the Terms of Submission. Acceptance confirms the authority from all co-authors, the right to share the content and the declarations [T3-1]. **re-check live**
- [ ] Submit, and confirm that the upload shows as awaiting approval in the author dashboard [T1-1]. **re-check live**

## After upload: screening

- [ ] Screening is by curators and is not peer review. Watch for the decision email [T1-1, T1-2]. **re-check live**
- [ ] If the upload is declined, read the stated ground against the list in requirements.md T1, "Screening", fix the cause and re-upload [T1-1, T1-2]. **re-check live**
- [ ] Once posted, record the DOI and version for C3 (the macros filled at C3 are in `metadata.yaml` `data_and_code_availability`). Corrections are made as new versions with a short explanation [T1-1, T2-1]. **re-check live**
- [ ] For the later RSC journal route, disclose the preprint at submission [T4-1, T4-5]. **re-check live**

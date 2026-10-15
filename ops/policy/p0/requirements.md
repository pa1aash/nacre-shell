# Preprint and journal policy requirements for track p0

Session P0-I0, step 8. These are the requirements from ChemRxiv (the track venue) and the Royal Society of Chemistry (the later journal route, RSC Advances) that bear on the P0 preprint. They are paraphrased; each bullet cites an entry in `ops/policy/p0/index.yaml`. Raw pages are local-only.

**Source caveat.** Live chemrxiv.org and www.rsc.org refuse headless clients (HTTP 403). Every page here is the newest status-200 Wayback capture. The ChemRxiv captures date from 2025-08-12 to 2025-10-15 (T1-1 to T3-1). ChemRxiv appears to have moved to a new hosting platform during 2026: no `/engage/` page has been captured since January 2026, and the 2026 captures of the new platform are challenge pages or assets, not policy text. The ChemRxiv rules below may therefore have been superseded. The operator re-checks them on the live site before submission (item C2); see the outstanding actions in `ops/reports/P0-I0.md`. The RSC captures date from 2026-08-06 to 2026-10-05.

## T1 ChemRxiv submission and author guidelines

- **Accepted content.** Scholarly research in the chemical sciences and related fields, in English, of the length and structure of a standard manuscript. A working paper must contain new results and analysis. News, commentary, opinion, hypothetical essays and stand-alone data sets are declined. [T1-2]
- **Status of the work.** The work may be under review at a journal but must not yet be accepted or published after peer review. It must not also be posted on another preprint server. [T1-2, T2-1]
- **Content type.** Research articles with new data and results are uploaded as a Working Paper. Curators may reassign the type during screening. [T1-1]
- **Main file.** The manuscript is a single PDF with figures and tables embedded where they belong. Figures of at least 300 dpi are recommended. There is no copyediting or typesetting: the approved upload is what appears online. [T1-1, T1-2]
- **Abstract and metadata.** The abstract is limited to 500 words. The form asks for title, keywords, up to three main categories and up to three subcategories; the first main category is displayed on the preprint page. [T1-1]
- **Authors in the form.** First and last name, email and up to five institutions per author, entered by the corresponding author for every co-author, with author order set in the form. [T1-1]
- **ORCID.** The submitting author must log in with an ORCID iD. [T1-1, T2-1]
- **File size limits.** None is stated on any reached page. Outstanding.
- **Supplementary information.** SI is uploaded as supporting material alongside the main PDF, in any file format, or linked through supplementary weblinks to repositories. It appears under a separate supplementary-materials heading on the landing page. [T1-1, T1-2]
- **Licences offered.** CC BY 4.0, CC BY-NC 4.0 and CC BY-NC-ND 4.0, chosen by the corresponding author at upload. Copyright is not transferred. [T1-1, T1-2]
- **Subject categories.** Selection is required and screening checks that the work fits a ChemRxiv subject. The category list itself was not on any reached page. Outstanding. [T1-1, T1-2]
- **Screening.** Curators with chemistry PhDs screen each upload, which is not peer review, typically within one to two business days. Grounds for decline include: not scholarly; outside the subjects; plagiarism (every upload is checked with similarity software); already accepted or published; not in English; infringing or unauthorised; unlawful or harmful content. [T1-1, T1-2]
- **Versions and retraction.** Corrections are made by posting a new version with a short explanation; earlier versions stay visible and linked. A preprint is not retracted merely because it was later published in a journal. [T1-1, T2-1]

## T2 ChemRxiv policy on AI or generative-tool use

- AI tools may be used in preparing a preprint, provided the text of the preprint discloses the "name of the tool(s) and method of use". [T1-2]
- The disclosure may sit in the Methods, in a statement at the end of the manuscript, or wherever suits the format. [T1-2]
- AI tools do not meet the authorship criteria. They are mentioned in the text and never listed as authors, either in the document or in the submission information. [T1-1, T1-2, T2-1]
- Authors remain accountable for the final text and must check it for errors introduced by such tools. [T2-1]

## T3 ChemRxiv consent, competing interests, funding, data and code

- **Co-author consent.** By accepting the Terms of Submission, the submitter confirms being the sole author or an authorised co-author with authority given by all co-authors. The submitter must also have communicated the terms in writing (email suffices) to every co-author, each of whom has authorised the submission. The policies page also expects the corresponding author to confirm permission with co-authors before upload. [T3-1, T2-1]
- **Authorship criteria.** ChemRxiv applies the ICMJE criteria. Everyone who meets them is listed, and authorship disputes must be settled by the authors before ChemRxiv acts. [T2-1]
- **Competing interests.** A competing-interest declaration covering all authors is required at submission, with a brief explanation of any conflict. The Terms of Submission also require the declarations to appear within the content. [T2-1, T3-1, T1-1]
- **Funding.** Funder name and grant number are encouraged in the upload form ("Add Funder") and may also be given in the file. The Terms of Submission require all relevant funding grants to be declared. [T2-1, T1-1, T3-1]
- **Data availability.** Sharing the underlying data under FAIR principles, in a subject or general repository, is encouraged. The content should include a Data Availability Statement. [T2-1]
- **Code.** No separate code policy is stated. Code may be uploaded as supporting material or linked. [T1-1, T1-2]
- **Ethics.** Approvals for research with humans or animals go in the upload form. This study involves neither. [T2-1, T1-1]
- **Originality and copyright.** The submitter must hold the right to share the content, which must not have been posted elsewhere before. [T2-1, T3-1]

## T4 RSC policy on prior preprint posting (journal-wide and RSC Advances)

- **Journal-wide.** RSC journals accept work previously deposited as a preprint, including on ChemRxiv, arXiv, institutional repositories and personal websites. A preprint is an un-refereed author version. For ChemRxiv only, the deposited version may be a revised one, but it must still be a pre-acceptance version. [T4-5]
- **Not accepted.** Work previously published, or under consideration, in another journal. Questions about borderline cases go to the journal editor. [T4-5]
- **Disclosure.** Prior posting of a preprint should be fully disclosed at submission, and redundant publication without cross-reference is not allowed. [T4-1]
- **RSC Advances.** The RSC Advances author guidelines add no preprint restriction of their own. They give the citation format for ChemRxiv preprints (authors, server, year, the word preprint, DOI with version), which assumes such citations. The licences and journal-article overview pages carry no preprint rule. [T4-3, T4-2, T4-4; also `charter/venue/manuscript.yaml` field `references.preprint_format`]

## T5 RSC policy on author use of AI tools

- **Authorship.** AI tools cannot be authors, and authors are fully accountable for any AI-produced content. [T4-1; V-1 `sections.ai_authorship`]
- **No AI data.** AI-generated content may not be presented as original research data or results. [T4-1]
- **Three disclosure locations.** Use of generative AI in any part of the manuscript must be:
  - declared in the cover letter at submission;
  - described in a Materials and Methods statement of how the tool was used, including the prompts;
  - named in the Acknowledgements, with the tool's name and specific model or version.

  If the manuscript has no Methods section, all of this goes in the Acknowledgements. AI-assisted copy editing alone need not be declared. RSC gives a recommended Acknowledgements wording. [T4-1; V-1 `sections.ai_disclosure`, `sections.acknowledgements.must_declare`]
- **Images.** AI-generated illustrative images:
  - need tools trained on licensed data, with output cleared for commercial reuse;
  - need a caption note on how they were made;
  - must not show identifiable people.

  AI must not be used to alter images. [T4-1; V-1 `figures.ai_generated`]
- **Undisclosed use.** It may lead to withdrawal, rejection or retraction. [T4-1]
- **Corporate principles.** The guiding-principles page states RSC's own corporate AI principles and refers authors back to the author-responsibilities page for publishing policy. [T5-1]

## Conflicts with track decisions

The track decision (ops/tracks/p0.yaml, `inputs.ai_disclosure`) places the AI disclosure in the Acknowledgements. The text comes from a local-only include, `.local/p0/ai_ack.tex`, and the release build fails if that file is missing.

1. **Must the AI disclosure name the tool?** Yes, under both policies. ChemRxiv wants the tool's name and how it was used [T1-2]. RSC wants the name and the specific model or version [T4-1]. The released PDF will therefore contain the tool name, even though the repository keeps it only in the local-only include. The wording is owned by Palaash at P0-W8.5.
2. **Does placement in the Acknowledgements satisfy ChemRxiv?** Yes. ChemRxiv accepts the disclosure anywhere in the preprint's text that suits the format [T1-2]. It must also state the method of use, not only the name.
3. **Does ChemRxiv's submission form have its own AI declaration field?** None is described on the reached pages. The form steps list author details, content and metadata, funders, competing interests, ethics approvals, supporting material, the licence and acceptance of the terms [T1-1]. ChemRxiv only says AI tools must not be entered as authors in the submission information [T1-2]. This is unverified against the 2026 platform.
4. **Is CC BY 4.0 offered?** Yes, as one of three licences chosen at upload [T1-1, T1-2].
5. **Must the SI be a separate file?** ChemRxiv does not require it. Its form takes supporting material as separate uploads or weblinks beside the main PDF, and nothing reached says SI may or may not be appended to the main PDF [T1-1, T1-2]. For RSC journals the SI is submitted as separate files with the original submission [T4-3].
6. **Does RSC Advances accept manuscripts previously posted on ChemRxiv?** Yes. RSC journal policy accepts ChemRxiv preprints, including a revised pre-acceptance version, with disclosure at submission [T4-5, T4-1]. The RSC Advances guidelines add no restriction [T4-3].
7. **Further conflict, for the journal route.** RSC's AI policy is stricter than the Acknowledgements-only decision. At the later RSC Advances submission it also requires a cover-letter declaration and a Methods statement that includes the prompts [T4-1]. The preprint can stay with the Acknowledgements placement. The journal version needs the Methods statement and the cover letter. Recorded as an open ruling for the planning chat.

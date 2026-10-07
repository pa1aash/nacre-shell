# CRediT contributor role taxonomy (fetched)

Fetched headlessly by `charter/fetch_credit.py` (rule R3: canonical third-party text is downloaded, never typed). Role names are the `<h1>` titles of the role pages linked from the NISO CRediT home page; each definition is the text of that page's "Definition" paragraph with HTML tags stripped and entities unescaped. Nothing else is edited, including the publisher's punctuation and any invisible characters.

Source: NISO, Contributor Role Taxonomy (CRediT), ANSI/NISO standard, licensed CC BY 4.0 by its publisher (as stated on the home page). Attribution: credit.niso.org.

| Page | URL | Retrieved (UTC) | sha256 of fetched bytes | HTTP |
|---|---|---|---|---|
| home (role list) | https://credit.niso.org/ | 2026-10-07T04:28:53Z | 98a0c8a2396be0a9c87b48dd97b9e5f962903410182b5073f3c95481b1c06524 | 200 |
| Conceptualization | https://credit.niso.org/contributor-roles/conceptualization/ | 2026-10-07T04:28:54Z | b522c941263fedbc6d772e00a3a46954ebe9503c3f220969a15f6a68cb76749c | 200 |
| Data curation | https://credit.niso.org/contributor-roles/data-curation/ | 2026-10-07T04:28:55Z | 14c5f1f94c865f8accf6ea6721a4cde17d77e020db77d40ef54113fbcb85ee75 | 200 |
| Formal analysis | https://credit.niso.org/contributor-roles/formal-analysis/ | 2026-10-07T04:28:56Z | 3daad421b5568aef76ebd23826b7b52c6f44bff6483fe50207b2137a6e217caa | 200 |
| Funding acquisition | https://credit.niso.org/contributor-roles/funding-acquisition/ | 2026-10-07T04:28:57Z | fe531325c17e3e7f60b05e4322572ff8edfd9d260d406aae3bd332259cf92935 | 200 |
| Investigation | https://credit.niso.org/contributor-roles/investigation/ | 2026-10-07T04:28:59Z | 053bfff87b93cf70769cffa6b283819b83551469753b7c761217675d3a0319b3 | 200 |
| Methodology | https://credit.niso.org/contributor-roles/methodology/ | 2026-10-07T04:29:00Z | b759ad470edac9fab1e88482ece5d7ea650758d5e43512568e084b683fa414e7 | 200 |
| Project administration | https://credit.niso.org/contributor-roles/project-administration/ | 2026-10-07T04:29:01Z | 2d145785a4ef869429e765ed92a1d41e91ee3cabb888d2bd578b2756d9bde8c0 | 200 |
| Resources | https://credit.niso.org/contributor-roles/resources/ | 2026-10-07T04:29:02Z | 3bd2bb1daab39960019211c774b4cfba5c0ea41f4c5fd793604930efaf375766 | 200 |
| Software | https://credit.niso.org/contributor-roles/software/ | 2026-10-07T04:29:04Z | 8c152f64b3fbf1db4796775f9d0c9a73cb060e9cea57411fc0089e9ba7c24f59 | 200 |
| Supervision | https://credit.niso.org/contributor-roles/supervision/ | 2026-10-07T04:29:05Z | fc297de4907a9608f76a1834f7c029b765576c704f8a8584b6a7e53db932e0a5 | 200 |
| Validation | https://credit.niso.org/contributor-roles/validation/ | 2026-10-07T04:29:06Z | 0454286b45c335ff9313788c60555c0507e429a18ac1b7a1ac9f28136fbe8796 | 200 |
| Visualization | https://credit.niso.org/contributor-roles/visualization/ | 2026-10-07T04:29:07Z | 39451c785ea678b18c2a10cdf00befe7b731ba001efc9a893ea700dbb647aa39 | 200 |
| Writing – original draft | https://credit.niso.org/contributor-roles/writing-original-draft/ | 2026-10-07T04:29:08Z | 4e475eb91ae6427af01ff90214abcc0415dac8e688cb3d6d71a91a131aac6283 | 200 |
| Writing – review & editing | https://credit.niso.org/contributor-roles/writing-review-editing/ | 2026-10-07T04:29:09Z | f559c9630ddfec5d45446c37b536dc9d1eda58b416dc0f3a75af37ea68c037b9 | 200 |

## Roles and definitions (verbatim)

### Conceptualization

Ideas; formulation or evolution of overarching research goals and aims.

### Data curation

Management activities to annotate (produce metadata), scrub data and maintain research data (including software code, where it is necessary for interpreting the data itself) for initial use and later re-use.

### Formal analysis

Application of statistical, mathematical, computational, or other formal techniques to analyse or synthesize study data.

### Funding acquisition

Acquisition of the financial support for the project leading to this publication.

### Investigation

Conducting a research and investigation process, specifically performing the experiments, or data/evidence collection.

### Methodology

Development or design of methodology; creation of models.

### Project administration

Management and coordination responsibility for the research activity planning and execution.

### Resources

Provision of study materials, reagents, materials, patients, laboratory samples, animals, instrumentation, computing resources, or other analysis tools.

### Software

Programming, software development; designing computer programs; implementation of the computer code and supporting algorithms; testing of existing code components.

### Supervision

Oversight and leadership responsibility for the research activity planning and execution, including mentorship external to the core team.

### Validation

Verification, whether as a part of the activity or separate, of the overall replication/reproducibility of results/experiments and other research outputs.

### Visualization

Preparation, creation and/or presentation of the published work, specifically visualization/data presentation.

### Writing – original draft

Preparation, creation and/or presentation of the published work, specifically writing the initial draft (including substantive translation).

### Writing – review & editing

Preparation, creation and/or presentation of the published work by those from the original research group, specifically critical review, commentary or revision – including pre- or post-publication stages.

## Machine-readable role list

Generated from the role pages above; `tests/charter/test_charter.py` checks `charter/credit.yaml` against it.

```yaml credit-roles
- "Conceptualization"
- "Data curation"
- "Formal analysis"
- "Funding acquisition"
- "Investigation"
- "Methodology"
- "Project administration"
- "Resources"
- "Software"
- "Supervision"
- "Validation"
- "Visualization"
- "Writing – original draft"
- "Writing – review & editing"
```

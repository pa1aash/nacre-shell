# RUNBOOK

The operating manual for this repository. Every session reads it first. Where it and a tool disagree, the tool's output is the fact and the RUNBOOK is corrected through main.

## 1. Roles

- **Operator (Palaash).** Gives sign-offs, holds the keys, starts and stops pods, runs HPC jobs, and answers every `YOU:` request.
- **Planning and audit chats.** Plan sessions, write the session prompts, and perform the layer C audit of each gate. They hold no repository access.
- **Executor session.** Works autonomously from a prompt inside one lane and one window, and stops only at `YOU:` points.
- **Compute.** Pods and HPC. Nothing is built or run locally beyond the test suite; containers are never built on a laptop.

## 2. Session header

Every session begins with these steps, in order.

1. Read this RUNBOOK, `ops/state/<lane>.json` and the last report named by `nacre status`.
2. Run `uv run nacre wave check <session-id>`. If it fails, stop with status BLOCKED.
3. Verify that the required tags exist, the tree is clean and the branch is the session's lane branch.
4. Print the plan.

## 3. During a session

- Commit after every coherent unit that passes its tests, with the commit style in section 11.
- Push at the end of each subsession.
- Stop at a `YOU:` marker and wait.

## 4. Session footer

1. Run `uv run nacre verify`.
2. Write `ops/reports/<session>.md`: what was built, check results, outstanding actions, decisions applied.
3. Update `ops/state/<lane>.json` with `last_session` and a status.
4. Push.
5. Print the END BLOCK.

## 5. END BLOCK statuses

| Status | Meaning | Operator action |
|---|---|---|
| DONE | All work complete and verified | Paste the END BLOCK into the planning chat; start the next session |
| HOLD-P | Waiting on a planning decision | Take the question to the planning chat and return the answer |
| HOLD-X | Waiting on an external action (access, credentials, a pod) | Perform the action, then resume the session |
| GATE-C | Layer A passed; the chat audit (layer C) is next | Take `ops/packets/<G>.md` to the audit chat |
| GATE-H | Layer C passed; human sign-offs are next | Fill the H-signoff fields in `ops/gates/<G>.md` |
| BLOCKED | A precondition failed | Read the reason, fix it, rerun the header |

## 6. Gates

A gate has three layers.

- **A (automatic).** `nacre gate <G> --check` evaluates `ops/gates/<G>.yaml` and records the result in `ops/gates/<G>.md`.
- **C (chat audit).** The audit chat reads `ops/packets/<G>.md` (written by `--packet`) and the record gets `C-audit: PASS <date>`.
- **H (human sign-off).** Every `H-signoff` field in the record is filled in.

`nacre gate <G> --tag` creates the signed, annotated tag `g<N>` only when all three layers hold. The tags are `g0` to `g13`, plus `prereg-v1` for the pre-registration. Gates G2, G9 and G12 also need the sign-off of the UIUC corresponding author. The G0 H sign-off is Palaash Gang only; the UIUC co-sign for G0 moves to G2 of the main study (audit fix F6, 2026-10-16).

## 7. Lanes and worktrees

- `ops/lanes.yaml` is the authority on who may write what; it documents its own schema. The pre-commit hook and `nacre verify` use the same matcher, `tools/githooks/_lanes.py`.
- Branch to lane: `main` is lane `a-main`; `lane/<id>` is lane `<id>`; any other branch is refused. The prefix names the laptop: `a-*` is Laptop A, `b-*` is Laptop B.
- `uv run nacre lane new <lane-id>` creates the worktree `nacre-shell-<lane-id>` beside the main checkout, on branch `lane/<lane-id>`, and refuses an unregistered lane.
- Lane work reaches main only through an integration session that merges with `--no-ff`. Merges carry no ownership check, but the attribution scan and identity check still run. The integration session resolves conflicts in `pyproject.toml` and `uv.lock` and re-runs `uv lock`.
- On a fresh clone or worktree, run `uv run nacre setup`. Use `--check` to report drift without changing anything.
- **Tracks.** A track (the `tracks` block of `ops/lanes.yaml`) is a lane set that branches from its own base instead of main; for track p0 the base is `preprint/p0` (lane `p0-int`, the integrator) and the lanes are `preprint/p0-w1` to `preprint/p0-w8`. Non-merge commits on the base are limited to the integrator's paths; merges carry no ownership check. `uv run nacre lane new <lane> --track p0` creates `nacre-shell-p-<lane>` from the base. The track's day ledger is `ops/tracks/p0.yaml`: a track session starts with `uv run nacre track check <session>` instead of `nacre wave check`, and the integrator opens each day with `uv run nacre track open-day <n>`.
- **macOS hidden flag.** On the Macs, the editable-install `.pth` files in `.venv` can gain the `hidden` file flag (likely from Desktop file syncing), and Python then skips them, so `import nacre` fails. Run `chflags -R nohidden .venv` and retry; if it recurs within a session, run commands with `PYTHONPATH=src` and record that in the report.
- **Shared test helpers.** A lane puts helpers shared by its tests in a uniquely named module, such as `tests/retrieval/retrieval_helpers.py`. It never adds `tests/<lane>/conftest.py`: a second `conftest` module shadows `tests/conftest.py` and breaks `from conftest import ...` in the older suites.

## 8. Wave ledger

- `ops/waves.yaml` is written only on main and read by every lane. Exactly one wave is open.
- A session may run only if it is listed in the open wave, on its registered lane branch, with the wave's base commit in its history and the required tags present: `uv run nacre wave check <session-id>`.
- `nacre wave status` shows each listed session as pending, running or DONE.
- The next wave opens, with `nacre wave open <n>` on main, only when every session listed in the previous wave has its lane state merged on main with status DONE. Opening closes the previous wave and commits the ledger.
- Integration session I<n> runs on main while wave n is open: it merges the lane work of wave n and then runs `nacre wave open n+1` to open the next wave. `nacre wave check I<n>` passes iff the current branch is main, wave n is the single open wave, and local main equals origin/main after a fetch. Integration sessions are not listed in the ledger's `sessions`/`lanes` maps.

## 9. Standing rules

- **R1 Identity.** Every commit and tag is authored and committed as Palaash Gang <palaashgang@gmail.com>. Commit messages carry no trailers of any kind.
- **R2 Banned strings.** The banned-string set defined in `tools/githooks/_scan.py` must not appear in any file, path, commit message, tag message, branch name or comment. Code that needs the local-only file names builds them at runtime from character codes; tests that plant banned strings build them the same way. The hooks and the CI history scan enforce this.
- **R3 Fetched, never typed.** Licence texts and other third-party canonical text are downloaded. If a fetch fails, write a one-line pointer file and log an outstanding action; do not reconstruct the text. Each fetch is recorded in `ops/fetch_log.md`.
- **R4 Headless retrieval.** Use curl or Python HTTP clients against APIs or raw URLs. No GUI browser.
- **R5 Figures.** Nothing inside a figure except axes and panel letters placed outside the axes. No legends and no text inside the axes. All other information lives in the caption. This replaces the earlier allowance for legends (section 14).
- **R6 No compression.** Never cut scope to save time. Whatever cannot be done is reported as an outstanding action.
- **R7 Frozen paths.** Enforced by the pre-commit hook; see section 10.
- **R8 Commit style.** Neutral engineering history with a conventional prefix; see section 11.

## 10. Frozen paths and the deviation protocol

`ops/frozen.yaml` lists the frozen paths. Each rule applies once its named tag exists.

- `registration/**` after `prereg-v1`. `registration/deviations.md` is append-only: its staged diff may only add lines.
- `structures/v1/**` and `structures/registry.csv` after `g4`.
- Model and dataset paths are added by the session that freezes them, before `g6`.

A needed change to a frozen path is never an edit. It becomes a dated entry in `registration/deviations.md`.

## 11. Commit message convention

`<phase>(<scope>): <imperative summary>`, for example `phase0(bootstrap): add lane ownership hook` or `ops(wave): open wave 1`. A message has a subject, and optionally a body of plain paragraphs. It has no trailer lines. Hooks run on every commit; do not bypass them.

## 12. The `YOU:` marker

A line starting `YOU:` is an action only the operator can take, such as confirming a key, a repository setting or a sign-off. The session prints the request and waits for the answer in the chat before continuing.

## 13. Data store

Pending (decision D11). The `DATA_STORE_*` variables in `.env.example` are reserved. The store is chosen and wired in session S31; until then nothing writes to a remote store.

## 14. Track p0 operating notes

Added by P0-I1 (2026-10-16). They apply to the preprint track `p0` and to any session that works beside it.

- **Figures.** Figures carry no legends and no text inside the axes. Panel letters sit outside the axes and everything else is in the caption. The figure checker rejects legends. This overrides the legend allowance that R5 used to give.
- **Environments outside synced folders.** The Python environment never lives in a synced folder. `.venv` is a symlink to `$HOME/.nacre-venvs/<name>`: `p-int` for the integrator and `p-<lane>` (for example `p-w3`) for a lane. `nacre lane new <lane> --track p0` creates the target with `uv venv` when it is absent, links it, and then runs `uv sync`. `.gitignore` lists `.venv` without a trailing slash so that the link is ignored. On a machine that already has a plain `.venv` directory: `uv venv "$HOME/.nacre-venvs/p-int"`, `rm -rf .venv`, `ln -s "$HOME/.nacre-venvs/p-int" .venv`, `uv sync`.
- **Background processes.** A session stops the background shells and the keep-awake process it started before it ends: `kill $(cat .local/caffeinate.pid) 2>/dev/null; rm -f .local/caffeinate.pid`.
- **RSC template packages.** The RSC article template needs four TeX packages that BasicTeX lacks: `sectsty`, `yafoot` (provides `fnpos`), `droid` (provides `droidsans`) and `charter`. Install them in user mode, which touches nothing system-wide: `tlmgr init-usertree` once, then `tlmgr --usermode install sectsty yafoot droid charter`. The packages land in `~/Library/texmf`, and deleting that tree reverses the install. The template itself is fetched by `nacre paper template --ensure`, which verifies the pinned sha256, and it stays local-only.
- **Theory documents.** Everything under `theory/` builds with standard TeX Live packages only. It must not need the user-mode packages above.
- **Blender scenes.** `figures/blender/scene.py` runs in Blender's own interpreter, which lacks PyYAML; it borrows the pure-Python PyYAML from the repository `.venv`. Run `uv sync` in a checkout before rendering.
- **xtb environment.** The conformer and semi-empirical tools are pinned in `src/nacre/anchor/xtb_env.yaml` (xtb 6.6.1, CREST 2.12, `libgfortran5` 13.4.0) and created outside synced folders at `~/.nacre-envs/xtb` with the command in that file. Run it single-threaded (`OMP_NUM_THREADS=1`) on the 8 GB laptops. A build with a newer `libgfortran` stops in the optimiser.
- **Charter changes.** `charter/**` changes only through an audit fix list, one commit per numbered fix, in the integrator lane.
- **CLI registration.** CLI subcommands register only by auto-discovery (`nacre/cli/commands/<name>.py` or `nacre/<pkg>/cli.py` with `register(subparsers)`). Nobody edits `src/nacre/cli/__init__.py` to add a command.
- **Test module names.** Test module basenames are unique across `tests/`; lanes prefix them with their topic (`test_structure_builders.py`, not `test_builders.py`). Pytest's default import mode cannot load two modules with one basename, and the collision only appears once the lanes are merged. `nacre verify` fails on a duplicate.
- **Bibliography.** P0 keeps its references in `preprint/paper/refs.bib`, owned by lane W8. W8 adds every reference with `uv run nacre bib add --bib preprint/paper/refs.bib <doi>`, taking DOIs from the W1 and W2 files. The provenance log is written beside the bib file, in `preprint/paper/bib/provenance.jsonl`. Without `--bib` the command keeps its old target, `paper/refs.bib`. `uv run nacre bib check --bib preprint/paper/refs.bib` checks it.
- **Preprint linters.** `nacre verify` runs `nacre preprint lint-numbers` and `lint-scope` whenever `preprint/paper/` exists. Mock-marked macros are accepted in draft state; the release build (`nacre preprint guard`) is the hard gate.
- **Retrieval retries.** `nacre.retrieval.http.Http` caps the wall time of one request's retries (default 120 s, `max_total_retry_seconds`) and logs one line per retry to stderr, so a caller cannot wait silently for tens of minutes.
- **Dependency groups.** On track p0 each worker lane's own dependencies live in `pyproject.toml` under `[dependency-groups]`, in the group named after the lane (`p0-w1` to `p0-w8`). `[tool.uv] default-groups` lists them all, so `uv sync` and `uv run` install every group. A worker lane edits only its own group: it adds a dependency with `uv add --group p0-wN <package>`, never touches `[project].dependencies` or `[tool.uv]`, and never stages `uv.lock` (run `git restore uv.lock` before committing; the lane's CI run uses `uv sync` without `--locked`). The pre-commit hook rejects any other change on `preprint/p0-wN`. The integrator moves a dependency that several lanes need into `[project].dependencies`, and regenerates `uv.lock` with `uv lock` after each merge.
- **Prior-construction rule.** W1's rule for building priors from evidence lives at `lit/corpus/params_README.md`. Ownership is unchanged: the file stays under the path the ownership hook already assigns to lane W1.
- **Merge-commit precedents (D8).** Cross-lane mechanical fixes made inside a merge commit so far: strict `xfail` markers on tests that wait for another lane's next session, with the reason naming the decision (D11, D13: contract version 3 and the cp2 thresholds, until W4.3); and a stated coordinate tolerance in place of exact text equality for platform-dependent force-field geometry, with species, order and counts kept exact (D12, `tests/anchor/test_builders.py`, 1e-3 Angstrom). A marker is removed by the lane that closes its gap, and a strict marker fails the suite the moment the gap closes.
- **Figure fonts.** Release figures are built on the Mac with Arial. The Linux CI runner has no Arial, so the `ci` workflow installs `fonts-liberation` (apt) before the tests, a metric-compatible substitute. Figure code is W6-owned and was not changed for this; the explicit font fallback is lane note N18.

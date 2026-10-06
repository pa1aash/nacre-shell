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

`nacre gate <G> --tag` creates the signed, annotated tag `g<N>` only when all three layers hold. The tags are `g0` to `g13`, plus `prereg-v1` for the pre-registration. Gates G0, G2, G9 and G12 also need the sign-off of the UIUC corresponding author.

## 7. Lanes and worktrees

- `ops/lanes.yaml` is the authority on who may write what; it documents its own schema. The pre-commit hook and `nacre verify` use the same matcher, `tools/githooks/_lanes.py`.
- Branch to lane: `main` is lane `a-main`; `lane/<id>` is lane `<id>`; any other branch is refused. The prefix names the laptop: `a-*` is Laptop A, `b-*` is Laptop B.
- `uv run nacre lane new <lane-id>` creates the worktree `nacre-shell-<lane-id>` beside the main checkout, on branch `lane/<lane-id>`, and refuses an unregistered lane.
- Lane work reaches main only through an integration session that merges with `--no-ff`. Merges carry no ownership check, but the attribution scan and identity check still run. The integration session resolves conflicts in `pyproject.toml` and `uv.lock` and re-runs `uv lock`.
- On a fresh clone or worktree, run `uv run nacre setup`. Use `--check` to report drift without changing anything.

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
- **R5 Figures.** Nothing inside a figure except axes, legends and panel letters placed outside the axes. All other information lives in the caption.
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

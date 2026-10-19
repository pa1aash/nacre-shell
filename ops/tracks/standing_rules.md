# Standing rules of track p0 (one page)

Read with ops/RUNBOOK.md. Decided 2026-10-20 (D34 to D40).

1. **Identity.** Commits are authored and committed as Palaash Gang, signed. No tool or vendor names in files, messages or trailers. Never `--no-verify`, never force-push, never rewrite pushed history, never commit to main.
2. **Fetched, not typed.** A value comes from a fetched source with its DOI and locator. Canonical text (licences, policies, standards) is fetched, never typed.
3. **Headless retrieval only.** No interactive browser; a login wall or HTTP 403 is recorded as a gap with the attempts, not worked around.
4. **Numbers in paper text** come through generated macros only.
5. **References** are added only through `nacre bib add`.
6. **Figures** carry no annotations and no in-axes text.
7. **Scope guard.** SG01 to SG16 plus the redirect additions in `ops/tracks/redirect_plan.md` (applied to `charter/scope_guard.md` by the integrator at PH-I5).
8. **Secrets and privacy.** Never print `.env` values. No personal email addresses in committed files.
9. **Memory (8 GB).** At most four sessions at once, at most one heavy. Blender renders run alone. No pods, no compute spending, no new DFT (D36).
10. **Dependencies.** `uv add --group <lane>`; commit `pyproject.toml` only, never `uv.lock` (the integrator regenerates it).
11. **No polling loops.** Dependencies are sequenced by the day plan and by END BLOCKs, not by watching state.
12. **Read only** your own lane's last report plus the files the brief names.
13. **Tests.** Run your own tests and `uv run nacre verify --quick` (all checks except the full suite). Never the full suite: the integrator runs `uv run pytest -q` once and `uv run nacre verify --strict` before any push.
14. **Commit after each deliverable.** Never push while `nacre verify --strict` fails (integrator).
15. **Frozen paths.** The `freeze:` block in `ops/tracks/p0.yaml` names a tag and path globs. A commit after the tag that touches a frozen path needs a dated entry with a `Re-audit:` line in `ops/tracks/p0_deviations.md`. Phosphate work adds keys and files under `lit/`, `theory/` and `configs/` without entries; it must not edit carbonate results.
16. **Do not edit `preprint/paper/**`** except through lane merges.
17. **END BLOCK.** Every session ends with the END BLOCK format of the RUNBOOK (session, lane, status DONE or BLOCKED, branch sha, tests, verify result, outstanding, next). Stop with BLOCKED plus a diagnosis; do not guess.
18. **Known failure.** CI Arial tests on Linux are resolved by the W6.3 font fallback.

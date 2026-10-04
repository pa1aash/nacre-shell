# Nacre Shell

Nacre Shell is a pre-registered computational feasibility study of a templated interfacial calcium-carbonate barrier against aluminium current-collector corrosion in fluorine-free lithium-ion cathodes.

**Status:** private; pre-registration in progress.

**Licences:** MIT for code (`LICENSE`), CC BY 4.0 for data (`LICENSE-DATA`).

## Layout

| Path | Purpose |
|---|---|
| `charter/` | study charter: claims, regimes, scope, credit |
| `lit/` | literature corpus and instrument gaps |
| `registration/` | pre-registration and its deviation log |
| `env/` | environment and container definitions |
| `src/nacre/` | the `nacre` Python package and CLI |
| `tests/` | test suite |
| `configs/` | run configurations |
| `structures/` | structure sets and registry |
| `jobs/ledger/` | per-lane job provenance ledgers |
| `hpc/outbox/`, `hpc/inbox/` | job hand-off to and from the cluster |
| `results/` | computed results |
| `figures/` | figure sources and styles |
| `review/` | review material |
| `ops/` | runbook, lanes, waves, gates, state, reports, packets |
| `tools/githooks/` | repository hooks and the history scan |

## Operating the repository

Read [ops/RUNBOOK.md](ops/RUNBOOK.md) first. It describes roles, session header and footer, gates, lanes, the wave ledger and the standing rules.

Setup on a fresh clone: `uv sync`, then `uv run nacre setup --signing-key <path to your public key>`.

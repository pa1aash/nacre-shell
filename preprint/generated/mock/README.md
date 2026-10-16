# Mock result files

Stand-ins for result files the producing lanes have not pushed yet. Every file carries
`"mock": true`, and its values are arbitrary: they exercise the macro pipeline and the draft
layout only. They are not results and are never inputs to the paper. A macro whose source is
a mock file is marked `mock: true` in `../sources.yaml`; it renders with a visible "mock" marker
in a draft build and stops a release build where it is used.

| File | Shape | Real source (owner) |
|---|---|---|
| `screen_summary.mock.json` | `configs/preprint/results_schema.json` v1, as pushed by p0-w4 (blob e81bcb3) | `results/preprint/screen/summary.json` (p0-w4), path assumed |
| `screen_precision.mock.json` | assumed | `results/preprint/screen/precision.json` (p0-w4), assumed |
| `pourbaix_summary.mock.json` | assumed | `results/preprint/pourbaix/summary.json` (p0-w5), assumed |
| `anchor_summary.mock.json` | assumed | `results/preprint/anchor/summary.json` (p0-w5), assumed |
| `retrodiction_summary.mock.json` | assumed | `preprint/retrodiction/summary.json` (p0-w2), assumed |
| `params_summary.mock.json` | assumed | `lit/params.yaml` summary (p0-w1), assumed |

The assumed shapes are reconciled with the owning lanes on Day 2 (see `ops/reports/P0-W8.1.md`).

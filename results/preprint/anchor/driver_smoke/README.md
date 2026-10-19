# Local smoke of the anchor production driver, real backend (P0-W5.4)

The real backend of `nacre.anchor.production`, run on the 8 GB laptop on the two smallest species only
(`water_w1`, `water_w2`), one thread, `--max-conformers 2`, to exercise the CREST, xtb and DFT code paths
before the pod run. It is a code-path check, not a production result, and enters no cycle.

    PATH="$HOME/.nacre-envs/xtb/bin:$PATH" NACRE_ANCHOR_DISP=none \
      uv run python -m nacre.anchor.production run --out <dir> --backend real --jobs 1 --threads 1 \
      --max-memory-mb 1500 --max-conformers 2 --species water_w1 water_w2

Departures from production, as recorded in `summary.json` (`env_check`):
- **SMD CDS term absent:** the laptop's PyPI PySCF has no `libsolvent` (`smd_cds.active: false`). The driver ran
  the electrostatic part and flagged it, as it would on a pod without the SMD build.
- **No dispersion:** the dispersion add-on has no macOS wheel, so `NACRE_ANCHOR_DISP=none` (E_disp = 0).
- **osx-arm64 tools:** xtb and CREST are the osx-arm64 builds of `xtb_env.yaml`, not the linux-64 lock.

Observed:
- **CREST on (H2O)2:** 851 conformers in 417 s on one thread.
- **`water_w2` conformer 0:** needed one restart from xtb's distorted geometry (one imaginary mode) and then
  finished.
- **`water_w2` conformer 1:** xtb exited with return code -5 on this machine. The conformer is recorded as
  failed and dropped, and the species continued with the remaining conformer.
- **Wall time:** 8 min 12 s for both species.

The run used the driver as committed in 792553f, but before that commit (on top of 9911ee8), so the ledger
records `git_dirty: true`.

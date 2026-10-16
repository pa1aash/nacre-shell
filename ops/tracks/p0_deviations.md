# Deviations of track p0

Once tag `p0-cp3` exists, `lit/params.yaml`, `configs/preprint/thresholds.yaml` and `theory/thresholds.md` are
frozen. A change to any of them since that tag fails `nacre track check` unless this file has a dated entry that
names the changed path and lists the outputs to re-audit. An entry is a level-2 heading that starts with its date,
followed by text that mentions each changed path and has a `Re-audit:` line:

    ## 2026-10-20 lit/params.yaml
    Change: <what changed and why>
    Re-audit: <outputs that depend on the changed input>

Entries are appended; an entry dated before the tag does not cover a later change.

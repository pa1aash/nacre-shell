"""PH-W5.1 run: every step after the benchmark (outputs under results/preprint/pourbaix/ph_w51/).

    uv run python -m nacre.pourbaix.ph_w51 run

Step 2 writes al_window.json and a_al3_oxide.csv; steps 3 to 7 write ladder_v2.csv and ph_w51.json; the
report ph_w51.md summarises all of them.
"""
import csv
import json

from nacre.pourbaix import ph_k1 as k
from nacre.pourbaix import ph_w51_al as al
from nacre.pourbaix import provenance
from nacre.pourbaix.paths import rel

OUT = k.POURBAIX_RESULTS / "ph_w51"
OUTPUTS = ("al_window.json", "a_al3_oxide.csv")


def _dump(path, doc):
    path.write_text(json.dumps(doc, indent=1, default=float) + "\n", encoding="utf-8")


def run_window(ctx=None):
    doc = al.run(ctx)
    doc = {"session": "PH-W5.1", "step": "2 Al-O-H passivation window", "generated_utc": provenance.utc_now(),
           "git_sha": provenance.git_sha(), "evidence_table_sha256": k.evidence_sha256(), "params_sha": k.PARAMS_SHA,
           **doc}
    OUT.mkdir(parents=True, exist_ok=True)
    _dump(OUT / "al_window.json", doc)
    rows = doc["a_al3_rows"]
    with open(OUT / "a_al3_oxide.csv", "w", newline="", encoding="utf-8") as fh:
        fh.write("# PH-W5.1 a(Al3+) at the oxide-equilibrium state (slurry stage, route R1), 298.15 K, I = 0, log10 "
                 "activities. Governing film: Al(OH)3 am (TB-027, grade C); crystalline reference boehmite (TI-026 with "
                 "TI-022, grade A); gibbsite TB-028, corundum TB-029; hydrolysis TB-023..TB-026.\n")
        fh.write("# Polyphosphate complexation leaves a(Al3+) unchanged at fixed solid equilibrium and raises total Al "
                 "only; linear-chain constants are a gap (polyp_al_log_beta1_linear), so totals exclude it.\n")
        wr = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        wr.writeheader()
        for r in rows:
            wr.writerow({c: ("%.2f" % v if c == "pH" else "%.4f" % v) for c, v in r.items()})
    print("wrote", rel(OUT / "al_window.json"), rel(OUT / "a_al3_oxide.csv"))
    return doc


def run():
    run_window()
    return 0

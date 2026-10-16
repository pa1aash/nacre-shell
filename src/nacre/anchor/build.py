"""Write every anchor species as .xyz plus metadata.

    uv run python -m nacre.anchor.build [--seed 7] [--out results/preprint/anchor/structures]

Thermodynamic question served (later, by W5.2 onward): what is the binding free energy of Ca2+
to catecholate (mono- and dianion) and to acetate (mono- and bidentate) in implicit solvent
with explicit first-shell waters, and is the pipeline self-consistent across these cases?
These files are starting geometries for that pipeline check, not results.
"""
import argparse
import json
import sys
from pathlib import Path

from nacre.anchor import builders as b

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "results" / "preprint" / "anchor" / "structures"


def write_all(out=OUT, seed=7, **kw):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    index = []
    for st in b.all_species(seed=seed, **kw):
        (out / (st.name + ".xyz")).write_text(st.xyz(), encoding="utf-8")
        rec = b.as_record(st)
        rec["min_distance_A"], rec["min_interfragment_distance_A"] = [
            round(v, 4) for v in b.min_distances(st)]
        (out / (st.name + ".json")).write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n",
                                               encoding="utf-8")
        index.append({k: rec[k] for k in ("name", "formula", "n_atoms", "charge", "multiplicity",
                                          "kind", "coordination_mode", "n_water", "seed",
                                          "builder_version")})
    (out / "index.json").write_text(json.dumps({"builder_version": b.BUILDER_VERSION, "seed": seed,
                                                "species": index}, indent=1, sort_keys=True) + "\n",
                                    encoding="utf-8")
    return index


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m nacre.anchor.build")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)
    for rec in write_all(args.out, args.seed):
        print("%-44s %-14s q=%+d n=%d" % (rec["name"], rec["formula"], rec["charge"], rec["n_atoms"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

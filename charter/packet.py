"""Render the charter into the G0 audit packet.

`nacre gate G0 --packet` writes ops/packets/G0.md with the layer A result only; the gate
tool lives on main (src/nacre/cli/commands/gate.py) and has no hook for gate-specific
content. Until it gains one, this script appends the charter sections to that packet.
It is idempotent: everything after MARKER is replaced on every run.

Run after the gate packet: uv run python charter/packet.py
"""
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CHARTER = ROOT / "charter"
PACKET = ROOT / "ops" / "packets" / "G0.md"
MARKER = "<!-- charter sections (charter/packet.py) -->"

SECTIONS = [
    "Claim register",
    "Numbering reconciliation",
    "Regimes",
    "Deletion register",
    "Scope guard",
    "Outcome branches",
    "CRediT draft",
    "Open items for the auditor",
]


def load(name):
    return yaml.safe_load((CHARTER / name).read_text(encoding="utf-8"))


def cell(value):
    if value is None:
        return "null"
    if isinstance(value, dict):
        value = "; ".join("%s: %s" % (k, cell(v)) for k, v in value.items())
    elif isinstance(value, list):
        value = "; ".join(cell(v) for v in value) if value else "none"
    return " ".join(str(value).split()).replace("|", "\\|")


def demote(markdown, levels=1):
    """Push every heading of an embedded file down so it nests under a packet section."""
    return re.sub(r"^(#+)", lambda m: m.group(1) + "#" * levels, markdown, flags=re.MULTILINE)


def claim_table(reg):
    cols = ["id", "name", "link", "observable", "physics", "computation", "regime", "threshold",
            "kill criterion", "depends on", "controls", "open items", "verdict bands"]
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for c in reg["claims"]:
        obs = c["physical_observable"]
        comp = c["computation"]
        row = [
            c["id"], c["name"], c["link"],
            "%s: %s [%s]" % (obs["symbol"], cell(obs["definition"]), obs["units"]),
            c["physics"],
            "%s (Phase %s items %s)" % (cell(comp["method"]), comp["phase"], cell(comp["items"])),
            c["regime"],
            "value: %s; status: %s; proposed: %s; objections: %s" % (
                cell(c["threshold"]["value"]), c["threshold"]["status"], cell(c["threshold"]["proposed"]),
                cell(c["threshold"]["objections"])),
            "%s (numeric form: %s)" % (cell(c["kill_criterion"]["statement"]), c["kill_criterion"]["numeric_form"]),
            cell(c["depends_on"]), cell(c["controls"]), cell(c["open_items"]), cell(c["verdict_bands"]),
        ]
        out.append("| " + " | ".join(cell(x) for x in row) + " |")
    return out


def regime_tables(reg):
    out = []
    for rid, r in reg["regimes"].items():
        out += ["### %s: %s" % (rid, r["name"]), "", cell(r["description"]), "",
                "| input | symbol | units | range | range basis | status | source | rationale |",
                "|---|---|---|---|---|---|---|---|"]
        for key, i in r["inputs"].items():
            units = i["units"] + (" (reference: %s)" % i["reference_electrode"] if i.get("reference_electrode") else "")
            out.append("| " + " | ".join(cell(x) for x in [key, i["symbol"], units, i["range"], i["range_basis"],
                                                         i["status"], i["source"], i["rationale"]]) + " |")
        out.append("")
    out += ["### Regime of each claim", "", "| claim | regime | why |", "|---|---|---|"]
    out += ["| %s | %s | %s |" % (k, v["regime"], cell(v["why"])) for k, v in reg["claim_regimes"].items()]
    return out


def deletion_tables(reg):
    out = ["| control | definition |", "|---|---|"]
    out += ["| %s | %s |" % (k, cell(v)) for k, v in reg["controls_defined"].items()]
    out += ["", "| step | claim | survives without mechanism | control | computation | expected direction |",
            "|---|---|---|---|---|---|"]
    for s in reg["steps"]:
        for c in s["controls"]:
            out.append("| " + " | ".join(cell(x) for x in [s["step"], s["claim"], s["survives_without_mechanism"],
                                                         c["control"], c["computation"], c["expected_direction"]]) + " |")
    out += ["", "**Rule.** " + cell(reg["rule"])]
    return out


def credit_table(reg):
    out = ["Status: %s. Role names are drawn from `charter/credit_taxonomy.md` (fetched)." % reg["status"], "",
           "| contributor | deck listing | status | roles |", "|---|---|---|---|"]
    for c in reg["contributors"]:
        out.append("| %s | %s | %s | %s |" % (cell(c["name"]), cell(c.get("deck_listing")),
                                              c.get("status", "pending-G0"), cell(c["roles"])))
    return out


def open_items(claims, regimes):
    out = ["### OPEN conventions and pending choices (per claim)", ""]
    for c in claims["claims"]:
        for item in c["open_items"]:
            out.append("- **%s.** %s" % (c["id"], cell(item)))
    out += ["", "### Thresholds", ""]
    for c in claims["claims"]:
        t = c["threshold"]
        out.append("- **%s.** value %s, status %s; proposed: %s" % (c["id"], cell(t["value"]), t["status"],
                                                                  cell(t["proposed"])))
    out += ["- **Study verdict.** rule %s; %s" % (claims["study_verdict"]["rule"], cell(claims["study_verdict"]["proposed"])),
            "", "### Provisional inputs (all source pending-S12)", ""]
    for rid, r in regimes["regimes"].items():
        for key, i in r["inputs"].items():
            out.append("- **%s / %s** (%s): range %s, basis %s" % (rid, key, i["symbol"], cell(i["range"]),
                                                                   cell(i["range_basis"])))
    out += ["", "### Disclosures", ""]
    out += ["- **%s.** %s" % (d["id"], cell(d["text"])) for d in claims["disclosures"]]
    out += ["", "### Design flags touched", "",
            "- **1** pre-registration timing and the calcite estimate seen near 0.5: C3 objection, disclosure D-flag1, S22.",
            "- **2** f(theta) <= 0.5 is not conformality: C3 objection; C4 criterion registered at G2.",
            "- **3** sign and definition of Delta_gamma_water: C3 OPEN item owned by S20/S21.",
            "- **4** nacre-to-PDA mapping: carboxylate controls and Li+/Al3+ competitors in C2; transplant row S12-T2.",
            "- **5** novelty audit: scope-guard patterns SG13-SG14 until the Phase 1 audit fixes the wording.",
            "- **6** MLIP free energies: C1 and C2 objections; trusted only after G6 tolerances.",
            "- **7** two corrosion regimes: charter/regimes.yaml; C5 split into aqueous Pourbaix and Li-referenced window.",
            "- **8** counting and scope hygiene: charter/numbering.md; insulating-film limitation in the scope guard and C4 item 18.",
            "", "### Process notes", "",
            "- This charter section is appended by `charter/packet.py` because the gate tool on main writes only the "
            "layer A summary; an integration change to `nacre gate --packet` is requested.",
            "- The CRediT fetch is recorded in `charter/credit_taxonomy.md`; its row in `ops/fetch_log.md` (outside "
            "lane a-charter) is an outstanding action for the integration session."]
    return out


def render():
    claims = load("claim_register.yaml")
    regimes = load("regimes.yaml")
    out = [MARKER, "", "## Claim register", "",
           "Source: `charter/claim_register.yaml` (version %s). Hypothesis: %s" % (claims["register_version"],
                                                                                  cell(claims["hypothesis"])), ""]
    out += claim_table(claims)
    out += ["", "## Numbering reconciliation", "",
            demote((CHARTER / "numbering.md").read_text(encoding="utf-8").split("\n", 1)[1].strip(), 2), ""]
    out += ["## Regimes", ""] + regime_tables(regimes) + [""]
    out += ["## Deletion register", ""] + deletion_tables(load("deletion_register.yaml")) + [""]
    out += ["## Scope guard", "",
            demote((CHARTER / "scope_guard.md").read_text(encoding="utf-8").split("\n", 1)[1].strip(), 2), ""]
    out += ["## Outcome branches", "",
            demote((CHARTER / "branches.md").read_text(encoding="utf-8").split("\n", 1)[1].strip(), 2), ""]
    out += ["## CRediT draft", ""] + credit_table(load("credit.yaml")) + [""]
    out += ["## Open items for the auditor", ""] + open_items(claims, regimes) + [""]
    return "\n".join(out)


def main():
    if not PACKET.exists():
        sys.exit("run `uv run nacre gate G0 --packet` first")
    head = PACKET.read_text(encoding="utf-8").split(MARKER, 1)[0].rstrip("\n")
    PACKET.write_text(head + "\n\n" + render(), encoding="utf-8")
    print("appended charter sections to %s" % PACKET.relative_to(ROOT))


if __name__ == "__main__":
    main()

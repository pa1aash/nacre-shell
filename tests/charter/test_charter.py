"""Structural checks on the Phase 0 charter (gate G0, layer A)."""
import importlib.util
import re
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
CHARTER = REPO / "charter"
CLAIM_IDS = ["C1", "C2", "C3", "C4", "C5"]
CLAIM_FIELDS = ["id", "name", "link", "physical_observable", "physics", "computation", "regime",
                "threshold", "kill_criterion", "depends_on", "controls", "open_items", "verdict_bands"]
PHASE7_ITEMS = {"C1": [1, 2, 3, 4], "C2": [5, 6, 7, 8], "C3": [9, 10, 11, 12, 13, 14],
                "C4": [15, 16, 17, 18], "C5": [19, 20, 21]}
DELETION_CONTROLS = {"bare_oxide", "chitosan_only", "catechol_only", "carboxylate_substituted", "PVDF"}


def load(name):
    return yaml.safe_load((CHARTER / name).read_text(encoding="utf-8"))


def fenced(text, info):
    m = re.search(r"^```%s\n(.*?)^```" % re.escape(info), text, re.MULTILINE | re.DOTALL)
    assert m, "no ```%s block" % info
    return m.group(1)


@pytest.fixture(scope="module")
def claims():
    return load("claim_register.yaml")["claims"]


@pytest.fixture(scope="module")
def regimes():
    return load("regimes.yaml")


@pytest.mark.parametrize("name", ["claim_register.yaml", "regimes.yaml", "deletion_register.yaml", "credit.yaml"])
def test_yaml_parses(name):
    assert isinstance(load(name), dict)


def test_claim_ids_exactly_c1_to_c5(claims):
    assert [c["id"] for c in claims] == CLAIM_IDS


def test_every_claim_has_every_field(claims):
    for c in claims:
        missing = [f for f in CLAIM_FIELDS if f not in c]
        assert not missing, "%s missing %s" % (c["id"], missing)
        assert set(c["physical_observable"]) >= {"symbol", "definition", "units"}
        assert set(c["verdict_bands"]) == {"feasible", "inconclusive", "falsified"}
        assert c["link"] in {"anchor", "sequester", "nucleate", "outcome-condition"}


def test_mechanistic_links_and_phase7_items(claims):
    links = {c["id"]: c["link"] for c in claims}
    assert links == {"C1": "anchor", "C2": "sequester", "C3": "nucleate",
                     "C4": "outcome-condition", "C5": "outcome-condition"}
    for c in claims:
        assert c["computation"]["phase"] == 7
        assert c["computation"]["items"] == PHASE7_ITEMS[c["id"]]


def test_thresholds_null_and_pending_g2(claims):
    for c in claims:
        t = c["threshold"]
        assert t["value"] is None, c["id"]
        assert t["status"] == "pending-G2", c["id"]
        assert "proposed" in t and isinstance(t["objections"], list)
        assert c["kill_criterion"]["numeric_form"] == "pending-G2", c["id"]


def test_deck_bands_recorded_as_proposed_with_flag2_objection(claims):
    c3 = claims[2]
    assert set(c3["threshold"]["proposed"]) == {"feasible", "inconclusive", "falsified"}
    assert "pending G2" in c3["threshold"]["proposed_status"]
    assert any("Design flag 2" in o for o in c3["threshold"]["objections"])
    assert any("OPEN (design flag 3)" in o for o in c3["open_items"])


def test_regimes_referenced_exist(claims, regimes):
    known = set(regimes["regimes"])
    for c in claims:
        refs = known if c["regime"] == "both" else {c["regime"]}
        assert refs <= known, c["id"]
        assert regimes["claim_regimes"][c["id"]]["regime"] == c["regime"]
    assert set(regimes["claim_regimes"]) == set(CLAIM_IDS)


def test_regime_inputs_provisional(regimes):
    required = {"pH", "electrode_potential", "temperature", "ionic_strength", "calcium_activity",
                "carbonate_speciation", "water_activity"}
    for rid, r in regimes["regimes"].items():
        keys = set(r["inputs"]) | ({"pH"} if "pH_analogue" in r["inputs"] else set())
        assert required <= keys, rid
        for key, i in r["inputs"].items():
            assert i["status"] == "provisional", (rid, key)
            assert i["source"] == "pending-S12", (rid, key)
            assert i["symbol"] and i["units"] and i["rationale"], (rid, key)
            assert "range" in i
            if i["range"] is not None:
                assert i["range_basis"], (rid, key)
        assert r["inputs"]["electrode_potential"]["reference_electrode"], rid


def test_every_mechanistic_step_has_deletion_control(claims):
    reg = load("deletion_register.yaml")
    assert set(reg["controls_defined"]) == DELETION_CONTROLS
    by_claim = {s["claim"]: s for s in reg["steps"]}
    for c in claims:
        if c["link"] in {"anchor", "sequester", "nucleate"}:
            step = by_claim[c["id"]]
            assert step["controls"] and step["survives_without_mechanism"]
    used = {ctl["control"] for s in reg["steps"] for ctl in s["controls"]}
    assert used <= DELETION_CONTROLS
    assert DELETION_CONTROLS <= used
    assert "generic adhesion study" in reg["rule"]


def test_numbering_maps_every_deck_item_once():
    rows = [ln for ln in (CHARTER / "numbering.md").read_text(encoding="utf-8").splitlines()
            if re.match(r"^\|\s*S\d+-\w+\s*\|", ln)]
    assert rows
    ids = []
    for ln in rows:
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        ids.append(cells[0])
        target = cells[2]
        assert target in CLAIM_IDS or target.startswith("dropped:"), ln
        if target.startswith("dropped:"):
            assert len(target) > len("dropped:") + 5, "dropped item needs a reason: " + ln
    assert len(ids) == len(set(ids)), "duplicate deck item ids"
    for prefix in ("S13-", "S21-K", "S28-"):
        assert any(i.startswith(prefix) for i in ids), prefix
    assert sum(i.startswith("S21-K") for i in ids) == 5


def test_depends_on_acyclic(claims):
    graph = {c["id"]: c["depends_on"] for c in claims}
    for deps in graph.values():
        assert set(deps) <= set(CLAIM_IDS)
    state = {}

    def visit(n):
        assert state.get(n) != "active", "cycle through %s" % n
        if state.get(n) == "done":
            return
        state[n] = "active"
        for d in graph[n]:
            visit(d)
        state[n] = "done"

    for n in graph:
        visit(n)


def test_scope_guard_patterns_parse():
    text = (CHARTER / "scope_guard.md").read_text(encoding="utf-8")
    lines = [ln for ln in fenced(text, "scope-guard").splitlines() if ln.strip() and not ln.startswith("#")]
    assert len(lines) >= 5
    rx = {}
    for ln in lines:
        pid, pattern = ln.split(None, 1)
        assert re.fullmatch(r"SG\d\d", pid), ln
        rx[pid] = re.compile(pattern, re.IGNORECASE)
    assert len(rx) == len(lines)
    hits = lambda s: any(r.search(s) for r in rx.values())
    for forbidden in ("a working device", "the corrosion rate fell", "capacity retention of the cell",
                      "the optimal interface"):
        assert hits(forbidden), forbidden
    assert not hits("the relaxed geometry of the interface")
    assert "thickness" in text and "item 18" in text


def test_credit_roles_from_fetched_taxonomy():
    text = (CHARTER / "credit_taxonomy.md").read_text(encoding="utf-8")
    assert "https://credit.niso.org/" in text and re.search(r"\b[0-9a-f]{64}\b", text)
    allowed = set(yaml.safe_load(fenced(text, "yaml credit-roles")))
    assert len(allowed) == 14
    credit = load("credit.yaml")
    for c in credit["contributors"]:
        assert set(c["roles"]) <= allowed, c["name"]
    drafted = [c for c in credit["contributors"] if c["roles"]]
    assert [c["name"] for c in drafted] == ["Palaash Gang"]
    assert drafted[0]["status"] == "draft"
    raw = (CHARTER / "credit.yaml").read_text(encoding="utf-8")
    assert ("# YOU: roles for every contributor, the Braun-group member names and the UIUC "
            "corresponding author are supplied at G0.") in raw


def test_packet_renders_every_section():
    spec = importlib.util.spec_from_file_location("charter_packet", CHARTER / "packet.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out = mod.render()
    for heading in mod.SECTIONS:
        assert "\n## %s\n" % heading in out, heading
    for cid in CLAIM_IDS:
        assert "| %s |" % cid in out

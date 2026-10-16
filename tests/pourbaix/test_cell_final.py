"""Final R-cell window (P0-W5.2): the F5 rule, the exchange route and the committed documents."""
import json

import pytest
from pourbaix_helpers import offline  # noqa: F401

from nacre.pourbaix import cell_final as C
from nacre.pourbaix import provenance
from nacre.pourbaix import window as w
from nacre.pourbaix.paths import POURBAIX_RESULTS, REPO

FINAL = POURBAIX_RESULTS / "final"


def _l(v):
    return {"status": "ok" if v is not None else "undetermined", "value_V": v}


def test_f5_falsification_must_hold_under_every_scheme():
    assert C.f5_verdict({"a": _l(3.9), "b": _l(3.7)}, 4.3, 0.0, True)[0] == "falsified"
    assert C.f5_verdict({"a": _l(4.32), "b": _l(3.7)}, 4.3, 0.0, True)[0] == "inconclusive"
    assert C.f5_verdict({"a": _l(3.9), "b": _l(None)}, 4.3, 0.0, True)[0] == "inconclusive"


def test_f5_solid_salt_pass_is_inconclusive_and_margin_applies():
    assert C.f5_verdict({"a": _l(4.6), "b": _l(4.5)}, 4.3, 0.0, True)[0] == "inconclusive"
    assert C.f5_verdict({"a": _l(4.6), "b": _l(4.5)}, 4.3, 0.0, False)[0] == "feasible"
    # a falsification has to clear the margin under every scheme
    assert C.f5_verdict({"a": _l(4.2), "b": _l(3.7)}, 4.3, 0.2, True)[0] == "inconclusive"


def test_exchange_book_adds_the_tabulated_enthalpy():
    def base(f):
        if f == "LiX":
            return -3.0, {}
        raise w.MissingPhase(f)

    bk = C.ExchangeBook(base, {"CaX2": ("LiX", 2, 0.25, [])})
    g, meta = bk("CaX2")
    assert g == pytest.approx(-5.75) and meta["kind"] == "derived"
    with pytest.raises(w.MissingPhase):
        bk("AlX3")


def _summary():
    p = FINAL / "cell_summary.json"
    if not p.is_file():
        pytest.skip("final R-cell not generated yet")
    return json.loads(p.read_text(encoding="utf-8"))


def test_every_phase_sink_and_scheme_is_reported_and_none_passes():
    s = _summary()
    for phase in ("CaCO3", "Al2O3"):
        po = s["phases"][phase]
        assert set(po["verdict_by_salt"]) == {"LiClO4", "LiBOB", "LiPCP"}
        for salt in ("LiClO4", "LiBOB", "LiPCP"):
            assert set(po["by_sink"][salt]["oxidation_by_scheme"]) == {"janaf", "mp", "expt"}
            assert po["by_sink"][salt]["F5"]["verdict"] in ("falsified", "inconclusive")
        assert po["by_sink"]["solvated"]["status"] == "undetermined"
    assert any("anodic stability" in x for x in s["limitations"])


def test_sink_attempts_cover_the_missing_salts():
    got = {a["formula"] for a in _summary()["sink_thermo_attempts"]}
    assert {"Al(NO3)3", "Ca(ClO4)2", "Al(ClO4)3", "AlCl3"} <= got


def test_cell_documents_conform_to_schema_v2():
    if provenance.git_object(*provenance.W4_SCHEMA_V2) is None:
        pytest.skip("schema v2 commit not in the local object store")
    for name in ("LiClO4", "LiBOB", "LiPCP", "solvated"):
        doc = json.loads((FINAL / "cell" / ("%s.json" % name)).read_text(encoding="utf-8"))
        assert provenance.validate_against(provenance.W4_SCHEMA_V2, doc)["valid"], name

"""Day 3 R-cell supplement (P0-W5.4): budget rules, the supplement cache, the Al(ClO4)3 quote and the
committed documents. Offline; nothing here needs the local-only Li-Al-O-H entries."""
import json
import math
import re

import pytest
from pourbaix_helpers import offline  # noqa: F401
from scipy import constants

from nacre.pourbaix import gas as gasmod
from nacre.pourbaix import supplement_cache as sc
from nacre.pourbaix import supplement_d3 as S
from nacre.pourbaix.paths import CONFIG_DIR, REPO

CFG = CONFIG_DIR / "supplement_d3.yaml"
DOCS = sc.SUPP_DIR / "cell"


def _cfg():
    import yaml

    return yaml.safe_load(CFG.read_text(encoding="utf-8"))["R-cell"]


class _P:
    """Minimal params stand-in: window_margin_expt sourced, window_margin sourced."""

    def entry(self, key):
        return {"value": 0.087 if key == "window_margin_expt" else 0.124}

    def value(self, key):
        return self.entry(key)["value"]


def test_m_expt_only_for_the_registered_reaction():
    cfg = _cfg()
    m, keys, _ = S.margin_for("CaCO3", "LiClO4", "expt", "CaCO3 + 2 LiClO4 -> Ca(ClO4)2 + CO2 + 0.5 O2 + 2 Li", cfg, _P())
    assert m == pytest.approx(0.087) and keys == ["window_margin_expt"]
    for phase, sink, rxn in (("Al2O3", "LiClO4", "Al2O3 + 6 LiClO4 -> 2 Al(ClO4)3 + 1.5 O2 + 6 Li"),
                             ("AlHO2", "LiClO4", "AlHO2 + 3 LiClO4 -> Al(ClO4)3 + 0.75 O2 + 0.5 H2O + 3 Li"),
                             ("CaCO3", "LiCl", "CaCO3 + 2 LiCl -> CaCl2 + CO2 + 0.5 O2 + 2 Li")):
        m, keys, why = S.margin_for(phase, sink, "expt", rxn, cfg, _P())
        assert m is None and keys == [] and "budget key" in why


def test_no_budget_key_never_passes_and_never_falsifies():
    assert S.ox_verdict([3.0], 4.5, None, True)[0] == "inconclusive"      # far below the cut-off
    assert S.ox_verdict([6.0], 4.5, None, False)[0] == "inconclusive"     # far above, solvated
    assert S.ox_verdict([], 4.5, 0.1, True)[0] == "inconclusive"          # undetermined
    assert S.ox_verdict([4.0], 4.5, 0.1, True)[0] == "falsified"
    assert S.ox_verdict([4.7], 4.5, 0.1, True)[0] == "inconclusive"       # solid-salt pass
    assert S.ox_verdict([4.7], 4.5, 0.1, False)[0] == "feasible"
    assert S.red_verdict(1.2, 2.8, None)[0] == "inconclusive"
    assert S.red_verdict(None, 2.8, 0.1)[0] == "inconclusive"
    assert S.red_verdict(1.2, 2.8, 0.1)[0] == "feasible"
    assert S.red_verdict(3.0, 2.8, 0.1)[0] == "falsified"


def test_supplement_cache_hashes_and_no_raw_mp_entries_committed(offline):
    bad = [b for b in sc.verify() if not b.startswith("absent (local only)")]
    assert bad == []
    man = sc.manifest()
    mp = [f for f in man["files"] if f["kind"] == "mp_entries"]
    assert mp and all(f["local_only"] and f["location"].startswith(".local/") for f in mp)
    assert all(f["licences"] == ["BY-C"] for f in mp)
    assert not list(sc.SUPP_CACHE.glob("mp_entries_*"))
    assert man["mp_database_version"] == json.loads((REPO / "results/preprint/pourbaix/cache/manifest.json")
                                                    .read_text())["mp_database_version"]


def test_janaf_tables_name_their_phase(offline):
    for species, head in sc.JANAF_HEADER.items():
        doc = json.loads((sc.SUPP_CACHE / ("janaf_%s.json" % species)).read_text(encoding="utf-8"))
        assert head in doc["text"].splitlines()[0]


def test_al_perchlorate_value_is_parsed_from_the_stored_quote(offline):
    doc = json.loads((sc.SUPP_CACHE / "lit_krivtsov1973_al_clo4_3.json").read_text(encoding="utf-8"))
    assert "anhydrous aluminum perchlorate" in doc["quote"] and "kcal" in doc["quote"]
    assert "html" not in doc and "text" not in doc  # only the quote is kept
    m = re.search(doc["value_pattern"], doc["quote"])
    kcal = float(m.group(1).replace("−", "-"))
    dfh, u, loc = sc.literature_dfh_kj("krivtsov1973_al_clo4_3")
    assert dfh == pytest.approx(kcal * constants.calorie) and dfh < 0 and u > 0
    assert "10.1007/BF00926423" in loc


def test_water_gas_terms_come_from_the_tables(offline):
    T = 298.15
    g = gasmod.formation_free_energy_ev("H2O", T, sc.SUPP_CACHE)
    h = gasmod.formation_enthalpy_ev("H2O", T, sc.SUPP_CACHE)
    s = gasmod.entropy_ev_per_K("H2O", T, sc.SUPP_CACHE)
    assert g < 0 and h < g and s > 0
    # liquid below gas at the standard state (the liquid onset is the lower one)
    gl = gasmod.formation_free_energy_ev("H2O_l", T, sc.SUPP_CACHE)
    assert gl < g


def test_extra_snapshot_matches_git(offline):
    path = S.extra_snapshot_path("8bc15c88f5f4a28e64d394186729836bac01cfec")
    if not path.is_file():
        pytest.skip("supplement not run yet")
    from nacre.pourbaix import inputs

    snap = json.loads(path.read_text(encoding="utf-8"))
    assert inputs.verify_snapshot(snap) == []
    assert set(snap["absent_keys"]) >= {"window_margin_red_caco3", "window_margin_red_corundum",
                                        "window_margin_red_boehmite"}


def _docs():
    paths = sorted(DOCS.glob("*.json"))
    if not paths:
        pytest.skip("supplement documents not written yet")
    return paths


def test_documents_are_schema_v3_and_never_unbounded(offline):
    for p in _docs():
        doc = json.loads(p.read_text(encoding="utf-8"))
        assert doc["schema_version"] == "3" and doc["mock"] is False
        sec = doc["stability"]["R-cell"]
        assert set(sec["windows"]) == {"CaCO3", "Al2O3", "AlOOH"}
        assert sec["schemes"]["expt"]["role"] == "governing"
        for win in sec["windows"].values():
            for lim in [win["reduction"], win["oxidation"], *win["oxidation_by_scheme"].values()]:
                if lim["status"] == "ok":
                    assert lim["value_V"] is not None and math.isfinite(lim["value_V"])
                else:
                    assert lim["value_V"] is None and lim["reason"]


def test_no_pass_is_reported_without_a_budget_or_with_a_solid_salt_sink(offline):
    for p in _docs():
        ver = json.loads(p.read_text(encoding="utf-8"))["extensions"]["p0-w5"]["verdicts"]
        for phase, v in ver.items():
            for c in v["by_cathode_class"].values():
                assert "feasible" not in c["verdict_at"].values()
            assert v["reduction"] == "inconclusive"  # no reduction budget key at the p0-cp3 params


def test_registered_caco3_perchlorate_confirms_the_c5_onset(offline):
    _docs()
    doc = json.loads((DOCS / "LiClO4.json").read_text(encoding="utf-8"))
    now = doc["stability"]["R-cell"]["windows"]["CaCO3"]["oxidation"]["value_V"]
    prev = json.loads((REPO / "results/preprint/pourbaix/c5/cell_scheme_table.json").read_text(encoding="utf-8"))
    row = next(r for r in prev["table"] if r["phase"] == "CaCO3" and r["sink"] == "LiClO4")
    assert now == pytest.approx(row["expt_V"], abs=1e-9)

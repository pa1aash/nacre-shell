import pytest

from lit_helpers import good_row
from nacre.lit import evidence as E

PATTERNS = [("SG05", E.re.compile(r"\bcorrosion[- ]rates?\b", E.re.I))]


def errs(**kw):
    return E.validate_row(good_row(**kw), PATTERNS)


def test_good_row_passes():
    assert errs() == []


def test_header_must_match_columns():
    out = E.validate_rows([good_row()], header=E.COLUMNS[:-1])
    assert out and out[0].startswith("header")


@pytest.mark.parametrize("doi", ["", "doi:10.1/x", "10.12/x", "https://doi.org/10.1021/x", "10.1021/ x"])
def test_doi_syntax(doi):
    assert any("DOI" in e for e in errs(doi=doi))


def test_doi_with_brackets_is_valid():
    assert errs(doi="10.1016/0022-0248(89)90168-1") == []


@pytest.mark.parametrize("loc", ["", "somewhere in the paper", "results"])
def test_locator_required_and_specific(loc):
    assert any("locator" in e for e in errs(locator=loc))


@pytest.mark.parametrize("loc", ["Table 1", "Fig. 3b", "Eq. (12)", "SI Table S4", "abstract", "pp. 12-13",
                                 "Section 3.2", "p. 155"])
def test_locator_forms(loc):
    assert errs(locator=loc) == []


@pytest.mark.parametrize("unit", ["mJ m^-2", "kJ mol^-1", "cm^3 mol^-1", "nm^-2", "V", "1", "degree", "mol/kg"])
def test_units_parse(unit):
    assert errs(unit=unit) == []


@pytest.mark.parametrize("unit", ["V vs Li", "wt%", "", "furlongs per bogon"])
def test_bad_units(unit):
    assert any("unit" in e for e in errs(unit=unit))


def test_grade_set_and_abstract_cap():
    assert any("grade" in e for e in errs(grade="E"))
    assert any("capped" in e for e in errs(extraction_route="abstract", grade="B"))
    assert errs(extraction_route="abstract", grade="D") == []


def test_compilation_capped_at_c():
    assert any("compilation" in e for e in errs(method="compilation: review table", grade="B"))
    assert errs(method="compilation: review table", grade="C") == []


def test_value_or_range_required():
    assert any("numeric value" in e for e in errs(value="", range_or_uncertainty=""))
    assert errs(value="", range_or_uncertainty="8.5..11.5") == []
    assert any("not numeric" in e for e in errs(value="about 9"))
    assert errs(value=">9") == []
    assert errs(value="1.2e-8") == []


@pytest.mark.parametrize("rng", ["±0.1", "±5%", "+0.2/-0.1", "1..2", ""])
def test_range_forms(rng):
    assert errs(range_or_uncertainty=rng) == []


def test_bad_range():
    assert any("range" in e for e in errs(range_or_uncertainty="roughly 1"))


def test_qualitative_rows():
    assert errs(unit="qualitative", value="calcite formed", range_or_uncertainty="",
                quantity="templated_mineralisation_outcome", retro_candidate="y: calcite formed") == []
    assert any("observed outcome" in e for e in errs(unit="qualitative", value=""))


def test_flags():
    assert any("contrary" in e for e in errs(contrary="maybe"))
    assert any("retro_candidate" in e for e in errs(retro_candidate="y"))
    assert any("retro_candidate" in e for e in errs(retro_candidate="yes"))


def test_row_id_unique_and_prefix():
    out = E.validate_rows([good_row(), good_row()])
    assert any("duplicate" in e for e in out)
    assert any("prefix" in e for e in errs(row_id="TA-001"))
    assert any("row_id" in e for e in errs(row_id="C-1"))


def test_method_and_conditions():
    assert any("method" in e for e in errs(method="guess"))
    assert any("conditions" in e for e in errs(conditions=""))
    assert any("retrieved_at" in e for e in errs(retrieved_at="yesterday"))


def test_long_quote_rejected():
    long = '"' + " ".join(["word"] * 15) + '"'
    assert any("quote" in e for e in errs(notes=long))
    assert errs(notes='"' + " ".join(["word"] * 14) + '"') == []


def test_scope_guard_patterns():
    assert any("SG05" in e for e in errs(notes="reports a corrosion rate"))


def test_scope_patterns_from_charter(tmp_path):
    (tmp_path / "charter").mkdir()
    (tmp_path / "charter" / "scope_guard.md").write_text("x\n```scope-guard\n# c\nSG01  \\bfoo\\b\n```\n")
    pats = E.scope_patterns(tmp_path)
    assert [p for p, _ in pats] == ["SG01"] and pats[0][1].search("FOO")
    assert E.scope_patterns(tmp_path / "missing") == []


def test_csv_roundtrip(tmp_path):
    p = tmp_path / "t.csv"
    E.write_csv(p, [good_row(notes="comma, and \"quote\"")])
    header, rows = E.read_csv(p)
    assert header == E.COLUMNS and rows[0]["notes"] == 'comma, and "quote"'
    assert E.validate_file(p) == []


def test_merge_dedupes_on_doi_locator_quantity():
    a = [good_row(row_id="TC-001")]
    b = [good_row(row_id="TE-001", thread="T-E", locator="P. 4,  table 2", doi="10.1021/EXAMPLE.123"),
         good_row(row_id="TE-002", thread="T-E", quantity="ksp_aragonite")]
    rows, dups = E.merge([a, b])
    assert [r["row_id"] for r in rows] == ["TC-001", "TE-002"]
    assert dups == [("TE-001", "TC-001")]


def test_merge_keeps_distinct_values_from_one_table():
    a = [good_row(row_id="TD-001", symbol="pKa1", value="9.12"),
         good_row(row_id="TD-002", symbol="pKa2", value="10.85")]
    rows, dups = E.merge([a])
    assert len(rows) == 2 and dups == []


def test_merge_qualitative_rows():
    q = dict(unit="qualitative", range_or_uncertainty="", quantity="templated_mineralisation_outcome")
    a = [good_row(row_id="TC-001", value="vaterite formed", **q),
         good_row(row_id="TC-002", value="no mineral", **q)]
    b = [good_row(row_id="TD-001", thread="T-D", value="vaterite microspheres", **q)]
    rows, dups = E.merge([a, b])
    assert [r["row_id"] for r in rows] == ["TC-001", "TC-002"]
    assert dups == [("TD-001", "TC-001")]


def test_coverage_statuses():
    rows = [good_row(row_id="TC-001"), good_row(row_id="TC-002", doi="10.1000/other", grade="D",
                                                  extraction_route="abstract"),
            good_row(row_id="TC-003", quantity="ksp_acc"),
            good_row(row_id="TC-004", quantity="ksp_vaterite", unit="qualitative", value="x")]
    cov = {c["id"]: c for c in E.coverage(rows)}
    assert cov["ksp_calcite"]["status"] == "covered"
    assert cov["ksp_calcite"]["grades"] == {"A": 1, "B": 0, "C": 0, "D": 1}
    assert cov["ksp_acc"]["status"] == "single-source"
    assert cov["ksp_vaterite"]["status"] == "gap"
    assert all(c["status"] in ("covered", "single-source", "gap") for c in cov.values())


def test_targets_cover_the_session_list():
    ids = {t["id"] for t in E.TARGETS}
    for need in ("gamma_nuc_water_acc", "gamma_nuc_water_calcite", "gamma_sub_water_oxide", "gamma_sub_water_organic",
                 "gamma_sub_nuc_or_contact_angle", "ksp_calcite", "ksp_aragonite", "ksp_vaterite", "ksp_acc",
                 "acc_excess_free_energy", "molar_volume_calcite", "molar_volume_acc", "hydration_free_energy_ca",
                 "pka_catechol", "dg_ca_catecholate", "dg_ca_carboxylate", "site_density_organic",
                 "w_adh_catechol_alumina_wet", "slurry_ph", "slurry_ionic_strength", "slurry_ca", "slurry_dic",
                 "incell_potential_range"):
        assert need in ids
    slugs = [s for t in E.TARGETS for s in t["slugs"]]
    assert len(slugs) == len(set(slugs))


def test_targets_cover_the_day4_list():
    ids = {t["id"] for t in E.TARGETS}
    for need in ("water_activity_drying_primary", "pvdf_surface_energy", "cathode_particle_diameter",
                 "asperity_contact_area", "template_mass_per_group", "ca_ionic_radius", "film_tunnelling_inputs",
                 "reduction_limit_thermochemistry", "al_perchlorate_thermochemistry", "anion_anodic_stability"):
        assert need in ids

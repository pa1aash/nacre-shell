"""The spec has a source for every value, the style is generated from it, and the palette holds its CVD record."""
import importlib.util
import itertools
import re
import warnings

import numpy as np
import pytest
import yaml
from figs_helpers import REPO

STYLE = REPO / "figures" / "style"


def _load(name):
    spec = importlib.util.spec_from_file_location("figs_" + name, STYLE / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def spec():
    return yaml.safe_load((STYLE / "rsc_spec.yaml").read_text())


@pytest.fixture(scope="module")
def palette():
    return yaml.safe_load((STYLE / "palette.yaml").read_text())


def test_every_spec_value_has_source_locator_and_quote(spec):
    for key, v in spec["values"].items():
        assert v.get("value") is not None, key
        assert v["source"] in spec["sources"], key
        assert v.get("locator", "").strip(), key
        assert v.get("quote", "").strip(), key


def test_sources_name_a_logged_fetch(spec):
    import json
    ids = {json.loads(line)["id"] for line in (STYLE / "fetch_log.jsonl").read_text().splitlines()}
    for sid, s in spec["sources"].items():
        assert s["fetch"] in ids, sid


def test_outstanding_values_record_the_search(spec):
    assert spec["outstanding"]
    for key, v in spec["outstanding"].items():
        assert v["searched"] and v["result"].strip(), key


def test_applied_values_trace_to_a_value_or_a_house_reason(spec):
    for key, a in spec["applied"].items():
        if a.get("house"):
            assert a.get("reason", "").strip(), key
        else:
            ref = a["from"]
            assert ref.startswith("values.") and ref.split(".", 1)[1] in spec["values"], key
            assert a.get("rule", "").strip(), key


def test_style_is_generated_and_current():
    mod = _load("build_style")
    assert (STYLE / "rsc.mplstyle").read_text() == mod.build()


def test_every_style_line_traces_to_the_spec(spec, palette):
    for line in (STYLE / "rsc.mplstyle").read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        assert "#" in line, line
        trace = line.split("#", 1)[1].strip()
        m = re.match(r"(applied|palette)\.([A-Za-z_.]+)", trace)
        assert m, line
        if m.group(1) == "applied":
            assert m.group(2).split(".")[0] in spec["applied"], line
        else:
            node = palette
            for part in m.group(2).split("."):
                node = node[part]


def test_style_values_match_spec(spec):
    import matplotlib
    rc = matplotlib.rc_params_from_file(str(STYLE / "rsc.mplstyle"), use_default_template=False)
    ap = spec["applied"]
    assert rc["font.size"] == ap["font_size"]["value"]
    assert rc["axes.linewidth"] == ap["line_width_min"]["value"]
    assert rc["savefig.dpi"] == ap["raster_dpi"]["value"]
    assert rc["font.sans-serif"][0] == ap["font_family"]["value"]
    assert rc["pdf.fonttype"] == 42


def test_widths_match_rsc_columns(spec):
    for kind in ("single", "double"):
        cm = spec["values"]["width_%s_column" % kind]["value"]
        assert abs(spec["applied"]["width_%s_in" % kind]["value"] - cm / 2.54) < 1e-4


def test_palette_rebuild_is_current_when_source_cached():
    mod = _load("build_palette")
    if not (mod.CACHE / "r_colorstuff.R").exists():
        pytest.skip("fetched Okabe-Ito source not cached locally (network rebuild not run in tests)")
    assert (STYLE / "palette.yaml").read_text() == mod.build()


def test_palette_elements_and_spaces(palette):
    from ase.data import atomic_numbers
    from ase.data.colors import jmol_colors
    for el in ["Al", "O", "H", "C", "Ca", "N", "Li"]:
        e = palette["elements"][el]
        assert np.allclose(e["jmol_srgb"], jmol_colors[atomic_numbers[el]], atol=5e-5)
        srgb = np.array(e["srgb"])
        lin = np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)
        assert np.allclose(lin, e["linear_rgb"], atol=1e-4)
        assert e["adjusted"] == (not np.allclose(e["srgb"], e["jmol_srgb"]))
    adjusted = {a["element"] for a in palette["adjustments"]}
    assert adjusted == {k for k, v in palette["elements"].items() if v["adjusted"]}


def test_palette_constrained_pairs_clear_threshold(palette):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        from colorspacious import cspace_convert, deltaE
    thr = palette["delta_e_min"]
    for pair in palette["pairs"]["required"] + palette["pairs"]["extended"]:
        a, b = pair.split("-")
        ca, cb = np.array(palette["elements"][a]["srgb"]), np.array(palette["elements"][b]["srgb"])
        for cond in (None, "deuteranomaly", "protanomaly", "tritanomaly"):
            if cond:
                sp = {"name": "sRGB1+CVD", "cvd_type": cond, "severity": 100}
                sa = np.clip(cspace_convert(ca, sp, "sRGB1"), 0, 1)
                sb = np.clip(cspace_convert(cb, sp, "sRGB1"), 0, 1)
            else:
                sa, sb = ca, cb
            assert deltaE(sa, sb, input_space="sRGB1") >= thr, (pair, cond)
    for pair in palette["pairs"]["required"] + palette["pairs"]["extended"]:
        assert min(palette["cvd_record"]["final"][pair].values()) >= thr


def test_required_pairs_are_the_session_pairs(palette):
    assert set(palette["pairs"]["required"]) == {"Ca-O", "Ca-C", "Al-O", "Al-H"}


def test_categorical_and_maps_recorded(palette):
    oi = palette["categorical"]["okabe_ito"]
    assert len(oi) == 9 and palette["provenance"]["categorical"]["version"] == "4.6.1"
    for name in palette["categorical"]["cycle"]:
        assert name in oi
    assert palette["provenance"]["colormaps"]["pinned"] == "==1.10"
    from importlib.metadata import version
    assert version("cmcrameri") == palette["provenance"]["colormaps"]["version"]


def test_mock_inputs_regenerate_identically(tmp_path, monkeypatch):
    spec_ = importlib.util.spec_from_file_location("figs_make_mock", REPO / "figures/src/mock/make_mock.py")
    mod = importlib.util.module_from_spec(spec_)
    spec_.loader.exec_module(mod)
    monkeypatch.setattr(mod, "HERE", tmp_path)
    mod.main()
    for f in ["retro_results.json", "screen_summary.json", "stability.json", "params.yaml"]:
        assert (tmp_path / f).read_text() == (REPO / "figures/src/mock" / f).read_text(), f

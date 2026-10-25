"""PH-W6.1: the regime figures (9 to 11), the templates (12 to 15) and the release check."""
import copy
import json
import re

import pytest
from figs_helpers import REPO

from nacre.figs import build, colours, paths, style, upstream

LADDER_SHA = "595636ef1c7cfd774e27040f7a60f5f32ff7e55569525a7a84e009ef37354d6b"
TEMPLATE_SOURCE = '''
from nacre.figs import style
from nacre.figs.template import placeholder

FIGURE = {"id": "fig99", "status": "template", "waits_for": "a test input", "claim": "c", "caption_key": "k",
          "width": "single", "height_cm": 7.0}


def build(data, root, aux):
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=style.figsize(FIGURE["width"], FIGURE["height_cm"], root))
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    placeholder(ax, root)
    return fig
'''


def _synthetic_template(tmp_path):
    path = tmp_path / "fig99.py"
    path.write_text(TEMPLATE_SOURCE)
    return build.load_template(path)


def _mod(fid):
    return build.load_template(paths(REPO)["src"] / (fid + ".py"))


def _manifest():
    return json.loads((REPO / "figures/out/manifest.json").read_text())


def test_ladder_input_is_the_registered_file():
    assert upstream.entry("ladder_v3", REPO)["sha256"] == LADDER_SHA
    upstream.snapshot_bytes("ladder_v3", REPO)  # raises on a mismatch
    rec = _manifest()["figures"]["fig9"]
    assert rec["input_sha256"] == LADDER_SHA and rec["input_source"]["owner"] == "p0-w5"


def test_ladder_cells_cover_both_framings_of_every_drawn_phase():
    f9 = _mod("fig9")
    cells, groups = f9.ladder_cells(upstream.load("ladder_v3", REPO))
    assert sum(len(v) for v in groups.values()) == 18 and len(cells) == 36
    assert {v for c in cells.values() for v in c.values()} <= set(f9.VERDICTS)


def test_ladder_refuses_a_sensitivity_that_changes_a_verdict():
    f9 = _mod("fig9")
    main = upstream.load("ladder_v3", REPO)
    sens = copy.deepcopy(main)
    sens["rows"][0]["k1_class_lfp"] = "falsified" if sens["rows"][0]["k1_class_lfp"] != "falsified" else "inconclusive"
    f9.same_verdicts(main, main)
    with pytest.raises(ValueError, match="changes verdicts"):
        f9.same_verdicts(main, sens)


def test_ladder_class_labels_come_from_the_registered_classes():
    f9 = _mod("fig9")
    assert f9.class_labels(upstream.load("thresholds_screen_ph", REPO)) == ["3.65", "4.2–4.3", "4.4–4.5"]


def test_verdict_fills_are_distinct_in_every_vision_condition():
    f9 = _mod("fig9")
    fills = f9.verdict_fills(REPO)
    assert colours.min_delta_e(list(fills.values())) >= float(style.palette(REPO)["delta_e_min"])
    assert len({f9.HATCH[v] for v in f9.ORDER}) == 3


def test_benchmark_markers_agree_with_the_band():
    f10 = _mod("fig10")
    data = upstream.load("benchmark_w51", REPO)
    band = float(upstream.load("benchmark_w51_summary", REPO)["summary"]["e_form"]["max"])
    pts = f10.points(data, band)
    assert len(pts) == 17 and all(v < 0 for _f, _p, v, _s in pts)
    with pytest.raises(ValueError, match="benchmarked"):
        f10.points(data, 1.0)


def test_passivation_windows_read_the_governing_and_reference_rows():
    f11 = _mod("fig11")
    w = f11.windows(upstream.load("passivation_window_v3", REPO), [3.0, 10.0])
    assert sorted(w) == [1e-6, 1e-5, 1e-4]
    assert w[1e-6]["governing"] is None and w[1e-4]["reference"][2] is True
    assert w[1e-4]["governing"][0] > w[1e-4]["reference"][0]  # inside the crystalline window


@pytest.mark.parametrize("fid", ["fig9", "fig10", "fig11", "fig12", "fig14", "fig15", "fig17"])
def test_new_captions_stay_short_and_avoid_banned_words(fid):
    text = (REPO / "figures/src/captions" / (fid + ".md")).read_text()
    draft = re.search(r"^## Draft\n(.*?)(?=^## |\Z)", text, re.S | re.M).group(1).strip()
    assert len(draft.split()) <= 75
    assert not re.search(r"\b(works?|protects?|outperforms?|failed)\b", draft, re.I)


def test_no_template_remains_and_fig13_is_dropped():
    """PH-W6.3: the Al-salt template is deregistered; the Al-salt ladder is a table input."""
    man = _manifest()
    assert not man.get("templates") and "fig13" not in man["figures"]
    assert not (paths(REPO)["src"] / "fig13.py").exists()
    assert not list((REPO / "figures/out").glob("**/fig13*"))
    assert "al_salt_ladder" in man["tables"]


def test_release_check_fails_while_stubs_remain():
    out = build.release_problems(REPO)
    assert any(x.startswith("fig16:") for x in out)
    assert not any("template" in x for x in out)


def test_release_check_passes_on_a_clean_manifest(tmp_path):
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps({"figures": {"fig9": {"mock": False}}, "schematics": {"fig3": {"stub": False}}}))
    assert build.release_problems(REPO, p) == []
    p.write_text(json.dumps({"figures": {"fig9": {"mock": True}}}))
    assert build.release_problems(REPO, p) == ["fig9: built from mock data"]


def test_template_without_placeholder_is_refused(tmp_path):
    mod = _synthetic_template(tmp_path)
    real = mod.build

    def bare(data, root, aux):
        fig = real(data, root, aux)
        for ax in fig.axes:
            for ln in list(ax.lines):
                ln.remove()
        return fig
    mod.build = bare
    with pytest.raises(Exception, match="placeholder"):
        build.render_template(REPO, mod, tmp_path, cvd=False)


def test_a_template_has_no_input_and_is_skipped_in_mock_mode(tmp_path):
    fig = _synthetic_template(tmp_path).FIGURE
    assert fig["status"] == "template" and "input" not in fig and fig["waits_for"]

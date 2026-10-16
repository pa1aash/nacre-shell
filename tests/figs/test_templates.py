"""The four templates build from mock inputs, pass the checker and respect the mock boundary."""
import json

import pytest
from figs_helpers import REPO, check, plt

from nacre.figs import build, paths, schema

TEMPLATES = ["fig4", "fig5", "fig6", "fig7"]


@pytest.fixture(autouse=True)
def _close():
    yield
    plt().close("all")


def _mod(fid):
    return build.load_template(paths(REPO)["src"] / (fid + ".py"))


def test_discovery_finds_the_four_templates():
    assert [p.stem for p in build.discover(REPO)] == TEMPLATES


@pytest.mark.parametrize("fid", TEMPLATES)
def test_template_declares_one_claim_and_a_caption_key(fid):
    fig = _mod(fid).FIGURE
    assert fig["claim"].strip() and fig["caption_key"].strip()
    assert fig["width"] in ("single", "double")


@pytest.mark.parametrize("fid", TEMPLATES)
def test_mock_input_is_marked_and_matches_schema(fid):
    mod = _mod(fid)
    data, path = build.load_input(REPO, mod, mock=True)
    assert data["mock"] is True
    assert path.parent == paths(REPO)["mock"]
    sch = json.loads((REPO / mod.FIGURE["schema"]).read_text())
    assert schema.validate(data, sch) == []


@pytest.mark.parametrize("fid", TEMPLATES)
def test_checker_accepts_template(fid):
    mod = _mod(fid)
    data, _ = build.load_input(REPO, mod, mock=True)
    _plt, fig = build.make_figure(REPO, mod, data)
    assert check(fig) == []


def test_mock_output_refused_outside_mock_dir(tmp_path):
    mod = _mod("fig4")
    data, path = build.load_input(REPO, mod, mock=True)
    with pytest.raises(build.FigureError, match="mock output"):
        build.render(REPO, mod, data, path, tmp_path)


def test_real_output_refused_in_mock_dir():
    mod = _mod("fig4")
    data, path = build.load_input(REPO, mod, mock=True)
    data = dict(data, mock=False)
    with pytest.raises(build.FigureError, match="real output"):
        build.render(REPO, mod, data, path, paths(REPO)["out_mock"])


def test_real_input_marked_mock_is_refused(tmp_path, monkeypatch):
    mod = _mod("fig4")
    fake = tmp_path / "in.json"
    fake.write_text((REPO / mod.FIGURE["mock_input"]).read_text())
    monkeypatch.setitem(mod.FIGURE, "input", str(fake))
    with pytest.raises(build.FigureError, match="marked mock"):
        build.load_input(REPO, mod, mock=False)


def test_missing_real_input_is_skipped_not_built():
    mod = _mod("fig5")
    data, path = build.load_input(REPO, mod, mock=False)
    if path.exists():
        pytest.skip("real input present")
    assert data is None


def test_schema_validator_reports_errors():
    sch = json.loads((REPO / "figures/src/schemas/fig4_retrodiction.schema.json").read_text())
    errs = schema.validate({"mock": True, "schema": "wrong", "cases": []}, sch)
    assert any("must equal" in e for e in errs)
    assert any("missing" in e for e in errs)
    assert any("fewer than" in e for e in errs)


def test_cli_is_discovered():
    from nacre.cli import build_parser
    args = build_parser().parse_args(["figs", "--mock", "--only", "fig4"])
    assert args.mock and args.only == ["fig4"] and callable(args.func)


def test_cvd_simulation_keeps_shape_and_range():
    import numpy as np

    from nacre.figs import cvd
    rgb = np.random.default_rng(0).random((4, 5, 3))
    for cond in cvd.CONDITIONS:
        out = cvd.simulate_rgb(rgb, cond)
        assert out.shape == rgb.shape and out.min() >= 0.0 and out.max() <= 1.0


def test_fig7_fills_clear_the_palette_threshold():
    from nacre.figs import colours, style
    fills, names, _f, d = colours.distinct_fills(4, REPO)
    assert len(set(names)) == 4
    assert colours.min_delta_e(fills) >= float(style.palette(REPO)["delta_e_min"])

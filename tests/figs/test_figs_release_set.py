"""PH-W6.8 (G10): the release figure set and the paper agree: nothing built is unreferenced, nothing referenced is unbuilt."""
import json
import re

import yaml
from figs_helpers import REPO

from nacre.figs import build

PAPER = REPO / "preprint/paper"
INCLUDE_RE = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{[^}]*?/figures/out/(?:[\w/]+/)?(\w+)\.pdf\}")
REF_RE = re.compile(r"\\(?:[a-zA-Z]*ref)\{([^}]*)\}")


def _manifest():
    return json.loads((REPO / "figures/out/manifest.json").read_text())


def _release_set():
    """Figure ids the release builds: data figures, renders and the deliverable schematics."""
    man = _manifest()
    table = yaml.safe_load((REPO / "figures/tikz/schematics.yaml").read_text())["schematics"]
    schem = {k for k in man.get("schematics", {}) if table.get(k, {}).get("deliverable", True)}
    return set(man.get("figures", {})) | set(man.get("renders", {})) | schem


def _paper_text():
    return {p: p.read_text(encoding="utf-8") for p in sorted(PAPER.rglob("*.tex"))}


def _included():
    return {m.group(1) for t in _paper_text().values() for m in INCLUDE_RE.finditer(t)}


def _referenced():
    """Ids whose figure environment is cited by a \\ref, plus every id the paper includes."""
    labels = {}
    for t in _paper_text().values():
        for env in re.finditer(r"\\begin\{(figure\*?)\}(.*?)\\end\{\1\}", t, re.S):
            inc, lab = INCLUDE_RE.search(env.group(2)), re.search(r"\\label\{([^}]+)\}", env.group(2))
            if inc and lab:
                labels[lab.group(1)] = inc.group(1)
    cited = {x.strip() for t in _paper_text().values() for m in REF_RE.finditer(t) for x in m.group(1).split(",")}
    return _included() | {fid for lab, fid in labels.items() if lab in cited}


def test_every_release_figure_is_referenced_by_the_paper_or_the_si():
    assert not _release_set() - _referenced(), sorted(_release_set() - _referenced())


def test_every_referenced_figure_is_built():
    built = _release_set()
    assert not _referenced() - built, sorted(_referenced() - built)
    for fid in _referenced():
        assert (REPO / "figures/out" / (fid + ".pdf")).exists(), fid


def test_dropped_figures_keep_their_sources_but_are_not_built():
    gone = build.dropped(REPO)
    assert set(gone) == {"fig5", "fig9", "fig12"}
    for fid in gone:
        assert (REPO / "figures/src" / (fid + ".py")).exists()
        assert fid not in _release_set() and fid not in {p.stem for p in build.discover(REPO)}
        assert not list((REPO / "figures/out").glob("**/%s[._]*" % fid))


def test_an_unreferenced_figure_is_caught():
    assert {"fig99"} - _referenced() == {"fig99"}
    assert {"fig2", "fig17", "fig1"} <= _referenced()

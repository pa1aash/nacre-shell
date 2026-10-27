"""Caption drafts: short, numbers only through macros, every macro defined or requested and resolvable."""
import json
import re
import subprocess

import pytest
import yaml
from figs_helpers import REPO

from nacre.figs import upstream

CAPTIONS = REPO / "figures/src/captions"
FIGS = ["fig1", "fig2", "fig3", "fig4", "fig7", "fig10", "fig11", "fig14", "fig15", "fig17"]  # release set (fig5, fig9, fig12 dropped)
MAX_WORDS = 75  # PH-W6.7: short descriptive captions, counting the bold figure label
MAX_SENTENCES = 3
CROSS_KEY = "cross: excluded (K2: every cell dissolves; K1: thermodynamically excluded†)"  # G4, verbatim
MACRO_RE = re.compile(r"\\(Num[A-Z][A-Za-z]*)")
# Digits a caption may carry that are not numbers of the study: the figure label, case and link
# identifiers (RC04, C3a), the saturation condition Omega_bulk = 1, which is a definition, and the
# class edges "4.4–4.5 V" the brushite sentence of fig15 names (G7).
ALLOWED_DIGITS = [r"\*\*Fig\. [0-9]+\*\*", r"\bRC[0-9]{2}\b", r"\bC[0-9][a-z]?\b", r"\bK[0-9]\b", r"Ω_bulk = 1\b", r"4\.4–4\.5 V"]


def _draft(fid):
    text = (CAPTIONS / (fid + ".md")).read_text()
    m = re.search(r"^## Draft\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    assert m, fid
    return m.group(1).strip()


def _requests():
    return yaml.safe_load((CAPTIONS / "macro_requests.yaml").read_text())["requests"]


def _w8():
    return yaml.safe_load((CAPTIONS / "macro_requests.yaml").read_text())["defined_by_w8"]


def _defined():
    """Macros in this tree's sources.yaml, plus those W8 has defined on its branch (not merged yet)."""
    path = REPO / "preprint/generated/sources.yaml"
    here = set(yaml.safe_load(path.read_text())["macros"]) if path.exists() else set()
    return here | set(_w8()["macros"])


def test_w8_defined_macros_exist_at_the_recorded_commit():
    w8 = _w8()
    out = subprocess.run(["git", "-C", str(REPO), "show", "%s:preprint/generated/sources.yaml" % w8["commit"]],
                         capture_output=True, text=True)
    if out.returncode != 0:
        pytest.skip("W8 commit %s not in this clone" % w8["commit"][:7])
    assert set(w8["macros"]) <= set(yaml.safe_load(out.stdout)["macros"])


@pytest.mark.parametrize("fid", FIGS)
def test_draft_is_short(fid):
    assert len(_draft(fid).split()) <= MAX_WORDS


def _sentences(draft):
    body = re.sub(r"^\*\*Fig\. [0-9]+\*\*\s*", "", draft)
    return [x for x in re.split(r"(?<=[.!?])\s+(?=[A-Z(\\])", body) if x.strip()]


@pytest.mark.parametrize("fid", FIGS)
def test_draft_has_at_most_three_sentences(fid):
    assert len(_sentences(_draft(fid))) <= MAX_SENTENCES, _sentences(_draft(fid))


@pytest.mark.parametrize("fid", FIGS)
def test_draft_states_no_findings_and_no_hedging_chains(fid):
    text = _draft(fid)
    assert not re.search(r"\b(consistent with|suggests?|appears?|may|might|could|shows? that|confirms?)\b", text, re.I)
    assert "thermodynamically excluded" not in text.replace(CROSS_KEY, "")


PROCESS_RE = re.compile(r"\b(registered|ruling|cp[0-9]+|deviations?|frozen|checkpoints?|ledger|pre-registered|sessions?|falsified)\b", re.I)


@pytest.mark.parametrize("fid", FIGS)
def test_draft_has_no_process_vocabulary(fid):
    assert not PROCESS_RE.findall(_draft(fid)), PROCESS_RE.findall(_draft(fid))


def test_the_process_vocabulary_check_catches_a_planted_word():
    assert PROCESS_RE.search("Grey band: registered error band.") and PROCESS_RE.search("falsified (vermillion)")


def test_the_sentence_counter_catches_a_fourth_sentence():
    assert len(_sentences("**Fig. 1** One. Two. Three. Four.")) == 4


@pytest.mark.parametrize("fid", FIGS)
def test_draft_numbers_are_macro_names_only(fid):
    text = _draft(fid)
    for pat in ALLOWED_DIGITS:
        text = re.sub(pat, "", text)
    assert not re.findall(r"[0-9]", text), re.findall(r".{0,20}[0-9].{0,20}", text)


@pytest.mark.parametrize("fid", FIGS)
def test_every_macro_is_defined_or_requested(fid):
    names = set(MACRO_RE.findall(_draft(fid)))
    missing = names - _defined() - set(_requests())
    assert not missing, sorted(missing)


def test_requests_do_not_duplicate_defined_macros():
    assert not set(_requests()) & _defined()


def _resolve(spec):
    """The value a requested macro reads, from the pinned snapshot of its owner file."""
    by_path = {e["path"]: k for k, e in upstream.registry(REPO).items()}
    if "pattern" in spec:
        text = (REPO / spec["source"]).read_text()
        if spec.get("reduce") == "count":
            return len(re.findall(spec["pattern"], text, re.M))
        return re.search(spec["pattern"], text, re.M).group(1)
    doc = json.loads(upstream.snapshot_bytes(by_path[spec["source"]], REPO))
    for part in spec["key"].split("/"):
        doc = doc[int(part)] if isinstance(doc, list) else doc[part]
    return doc


@pytest.mark.parametrize("name", sorted(yaml.safe_load((CAPTIONS / "macro_requests.yaml").read_text())["requests"]))
def test_requested_macro_resolves_to_a_number(name):
    value = _resolve(_requests()[name])
    assert isinstance(float(value), float)


def test_fig4_caption_names_one_null_range_for_both_nulls():
    rec = json.loads(upstream.snapshot_bytes("retro_results", REPO))
    nulls = rec["summary"]["permutation_null"]
    assert nulls["within_study"]["median"] == nulls["across_studies"]["median"]
    assert nulls["within_study"]["range95"] == nulls["across_studies"]["range95"]


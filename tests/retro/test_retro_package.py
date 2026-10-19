"""ChemRxiv package validator (lane p0-w2, P0-W2.4a)."""
import argparse
import shutil
from pathlib import Path

import pytest
import yaml

from nacre import _util
from nacre.retro import cli, package

ROOT = _util.repo_root(Path(__file__).parent)
INPUTS = [package.METADATA, package.CHECKLIST, package.RECHECK, package.FETCH_INDEX, package.POLICY_INDEX,
          package.LEDGER, package.REGISTER, package.TAXONOMY, Path("charter/scope_guard.md"),
          Path("preprint/paper/lint/scope_allowlist.txt"), Path("preprint/paper/lint/scope_patterns.txt")]


@pytest.fixture
def root(tmp_path):
    for rel in INPUTS:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, tmp_path / rel)
    return tmp_path


def _edit_meta(root, fn):
    path = root / package.METADATA
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    fn(data)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _append(root, rel, text):
    path = root / rel
    path.write_text(path.read_text(encoding="utf-8") + text, encoding="utf-8")


def test_orcid_checksum():
    assert package.orcid_checksum_ok("0009-0006-7448-9488")
    assert package.orcid_checksum_ok("0000-0002-1694-233X")
    assert not package.orcid_checksum_ok("0009-0006-7448-9487")
    assert not package.orcid_checksum_ok("0009-0006-7448")
    assert not package.orcid_checksum_ok(None)


def test_committed_package_passes_with_placeholders_listed():
    errors, info = package.check(ROOT)
    assert errors == []
    paths = {p for p, _ in info["placeholders"]}
    assert {"title.final", "funding.statement", "competing_interests.statement", "ai_use.wording",
            "authors[5].orcid"} <= paths
    assert "Paul V. Braun" in info["credit_missing"]


def test_release_mode_fails_on_placeholders():
    errors, info = package.check(ROOT, release=True)
    assert len(errors) == len(info["placeholders"]) > 0
    assert all(e.startswith("release: placeholder") for e in errors)


def test_copied_package_passes(root):
    assert package.check(root)[0] == []


def test_email_address_rejected(root):
    _append(root, package.CHECKLIST, "\nContact: someone" + chr(64) + "example.org\n")
    assert any("email address" in e for e in package.check(root)[0])


def test_bad_orcid_rejected(root):
    _edit_meta(root, lambda d: d["authors"][0].update(orcid="0009-0000-8926-5521"))
    errors = package.check(root)[0]
    assert any("MOD 11-2" in e for e in errors)
    assert any("differs from the register" in e for e in errors)


def test_author_order_must_match_register(root):
    _edit_meta(root, lambda d: d["authors"].reverse())
    assert any("family_name" in e and "register" in e for e in package.check(root)[0])


def test_single_corresponding_author(root):
    _edit_meta(root, lambda d: d["authors"][0].update(corresponding=True))
    assert any("exactly one corresponding" in e for e in package.check(root)[0])


def test_credit_roles_checked_against_taxonomy(root):
    _edit_meta(root, lambda d: d["authors"][0].update(credit_roles=["Methodology", "Coding"]))
    errors = package.check(root)[0]
    assert errors == ["authors[0] Bharti: 'Coding' is not a CRediT role"]


def test_sourced_item_needs_recheck_mark_and_known_id(root):
    def edit(d):
        d["licence"]["recheck_live"] = False
        d["content_type"]["source"] = ["T9-9"]
    _edit_meta(root, edit)
    errors = package.check(root)[0]
    assert any("licence" in e and "recheck_live" in e for e in errors)
    assert any("unknown requirement id 'T9-9'" in e for e in errors)


def test_cited_id_must_appear_in_recheck_list(root):
    _edit_meta(root, lambda d: d["content_type"].update(source=["T1-3"]))
    assert any("T1-3 is not listed" in e for e in package.check(root)[0])


def test_checklist_items_need_source_and_mark(root):
    _append(root, package.CHECKLIST, "\n- [ ] An unsourced step.\n- [ ] A captured step [T1-1].\n")
    errors = package.check(root)[0]
    assert any("cites no requirement" in e for e in errors)
    assert any("not marked 're-check live'" in e for e in errors)


def test_result_numbers_rejected(root):
    _append(root, package.RECHECK, "\nThe margin is 0.12 V and 40 % of draws.\n")
    found = [e for e in package.check(root)[0] if "rule R5" in e]
    assert len(found) == 2


def test_non_result_digits_allowed():
    text = "CC BY 4.0, ORCID 0009-0006-7448-9488, doi:10.1063/1.4812323, [T1-2], P0-W8.5, 2026-10-19, SHA-256"
    assert package.result_numbers(text) == []


def test_scope_language_rejected(root):
    _edit_meta(root, lambda d: d["keywords"]["proposed"].append("corrosion rate"))
    assert any("SG05" in e for e in package.check(root)[0])


def test_missing_file_reported(root):
    (root / package.RECHECK).unlink()
    assert package.check(root)[0] == ["missing package file: %s" % package.RECHECK]


def test_package_check_command(capsys):
    parser = argparse.ArgumentParser()
    cli.register(parser.add_subparsers(dest="command"))
    args = parser.parse_args(["retro", "package-check"])
    assert args.func(args) == 0
    out = capsys.readouterr().out
    assert "package check: PASS" in out
    assert "title.final: TBD" in out
    args = parser.parse_args(["retro", "package-check", "--release"])
    assert args.func(args) == 1

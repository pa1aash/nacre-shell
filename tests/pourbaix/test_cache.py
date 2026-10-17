"""The data cache: complete, hash-pinned, attributed, offline-readable and free of the key."""
import json

from pourbaix_helpers import env_key, offline  # noqa: F401

from nacre.pourbaix import cache, gas


def test_manifest_hashes_match(offline):  # noqa: F811
    assert cache.verify() == []


def test_every_file_records_request_time_and_version(offline):  # noqa: F811
    m = cache.manifest()
    assert m["mp_database_version"]
    kinds = {f["kind"] for f in m["files"]}
    assert kinds == {"mp_entries", "mp_ion_reference_data", "janaf_table", "nbs_ocr"}
    for f in m["files"]:
        rec = cache.load(f["file"])
        assert rec["request"] and rec["retrieved_utc"].endswith("Z")
        if f["kind"].startswith("mp_"):
            assert rec["mp_database_version"] == m["mp_database_version"]
            assert rec["client_versions"]["mp-api"]


def test_licence_and_attribution_recorded(offline):  # noqa: F811
    readme = (cache.CACHE_DIR / "README.md").read_text(encoding="utf-8")
    assert "Licence and attribution" in readme
    ions = cache.load("mp_ion_reference_data.json")
    assert ions["project"]["license"]
    for name in cache.files_of_kind("mp_entries"):
        for d in cache.load(name)["response"]:
            assert d["data"].get("license")


def test_cache_does_not_contain_the_key(offline):  # noqa: F811
    key = env_key()
    if key is None:
        return  # no .env on this machine; nothing to compare against
    leaked = [p.name for p in cache.CACHE_DIR.iterdir() if p.is_file()
              and key in p.read_text(encoding="utf-8", errors="replace")]
    assert not leaked, "the Materials Project key appears in %d cache file(s)" % len(leaked)


def test_janaf_tables_parse(offline):  # noqa: F811
    for species in ("O2", "CO2"):
        t = gas.table(species)
        assert 298.15 in set(t["T"].tolist())
        assert gas.entropy_ev_per_K(species, 298.15) > 0
    # O2 is an element in its reference state: zero enthalpy of formation in its own table
    assert gas.formation_enthalpy_ev("O2", 298.15) == 0.0
    assert gas.formation_enthalpy_ev("CO2", 298.15) < 0


def test_ion_records_are_plain_json(offline):  # noqa: F811
    recs = cache.load("mp_ion_reference_data.json")["response"]
    json.dumps(recs)
    carbonates = {r["identifier"] for r in recs if r["data"]["MajElements"] == "C"}
    assert {"CO2(aq)", "HCO3[-]", "CO3[2-]"} <= carbonates


def test_no_cached_entry_is_excluded_by_licence(offline):  # noqa: F811
    """Every cached Materials Project entry carries BY-C; GNoME (BY-NC) entries are excluded."""
    for name in cache.files_of_kind("mp_entries"):
        assert cache.excluded_entries(name) == [], name


def test_load_entries_drops_a_by_nc_entry(offline, tmp_path):  # noqa: F811
    import shutil

    name = cache.files_of_kind("mp_entries")[0]
    shutil.copy(cache.CACHE_DIR / cache.MANIFEST, tmp_path / cache.MANIFEST)
    rec = cache.load(name)
    n = len(rec["response"])
    rec["response"][0]["data"]["license"] = "BY-NC"
    (tmp_path / name).write_text(json.dumps(rec), encoding="utf-8")
    assert len(cache.load_entries(name, tmp_path)) == n - 1
    assert cache.excluded_entries(name, tmp_path)[0][1] == "BY-NC"

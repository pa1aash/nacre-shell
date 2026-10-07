"""Offline checks on the container definitions (S30)."""
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
ROLES = ("gpu", "cpu")
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


def _text(rel):
    return (ROOT / rel).read_text()


def test_digests_yaml_schema():
    path = ROOT / "env" / "digests.yaml"
    if not path.exists():
        pytest.skip("env/digests.yaml is written after the first successful CI build")
    data = yaml.safe_load(path.read_text())
    assert {"git_sha", "run_url", "images"} <= set(data)
    assert re.fullmatch(r"[0-9a-f]{40}", data["git_sha"])
    assert data["run_url"].startswith("https://github.com/pa1aash/nacre-shell/actions/runs/")
    assert set(data["images"]) == set(ROLES)
    for role in ROLES:
        entry = data["images"][role]
        assert DIGEST.match(entry["digest"]), role
        assert entry["image"] == f"ghcr.io/pa1aash/nacre-shell-{role}"
        assert entry["tags"], role


@pytest.mark.parametrize("role", ROLES)
def test_apptainer_def_uses_digest_placeholder(role):
    text = _text(f"env/apptainer/{role}.def")
    assert "Bootstrap: docker" in text
    froms = [ln for ln in text.splitlines() if ln.startswith("From:")]
    assert froms == [f"From: ghcr.io/pa1aash/nacre-shell-{role}@sha256:{{{{DIGEST}}}}"]
    assert not re.search(r"nacre-shell-\w+:[\w.-]+", text), "tag-only reference"


def test_runpod_spec_references_images_by_digest_only():
    spec = yaml.safe_load(_text("env/runpod/template.yaml"))
    assert set(spec["templates"]) == {f"nacre-shell-{r}" for r in ROLES}
    for name, tpl in spec["templates"].items():
        image = tpl["image"]
        assert re.fullmatch(r"ghcr\.io/pa1aash/nacre-shell-(gpu|cpu)@sha256:(<DIGEST_\w+>|[0-9a-f]{64})", image), image
        assert ":latest" not in image
        assert "22/tcp" in tpl["ports"]
        assert tpl["volume"]["mount_path"] and tpl["container_disk_gb"]
        assert "PUBLIC_KEY" in tpl["env"]


@pytest.mark.parametrize("role", ROLES)
def test_dockerfile_pins_base_images_by_digest(role):
    text = _text(f"env/{role}/Dockerfile")
    arg_defaults = dict(re.findall(r"^ARG (\w+)=(\S+)$", text, re.M))
    froms = re.findall(r"^FROM (\S+)", text, re.M)
    stages = set(re.findall(r"^FROM \S+ AS (\w+)", text, re.M))
    external = 0
    for ref in froms:
        if ref in stages:
            continue
        m = re.fullmatch(r"\$\{(\w+)\}", ref)
        resolved = arg_defaults[m.group(1)] if m else ref
        assert re.search(r"@sha256:[0-9a-f]{64}$", resolved), f"{role}: {ref} is not pinned by digest"
        external += 1
    assert external >= 2
    for key in ("org.opencontainers.image.source", "org.opencontainers.image.revision", "org.opencontainers.image.created"):
        assert key in text
    assert "useradd" in text and "nacre-entrypoint" in text and "EXPOSE 22" in text


@pytest.mark.parametrize("role", ROLES)
def test_source_builds_pin_tag_and_commit(role):
    text = _text(f"env/{role}/Dockerfile")
    pairs = re.findall(r"^ARG (\w+)_TAG=\S+$", text, re.M)
    commits = re.findall(r"^ARG (\w+)_COMMIT=[0-9a-f]{40}$", text, re.M)
    assert pairs == commits and pairs


def test_workflow_pins_actions_to_tags():
    wf = yaml.safe_load(_text(".github/workflows/containers.yml"))
    uses = [s["uses"] for job in wf["jobs"].values() for s in job["steps"] if "uses" in s]
    assert uses
    for ref in uses:
        assert re.fullmatch(r"[\w.-]+/[\w.-]+@v\d+\.\d+\.\d+", ref), ref
    assert wf["permissions"] == {"contents": "read", "packages": "write"}
    triggers = wf[True] if True in wf else wf["on"]
    assert "workflow_dispatch" in triggers
    assert set(triggers["push"]["paths"]) == {"env/**", ".github/workflows/containers.yml"}
    matrix = wf["jobs"]["build"]["strategy"]["matrix"]["role"]
    assert matrix == list(ROLES)


def test_versions_md_lists_every_pinned_component():
    versions = _text("env/VERSIONS.md")
    for role in ROLES:
        df = _text(f"env/{role}/Dockerfile")
        for digest in re.findall(r"sha256:[0-9a-f]{64}", df):
            assert digest in versions, f"{role}: base digest {digest[:19]} missing"
        for tag, commit in re.findall(r"^ARG \w+_TAG=(\S+)\nARG \w+_COMMIT=([0-9a-f]{40})$", df, re.M):
            assert tag in versions and commit in versions, (role, tag)
        lock = _text(f"env/{role}/uv.lock")
        direct = yaml_deps(role)
        for dep in direct:
            m = re.search(rf'^name = "{re.escape(dep)}"\nversion = "([^"]+)"', lock, re.M)
            assert m, f"{dep} not in {role} lock"
            assert dep.lower() in versions.lower(), f"{dep} missing from VERSIONS.md"
            assert m.group(1) in versions, f"{dep} {m.group(1)} missing from VERSIONS.md"
    for action in re.findall(r"uses: ([\w./-]+@v[\d.]+)", _text(".github/workflows/containers.yml")):
        name, tag = action.split("@")
        assert name in versions and tag in versions


def yaml_deps(role):
    import tomllib
    proj = tomllib.loads(_text(f"env/{role}/pyproject.toml"))
    return sorted({re.split(r"[=<>!~ ]", d)[0].lower() for d in proj["project"]["dependencies"]})

"""Template provisioning: verify, fetch and unpack the publisher template, never patch it.

charter/venue/template.yaml records the archive and the sha256 of every file. The
template is local-only (it is git-ignored), so `ensure` either verifies the files
already present or downloads, verifies and unpacks the archive. It then renders the
derived head file paper/build/rsc_head.tex, which is built output and is never
committed: the committed documents carry only their own text.
"""
import hashlib
import re
import shutil
import zipfile
from pathlib import Path

import yaml

from nacre.report.fetch import Fetcher


class TemplateError(Exception):
    pass


def paths(root):
    root = Path(root)
    return {"yaml": root / "charter" / "venue" / "template.yaml",
            "dir": root / "paper" / "rsc_template",
            "build": root / "paper" / "build"}


def load_spec(root):
    p = paths(root)["yaml"]
    if not p.exists():
        raise TemplateError("missing %s" % p)
    spec = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    for key in ("archive_url", "archive_sha256", "files"):
        if not spec.get(key):
            raise TemplateError("template.yaml lacks %s" % key)
    return spec


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def verify_dir(directory, spec):
    """Return a list of problems comparing a directory to the recorded files."""
    directory = Path(directory)
    problems = []
    expected = {f["path"]: f["sha256"] for f in spec["files"]}
    for rel, want in sorted(expected.items()):
        f = directory / rel
        if not f.is_file():
            problems.append("missing: %s" % rel)
        elif _sha(f.read_bytes()) != want:
            problems.append("differs: %s" % rel)
    if directory.is_dir():
        have = {p.relative_to(directory).as_posix() for p in directory.rglob("*") if p.is_file()}
        for rel in sorted(have - set(expected)):
            problems.append("unexpected: %s" % rel)
    return problems


def _safe_unpack(archive_bytes, dest):
    import io
    dest = Path(dest)
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as zf:
        for info in zf.infolist():
            name = info.filename
            parts = Path(name).parts
            if name.startswith(("/", "\\")) or ".." in parts or (parts and ":" in parts[0]):
                raise TemplateError("unsafe path in archive: %s" % name)
            target = dest / name
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(zf.read(info))


def download(root, spec, fetcher=None):
    """Download the archive from a recorded URL; the first whose hash matches wins."""
    p = paths(root)
    fetcher = fetcher or Fetcher(venue_dir=p["build"] / "_fetch")
    tried = []
    for url in [spec.get("archive_url"), spec.get("archive_url_fetched")]:
        if not url:
            continue
        res = fetcher.get(url, wayback=False)
        if not res.ok:
            tried.append("%s: %s" % (url, res.error))
            continue
        if res.sha256 != spec["archive_sha256"]:
            tried.append("%s: sha256 %s differs from recorded %s" % (url, res.sha256, spec["archive_sha256"]))
            continue
        return res.content, url
    raise TemplateError("could not obtain an archive matching the recorded sha256:\n  " + "\n  ".join(tried))


def _read_template_tex(directory):
    return (Path(directory) / "main.tex").read_text(encoding="utf-8")


def _sub_once(text, pattern, repl, label, flags=re.S):
    new, n = re.subn(pattern, lambda m: repl, text, flags=flags)
    if n != 1:
        raise TemplateError("template layout changed: %s matched %d times (expected 1)" % (label, n))
    return new


def render_head(template_dir):
    """Derive the head of the template's example article with placeholder macros.

    The sample title, author line, abstract, address footnotes and the whole sample
    body are replaced; everything else (class, packages, page and figure setup,
    header and footer, front-matter layout) is kept exactly as the template has it.
    """
    t = _read_template_tex(template_dir)
    t = _sub_once(t, r"\\textbf\{This is the title\$\^\\dag\$\}", r"\textbf{\nacreTitle\nacreTitleMark}", "title")
    t = _sub_once(t, r"Full Name,\$\^\{\\ast\}\$.*?Full Name\\textit\{\$\^\{a\}\$\}",
                  r"\nacreAuthors", "authors")
    t = _sub_once(t, r"\\noindent\\normalsize\{The abstract should be.*?\} \\\\%The abstrast",
                  r"\noindent\normalsize{\nacreAbstract} \\%The abstrast", "abstract")
    t = _sub_once(t, r"%%%FOOTNOTES%%%.*?%%%END OF FOOTNOTES%%%",
                  "%%%FOOTNOTES%%%\n\\nacreFootnotes\n%%%END OF FOOTNOTES%%%", "footnotes")
    t = _sub_once(t, r"%%%%%%%%% Preamble of the bibliography.*?(?=\\begin\{document\})", "", "bib preamble")
    t = _sub_once(t, r"%%%MAIN TEXT%%%%.*\Z", "%%%MAIN TEXT%%%%\n", "main text")
    return t


def ensure(root, fetcher=None, out=print):
    """Verify or provision the template, then render the derived head. Returns files verified."""
    p = paths(root)
    spec = load_spec(root)
    if p["dir"].is_dir():
        problems = verify_dir(p["dir"], spec)
        if problems:
            raise TemplateError("template files do not match template.yaml:\n  " + "\n  ".join(problems))
        out("template present: %d files verified" % len(spec["files"]))
    else:
        data, url = download(root, spec, fetcher)
        tmp = p["build"] / "_template_unpack"
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir(parents=True)
        _safe_unpack(data, tmp)
        problems = verify_dir(tmp, spec)
        if problems:
            shutil.rmtree(tmp)
            raise TemplateError("unpacked files do not match template.yaml:\n  " + "\n  ".join(problems))
        shutil.move(str(tmp), str(p["dir"]))
        out("template downloaded from %s: %d files verified" % (url, len(spec["files"])))
    p["build"].mkdir(parents=True, exist_ok=True)
    (p["build"] / "rsc_head.tex").write_text(render_head(p["dir"]), encoding="utf-8", newline="\n")
    return len(spec["files"])

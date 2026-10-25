"""The preprint bibliography: citation keys, the build-time copy of refs.bib, and its release checks.

preprint/paper/refs.bib is written only by `nacre bib add --bib preprint/paper/refs.bib <doi>`
and keeps every entry exactly as fetched. Three problems are handled here:

  - a \\cite key in the manuscript that has no entry in refs.bib (a key that was typed, not
    fetched). It fails prepare in both modes.
  - an article with no `pages` field. Crossref omits pages for article-number journals, and the
    publisher style stops bibtex on such an entry when it has a volume. The build reads a copy,
    build/bib/refs_build.bib (a distinct name, so bibtex cannot pick up the source instead),
    in which each such entry carries `pages={\\nacreMissing{article number}}`: a draft renders
    the red marker and a release stops at it. The release guard reports the same entries.
  - a bare `&` in a fetched field, or the HTML entity `&amp;` that Crossref returns for one (the
    journal "Crystal Growth & Design"); TeX reads `&` as an alignment tab. The build copy
    decodes entities and writes `\\&`.
  - Unicode that pdflatex cannot set: decomposed accents are composed (NFC), the characters in
    TEX_MAP are written as TeX, and any other character outside Latin-1 and the dashes and
    quotes the input encoding knows stops prepare with its name, so a new fetch never fails
    silently inside bibtex or LaTeX.

The fetched source is never edited; only the build copy differs.
"""
import html
import re
import unicodedata

from nacre.preprint import paths, texscan
from nacre.report import bib as bibmod

BIB = "refs.bib"
# The name main.tex and si/main_si.tex give \bibliography; it exists only in build/bib.
BUILD_BIB = "refs_build.bib"
MISSING_PAGES = r"\nacreMissing{article number}"
_BARE_AMP = re.compile(r"(?<!\\)&")
# U+2500 is how Crossref writes the em dash of some ACS titles ("GFN2-xTB\u2500An ...").
TEX_MAP = {"\u2010": "-", "\u2011": "-", "\u03b2": r"$\beta$", "\u03b3": r"$\gamma$", "\u2500": "---", "\u0107": r"\'{c}"}
_TEX_KNOWN = set("\u2013\u2014\u2018\u2019\u201c\u201d")

_CITE = re.compile(r"\\(?:cite|citep|citet|citealp|citenum|nocite)\*?(?:\[[^\]]*\]){0,2}\{([^}]*)\}")


class RefsError(Exception):
    pass


def source(root):
    return paths.paper(root) / BIB


def build_copy(root):
    return paths.build(root) / "bib" / BUILD_BIB


def entries(root):
    """[(key, entry text)] of refs.bib, in file order."""
    f = source(root)
    text = f.read_text(encoding="utf-8") if f.is_file() else ""
    out = []
    for e in bibmod.split_entries(text):
        _, key, _ = bibmod.parse_head(e)
        out.append((key, e))
    return out


def cited(root, files=None):
    """{key: [(file, line)]} for every citation key in the manuscript sources and the generated tables (comments ignored)."""
    out = {}
    if files is None:
        files = texscan.manuscript_tex(root) + sorted(f for f in paths.generated(root).glob("*.tex") if f.is_file())
    for f in files:
        for no, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            for m in _CITE.finditer(texscan.strip_comment(line)):
                for key in m.group(1).split(","):
                    if key.strip():
                        out.setdefault(key.strip(), []).append((texscan.rel(root, f), no))
    return out


def unresolved(root):
    """Problems: citation keys with no refs.bib entry."""
    keys = {k for k, _ in entries(root)}
    problems = []
    for key, where in sorted(cited(root).items()):
        if key not in keys:
            f, no = where[0]
            problems.append("%s:%d: \\cite key %r has no entry in %s (add it with nacre bib add)"
                            % (f, no, key, texscan.rel(root, source(root))))
    return problems


def needs_pages(entry):
    """An article without a pages field. Books and reports carry no pages and need none."""
    kind, _, _ = bibmod.parse_head(entry)
    return kind.lower() == "article" and bibmod.field(entry, "pages") is None


def without_pages(root, only_cited=True):
    """Keys of articles that have no pages field (cited ones only, by default)."""
    keys = set(cited(root)) if only_cited else None
    return [k for k, e in entries(root) if needs_pages(e) and (keys is None or k in keys)]


def _with_marker(entry):
    body = entry.rstrip()
    if not body.endswith("}"):
        raise ValueError("bib entry does not end with '}'")
    head = body[:-1].rstrip()
    sep = "" if head.endswith(",") else ","
    return "%s%s pages={%s} }\n" % (head, sep, MISSING_PAGES)


def tex_safe(entry):
    """The entry as pdflatex can read it: HTML entities decoded (Crossref writes "&amp;"), bare
    ampersands escaped, accents composed, mapped
    characters written as TeX. Raises RefsError on a character it cannot place."""
    s = _BARE_AMP.sub(r"\\&", html.unescape(unicodedata.normalize("NFC", entry)))
    s = "".join(TEX_MAP.get(ch, ch) for ch in s)
    bad = sorted({ch for ch in s if ord(ch) > 255 and ch not in _TEX_KNOWN})
    if bad:
        _, key, _ = bibmod.parse_head(entry)
        raise RefsError("%s: no TeX form for %s; add it to nacre.preprint.refs.TEX_MAP"
                        % (key, ", ".join("U+%04X %s" % (ord(c), unicodedata.name(c, "?")) for c in bad)))
    return s


def write_build_copy(root):
    """Write the build copy: refs.bib with bare ampersands escaped and a marker in the pages
    field of each article that has none. Returns (path, keys marked)."""
    out, marked = [], []
    for key, e in entries(root):
        e = tex_safe(e)
        if needs_pages(e):
            out.append(_with_marker(e))
            marked.append(key)
        else:
            out.append(e if e.endswith("\n") else e + "\n")
    dest = build_copy(root)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(x.rstrip("\n") + "\n" for x in out), encoding="utf-8", newline="\n")
    return dest, marked

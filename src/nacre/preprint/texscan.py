"""Line-level helpers for scanning LaTeX sources (no full parser; one line at a time)."""
import re
from pathlib import Path

from nacre.preprint import paths

COMMENT = re.compile(r"(?<!\\)%.*")
_CS = re.compile(r"\\([A-Za-z@]+)\*?")


def strip_comment(line):
    return COMMENT.sub("", line)


def skip_ws(s, j):
    while j < len(s) and s[j] in " \t":
        j += 1
    return j


def skip_group(s, j, open_="{", close="}"):
    """Skip one balanced group starting at s[j]; returns j unchanged if none starts there."""
    j = skip_ws(s, j)
    if j >= len(s) or s[j] != open_:
        return j
    depth = 0
    while j < len(s):
        ch = s[j]
        if ch == "\\":
            j += 2
            continue
        if ch == open_:
            depth += 1
        elif ch == close:
            depth -= 1
            if depth == 0:
                return j + 1
        j += 1
    return j


def skip_opts(s, j):
    while True:
        k = skip_ws(s, j)
        if k < len(s) and s[k] == "[":
            j = skip_group(s, k, "[", "]")
        else:
            return j


def group_text(s, j):
    j = skip_ws(s, j)
    end = skip_group(s, j)
    return s[j + 1:end - 1] if end > j else ""


def manuscript_tex(root):
    """The prose sources: main, sections, SI and captions (not the preamble, build output or generated)."""
    p = paths.paper(root)
    files = [p / "main.tex"]
    for sub in ("sections", "si", "captions"):
        d = p / sub
        if d.is_dir():
            files += sorted(d.rglob("*.tex"))
    return [f for f in files if f.is_file()]


def rel(root, f):
    try:
        return Path(f).resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return str(f)


def load_rules(path, id_prefix):
    """`<id> <regex>` per line; `#` lines are comments. Returns [(id, compiled)]."""
    rules = []
    for no, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split(None, 1)
        if len(parts) != 2 or not parts[0].startswith(id_prefix):
            raise ValueError("%s:%d: expected '<%s..> <regex>'" % (path, no, id_prefix))
        rules.append((parts[0], re.compile(parts[1], re.I)))
    return rules

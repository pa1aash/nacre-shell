"""Shared helpers for the repository hooks and the history scan.

Standard library only. The banned-string set (rule R2) is defined here and
nowhere else; every other component imports it from this module.
"""
import re
import subprocess
import sys

R1_NAME = "Palaash Gang"
R1_EMAIL = "palaashgang@gmail.com"


def _word(codes):
    return "".join(map(chr, codes))


_PRODUCT = _word([99, 108, 97, 117, 100, 101])
LOCAL_GUIDE = _PRODUCT.upper() + ".md"
LOCAL_SETTINGS_DIR = "." + _PRODUCT
LOCAL_ONLY = (LOCAL_GUIDE, LOCAL_SETTINGS_DIR)

# Character classes keep the literal words out of this file.
RULES = {
    "banned-product-name": re.compile(r"c[l]aude", re.IGNORECASE),
    "banned-maker-name": re.compile(r"a[n]thropic", re.IGNORECASE),
    "banned-coauthor-trailer": re.compile(r"co[-_ ]?a[u]thored[-_ ]?by", re.IGNORECASE),
}

_TRAILER = re.compile(r"^[A-Za-z][A-Za-z0-9-]*:\s+\S")
_IDENT = re.compile(r"^(.*) <(.*)> \d+ [+-]\d{4}$")
ZERO_SHA = re.compile(r"^0+$")


def git(*args, cwd=None, raw=False, stdin=None):
    """Run git; return (returncode, stdout). stdout is bytes when raw."""
    p = subprocess.run(["git", *args], cwd=cwd, capture_output=True, input=stdin)
    out = p.stdout if raw else p.stdout.decode("utf-8", "replace")
    return p.returncode, out


def git_out(*args, cwd=None, raw=False):
    rc, out = git(*args, cwd=cwd, raw=raw)
    if rc != 0:
        raise RuntimeError("git " + " ".join(args) + " failed")
    return out


def is_binary(data):
    return b"\0" in data[:8192]


def scan_text(text):
    """Return [(line_number, rule)] for every banned pattern in text."""
    hits = []
    for no, line in enumerate(text.splitlines(), 1):
        for rule, rx in RULES.items():
            if rx.search(line):
                hits.append((no, rule))
    return hits


def scan_bytes(data):
    if is_binary(data):
        return []
    return scan_text(data.decode("utf-8", "replace"))


def scan_path(path):
    """Return the rules a path violates (banned patterns, local-only names)."""
    hits = [rule for rule, rx in RULES.items() if rx.search(path)]
    parts = path.replace("\\", "/").split("/")
    if any(p in LOCAL_ONLY for p in parts):
        hits.append("local-only-name")
    return hits


def message_lines(message):
    """Non-comment lines of a commit message as [(line_number, text)]."""
    return [(no, ln) for no, ln in enumerate(message.splitlines(), 1) if not ln.startswith("#")]


def scan_message(message):
    hits = []
    for no, line in message_lines(message):
        for rule, rx in RULES.items():
            if rx.search(line):
                hits.append((no, rule))
    return hits


def trailer_hits(message):
    """Trailer-looking lines in the final paragraph.

    A single-paragraph message is only a subject line and is never a trailer
    block, so it is ignored.
    """
    paragraphs, current = [], []
    for no, line in message_lines(message):
        if line.strip():
            current.append((no, line))
        elif current:
            paragraphs.append(current)
            current = []
    if current:
        paragraphs.append(current)
    if len(paragraphs) < 2:
        return []
    return [(no, ln) for no, ln in paragraphs[-1] if _TRAILER.match(ln)]


def check_message(message, where):
    """Report every message violation; return the number found."""
    n = 0
    for no, rule in scan_message(message):
        report(rule, where, no)
        n += 1
    for no, ln in trailer_hits(message):
        report("git-trailer", where, no, ln.strip())
        n += 1
    return n


def parse_ident(ident):
    m = _IDENT.match(ident.strip())
    return (m.group(1), m.group(2)) if m else (None, None)


def ident_ok(name, email):
    return name == R1_NAME and email == R1_EMAIL


def identity_problems():
    """Problems with the identity git would use for a new commit."""
    problems = []
    for var in ("GIT_AUTHOR_IDENT", "GIT_COMMITTER_IDENT"):
        rc, out = git("var", var)
        if rc != 0:
            problems.append(var + " is not configured")
            continue
        name, email = parse_ident(out)
        if not ident_ok(name, email):
            problems.append("%s is %s <%s>, expected %s <%s>" % (var, name, email, R1_NAME, R1_EMAIL))
    return problems


def report(rule, where, line=None, detail=""):
    msg = "REJECTED [%s] %s" % (rule, where)
    if line:
        msg += ":%s" % line
    if detail:
        msg += " - %s" % detail
    print(msg, file=sys.stderr)


def staged_paths(filter_=None):
    args = ["diff", "--cached", "--name-only", "-z", "--no-renames"]
    if filter_:
        args.append("--diff-filter=" + filter_)
    return [p for p in git_out(*args).split("\0") if p]


def scan_staged():
    """Scan staged paths and staged blobs; return the number of violations."""
    n = 0
    for path in staged_paths("ACM"):
        for rule in scan_path(path):
            report(rule, path, None, "staged path")
            n += 1
        rc, data = git("cat-file", "blob", ":" + path, raw=True)
        if rc != 0:
            continue
        for no, rule in scan_bytes(data):
            report(rule, path, no, "staged content")
            n += 1
    return n

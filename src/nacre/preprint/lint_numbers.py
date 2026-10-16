"""lint-numbers: no digit in manuscript prose or captions unless it comes from a macro.

Rule R5: every number in the paper is a generated macro (preprint/generated/numbers.tex).
For each line of main.tex, sections/, si/ and captions/ the linter
  1. drops the comment;
  2. removes the explicitly allowlisted mathematical forms (preprint/paper/lint/numbers_allowlist.txt);
  3. removes the arguments of commands whose arguments are keys, labels, file names or
     layout, not text: labels (equation and section labels), cross-references, citation keys,
     file inputs, environment names and table column specifications, lengths;
  4. removes every control-sequence name (so \\NumFoo and \\nacre* calls disappear);
and reports any digit that remains. Captions are ordinary text and are checked.
"""
import re

from nacre.preprint import paths, texscan

# command -> number of mandatory arguments that are keys or layout, not text.
KEY_ARGS = {
    "label": 1, "ref": 1, "eqref": 1, "pageref": 1, "autoref": 1, "cref": 1, "Cref": 1, "nameref": 1,
    "cite": 1, "citep": 1, "citet": 1, "citealp": 1, "nocite": 1,
    "input": 1, "include": 1, "InputIfFileExists": 1, "IfFileExists": 1, "includegraphics": 1,
    "usepackage": 1, "RequirePackage": 1, "documentclass": 1, "bibliography": 1, "bibliographystyle": 1,
    "begin": 1, "end": 1, "vspace": 1, "hspace": 1, "setlength": 2, "addtolength": 2, "setcounter": 2,
    "url": 1, "href": 1, "hypersetup": 1, "definecolor": 3, "color": 1, "textcolor": 1,
    "newcounter": 1, "renewcommand": 1, "newcommand": 1,
}
TABULAR = {"tabular", "tabular*", "tabularx", "array", "longtable"}
ALLOWLIST = "numbers_allowlist.txt"


def allowlist(root):
    return texscan.load_rules(paths.lint_dir(root) / ALLOWLIST, "NA")


def scrub(line, allow):
    """Return the text of one line that the digit check applies to."""
    s = texscan.strip_comment(line)
    for _, rx in allow:
        s = rx.sub(" ", s)
    out, i = [], 0
    while i < len(s):
        ch = s[i]
        if ch == "\\":
            m = texscan._CS.match(s, i)
            if not m:
                out.append(" ")
                i += 2
                continue
            name, j = m.group(1), m.end()
            if name in KEY_ARGS:
                env = texscan.group_text(s, texscan.skip_opts(s, j)) if name == "begin" else ""
                for _ in range(KEY_ARGS[name]):
                    j = texscan.skip_group(s, texscan.skip_opts(s, j))
                j = texscan.skip_opts(s, j)
                if name == "begin" and env in TABULAR:
                    if env.endswith("*") or env == "tabularx":
                        j = texscan.skip_group(s, j)
                    j = texscan.skip_group(s, j)
            out.append(" ")
            i = j
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def lint(root, files=None):
    root_files = files if files is not None else texscan.manuscript_tex(root)
    allow = allowlist(root)
    problems = []
    for f in root_files:
        for no, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            rest = scrub(line, allow)
            hits = re.findall(r"[0-9][0-9.,]*", rest)
            if hits:
                problems.append("%s:%d: digit outside a macro: %s" % (texscan.rel(root, f), no, " ".join(hits)))
    return problems

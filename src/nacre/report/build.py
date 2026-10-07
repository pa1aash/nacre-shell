"""Build the manuscript and the supplementary information, and run the paper checks."""
import re
import shutil
import subprocess
from pathlib import Path

from nacre.report import template

# Optional inputs: their absence is expected until the other lane delivers them.
EXPECTED_MARKERS = ("NACRE-WARNING: generated/macros.tex is absent",)

# Words that must not appear anywhere in the paper sources (scope guard).
SCOPE_PATTERNS = [
    r"corrosion[\s-]+rates?", r"\bcapacit(?:y|ies)\b", r"\bdevices?\b", r"\bbatter(?:y|ies)\b",
    r"state[\s-]+of[\s-]+charge",
]

# Commands whose arguments are file names, keys or options, not text.
_ARG_COMMANDS = ("input", "InputIfFileExists", "include", "bibliography", "bibliographystyle", "usepackage",
                 "documentclass", "label", "ref", "cite", "nocite", "includegraphics", "pageref")


def paper_dir(root):
    return Path(root) / "paper"


def text_sources(root):
    """Committed manuscript sources: main, sections and SI (not the template or build output)."""
    p = paper_dir(root)
    files = [p / "main.tex", p / "si" / "si.tex"]
    files += sorted((p / "sections").glob("*.tex"))
    return [f for f in files if f.exists()]


def all_tex(root):
    p = paper_dir(root)
    skip = (p / "rsc_template", p / "build")
    return [f for f in sorted(p.rglob("*.tex")) if not any(s in f.parents for s in skip)]


def _strip_markup(text):
    text = re.sub(r"(?<!\\)%.*", "", text)
    for cmd in _ARG_COMMANDS:
        text = re.sub(r"\\%s\*?(?:\[[^\]]*\])?\{[^}]*\}" % cmd, " ", text)
    text = re.sub(r"\\[A-Za-z@]+\*?", " ", text)
    text = re.sub(r"\\.", " ", text)
    return text


def digit_problems(root):
    """Digits in manuscript text (outside comments, command names and file-name arguments)."""
    problems = []
    for f in text_sources(root):
        for no, line in enumerate(_strip_markup(f.read_text(encoding="utf-8")).splitlines(), 1):
            if re.search(r"\d", line):
                problems.append("%s:%d digit in text" % (f.relative_to(root).as_posix(), no))
    return problems


def scope_problems(root):
    problems = []
    pats = [re.compile(p, re.I) for p in SCOPE_PATTERNS]
    for f in all_tex(root) + [paper_dir(root) / "claims.yaml"]:
        if not f.exists():
            continue
        for no, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            for pat in pats:
                if pat.search(line):
                    problems.append("%s:%d scope word (%s)" % (f.relative_to(root).as_posix(), no, pat.pattern))
    return problems


def log_problems(log_text, blg_text=""):
    """Classify the final log. Returns (unexpected, expected)."""
    unexpected, expected = [], []
    for line in log_text.splitlines():
        if any(m in line for m in EXPECTED_MARKERS):
            expected.append(line.strip())
        elif re.search(r"Warning:.*(Reference|Citation|Label).*undefined|There were undefined (references|citations)"
                       r"|Warning:.*Label\(s\) may have changed|Warning: File `[^']*' not found|No file [^ ]+\.(?!bbl)",
                       line):
            unexpected.append(line.strip())
        elif re.search(r"LaTeX Warning: .*Please \(re\)run", line):
            unexpected.append(line.strip())
    if re.search(r"I didn't find a database entry|Warning--", blg_text):
        unexpected += [ln.strip() for ln in blg_text.splitlines() if "didn't find" in ln or ln.startswith("Warning--")]
    if "I found no \\citation commands" in blg_text:
        expected.append("bibtex: no citations yet (expected while the manuscript cites nothing)")
    return unexpected, expected


def _pages(log_text):
    m = re.search(r"Output written on .*? \((\d+) pages?", log_text)
    return int(m.group(1)) if m else None


def _latexmk(root, source, outdir):
    cmd = ["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "-outdir=" + outdir, source]
    return subprocess.run(cmd, cwd=paper_dir(root), capture_output=True, text=True)


def build(root, si=False, check=False, out=print):
    root = Path(root)
    if shutil.which("latexmk") is None:
        out("build: latexmk not found on PATH")
        return 1
    template.ensure(root, out=out)
    failures, summary = [], []
    jobs = [("main", "main.tex", "build")]
    if si:
        jobs.append(("si", "si/si.tex", "build/si"))
    for name, source, outdir in jobs:
        p = _latexmk(root, source, outdir)
        stem = Path(source).stem
        log = paper_dir(root) / outdir / (stem + ".log")
        if p.returncode != 0 or not log.exists():
            tail = "\n".join((p.stdout + p.stderr).strip().splitlines()[-25:])
            out("build %s FAILED (latexmk exit %d)\n%s" % (name, p.returncode, tail))
            return 1
        log_text = log.read_text(encoding="utf-8", errors="replace")
        blg = paper_dir(root) / outdir / (stem + ".blg")
        blg_text = blg.read_text(encoding="utf-8", errors="replace") if blg.exists() else ""
        unexpected, expected = log_problems(log_text, blg_text)
        out("build %s: %s pages, %d unexpected warning(s)" % (name, _pages(log_text), len(unexpected)))
        for line in unexpected:
            out("  unexpected: " + line)
        for line in sorted(set(expected)):
            out("  expected:   " + line)
        if not (paper_dir(root) / "sections" / "results.tex").exists():
            out("  expected:   sections/results.tex absent (optional input)")
        summary.append((name, _pages(log_text), len(unexpected)))
        if check:
            failures += ["%s: %s" % (name, u) for u in unexpected]
    if check:
        failures += digit_problems(root) + scope_problems(root)
        for f in failures:
            out("check: " + f)
        out("paper check: %s" % ("FAIL (%d)" % len(failures) if failures else "PASS"))
    return 1 if failures else 0

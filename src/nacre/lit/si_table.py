"""SI parameter table and conflicts table, generated from lit/params.yaml and lit/conflicts.md.

    uv run python -m nacre.lit.si_table [--out DIR] [--check]

Writes, under lit/corpus/si_table/ (default):

    params_table.tex     longtable: symbol, quantity, value or range, prior, method, grade, sources
    conflicts_table.tex  longtable: one row per entry of the ```conflicts block of lit/conflicts.md
    params_table_dois.csv the DOIs cited by both tables, one per row under a `doi` header (input to `nacre bib add`)

Every number in the tables is computed here from lit/params.yaml (values, ranges and prior parameters,
converted for display by pint) or counted from it; the generator types no number. Sources are printed as
\\paramcite{<doi>}. The files define \\paramcite with \\providecommand to print the DOI, so they compile
standalone; the manuscript redefines it to cite the matching bibliography key (W8). Both tables use only
the booktabs, longtable and array packages.

--check regenerates in memory and fails if the committed files differ (used by the tests and by W8).

--early-read DIR writes DIR/params_table_for_coauthors.tex (a short preface on how the priors were built, then
both tables) and builds it with latexmk into DIR/params_table_for_coauthors.pdf. DIR is local-only (.local/).
"""
import argparse
import math
import re
import sys
from pathlib import Path

import yaml

from nacre import _util
from nacre.lit import evidence as E
from nacre.lit import params as P

OUT = Path("lit") / "corpus" / "si_table"
LABELS = OUT / "labels.yaml"  # quantity name per key, and a LaTeX symbol where the symbol is not registered
CONFLICTS = Path("lit") / "conflicts.md"
FILES = ("params_table.tex", "conflicts_table.tex", "params_table_dois.csv")

# display units: stored SI unit -> (pint target, LaTeX)
DISPLAY = {
    "J m^-2": ("mJ/m^2", r"mJ\,m$^{-2}$"),
    "J mol^-1": ("kJ/mol", r"kJ\,mol$^{-1}$"),
    "m^3 mol^-1": ("cm^3/mol", r"cm$^{3}$\,mol$^{-1}$"),
    "kg m^-3": ("g/cm^3", r"g\,cm$^{-3}$"),
    "mol m^-2": ("umol/m^2", r"$\mu$mol\,m$^{-2}$"),
    "mol m^-3": ("mol/m^3", r"mol\,m$^{-3}$"),
    "mol kg^-1": ("mol/kg", r"mol\,kg$^{-1}$"),
    "J": ("eV", r"eV"),
    "m": ("nm", r"nm"),
    "m^2": ("um^2", r"$\mu$m$^{2}$"),
    "m^-2": ("m^-2", r"m$^{-2}$"),
    "m^-2 s^-1": ("m^-2/s", r"m$^{-2}$\,s$^{-1}$"),
    "s": ("s", r"s"),
    "K": ("K", r"K"),
    "V": ("V", r"V"),
    "A m^-2": ("A/m^2", r"A\,m$^{-2}$"),
    "ohm m": ("ohm*m", r"$\Omega$\,m"),
    "ohm m^2": ("ohm*m^2", r"$\Omega$\,m$^{2}$"),
    "kg": ("kg", r"kg"),
    "J K^-1 mol^-1": ("J/K/mol", r"J\,K$^{-1}$\,mol$^{-1}$"),
    "1": (None, ""),
}
FLAG_MARKS = {"single_source": r"$^{s}$", "analog": r"$^{a}$", "truncated": r"$^{t}$", "widened": r"$^{w}$",
              "registered": r"$^{r}$", "ionic_strength": r"$^{I}$"}
ROLE_MARKS = {"sensitivity": r"$^{\dagger}$", "design-axis": r"$^{d}$"}
RULE_TEXT = {
    "N1": "normal, concordant sources (N1)", "N2": "normal, one grade-A source (N2)",
    "N3": "uniform, normal left the domain (N3)", "U1": "uniform over sourced span (U1)",
    "L1": "log-uniform over sourced span (L1)", "P1": "single point, width not sourced (P1)",
    "T1": "sourced span cut by ruling (T1)", "W1": "single source widened to method error (W1)",
    "I1": "ignorance prior (I1)", "D1": "derived by formula (D1)", "R1": "registered convention (R1)",
    "G1": "design axis by class (G1)", "M0": "margin zero, prior carries error (M0)",
    "X1": "gap, no admitted evidence (X1)", "X2": "computed or registered (X2)", "X3": "definitional (X3)",
}
SECTIONS = (("R-slurry", "Slurry regime (R-slurry)"), ("R-cell", "Cell regime (R-cell)"),
            ("shared", "Both regimes"))
LATEX_SPECIAL = {"&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
                 "~": r"\textasciitilde{}", "^": r"\textasciicircum{}", "\\": r"\textbackslash{}"}


def tex(text):
    return "".join(LATEX_SPECIAL.get(c, c) for c in str(text))


def texkey(key):
    """A key name in \\texttt that may break after its underscores."""
    return r"\texttt{%s}" % tex(key).replace(r"\_", r"\_\allowbreak{}")


def num(x, sig=4):
    """A number for the table: up to `sig` significant digits, scientific outside [1e-3, 1e5)."""
    x = float(x)
    if x == 0:
        return "0"
    if not math.isfinite(x):
        return r"$\infty$" if x > 0 else r"$-\infty$"
    exp = math.floor(math.log10(abs(x)))
    if -3 <= exp < 5:
        digits = max(sig - 1 - exp, 0)
        s = ("%.*f" % (digits, x))
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return "$%s$" % s.replace("-", "-")
    m = x / 10 ** exp
    ms = ("%.*f" % (sig - 1, m)).rstrip("0").rstrip(".")
    if ms in ("10", "-10"):
        ms, exp = ms.replace("10", "1"), exp + 1
    return r"$%s\times10^{%d}$" % (ms, exp)


def convert(x, unit):
    """(converted value, LaTeX unit) for display."""
    unit = str(unit)
    target, label = DISPLAY.get(unit, (None, tex(unit)))
    if target is None or x is None:
        return x, label
    q = E.ureg().Quantity(float(x), unit.replace("Ohm", "ohm"))
    return float(q.to(target).magnitude), label


def value_cell(e):
    unit, rng = e["unit"], e.get("range")
    fam = e["prior"]["family"]
    if fam == "categorical":
        opts = e["prior"]["options"]
        if e.get("rule") == "G1":
            parts = []
            for o in opts:
                lo, lab = convert(o["range"]["min"], unit) if o.get("range") else (None, "")
                hi, _ = convert(o["range"]["max"], unit) if o.get("range") else (None, "")
                parts.append("%s: %s" % (tex(o["label"]), "--" if lo is None else
                                         (num(lo) if lo == hi else "%s--%s" % (num(lo), num(hi)))))
            return "; ".join(parts) + (" %s" % lab if lab else "")
        return ", ".join(tex(o["label"]) for o in opts)
    v = e.get("value")
    if v is None and rng is None:
        return "--"
    cv, lab = convert(v, unit)
    if rng is None:
        return "%s %s" % (num(cv), lab)
    lo, _ = convert(rng["min"], unit)
    hi, _ = convert(rng["max"], unit)
    if lo == hi:
        core = num(lo)
    elif v is None:
        core = "%s to %s" % (num(lo), num(hi))
    else:
        core = "%s (%s to %s)" % (num(cv), num(lo), num(hi))
    return ("%s %s" % (core, lab)).strip()


def prior_cell(e):
    pr, unit = e["prior"], e["unit"]
    fam = pr["family"]
    if fam == "normal":
        m, lab = convert(pr["mean"], unit)
        s, _ = convert(pr["mean"] + pr["sd"], unit)
        return r"$\mathcal{N}$(%s, %s)" % (num(m), num(s - m))
    if fam in ("uniform", "loguniform"):
        lo, _ = convert(pr["low"], unit)
        hi, _ = convert(pr["high"], unit)
        return "%s[%s, %s]" % ("logU" if fam == "loguniform" else "U", num(lo), num(hi))
    if fam == "fixed":
        v, _ = convert(pr["value"], unit)
        return "fixed %s" % num(v)
    if fam == "categorical":
        return "per class" if e.get("rule") == "G1" else "categorical"
    if e.get("rule") == "I1":
        ig = e["ignorance"]
        return r"U[%s, %s]" % (tex(ig["low"]), tex(ig["high"]))
    return "none"


def label_of(key, e, symbols, labels=None):
    if labels and key in labels:
        return tex(labels[key]["label"])
    sym = symbols.get(e["symbol"])
    if sym and sym.get("short"):
        return tex(sym["short"])
    if sym and sym.get("meaning"):
        return tex(sym["meaning"].split(";")[0][:60])
    return tex(key.replace("_", " "))


def symbol_cell(e, symbols, override=None):
    sym = symbols.get(e["symbol"])
    if override:
        s = "$%s$" % override
    elif sym and sym.get("latex"):
        s = "$%s$" % sym["latex"]
    else:
        s = r"\texttt{%s}" % tex(e["symbol"])
    if e.get("transform") == "log10":
        s = r"$\log_{10}$ %s" % s
    return s


def dois_of(e, rows):
    out = []
    srcs = list(e.get("sources") or [])
    if e["prior"]["family"] == "categorical":
        for o in e["prior"]["options"]:
            srcs += [s for s in o.get("sources") or [] if s not in srcs]
    for s in srcs:
        d = rows[s]["doi"].lower()
        if d not in out:
            out.append(d)
    return out


def cite(dois):
    return ", ".join(r"\paramcite{%s}" % d for d in dois) if dois else "--"


def marks(e):
    m = "".join(ROLE_MARKS.get(e.get("role"), ""))
    m += "".join(FLAG_MARKS[f] for f in e.get("flags") or [] if f in FLAG_MARKS)
    return m


HEAD = r"""%% GENERATED by `uv run python -m nacre.lit.si_table` from lit/params.yaml (sha256 %(sha)s).
%% Do not edit by hand. Lane p0-w1; every number is computed from lit/params.yaml.
\providecommand{\paramcite}[1]{\texttt{\detokenize{#1}}}
"""

LEGEND = (r"Marks: $^{s}$ single source; $^{w}$ widened to the method error (W1); $^{t}$ truncated by ruling (T1); "
          r"$^{a}$ analog prior, run beside the ignorance prior of the key it names; $^{\dagger}$ labelled "
          r"sensitivity, never decides a verdict; $^{d}$ design axis; $^{r}$ registered convention; $^{I}$ "
          r"ionic-strength flag. Prior notation: U uniform, logU log-uniform, $\mathcal{N}$(mean, sd) normal, in "
          r"the units of the value column; an ignorance prior names its bounds by the keys in its row of "
          r"lit/params.yaml. "
          r"Values are the central value with the sourced span in brackets. Method clauses are those of the "
          r"prior-construction rule. Grades: A direct measurement with uncertainty under the study's conditions; "
          r"B direct, other conditions or no uncertainty; C derived, fitted or compiled; D abstract only.")


def params_table(params, rows, symbols, sha, labels=None):
    labels = labels or {}
    lines = [HEAD % {"sha": sha},
             r"\begin{longtable}{@{}>{\raggedright}p{0.08\linewidth}>{\raggedright}p{0.17\linewidth}"
             r">{\raggedright}p{0.17\linewidth}>{\raggedright}p{0.12\linewidth}>{\raggedright}p{0.12\linewidth}"
             r"p{0.04\linewidth}>{\raggedright\arraybackslash}p{0.16\linewidth}@{}}",
             r"\caption{Input parameters of the screen, their priors and sources.}\label{tab:si-params}\\",
             r"\toprule",
             r"Symbol & Quantity & Value or range & Prior & Method & Grade & Sources \\",
             r"\midrule", r"\endfirsthead",
             r"\toprule",
             r"Symbol & Quantity & Value or range & Prior & Method & Grade & Sources \\",
             r"\midrule", r"\endhead",
             r"\bottomrule", r"\endfoot"]
    seen = set()
    for reg, title in SECTIONS:
        keys = [k for k, e in params.items() if k not in seen and (reg in e["regimes"])]
        if not keys:
            continue
        lines.append(r"\multicolumn{7}{@{}l}{\textit{%s}} \\" % title)
        for k in keys:
            seen.add(k)
            e = params[k]
            lines.append(" & ".join([
                symbol_cell(e, symbols, (labels.get(k) or {}).get("latex")) + marks(e),
                r"%s \newline {\scriptsize %s}" % (label_of(k, e, symbols, labels), texkey(k)),
                value_cell(e), prior_cell(e), tex(RULE_TEXT.get(e["rule"], e["rule"])),
                e.get("best_grade") or "--", cite(dois_of(e, rows))]) + r" \\")
        lines.append(r"\midrule")
    if lines[-1] == r"\midrule":
        lines.pop()
    lines += [r"\end{longtable}", r"{\footnotesize %s\par}" % LEGEND, ""]
    return "\n".join(lines)


def conflicts_block(root):
    text = (Path(root) / CONFLICTS).read_text(encoding="utf-8")
    m = re.search(r"```conflicts\n(.*?)```", text, re.S)
    if not m:
        raise ValueError("%s has no ```conflicts block" % CONFLICTS)
    return yaml.safe_load(m.group(1)) or []


def conflicts_table(entries, params, rows, sha):
    lines = [HEAD % {"sha": sha},
             r"\begin{longtable}{@{}p{0.03\linewidth}>{\raggedright}p{0.14\linewidth}>{\raggedright}p{0.17\linewidth}"
             r">{\raggedright}p{0.23\linewidth}>{\raggedright}p{0.2\linewidth}>{\raggedright\arraybackslash}p{0.13\linewidth}@{}}",
             r"\caption{Disagreements between sources beyond their stated uncertainties, and how the parameter "
             r"table resolves them.}\label{tab:si-conflicts}\\",
             r"\toprule",
             r"No. & Quantity & Sourced span & Physical reason & Resolution & Sources \\",
             r"\midrule", r"\endfirsthead",
             r"\toprule",
             r"No. & Quantity & Sourced span & Physical reason & Resolution & Sources \\",
             r"\midrule", r"\endhead",
             r"\bottomrule", r"\endfoot"]
    for i, c in enumerate(entries, 1):
        spans = []
        for k in c["keys"]:
            e = params[k]
            spans.append(r"%s: %s" % (texkey(k), value_cell(e) if e["prior"]["family"] != "categorical"
                                                else prior_cell(e)))
        dois = []
        for r in c.get("rows") or []:
            d = rows[r]["doi"].lower()
            if d not in dois:
                dois.append(d)
        res = tex(c["resolution"]) + " " + "; ".join(
            r"%s: %s" % (texkey(k), prior_cell(params[k])) for k in c["keys"])
        lines.append(" & ".join([str(i), tex(c["title"]), r" \newline ".join(spans), tex(c["reason"]), res,
                                 cite(dois)]) + r" \\")
    lines += [r"\end{longtable}", ""]
    return "\n".join(lines)


def generate(root):
    root = Path(root)
    p = P.load_params(root / P.PARAMS, root)
    params = p.entries
    _, rows = E.read_csv(root / P.TABLE)
    rows = {r["row_id"]: r for r in rows}
    symbols = P.load_symbols(root)
    sha = p.sha256.split(":")[1][:12]
    entries = conflicts_block(root)
    for c in entries:
        for k in c["keys"]:
            if k not in params:
                raise ValueError("conflict %r names unknown key %s" % (c["title"], k))
        for r in c.get("rows") or []:
            if r not in rows:
                raise ValueError("conflict %r names unknown row %s" % (c["title"], r))
    dois = []
    for e in params.values():
        dois += [d for d in dois_of(e, rows) if d not in dois]
    for c in entries:
        dois += [rows[r]["doi"].lower() for r in c.get("rows") or [] if rows[r]["doi"].lower() not in dois]
    labels = yaml.safe_load((root / LABELS).read_text(encoding="utf-8")) if (root / LABELS).exists() else {}
    missing = [k for k in params if k not in labels]
    if missing:
        raise ValueError("%s has no label for %s" % (LABELS, ", ".join(missing)))
    return {"params_table.tex": params_table(params, rows, symbols, sha, labels),
            "conflicts_table.tex": conflicts_table(entries, params, rows, sha),
            "params_table_dois.csv": "doi\n" + "\n".join(dois) + "\n"}


PREFACE = r"""
\section*{How the priors were built}

This document is the parameter table of the preprint's thermodynamic screen, sent for an early read. It
lists every input the screen samples or holds fixed, with its prior and its sources, followed by the
disagreements between sources and how the table resolves them. It reports inputs, not results: no
screen output is shown here or was used to build the table.

\paragraph{Evidence.} Every number traces to a row of the evidence table: a value read from a fetched
open text, with its DOI, the page, table or figure it was read from, its conditions, the method and a
quality grade. The parameter table is generated by code from those rows and from a key specification
that names the admitted rows; no value in it was typed. The construction rule was committed before any
value was entered, and the clauses added since then apply named rulings of the study's checkpoints.

\paragraph{Choice of prior.} A normal prior is used only when at least two independent sources of grade A
or B, each with a stated uncertainty, agree within their combined uncertainty, or when one critically
evaluated grade-A source states its uncertainty. In every other case the prior is uniform over the
union of the sourced intervals, so the prior is never narrower than the disagreement between sources;
it is log-uniform when that span exceeds a decade. A single value without an uncertainty is held fixed
and marked, because its width is not sourced. A different quantity used in place of the target (for
example a surface enthalpy for an interfacial free energy) is never admitted silently: where such a
measured analog exists it becomes a separate, flagged analog prior that is run beside the main prior.

\paragraph{Unmeasured quantities.} Interfacial free energies that no source measures get ignorance priors:
uniform between bounds that follow from physics alone (a dry work of adhesion cannot be negative and an
interfacial free energy between immiscible phases cannot be negative). Verdicts under an ignorance prior
are reported as properties of the prior, never as a probability that the barrier forms. Single-source
binding free energies are widened to at least the method error of their class and flagged. The
template-water interfacial energy is cut at zero, as ruled, with the uncut range kept as a labelled
sensitivity. Method conventions (credible level, margins) are read from the registered thresholds, not
retyped.

\paragraph{What we ask of readers.} Missing or better sources for any row, especially those marked as gaps,
single sources or analogs; conditions that do not match the slurry or cell regimes; and any disagreement
in the conflicts table whose physical reason is misread.
"""


def early_read(root, out_dir):
    """Write and build the early-read PDF (local-only). Returns the PDF path."""
    import shutil
    import subprocess

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for n in ("params_table.tex", "conflicts_table.tex"):
        shutil.copyfile(Path(root) / OUT / n, out_dir / n)
    tex_path = out_dir / "params_table_for_coauthors.tex"
    tex_path.write_text("\n".join([
        r"\documentclass[10pt]{article}",
        r"\usepackage[a4paper,landscape,margin=15mm]{geometry}",
        r"\usepackage[T1]{fontenc}", r"\usepackage{lmodern}", r"\usepackage{booktabs,longtable,array}",
        r"\usepackage{amssymb}", r"\usepackage[hyphens]{url}", r"\usepackage[hidelinks]{hyperref}",
        r"\setlength{\parskip}{0.4em}", r"\newcommand{\paramcite}[1]{\nolinkurl{#1}}",
        r"\renewcommand{\arraystretch}{1.15}",
        r"\begin{document}", r"{\Large\bfseries Parameter table and source conflicts (early read)\par}",
        r"\vspace{0.5em}", PREFACE, r"\clearpage", r"{\small \input{params_table.tex}}", r"\clearpage",
        r"{\small \input{conflicts_table.tex}}", r"\end{document}", ""]), encoding="utf-8")
    subprocess.run(["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
                   cwd=out_dir, check=True, stdout=subprocess.DEVNULL)
    return out_dir / "params_table_for_coauthors.pdf"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m nacre.lit.si_table")
    ap.add_argument("--out")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--early-read", metavar="DIR")
    a = ap.parse_args(argv)
    root = _util.repo_root()
    if a.early_read:
        print("built %s" % early_read(root, a.early_read))
        return 0
    out = Path(a.out) if a.out else root / OUT
    files = generate(root)
    if a.check:
        stale = [n for n, t in files.items() if not (out / n).exists() or (out / n).read_text(encoding="utf-8") != t]
        print("si_table: %s" % ("up to date" if not stale else "stale: %s" % ", ".join(stale)))
        return 1 if stale else 0
    out.mkdir(parents=True, exist_ok=True)
    for n, t in files.items():
        (out / n).write_text(t, encoding="utf-8")
    print("wrote %s (%d DOIs)" % (", ".join(str(out / n) for n in files),
                                  len(files["params_table_dois.csv"].split()) - 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Build the TikZ schematics of figures/tikz/schematics.yaml and check their PDFs.

Each schematic is compiled with latexmk in a scratch directory (pdflatex, or xelatex for a
variant that sets text in the figure font), copied to figures/out/, rendered to a 600 dpi PNG
and simulated for colour-vision deficiency. The PDF is then checked: one page exactly one RSC
column wide and no taller than the maximum, every stroke at least the minimum width, and, for a
text-free schematic, no text at all (nacre.figs.checker.check_pdf_schematic). The pictograms
the schematics use are regenerated first (nacre.figs.pictograms).

The PDFs omit their dates and document id (pdfTeX primitives in schematic_preamble.tex;
SOURCE_DATE_EPOCH for XeTeX), so a rebuild is byte-identical.
"""
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

import yaml

from nacre.figs import checker, paths, pictograms, style

ENGINES = {"pdflatex": "-pdf", "xelatex": "-xelatex"}


class SchematicError(Exception):
    pass


def tikz_dir(root):
    return paths(root)["root"] / "figures" / "tikz"


@lru_cache(maxsize=4)
def _table(path):
    return yaml.safe_load(Path(path).read_text())["schematics"]


def table(root):
    return _table(str(tikz_dir(root) / "schematics.yaml"))


def compile_pdf(root, entry):
    """Compile one schematic; return the PDF bytes."""
    tdir = tikz_dir(root)
    env = dict(os.environ, TEXINPUTS="%s//:" % tdir, SOURCE_DATE_EPOCH="0", FORCE_SOURCE_DATE="1")
    # A fixed scratch path: XeTeX's PDF driver derives the document id and the font-subset tags
    # from the output path, so a random temporary directory would change the bytes.
    tmp = Path(tempfile.gettempdir()) / "nacre-figs-tikz" / Path(entry["tex"]).stem
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    try:
        cmd = ["latexmk", ENGINES[entry["engine"]], "-interaction=nonstopmode", "-halt-on-error",
               "-outdir=" + str(tmp), entry["tex"]]
        proc = subprocess.run(cmd, cwd=tdir, env=env, capture_output=True, text=True)
        pdf = tmp / (Path(entry["tex"]).stem + ".pdf")
        if proc.returncode != 0 or not pdf.exists():
            log = tmp / (Path(entry["tex"]).stem + ".log")
            errs = [line for line in log.read_text(errors="replace").splitlines() if line.startswith("!")] \
                if log.exists() else [proc.stdout[-500:]]
            raise SchematicError("%s: latexmk failed: %s" % (entry["tex"], "; ".join(errs[:3])))
        return pdf.read_bytes()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


_DRAW_RE = re.compile(r"\\draw\[(proc|force)\b[^\]]*\]\s*(.*?);", re.S)
_DEF_RE = re.compile(r"\\def\\([A-Za-z]+)\{([^}]*)\}")
_COORD_RE = re.compile(r"\(\s*([^,()]+?)\s*,\s*([^,()]+?)\s*\)")
_TOL_CM = 1e-9


def _number(text, macros):
    text = text.strip()
    for name, val in macros.items():
        text = re.sub(r"\\%s(?![A-Za-z])" % name, val, text)
    return float(text)  # a plain number or a \def macro holding one; anything else raises ValueError


def arrow_problems(tex):
    """Problems with the arrows of the cycle in a schematic body (lane decision P0-W6.3).

    Every `proc` arrow must be absolute coordinates joined by `--`, each step horizontal or
    vertical (right-angle bends only): no curves (`to`, `arc`, `..`), no relative or implicit
    corners. `force` arrows (the line tensions at the contact line) are exempt and keep their
    physical directions. Comments are ignored.
    """
    body = "\n".join(line.split("%")[0] for line in tex.splitlines())
    macros = dict(_DEF_RE.findall(body))
    problems = []
    for style_name, path in _DRAW_RE.findall(body):
        if style_name == "force":
            continue
        tokens = [s.strip() for s in path.split("--")]
        pts = []
        for tok in tokens:
            m = _COORD_RE.fullmatch(tok)
            if not m:
                problems.append("arrow %r: %r is not an absolute (x,y) joined by --" % (path.strip(), tok))
                break
            try:
                pts.append((_number(m.group(1), macros), _number(m.group(2), macros)))
            except ValueError:
                problems.append("arrow %r: %r is not a numeric coordinate" % (path.strip(), tok))
                break
        else:
            if len(pts) < 2:
                problems.append("arrow %r has no segment" % path.strip())
            for a, b in zip(pts, pts[1:]):
                dx, dy = abs(a[0] - b[0]), abs(a[1] - b[1])
                if (dx > _TOL_CM) == (dy > _TOL_CM):
                    problems.append("arrow %r: segment %s -> %s is %s" % (
                        path.strip(), a, b, "empty" if dx <= _TOL_CM else "diagonal"))
    return problems


def check(root, pdf_path, entry):
    pt = 72.0
    return checker.check_pdf_schematic(
        pdf_path,
        min_line_pt=style.min_line_pt(root),
        widths_pt=(style.width_in(entry["width"], root) * pt,),
        max_height_pt=style.max_height_in(root) * pt,
        text_free=bool(entry["text_free"]),
    )


def build(root, only=None, cvd=True, log=print):
    """Build every schematic (or those in `only`). Returns (records, failures)."""
    root = Path(root)
    pictograms.write(root)
    out = paths(root)["out"]
    dpi = int(style.applied(root)["raster_dpi"]["value"])
    records, failures = {}, []
    for sid, entry in table(root).items():
        if only and sid not in only and entry.get("variant_of") not in only:
            continue
        if entry.get("deliverable", True) is False and not (only and sid in only):
            continue
        try:
            if shutil.which("latexmk") is None:
                raise SchematicError("latexmk is not installed")
            data = compile_pdf(root, entry)
            pdf = out / entry["out"]
            pdf.parent.mkdir(parents=True, exist_ok=True)
            pdf.write_bytes(data)
            problems = check(root, pdf, entry)
            if entry.get("orthogonal_arrows"):
                problems += arrow_problems((tikz_dir(root) / entry["orthogonal_arrows"]).read_text())
            if problems:
                failures.extend("%s: %s" % (sid, p) for p in problems)
                log("%s: checker FAIL\n  %s" % (sid, "\n  ".join(problems)))
                continue
            from nacre.figs import structures
            png = pdf.with_suffix(".png")
            structures.pdf_to_png(pdf, png, dpi)
            outs = [pdf, png]
            if cvd:
                from nacre.figs import cvd as cvdmod
                cdir = pdf.parent / "cvd"
                cdir.mkdir(exist_ok=True)
                outs += cvdmod.simulate_png(png, cdir, pdf.stem, dpi)
            records[sid] = {
                "tex": "figures/tikz/" + entry["tex"], "claim": entry["claim"], "caption": entry["caption"],
                "text_free": entry["text_free"], "source": entry["source"],
                "w3_commit": entry.get("w3_commit"),
                "stub": bool(entry.get("stub", False)),
                "checker": "pass (PDF: %s, strokes, page width%s)" % (
                    "no text" if entry["text_free"] else "text allowed",
                    "; arrows orthogonal" if entry.get("orthogonal_arrows") else ""),
                "font": "none (no text)" if entry["text_free"] else "Arial (fontspec, XeLaTeX)",
                "outputs": {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in outs},
            }
            log("%s: ok -> %s" % (sid, pdf.relative_to(root)))
        except SchematicError as exc:
            failures.append(str(exc))
            log("%s: FAIL %s" % (sid, exc))
    return records, failures

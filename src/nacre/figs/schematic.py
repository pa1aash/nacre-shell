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
        try:
            if shutil.which("latexmk") is None:
                raise SchematicError("latexmk is not installed")
            data = compile_pdf(root, entry)
            pdf = out / entry["out"]
            pdf.parent.mkdir(parents=True, exist_ok=True)
            pdf.write_bytes(data)
            problems = check(root, pdf, entry)
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
                "checker": "pass (PDF: %s, strokes, page width)" % ("no text" if entry["text_free"] else "text allowed"),
                "outputs": {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in outs},
            }
            log("%s: ok -> %s" % (sid, pdf.relative_to(root)))
        except SchematicError as exc:
            failures.append(str(exc))
            log("%s: FAIL %s" % (sid, exc))
    return records, failures

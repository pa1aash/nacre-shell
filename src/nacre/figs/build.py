"""Discover figure templates, load and validate their inputs, render, check and write outputs.

A template is figures/src/figN.py defining:
  FIGURE  dict with id, claim (the one physical claim the figure carries), caption_key (what
          the caption must identify, since the figure holds no legend or labels), width
          ('single' | 'double'), height_cm, schema, mock_input and input (repo-relative paths);
  build(data, root) -> matplotlib Figure.

Mock inputs carry "mock": true and render only into figures/out/mock/. Real inputs must not
carry it and render into figures/out/.
"""
import hashlib
import importlib.util
import json
import re
from pathlib import Path

from nacre.figs import checker, paths, schema, style

_FIG_RE = re.compile(r"^fig(\d+)\.py$")
_REQUIRED = ("id", "claim", "caption_key", "width", "height_cm", "schema", "mock_input", "input")


class FigureError(Exception):
    pass


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def discover(root):
    src = paths(root)["src"]
    found = []
    for p in src.iterdir() if src.is_dir() else []:
        m = _FIG_RE.match(p.name)
        if m:
            found.append((int(m.group(1)), p))
    return [p for _, p in sorted(found)]


def load_template(path):
    spec = importlib.util.spec_from_file_location("nacre_figure_" + path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fig = getattr(mod, "FIGURE", None)
    if not isinstance(fig, dict) or not callable(getattr(mod, "build", None)):
        raise FigureError("%s: needs FIGURE and build(data, root)" % path.name)
    missing = [k for k in _REQUIRED if k not in fig]
    if missing:
        raise FigureError("%s: FIGURE lacks %s" % (path.name, ", ".join(missing)))
    if fig["id"] != path.stem:
        raise FigureError("%s: FIGURE id %r does not match the file name" % (path.name, fig["id"]))
    if fig["width"] not in ("single", "double"):
        raise FigureError("%s: width must be single or double" % path.name)
    return mod


def load_input(root, mod, mock):
    """Return (data, path) or (None, path) when a real input does not exist yet."""
    fig = mod.FIGURE
    path = Path(root) / (fig["mock_input"] if mock else fig["input"])
    if not path.exists():
        if mock:
            raise FigureError("%s: mock input %s missing" % (fig["id"], path))
        return None, path
    data = json.loads(path.read_text())
    if mock and data.get("mock") is not True:
        raise FigureError("%s: mock input must carry \"mock\": true" % fig["id"])
    if not mock and data.get("mock") is True:
        raise FigureError("%s: input %s is marked mock" % (fig["id"], path))
    sch = json.loads((Path(root) / fig["schema"]).read_text())
    errs = schema.validate(data, sch)
    if errs:
        raise FigureError("%s: input does not match %s:\n  %s" % (fig["id"], fig["schema"], "\n  ".join(errs)))
    return data, path


def make_figure(root, mod, data):
    plt = style.use(root)
    fig = mod.build(data, root)
    return plt, fig


def render(root, mod, data, input_path, out_dir, tiff=False, cvd=True):
    root = Path(root)
    p = paths(root)
    fid = mod.FIGURE["id"]
    is_mock = data.get("mock") is True
    if is_mock and Path(out_dir).resolve() != p["out_mock"].resolve():
        raise FigureError("%s: mock output goes only to %s" % (fid, p["out_mock"].relative_to(root)))
    if not is_mock and Path(out_dir).resolve() == p["out_mock"].resolve():
        raise FigureError("%s: real output must not go to the mock directory" % fid)
    plt, fig = make_figure(root, mod, data)
    try:
        expected = style.figsize(mod.FIGURE["width"], mod.FIGURE["height_cm"], root)
        got = tuple(fig.get_size_inches())
        if any(abs(a - b) > 1e-3 for a, b in zip(expected, got)):
            raise FigureError("%s: size %s differs from FIGURE width/height_cm %s" % (fid, got, expected))
        problems = checker.check_rsc(fig, root)
        if problems:
            raise checker.FigureCheckError(["%s: %s" % (fid, x) for x in problems])
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        dpi = int(style.applied(root)["raster_dpi"]["value"])
        pdf = out_dir / (fid + ".pdf")
        png = out_dir / (fid + ".png")
        fig.savefig(pdf, format="pdf", metadata={"Creator": None, "Producer": None, "CreationDate": None})
        fig.savefig(png, format="png", dpi=dpi, metadata={"Software": None})
        outputs = [pdf, png]
        if tiff:
            tif = out_dir / (fid + ".tiff")
            fig.savefig(tif, format="tiff", dpi=dpi, pil_kwargs={"compression": "tiff_lzw"})
            outputs.append(tif)
    finally:
        plt.close(fig)
    if cvd:
        from nacre.figs import cvd as cvdmod
        cdir = out_dir / "cvd"
        cdir.mkdir(exist_ok=True)
        outputs += cvdmod.simulate_png(png, cdir, fid, dpi)
    w, h = expected
    return {
        "id": fid,
        "claim": mod.FIGURE["claim"],
        "caption_key": mod.FIGURE["caption_key"],
        "mock": is_mock,
        "width": mod.FIGURE["width"],
        "size_cm": [round(w * style.CM_PER_IN, 2), round(h * style.CM_PER_IN, 2)],
        "input": str(Path(input_path).resolve().relative_to(root.resolve())),
        "input_sha256": _sha(input_path),
        "outputs": {str(o.resolve().relative_to(root.resolve())): _sha(o) for o in outputs},
        "checker": "pass",
    }


def run(root, mock=False, only=None, tiff=False, cvd=True, log=print):
    """Build every template (or those in `only`). Returns (records, failures)."""
    root = Path(root)
    p = paths(root)
    out_dir = p["out_mock"] if mock else p["out"]
    records, failures = [], []
    templates = discover(root)
    if only:
        wanted = set(only)
        templates = [t for t in templates if t.stem in wanted]
        missing = wanted - {t.stem for t in templates}
        for m in sorted(missing):
            failures.append("%s: no template figures/src/%s.py" % (m, m))
    for path in templates:
        try:
            mod = load_template(path)
            data, input_path = load_input(root, mod, mock)
            if data is None:
                log("%s: skipped, input %s not present yet" % (path.stem, input_path.relative_to(root)))
                continue
            rec = render(root, mod, data, input_path, out_dir, tiff=tiff, cvd=cvd)
            records.append(rec)
            log("%s: ok -> %s" % (rec["id"], ", ".join(sorted(rec["outputs"]))))
        except checker.FigureCheckError as exc:
            failures.extend(exc.problems)
            log("%s: checker FAIL\n  %s" % (path.stem, "\n  ".join(exc.problems)))
        except FigureError as exc:
            failures.append(str(exc))
            log("%s: FAIL %s" % (path.stem, exc))
    if records:
        manifest = out_dir / "manifest.json"
        old = json.loads(manifest.read_text()) if manifest.exists() else {"figures": {}}
        figs = old.get("figures", {})
        for r in records:
            figs[r["id"]] = r
        manifest.write_text(json.dumps({"mock": mock, "figures": dict(sorted(figs.items()))}, indent=1) + "\n")
    return records, failures

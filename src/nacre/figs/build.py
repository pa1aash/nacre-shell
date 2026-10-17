"""Discover figure templates, load and validate their inputs, render, check and write outputs.

A template is figures/src/figN.py defining:
  FIGURE  dict with id, claim (the one physical claim the figure carries), caption_key (what
          the caption must identify, since the figure holds no legend or labels), width
          ('single' | 'double'), height_cm, schema (an owner contract, "upstream:<key>", or a
          schema path), mock_input and input (repo-relative paths), and optionally aux:
          {name: "upstream:<key>" | {"mock": path, "real": path}} for further inputs (the
          parameter rows behind threshold contours, for example);
  build(data, root, aux) -> matplotlib Figure.

Mock inputs carry "mock": true and render only into figures/out/mock/. Real inputs must not
carry it and render into figures/out/. An aux file follows the same rule as the main input.

After saving, the PDF itself is checked: every text span in it must lie inside the box of a
tick label, an axis title, a colour-bar label or a panel letter (checker.check_pdf_text).
"""
import hashlib
import importlib.util
import json
import re
from pathlib import Path

import yaml

from nacre.figs import checker, paths, schema, style, upstream

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
    sch, cite = schema.resolve(fig["schema"], root)
    errs = schema.validate(data, sch)
    if errs:
        raise FigureError("%s: input does not match %s:\n  %s" % (fig["id"], cite, "\n  ".join(errs[:20])))
    return data, path


def _read(path):
    text = Path(path).read_text()
    return json.loads(text) if Path(path).suffix == ".json" else yaml.safe_load(text)


def load_aux(root, mod, mock):
    """{name: (data, citation)} for FIGURE["aux"], or None when a real aux file is absent."""
    out = {}
    for name, ref in mod.FIGURE.get("aux", {}).items():
        if isinstance(ref, str) and ref.startswith(schema.UPSTREAM):
            key = ref[len(schema.UPSTREAM):]
            out[name] = (upstream.load(key, root), upstream.cite(key, root))
            continue
        path = Path(root) / ref["mock" if mock else "real"]
        if not path.exists():
            if mock:
                raise FigureError("%s: mock aux %s missing" % (mod.FIGURE["id"], path))
            return None
        data = _read(path)
        marked = isinstance(data, dict) and data.get("mock") is True
        if mock and not marked:
            raise FigureError("%s: mock aux %s must carry mock: true" % (mod.FIGURE["id"], path))
        if not mock and marked:
            raise FigureError("%s: aux %s is marked mock" % (mod.FIGURE["id"], path))
        out[name] = (data, "%s sha256:%s" % (Path(path).resolve().relative_to(Path(root).resolve()), _sha(path)))
    return out


def make_figure(root, mod, data, aux=None):
    plt = style.use(root)
    fig = mod.build(data, root, {k: v[0] for k, v in (aux or {}).items()})
    return plt, fig


def render(root, mod, data, input_path, out_dir, tiff=False, cvd=True, aux=None):
    root = Path(root)
    p = paths(root)
    fid = mod.FIGURE["id"]
    is_mock = data.get("mock") is True
    if is_mock and Path(out_dir).resolve() != p["out_mock"].resolve():
        raise FigureError("%s: mock output goes only to %s" % (fid, p["out_mock"].relative_to(root)))
    if not is_mock and Path(out_dir).resolve() == p["out_mock"].resolve():
        raise FigureError("%s: real output must not go to the mock directory" % fid)
    plt, fig = make_figure(root, mod, data, aux)
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
        boxes = checker.allowed_text_boxes(fig)
        fig.savefig(pdf, format="pdf", metadata={"Creator": None, "Producer": None, "CreationDate": None})
        fig.savefig(png, format="png", dpi=dpi, metadata={"Software": None})
        problems = checker.check_pdf_text(pdf, boxes)
        if problems:
            raise checker.FigureCheckError(["%s: %s" % (fid, x) for x in problems])
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
        "schema": schema.resolve(mod.FIGURE["schema"], root)[1],
        "aux": {k: v[1] for k, v in sorted((aux or {}).items())},
        "outputs": {str(o.resolve().relative_to(root.resolve())): _sha(o) for o in outputs},
        "checker": "pass (artists and PDF text)",
    }


def run(root, mock=False, only=None, tiff=False, cvd=True, log=print):
    """Build every template (or those in `only`). Returns (records, failures)."""
    root = Path(root)
    p = paths(root)
    out_dir = p["out_mock"] if mock else p["out"]
    records, failures = [], []
    for key, msg in upstream.drift(root):
        log("upstream %s: %s" % (key, msg))
    templates = discover(root)
    if only:
        wanted = set(only)
        templates = [t for t in templates if t.stem in wanted]
        from nacre.figs import schematic
        others = set(schematic.table(root)) | {"rdkit"}
        missing = wanted - {t.stem for t in templates} - others
        for m in sorted(missing):
            failures.append("%s: no template figures/src/%s.py, schematic or structure set" % (m, m))
    for path in templates:
        try:
            mod = load_template(path)
            data, input_path = load_input(root, mod, mock)
            aux = load_aux(root, mod, mock) if data is not None else None
            if data is None or aux is None:
                log("%s: skipped, real input not present yet" % path.stem)
                continue
            rec = render(root, mod, data, input_path, out_dir, tiff=tiff, cvd=cvd, aux=aux)
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
    n_other, other_failures = build_drawings(root, only=only, cvd=cvd, log=log)
    failures += other_failures
    return records + [None] * n_other, failures


def build_drawings(root, only=None, cvd=True, log=print):
    """The schematics (figures/tikz) and the RDKit structure set: no data, so the same with or
    without --mock. Writes figures/out/manifest.json. Returns (count built, failures)."""
    from nacre.figs import schematic, structures
    root = Path(root)
    want_s = only is None or any(o in schematic.table(root) for o in only)
    want_r = only is None or "rdkit" in only
    if not (want_s or want_r):
        return 0, []
    manifest = paths(root)["out"] / "manifest.json"
    old = json.loads(manifest.read_text()) if manifest.exists() else {}
    failures, n = [], 0
    if want_s:
        recs, fails = schematic.build(root, only=only, cvd=cvd, log=log)
        old.setdefault("schematics", {}).update(recs)
        failures += fails
        n += len(recs)
    if want_r:
        recs = structures.build_all(root, cvd=cvd, log=log)
        old["rdkit"] = recs
        n += len(recs)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({k: dict(sorted(v.items())) for k, v in sorted(old.items())}, indent=1) + "\n")
    return n, failures

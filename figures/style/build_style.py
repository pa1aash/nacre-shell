"""Generate figures/style/rsc.mplstyle from rsc_spec.yaml (and the colour cycle from palette.yaml).

Every line of the output carries a trailing comment naming the entry it came from:
`applied.<key>` in rsc_spec.yaml, or `palette.<path>` in palette.yaml. Nothing is typed here
that the spec does not hold; the mapping below only says which rcParams an applied value sets.

Run: uv run python figures/style/build_style.py [--check]
"""
import argparse
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SPEC = HERE / "rsc_spec.yaml"
PALETTE = HERE / "palette.yaml"
OUT = HERE / "rsc.mplstyle"

# applied key -> rcParams it sets. A value of None means "the applied value itself".
_TEXT_SIZE = ["font.size", "axes.labelsize", "axes.titlesize", "xtick.labelsize", "ytick.labelsize",
              "legend.fontsize", "figure.titlesize", "figure.labelsize"]
_MIN_LINE = ["axes.linewidth", "xtick.major.width", "ytick.major.width", "xtick.minor.width",
             "ytick.minor.width", "patch.linewidth", "hatch.linewidth", "lines.markeredgewidth",
             "contour.linewidth", "grid.linewidth"]
_BLACK = ["text.color", "axes.edgecolor", "axes.labelcolor", "xtick.color", "ytick.color",
          "xtick.labelcolor", "ytick.labelcolor", "patch.edgecolor", "hatch.color"]


def _fmt(v):
    if isinstance(v, bool):
        return "True" if v else "False"
    if isinstance(v, float):
        return ("%.4f" % v).rstrip("0").rstrip(".")
    return str(v)


def build():
    spec = yaml.safe_load(SPEC.read_text())["applied"]
    pal = yaml.safe_load(PALETTE.read_text())
    lines = []

    def put(key, value, trace):
        lines.append("%-28s: %-34s # %s" % (key, _fmt(value), trace))

    def section(title):
        lines.append("")
        lines.append("## " + title)

    section("Font")
    fam = spec["font_family"]
    put("font.family", "sans-serif", "applied.font_family")
    put("font.sans-serif", ", ".join([fam["value"]] + fam.get("fallbacks", [])), "applied.font_family")
    put("mathtext.fontset", "custom", "applied.font_family (mathtext in the same family)")
    put("mathtext.rm", "sans", "applied.font_family")
    put("mathtext.it", "sans:italic", "applied.font_family")
    put("mathtext.bf", "sans:bold", "applied.font_family")
    put("mathtext.sf", "sans", "applied.font_family")
    put("mathtext.cal", "sans:italic", "applied.font_family (no second family for calligraphic)")
    put("mathtext.tt", "sans", "applied.font_family (no second family for typewriter)")
    put("mathtext.fallback", "None", "applied.font_family (no silent fallback to another family)")
    put("axes.unicode_minus", True, "applied.font_family (true minus sign from the same font)")
    for key in _TEXT_SIZE:
        put(key, float(spec["font_size"]["value"]), "applied.font_size")
    put("axes.titleweight", spec["panel_letter"]["value"]["weight"], "applied.panel_letter")
    put("axes.titlelocation", "left", "applied.panel_letter")

    section("Lines")
    for key in _MIN_LINE:
        put(key, float(spec["line_width_min"]["value"]), "applied.line_width_min")
    put("lines.linewidth", float(spec["line_width_data"]["value"]), "applied.line_width_data")
    put("lines.markersize", float(spec["marker_size"]["value"]), "applied.marker_size")
    tick = spec["tick_length"]
    for ax in ("xtick", "ytick"):
        put(ax + ".major.size", float(tick["value"]), "applied.tick_length")
        put(ax + ".minor.size", float(tick["value"]) / 2, "applied.tick_length / 2")
    put("errorbar.capsize", float(spec["errorbar_capsize"]["value"]), "applied.errorbar_capsize")
    put("contour.negative_linestyle", spec["contour_linestyle"]["value"], "applied.contour_linestyle")

    section("Colour")
    black = spec["text_colour"]["value"]
    for key in _BLACK:
        put(key, black.lstrip("#"), "applied.text_colour")
    cyc = pal["categorical"]["cycle"]
    oi = pal["categorical"]["okabe_ito"]
    hexes = ", ".join("'%s'" % oi[n]["hex"].lstrip("#") for n in cyc)
    put("axes.prop_cycle", "cycler('color', [%s])" % hexes, "palette.categorical.cycle (Okabe-Ito)")

    section("Axes and layout")
    put("xtick.direction", spec["tick_direction"]["value"], "applied.tick_direction")
    put("ytick.direction", spec["tick_direction"]["value"], "applied.tick_direction")
    put("axes.spines.top", spec["spines_top_right"]["value"], "applied.spines_top_right")
    put("axes.spines.right", spec["spines_top_right"]["value"], "applied.spines_top_right")
    put("axes.grid", spec["grid"]["value"], "applied.grid")
    put("legend.frameon", spec["legend"]["value"], "applied.legend (legends are rejected by the checker)")
    put("figure.constrained_layout.use", spec["layout"]["value"] == "constrained", "applied.layout")
    put("figure.figsize", "%s, %s" % (_fmt(spec["width_single_in"]["value"]),
                                      _fmt(round(spec["width_single_in"]["value"] * 0.75, 4))),
        "applied.width_single_in (default only; each figure sets its own height)")

    section("Output")
    put("savefig.dpi", int(spec["raster_dpi"]["value"]), "applied.raster_dpi")
    put("figure.dpi", int(spec["raster_dpi"]["value"]) // 4, "applied.raster_dpi / 4 (screen preview only)")
    put("savefig.format", spec["vector_format"]["value"], "applied.vector_format")
    put("savefig.bbox", "standard", "applied.width_single_in / width_double_in (no tight crop; widths are exact)")
    put("savefig.transparent", False, "applied.text_colour (opaque white ground)")
    put("pdf.fonttype", 42, "applied.vector_format (TrueType embedded)")
    put("ps.fonttype", 42, "applied.vector_format (TrueType embedded)")
    put("svg.fonttype", "none", "applied.vector_format (text kept as text)")

    head = ["# Generated by figures/style/build_style.py from rsc_spec.yaml and palette.yaml; do not edit.",
            "# Each line names the spec entry it traces to."]
    return "\n".join(head + lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="fail if rsc.mplstyle differs from a fresh build")
    args = ap.parse_args(argv)
    text = build()
    if args.check:
        if not OUT.exists() or OUT.read_text() != text:
            print("rsc.mplstyle is stale; run figures/style/build_style.py")
            return 1
        print("rsc.mplstyle is current")
        return 0
    OUT.write_text(text)
    print("wrote %s" % OUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())

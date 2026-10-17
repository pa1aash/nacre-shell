"""Load the generated RSC style and the palette; expose column widths and colours."""
import warnings
from functools import lru_cache
from pathlib import Path

import yaml

from nacre.figs import paths

CM_PER_IN = 2.54


def _root():
    from nacre import _util
    return _util.repo_root()


@lru_cache(maxsize=4)
def _spec(style_dir):
    return yaml.safe_load((Path(style_dir) / "rsc_spec.yaml").read_text())


@lru_cache(maxsize=4)
def _palette(style_dir):
    return yaml.safe_load((Path(style_dir) / "palette.yaml").read_text())


def spec(root=None):
    return _spec(str(paths(root or _root())["style"]))


def palette(root=None):
    return _palette(str(paths(root or _root())["style"]))


def applied(root=None):
    return spec(root)["applied"]


class FontError(Exception):
    pass


def font_chain(root=None):
    """The figure font and its fallbacks, in order (applied.font_family, lane note N18)."""
    fam = applied(root)["font_family"]
    return [fam["value"]] + list(fam.get("fallbacks", []))


def _find(name):
    """Path of an installed font of family `name`, or None (no silent default font)."""
    from matplotlib import font_manager
    try:
        return font_manager.findfont(name, fallback_to_default=False)
    except ValueError:
        return None


def font(root=None):
    """The first installed font of the chain: {family, file, rank, release}.

    rank 0 is the specification's own face; release is True only for it. Raises FontError when
    no face of the chain is installed, rather than letting matplotlib fall back to its default.
    """
    chain = font_chain(root)
    for rank, name in enumerate(chain):
        path = _find(name)
        if path:
            return {"family": name, "file": path, "rank": rank, "release": rank == 0}
    raise FontError("none of the figure fonts is installed: %s" % ", ".join(chain))


def font_record(root=None):
    """Provenance form of font(): the family, the font file's base name and the release flag."""
    f = font(root)
    return {"family": f["family"], "file": Path(f["file"]).name, "release": f["release"]}


def use(root=None):
    """Select the Agg backend, register the Crameri maps, apply rsc.mplstyle and pin the font.

    The style lists the whole chain; the font actually used is then set alone, so matplotlib can
    neither pick a different face of the list nor fall back silently.
    """
    import matplotlib
    matplotlib.use("Agg")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        import cmcrameri  # noqa: F401  (registers cmc.* colour maps)
    import matplotlib.pyplot as plt
    plt.rcdefaults()
    plt.style.use(str(paths(root or _root())["style"] / "rsc.mplstyle"))
    plt.rcParams["font.sans-serif"] = [font(root)["family"]]
    return plt


def width_in(kind, root=None):
    """Column width in inches: kind is 'single' or 'double'."""
    return float(applied(root)["width_%s_in" % kind]["value"])


def max_height_in(root=None):
    return float(applied(root)["max_height_in"]["value"])


def figsize(kind, height_cm, root=None):
    h = height_cm / CM_PER_IN
    if h > max_height_in(root):
        raise ValueError("height %.1f cm exceeds the RSC maximum" % height_cm)
    return (width_in(kind, root), h)


def min_font_pt(root=None):
    return float(applied(root)["font_size"]["value"])


def min_line_pt(root=None):
    return float(applied(root)["line_width_min"]["value"])


def categorical(name, root=None):
    """Okabe-Ito colour by name (hex)."""
    return palette(root)["categorical"]["okabe_ito"][name]["hex"]


def cycle(root=None):
    pal = palette(root)
    return [pal["categorical"]["okabe_ito"][n]["hex"] for n in pal["categorical"]["cycle"]]


def colormap(role, root=None):
    """Crameri colour map for 'sequential' or 'diverging'."""
    from matplotlib import colormaps
    return colormaps[palette(root)["colormaps"][role]["matplotlib_name"]]


def element(symbol, space="srgb", root=None):
    return tuple(palette(root)["elements"][symbol][space])

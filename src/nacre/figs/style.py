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


def use(root=None):
    """Select the Agg backend, register the Crameri maps and apply rsc.mplstyle."""
    import matplotlib
    matplotlib.use("Agg")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        import cmcrameri  # noqa: F401  (registers cmc.* colour maps)
    import matplotlib.pyplot as plt
    plt.rcdefaults()
    plt.style.use(str(paths(root or _root())["style"] / "rsc.mplstyle"))
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

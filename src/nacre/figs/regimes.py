"""The regime vocabulary of the paper as fills and hatching, shared by the regime figures.

The data files use the verdict words feasible, falsified, inconclusive and undetermined; the
paper's vocabulary (theory/claims_redirect.md section 11d) reads excluded, not excluded,
suitable against dissolution, open and undetermined. Four words occur in the outputs (no output
carries "not excluded"), and four fills clear the palette threshold in every vision condition
(nacre.figs.colours.distinct_fills), so the figures draw those four, each with its own
hatching; the fill and the hatching both tell them apart.
"""
from nacre.figs import colours

# Data word -> registered word, for a K1 ladder cell or a K2 cell.
FROM_VERDICT = {
    "feasible": "suitable against dissolution",
    "falsified": "excluded",
    "inconclusive": "open",
    "undetermined": "undetermined",
}
REGISTERED = tuple(FROM_VERDICT.values())
HUE = {"excluded": "vermillion", "open": "yellow", "undetermined": "blue",
       "suitable against dissolution": "skyblue"}
HATCH = {"excluded": "xxxx", "open": "////", "undetermined": None, "suitable against dissolution": ".."}
ORDER = ("suitable against dissolution", "undetermined", "open", "excluded")  # drawing and key order


def word(verdict):
    """The registered word of a data verdict word; refuses an unknown one."""
    if verdict not in FROM_VERDICT:
        raise ValueError("regimes: unknown verdict %r" % (verdict,))
    return FROM_VERDICT[verdict]


def fills(root=None):
    """{registered word: sRGB fill} from the four-colour set that clears delta_e_min."""
    cols, names, _f, _d = colours.distinct_fills(len(ORDER), root)
    by_name = dict(zip(names, cols))
    if set(HUE.values()) != set(names):
        raise ValueError("regimes: the distinct four-fill set %s is not the one the regime hues name" % (names,))
    return {w: by_name[HUE[w]] for w in ORDER}


def aggregate(verdicts):
    """The regime word of a set of K2 cell verdicts: suitable where any cell passes, otherwise open
    where any cell is inconclusive, excluded where every cell is falsified, undetermined where the
    data are missing. The rule of the production row labels (k2_grid_ph ph_rows K2 regime)."""
    vs = set(verdicts)
    if not vs:
        raise ValueError("regimes: no verdicts to aggregate")
    for v in ("feasible", "inconclusive", "falsified", "undetermined"):
        if v in vs:
            return FROM_VERDICT[v]
    raise ValueError("regimes: unknown verdicts %s" % sorted(vs))

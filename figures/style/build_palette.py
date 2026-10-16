"""Generate figures/style/palette.yaml: element colours, the categorical palette and colour maps.

Inputs, none typed by hand:
  - element colours: the Jmol table shipped with ASE (ase.data.colors.jmol_colors);
  - categorical: the Okabe-Ito table in R's grDevices source (fetch F5 in fetch_log.jsonl),
    read from the local cache or re-fetched and checked against the recorded sha256;
  - colour maps: Crameri maps from the pinned cmcrameri package.

Colour-vision-deficiency (CVD) check: each constrained element pair is compared under normal
vision and simulated deuteranopia, protanopia and tritanopia (colorspacious "sRGB1+CVD",
severity 100, results clipped to the sRGB cube). Distance is colorspacious.deltaE, Euclidean
distance in CAM02-UCS. A pair below DELTA_E_MIN in any condition is fixed by moving the more
adjustable element of the pair (ADJUST_ORDER) to the nearest in-gamut colour, by CAM02-UCS
distance from its Jmol colour, that clears every constrained pair in every condition.

Run: uv run python figures/style/build_palette.py [--check]
"""
import argparse
import hashlib
import itertools
import json
import re
import sys
import urllib.request
import warnings
from importlib.metadata import version
from pathlib import Path

import numpy as np
import yaml

warnings.filterwarnings("ignore", category=SyntaxWarning)
from ase.data import atomic_numbers  # noqa: E402
from ase.data.colors import jmol_colors  # noqa: E402
from colorspacious import cspace_convert, deltaE  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "palette.yaml"
FETCH_LOG = HERE / "fetch_log.jsonl"
CACHE = ROOT / ".local" / "w6" / "fetch"

ELEMENTS = ["Al", "O", "H", "C", "Ca", "N", "Li"]

# Design choice: minimum CAM02-UCS distance for elements shown together.
DELTA_E_MIN = 20.0
# The search clears the threshold by this margin so 4-decimal rounding cannot undo it.
SEARCH_MARGIN = 0.1

# Pairs named by the session plan: Ca against O and C, Al against O and H.
REQUIRED_PAIRS = [("Ca", "O"), ("Ca", "C"), ("Al", "O"), ("Al", "H")]
# Lane extension: every other pair co-present in the hero image (CaCO3 film on Al with its
# oxide/hydroxide), i.e. within each phase and across the Al/carbonate interface.
EXTENDED_PAIRS = [("C", "O"), ("O", "H"), ("Al", "C"), ("Al", "Ca"), ("H", "C"), ("H", "Ca")]

# Most adjustable first. O red, H white and C grey are the conventions readers rely on most;
# Al's Jmol colour is a weakly saturated pink-grey with no strong convention.
ADJUST_ORDER = ["Al", "Li", "N", "Ca", "C", "H", "O"]

CONDITIONS = {
    "normal": None,
    "deuteranopia": "deuteranomaly",
    "protanopia": "protanomaly",
    "tritanopia": "tritanomaly",
}

OKABE_ITO_FETCH = "F5"
OKABE_ITO_LINES = "277-281"
# Lane cycle order: dark blue and vermilion first for thin lines; yellow and gray are left out.
# The source page (F4) advises darker blue and orange over sky blue and yellow for thin lines.
CATEGORICAL_CYCLE = ["blue", "vermillion", "bluishgreen", "orange", "reddishpurple", "skyblue", "black"]

COLORMAPS = {
    "sequential": {"name": "batlow", "use": "magnitudes on one side of zero (nucleation barrier map, fig5)"},
    "diverging": {"name": "vik", "use": "signed quantities about a meaningful zero"},
}


def srgb_to_linear(c):
    c = np.asarray(c, dtype=float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def simulate(rgb, condition):
    cvd = CONDITIONS[condition]
    rgb = np.asarray(rgb, dtype=float)
    if cvd is None:
        return rgb
    space = {"name": "sRGB1+CVD", "cvd_type": cvd, "severity": 100}
    return np.clip(cspace_convert(rgb, space, "sRGB1"), 0.0, 1.0)


def pair_de(a, b, condition):
    return float(deltaE(simulate(a, condition), simulate(b, condition), input_space="sRGB1"))


def hexcode(rgb):
    return "#" + "".join("%02X" % int(round(float(x) * 255)) for x in rgb)


def r4(x):
    return [round(float(v), 4) for v in x]


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def fetch_row(fid):
    for line in FETCH_LOG.read_text().splitlines():
        row = json.loads(line)
        if row["id"] == fid:
            return row
    raise SystemExit("fetch %s not in %s" % (fid, FETCH_LOG))


def okabe_ito():
    """Return ({name: hex}, source record) parsed from the fetched R source."""
    row = fetch_row(OKABE_ITO_FETCH)
    cached = CACHE / "r_colorstuff.R"
    if cached.exists():
        data = cached.read_bytes()
    else:
        req = urllib.request.Request(row["url"], headers={"User-Agent": "nacre-shell figures"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
    if _sha256(data) != row["sha256"]:
        raise SystemExit("Okabe-Ito source sha256 differs from fetch %s" % OKABE_ITO_FETCH)
    text = data.decode("utf-8")
    m = re.search(r'"Okabe-Ito"\s*=\s*c\((.*?)\)', text, re.S)
    if not m:
        raise SystemExit("Okabe-Ito table not found in fetched source")
    pairs = re.findall(r'(\w+)\s*=\s*"(#[0-9A-Fa-f]{6})"', m.group(1))
    colours = {name: hx.upper() for name, hx in pairs}
    src = {
        "fetch": OKABE_ITO_FETCH,
        "url": row["url"],
        "sha256": row["sha256"],
        "package": "R grDevices",
        "version": "4.6.1",
        "locator": "src/library/grDevices/R/colorstuff.R lines %s, .palette_colors_hex$\"Okabe-Ito\"" % OKABE_ITO_LINES,
        "reference": "Okabe and Ito, Color Universal Design (fetch F4, Fig. 16)",
    }
    return colours, src


def constrained_pairs():
    return REQUIRED_PAIRS + EXTENDED_PAIRS


def failures(colours, pairs):
    out = []
    for a, b in pairs:
        for cond in CONDITIONS:
            d = pair_de(colours[a], colours[b], cond)
            if d < DELTA_E_MIN:
                out.append((a, b, cond, d))
    return out


def _grid_candidates(origin_ucs, half, step):
    axis = np.arange(-half, half + step / 2, step)
    g = np.stack(np.meshgrid(axis, axis, axis, indexing="ij"), -1).reshape(-1, 3)
    return origin_ucs + g


def adjust(element, colours, pairs):
    """Nearest in-gamut colour to the element's colour clearing all pairs that involve it."""
    involved = [(a, b) for a, b in pairs if element in (a, b)]
    others = [b if a == element else a for a, b in involved]
    origin = cspace_convert(colours[element], "sRGB1", "CAM02-UCS")
    best = None
    for half, step, centre in ((40.0, 1.0, origin), (1.0, 0.05, None)):
        if centre is None:
            centre = best
        cand = _grid_candidates(centre, half, step)
        rgb = cspace_convert(cand, "CAM02-UCS", "sRGB1")
        ok = np.all((rgb >= 0.0) & (rgb <= 1.0), axis=1)
        cand, rgb = cand[ok], rgb[ok]
        for o in others:
            for cond in CONDITIONS:
                sim_c = simulate(rgb, cond)
                sim_o = simulate(colours[o], cond)
                d = deltaE(sim_c, np.broadcast_to(sim_o, sim_c.shape), input_space="sRGB1")
                keep = d >= DELTA_E_MIN + SEARCH_MARGIN
                cand, rgb = cand[keep], rgb[keep]
        if len(cand) == 0:
            raise SystemExit("no in-gamut colour for %s clears DELTA_E_MIN" % element)
        dist = np.linalg.norm(cand - origin, axis=1)
        best = cand[int(np.argmin(dist))]
    rgb = np.clip(cspace_convert(best, "CAM02-UCS", "sRGB1"), 0.0, 1.0)
    # Store at 4 decimals; re-check after rounding.
    return np.array(r4(rgb))


def de_table(colours, pairs):
    return {
        "%s-%s" % (a, b): {c: round(pair_de(colours[a], colours[b], c), 1) for c in CONDITIONS}
        for a, b in pairs
    }


def build():
    import cmcrameri  # noqa: F401  (registers cmc.* maps)
    from matplotlib import colormaps

    jmol = {e: np.array(r4(jmol_colors[atomic_numbers[e]])) for e in ELEMENTS}
    final = dict(jmol)
    pairs = constrained_pairs()
    adjustments = []
    for _ in range(len(ELEMENTS)):
        fails = failures(final, pairs)
        if not fails:
            break
        a, b, _cond, _d = fails[0]
        target = min((a, b), key=ADJUST_ORDER.index)
        before = final[target]
        final[target] = adjust(target, final, pairs)
        adjustments.append({
            "element": target,
            "trigger": ["%s-%s %s %.1f" % f for f in fails if target in f[:2]],
            "from_srgb": r4(before),
            "to_srgb": r4(final[target]),
            "shift_cam02ucs": round(float(deltaE(before, final[target], input_space="sRGB1")), 1),
            "rule": "nearest in-gamut CAM02-UCS colour clearing every constrained pair in all four conditions",
        })
    remaining = failures(final, pairs)
    if remaining:
        raise SystemExit("palette still below threshold: %s" % remaining)

    elements = {}
    for e in ELEMENTS:
        adj = next((x for x in adjustments if x["element"] == e), None)
        elements[e] = {
            "Z": int(atomic_numbers[e]),
            "srgb": r4(final[e]),
            "hex": hexcode(final[e]),
            "linear_rgb": r4(srgb_to_linear(final[e])),
            "jmol_srgb": r4(jmol[e]),
            "adjusted": adj is not None,
        }

    oi, oi_src = okabe_ito()
    categorical = {
        name: {"hex": hx, "srgb": r4(np.array([int(hx[i:i + 2], 16) for i in (1, 3, 5)]) / 255.0),
               "linear_rgb": r4(srgb_to_linear(np.array([int(hx[i:i + 2], 16) for i in (1, 3, 5)]) / 255.0))}
        for name, hx in oi.items()
    }
    for name in CATEGORICAL_CYCLE:
        if name not in categorical:
            raise SystemExit("cycle colour %s not in Okabe-Ito source" % name)

    maps = {}
    for role, spec in COLORMAPS.items():
        cmap = colormaps["cmc." + spec["name"]]
        maps[role] = {"name": spec["name"], "matplotlib_name": "cmc." + spec["name"],
                      "n": int(cmap.N), "use": spec["use"]}

    doc = {
        "generated_by": "figures/style/build_palette.py",
        "provenance": {
            "element_table": {"package": "ase", "version": version("ase"),
                              "object": "ase.data.colors.jmol_colors", "indexed_by": "atomic number"},
            "cvd_simulation": {"package": "colorspacious", "version": version("colorspacious"),
                               "space": "sRGB1+CVD", "severity": 100, "clip": "[0, 1]",
                               "conditions": {k: v for k, v in CONDITIONS.items() if v}},
            "delta_e": {"package": "colorspacious", "function": "deltaE",
                        "space": "CAM02-UCS", "metric": "Euclidean"},
            "colormaps": {"package": "cmcrameri", "version": version("cmcrameri"), "pinned": "==1.10"},
            "categorical": oi_src,
            "linear_rgb": "IEC 61966-2-1 sRGB transfer function, inverted",
        },
        "delta_e_min": DELTA_E_MIN,
        "delta_e_min_reason": ("design choice: CAM02-UCS distance of 20 keeps shaded spheres of two elements "
                               "separable in a render under every simulated condition; Jmol already clears it "
                               "for all four required pairs"),
        "pairs": {"required": ["%s-%s" % p for p in REQUIRED_PAIRS],
                  "extended": ["%s-%s" % p for p in EXTENDED_PAIRS],
                  "adjust_order": ADJUST_ORDER},
        "elements": elements,
        "adjustments": adjustments,
        "cvd_record": {
            "jmol": de_table(jmol, pairs),
            "final": de_table(final, pairs),
            "all_pairs_final": de_table(final, list(itertools.combinations(ELEMENTS, 2))),
        },
        "categorical": {"okabe_ito": categorical, "cycle": CATEGORICAL_CYCLE},
        "colormaps": maps,
    }
    header = ("# Generated by figures/style/build_palette.py; do not edit by hand.\n"
              "# Element colours: srgb for matplotlib, linear_rgb for the renderer (lane p0-w7).\n")
    return header + yaml.safe_dump(doc, sort_keys=False, width=110)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="fail if palette.yaml differs from a fresh build")
    args = ap.parse_args(argv)
    text = build()
    if args.check:
        if not OUT.exists() or OUT.read_text() != text:
            print("palette.yaml is stale; run figures/style/build_palette.py")
            return 1
        print("palette.yaml is current")
        return 0
    OUT.write_text(text)
    print("wrote %s" % OUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())

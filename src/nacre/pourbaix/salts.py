"""Experimental thermochemistry of the sink salts from the cached open tables.

Two routes, both fetched (cache files listed in the manifest), never typed:

- NIST-JANAF condensed-phase tables (janaf_<formula>.json): dfH, dfG and S at T.
- The NBS tables (Wagman et al. 1982) as OCR text of the scanned pages (nbs1982_ocr.json). A row
  is found by its formula as the OCR prints it, its state and its molar mass; its seven numeric
  columns (molar mass, dfH(0 K), dfH, dfG, H-H0, S, Cp) are read by position, a blank column
  being printed as a dash. Each row used here was checked against the page image in P0-W5.2
  (see NBS_ROWS); a parse that does not give exactly seven columns is refused.
"""
import re

from nacre.pourbaix import cache
from nacre.pourbaix import gas as gasmod

NBS_COLUMNS = ["molar_mass", "dfH0_kJ", "dfH_kJ", "dfG_kJ", "H_minus_H0_kJ", "S_J_per_K", "Cp_J_per_K"]
_BLANK = re.compile(r"^[-_—~=|‘'.:]+$")
_NUM = re.compile(r"^[~«-]?-?\d+(\.\d*)?$")

# formula -> (pdf page, OCR line prefix pattern, state, molar mass as printed, note)
NBS_ROWS = {
    "Ca(ClO4)2": (276, r"^Ca\(Cl[O0],\),", "cr", "238.9812",
                  "printed p. 2-268; dfH printed, dfG and S blank (checked against the page image)"),
    "AlCl3": (136, r"^A[Il]CL?,", "cr", "133.3405",
              "printed p. 2-128; all columns printed (checked against the page image)"),
}


class NotTabulated(KeyError):
    """The table has no usable value for this quantity."""


def _num(tok):
    tok = tok.lstrip("~«")
    return float(tok)


def nbs_row(formula, cache_dir=cache.CACHE_DIR):
    """Columns of one NBS row as a dict (None for a blank column), with its locator."""
    page, prefix, state, mass, note = NBS_ROWS[formula]
    doc = cache.load("nbs1982_ocr.json", cache_dir)
    text = doc["pages"][str(page)]["ocr_text"]
    for line in text.splitlines():
        line = line.strip()
        if not re.match(prefix, line):
            continue
        toks = line.split()
        try:
            i = toks.index(state)
        except ValueError:
            continue
        rest = [t for t in toks[i + 1:] if t]
        if not rest or rest[0].lstrip("«") != mass:
            continue
        cols = []
        for t in rest:
            if _BLANK.match(t):
                cols.append(None)
            elif _NUM.match(t):
                cols.append(_num(t))
            else:
                raise ValueError("unreadable token %r in NBS row %r" % (t, line))
        if len(cols) != len(NBS_COLUMNS):
            raise ValueError("NBS row %r gives %d columns, expected %d" % (line, len(cols), len(NBS_COLUMNS)))
        out = dict(zip(NBS_COLUMNS, cols))
        out["locator"] = "%s, pdf p. %d (%s), OCR line %r; %s" % (
            doc["request"]["url"], page, doc["pages"][str(page)]["printed_page"], line, note)
        out["pdf_sha256"] = doc["pdf_sha256"]
        return out
    raise NotTabulated("%s (%s) not found on NBS pdf p. %d" % (formula, state, page))


def janaf(formula, T, cache_dir=cache.CACHE_DIR):
    """dfH, dfG (kJ mol^-1) and S of a cached JANAF table at T."""
    return gasmod.row_kj(formula, T, cache_dir)


def dfh_kj(formula, T=298.15, cache_dir=cache.CACHE_DIR):
    """Experimental dfH (kJ mol^-1, 298.15 K) of a sink-related solid: JANAF first, then NBS."""
    if "janaf_%s.json" % formula in {f["file"] for f in cache.manifest(cache_dir)["files"]}:
        r = janaf(formula, T, cache_dir)
        return r["dfH_kJ_per_mol"], "NIST-JANAF %s, T = %s K" % (r["table"], T)
    if formula in NBS_ROWS:
        if abs(T - 298.15) > 1e-9:
            raise NotTabulated("NBS values are at 298.15 K only")
        r = nbs_row(formula, cache_dir)
        if r["dfH_kJ"] is None:
            raise NotTabulated("%s: dfH blank in the NBS table" % formula)
        return r["dfH_kJ"], r["locator"]
    raise NotTabulated(formula)

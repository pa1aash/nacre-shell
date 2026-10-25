"""The K1 cells the regime table states, shared by the figures that draw the K1 ladder (fig9, fig15)."""
import re

from nacre.figs import regimes

FRAMINGS = ("crystalline", "amorphous")
# Ladder phase of each regime-table row that carries K1 cells; the framing of a row with one word is read
# from its note. A row with two words ("crystalline; amorphous") covers both framings of its phase.
TABLE_K1_PHASE = {"hap": "HAp", "acp": "ACP", "btcp": "b-TCP", "atcp": "a-TCP", "ocp": "OCP", "brushite": "brushite",
                  "li_ortho": "Li3PO4", "ca_pyro": "Ca2P2O7", "ca_meta_crystal": "Ca(PO3)2 / Ca-polyphosphate glass",
                  "ca_meta_glass": "Ca(PO3)2 / Ca-polyphosphate glass", "al_ortho": "AlPO4", "al_meta": "Al(PO3)3",
                  "al_polyp": "Al-polyphosphate (R1 gel)", "lipo3n": "(LiPO3)n Hydro-Quebec film",
                  "baked": "baked aluminophosphate (Tsinghua)", "carbonate_ctl": "CaCO3"}
CLASSES = ("C_lo", "C_mid", "C_hi")


def table_k1(table, carbonate="CaCO3"):
    """{(ladder phase, framing): {class: registered word}} for every K1 cell the regime table states.

    The regime table is the authority on the K1 cells it carries (the amorphous cells excluded by the
    I17a bound are stated there and not in the ladder file); the ladder fills the cells it does not state.
    The carbonate control is keyed by `carbonate`.
    """
    out = {}
    for r in table["rows"]:
        if r["column"] not in CLASSES or r["row_id"] not in TABLE_K1_PHASE or not r["words"]:
            continue
        words = [w.strip() for w in r["words"].split(";")]
        phase = TABLE_K1_PHASE[r["row_id"]]
        if len(words) == 2:
            framings = FRAMINGS
        elif len(words) == 1:
            m = re.search(r"framing (crystalline|amorphous)", r["note"])
            if not m:
                raise ValueError("regime table row %s has one word and no framing in its note" % r["row_id"])
            framings = (m.group(1),)
        else:
            raise ValueError("regime table row %s column %s has %d words" % (r["row_id"], r["column"], len(words)))
        for fr, w in zip(framings, words):
            if w not in regimes.REGISTERED:
                raise ValueError("regime table word %r (row %s) is not a registered word" % (w, r["row_id"]))
            key = (carbonate if phase == "CaCO3" else phase, fr)
            out.setdefault(key, {})[r["column"]] = w
    return out

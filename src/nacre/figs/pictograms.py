"""Text-free structure pictograms for the TikZ schematics (Fig. 2, Fig. 3).

The default schematics carry no text at all (R7), so a structure cannot show its element
symbols. A pictogram is the RDKit structure of figures/rdkit/structures.yaml (same SMILES, same
2D coordinates) drawn as a skeleton: bonds as strokes, every atom that is not carbon as a disc
in its palette colour. Hydrogen is drawn only where the structure is water. Charges are not
drawn; the captions identify every state.

Writes figures/tikz/generated/pictograms.tex: colour definitions from palette.yaml and one TikZ
pic per structure, in units of one bond length (set the size with the pic's scale). Inside a
pic, the coordinate (-a<i>) is atom i of the RDKit molecule, so the schematics can place an ion
against a named oxygen. Regenerate with `nacre figs`; a test checks the file is current.
"""
import math
from pathlib import Path

from nacre.figs import paths, style
from nacre.figs import structures as S

PICTOGRAMS = ("catechol", "catecholate_dianion", "acetate", "oligomer_unit", "chitosan_unit", "water",
              "carbonate")
ELEMENTS = ("H", "C", "N", "O", "Al", "Ca")
OKABE = ("black", "orange", "skyblue", "bluishgreen", "yellow", "blue", "vermillion", "reddishpurple", "gray")
# Disc radii in bond lengths (house: large enough to read the colour at the pictogram scale,
# small enough that neighbouring discs do not touch).
RADIUS = {"H": 0.20, "default": 0.30}
INNER_OFFSET = 0.22    # second line of a ring double bond, towards the ring centre (bond lengths)
INNER_SHORTEN = 0.18   # each end of that line is shortened by this fraction of the bond
PAIR_OFFSET = 0.11     # half the separation of the two lines of a non-ring double bond
STUB = 0.55            # length of an attachment stub (bond lengths)
# Pictograms turned so that their binding oxygens (the terminal O atoms) point along +y from the
# centroid of all atoms; the pic then defines (-head) at the midpoint of those oxygens.
ORIENTED = ("catechol", "catecholate_dianion", "acetate", "oligomer_unit", "water")


def out_path(root):
    return paths(root)["root"] / "figures" / "tikz" / "generated" / "pictograms.tex"


def _colour_defs(root):
    pal = style.palette(root)
    lines = []
    for el in ELEMENTS:
        r, g, b = pal["elements"][el]["srgb"]
        lines.append("\\definecolor{el%s}{rgb}{%.4f,%.4f,%.4f}" % (el, r, g, b))
    for name in OKABE:
        r, g, b = pal["categorical"]["okabe_ito"][name]["srgb"]
        lines.append("\\definecolor{ok%s}{rgb}{%.4f,%.4f,%.4f}" % (name, r, g, b))
    return lines


def _geometry(name, root):
    """(atoms [(i, symbol, x, y)], bonds [(i, j, order, ring_centre or None)]) in bond lengths."""
    from rdkit import Chem
    from rdkit.Chem import rdDepictor
    mol = S.molecule(name, root)
    if name == "water":
        mol = Chem.AddHs(mol)
        rdDepictor.Compute2DCoords(mol)
    Chem.Kekulize(mol, clearAromaticFlags=True)
    conf = mol.GetConformer()
    pos = [conf.GetAtomPosition(i) for i in range(mol.GetNumAtoms())]
    lengths = [math.dist((pos[b.GetBeginAtomIdx()].x, pos[b.GetBeginAtomIdx()].y),
                         (pos[b.GetEndAtomIdx()].x, pos[b.GetEndAtomIdx()].y)) for b in mol.GetBonds()]
    unit = sum(lengths) / len(lengths)
    heavy = [p for a, p in zip(mol.GetAtoms(), pos) if a.GetAtomicNum() > 1]
    cx = sum(p.x for p in heavy) / len(heavy)
    cy = sum(p.y for p in heavy) / len(heavy)
    atoms = [(a.GetIdx(), a.GetSymbol() if a.GetAtomicNum() else "*", (pos[a.GetIdx()].x - cx) / unit,
              (pos[a.GetIdx()].y - cy) / unit) for a in mol.GetAtoms()]
    if name in ORIENTED:
        head = [a.GetIdx() for a in mol.GetAtoms() if a.GetSymbol() == "O"
                and sum(1 for nb in a.GetNeighbors() if nb.GetAtomicNum() > 1) <= 1]
        hx = sum(atoms[k][2] for k in head) / len(head)
        hy = sum(atoms[k][3] for k in head) / len(head)
        gx = sum(a[2] for a in atoms) / len(atoms)
        gy = sum(a[3] for a in atoms) / len(atoms)
        turn = math.pi / 2 - math.atan2(hy - gy, hx - gx)
        c, s_ = math.cos(turn), math.sin(turn)
        atoms = [(i, sy, x * c - y * s_, x * s_ + y * c) for i, sy, x, y in atoms]
        hx, hy = hx * c - hy * s_, hx * s_ + hy * c
        atoms.append((-1, "head", hx, hy))
    rings = mol.GetRingInfo().AtomRings()
    bonds = []
    for b in mol.GetBonds():
        i, j = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
        centre = None
        for ring in rings:
            if i in ring and j in ring:
                centre = (sum(atoms[k][2] for k in ring) / len(ring), sum(atoms[k][3] for k in ring) / len(ring))
                break
        bonds.append((i, j, int(b.GetBondTypeAsDouble()), centre))
    return atoms, bonds


def _line(a, b):
    return "\\draw[bond] (%.4f,%.4f) -- (%.4f,%.4f);" % (a[0], a[1], b[0], b[1])


def pic(name, root):
    """TikZ pic definition of one structure."""
    atoms, bonds = _geometry(name, root)
    xy = {i: (x, y) for i, _s, x, y in atoms if i >= 0}
    sym = {i: s for i, s, _x, _y in atoms if i >= 0}
    body = []
    for i, j, order, centre in bonds:
        a, b = xy[i], xy[j]
        if "*" in (sym[i], sym[j]):
            star, other = (a, b) if sym[i] == "*" else (b, a)
            dx, dy = star[0] - other[0], star[1] - other[1]
            n = math.hypot(dx, dy)
            body.append(_line(other, (other[0] + dx / n * STUB, other[1] + dy / n * STUB)))
            continue
        body.append(_line(a, b) if order != 2 or centre is None else _line(a, b))
        if order == 2:
            dx, dy = b[0] - a[0], b[1] - a[1]
            n = math.hypot(dx, dy)
            nx, ny = -dy / n, dx / n
            if centre is not None:
                mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                if (centre[0] - mx) * nx + (centre[1] - my) * ny < 0:
                    nx, ny = -nx, -ny
                s = INNER_SHORTEN
                p = (a[0] + dx * s + nx * INNER_OFFSET, a[1] + dy * s + ny * INNER_OFFSET)
                q = (b[0] - dx * s + nx * INNER_OFFSET, b[1] - dy * s + ny * INNER_OFFSET)
                body.append(_line(p, q))
            else:
                body[-1] = _line((a[0] + nx * PAIR_OFFSET, a[1] + ny * PAIR_OFFSET),
                                 (b[0] + nx * PAIR_OFFSET, b[1] + ny * PAIR_OFFSET))
                body.append(_line((a[0] - nx * PAIR_OFFSET, a[1] - ny * PAIR_OFFSET),
                                  (b[0] - nx * PAIR_OFFSET, b[1] - ny * PAIR_OFFSET)))
    for i, s, x, y in atoms:
        if s == "head":
            body.append("\\coordinate (-head) at (%.4f,%.4f);" % (x, y))
            continue
        body.append("\\coordinate (-a%d) at (%.4f,%.4f);" % (i, x, y))
        if s in ("C", "*"):
            continue
        r = RADIUS.get(s, RADIUS["default"])
        body.append("\\filldraw[atom, fill=el%s] (%.4f,%.4f) circle (%.3f);" % (s, x, y, r))
    key = name.replace("_", "")
    return "\\tikzset{pics/%s/.style={code={\n  %s\n}}}" % (key, "\n  ".join(body))


def text(root):
    s = style.applied(root)
    head = [
        "% Generated by nacre.figs.pictograms from figures/rdkit/structures.yaml and figures/style;",
        "% do not edit. Text-free structure pictograms for the TikZ schematics, one bond length = 1.",
        "% Strokes: applied.schematic_stroke (bonds, disc outlines), applied.schematic_stroke_bold (arrows).",
    ]
    head += _colour_defs(root)
    head.append("\\tikzset{bond/.style={line width=%gbp, line cap=round, draw=okblack},"
                % float(s["schematic_stroke"]["value"]))
    head.append("  atom/.style={line width=%gbp, draw=okblack}," % float(s["schematic_stroke"]["value"]))
    head.append("  thin/.style={line width=%gbp}," % float(s["schematic_stroke"]["value"]))
    head.append("  bold/.style={line width=%gbp}}" % float(s["schematic_stroke_bold"]["value"]))
    return "\n".join(head + [pic(n, root) for n in PICTOGRAMS]) + "\n"


def write(root):
    p = out_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text(root))
    return p

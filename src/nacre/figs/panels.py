"""Panel letters, placed outside the axes.

A letter is the axes' left title: above the plot area, left-aligned with its edge, so the
constrained layout reserves room for it and it never enters the data region. It is tagged
with gid PANEL_GID so the checker can tell it from a forbidden title.
"""
import string

PANEL_GID = "panel-letter"


def panel_letters(axes, start="a"):
    """Label each axes in order with a, b, c, ... (bold, lower case, from rsc.mplstyle)."""
    first = string.ascii_lowercase.index(start)
    out = []
    for i, ax in enumerate(axes):
        letter = string.ascii_lowercase[first + i]
        t = ax.set_title(letter, loc="left")
        t.set_gid(PANEL_GID)
        out.append(t)
    return out

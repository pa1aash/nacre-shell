"""Side-by-side contact sheet of transparent renders, for comparing compositions (local only).

    uv run python figures/blender/contact_sheet.py <out.png> <a.png> <b.png> ...

Each render is composited over a white page, scaled to a common height and placed left to
right with a gap. The sheet carries no text (R7): the order of the inputs is the key. It
is written under .local/ and never committed.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

HEIGHT = 900
GAP = 40


def sheet(paths, height=HEIGHT, gap=GAP):
    tiles = []
    for p in paths:
        im = Image.open(p).convert("RGBA")
        page = Image.new("RGBA", im.size, (255, 255, 255, 255))
        page.alpha_composite(im)
        w = round(im.width * height / im.height)
        tiles.append(page.convert("RGB").resize((w, height), Image.LANCZOS))
    out = Image.new("RGB", (sum(t.width for t in tiles) + gap * (len(tiles) + 1), height + 2 * gap),
                    (255, 255, 255))
    x = gap
    for t in tiles:
        out.paste(t, (x, gap))
        x += t.width + gap
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) < 2:
        raise SystemExit(__doc__)
    out = Path(argv[0])
    if ".local" not in out.parts:
        raise SystemExit("the contact sheet is local-only: write it under .local/")
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet(argv[1:]).save(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()

"""Colour-vision-deficiency simulations of rendered figures (colorspacious, severity 100)."""
import warnings

import numpy as np

CONDITIONS = {
    "deuteranopia": "deuteranomaly",
    "protanopia": "protanomaly",
    "tritanopia": "tritanomaly",
}
_CHUNK = 1 << 20


def simulate_rgb(rgb, condition):
    """rgb: float array (..., 3) in [0, 1]. Returns the simulated array, clipped to [0, 1]."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        from colorspacious import cspace_convert
    space = {"name": "sRGB1+CVD", "cvd_type": CONDITIONS[condition], "severity": 100}
    flat = rgb.reshape(-1, 3)
    out = np.empty_like(flat)
    for i in range(0, len(flat), _CHUNK):
        out[i:i + _CHUNK] = cspace_convert(flat[i:i + _CHUNK], space, "sRGB1")
    return np.clip(out, 0.0, 1.0).reshape(rgb.shape)


def simulate_png(src, out_dir, stem, dpi):
    """Write <stem>_<condition>.png for each condition; return the written paths."""
    from PIL import Image
    img = Image.open(src).convert("RGB")
    rgb = np.asarray(img, dtype=np.float64) / 255.0
    written = []
    for cond in CONDITIONS:
        sim = simulate_rgb(rgb, cond)
        out = out_dir / ("%s_%s.png" % (stem, cond))
        Image.fromarray(np.round(sim * 255.0).astype(np.uint8)).save(out, dpi=(dpi, dpi), optimize=False)
        written.append(out)
    return written

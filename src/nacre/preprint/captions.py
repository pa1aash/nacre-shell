"""One caption source (PH-W8.8): the figure captions of the paper are the W6 drafts in figures/src/captions,
translated to LaTeX by a fixed character map. The drafts are plain text with Unicode; number macros (\\NumX) pass through."""
import re

DRAFT_DIR = "figures/src/captions"
# figure id -> paper label of the figures the main text and SI use
USED = {"fig1": "fig:hero", "fig2": "fig:chain", "fig3": "fig:cycle", "fig4": "fig:si-retro", "fig7": "fig:si-carbonate",
        "fig10": "fig:si-dft", "fig11": "fig:si-window", "fig14": "fig:si-precision", "fig15": "fig:heatmap",
        "fig17": "fig:ladder"}

_CHEM = {"Ca²⁺": r"\ce{Ca^2+}", "CO₃²⁻": r"\ce{CO3^2-}", "Li⁺": r"\ce{Li+}", "ClO₄⁻": r"\ce{ClO4-}",
         "Al(OH)₃": r"\ce{Al(OH)3}", "CaCO₃": r"\ce{CaCO3}"}
_MATH = [("k_BT ln Ω_bulk", r"$\kB T\ln\Omb$"), ("ΔG_seq", r"$\DGseq$"), ("γ_sn", r"$\gsn$"), ("γ_sl", r"$\gsl$"),
         ("Ω_bulk = 1", r"$\Omb=1$"), ("Ω_bulk", r"$\Omb$"), ("E_ub", r"$E_\mathrm{ub}$"),
         ("Ca_T", r"$\mathrm{Ca_T}$"), ("C_T", r"$\mathrm{C_T}$"), ("P_T", r"$\mathrm{P_T}$"),
         ("4.4–4.5 V", r"\NumClassHiLow–\NumClassHiHigh"),   # class edges by macro (numbers come through macros only)
         ("α-TCP", r"$\alpha$-TCP"), ("β-TCP", r"$\beta$-TCP")]
_PLAIN = {"–": "--", "—": "---", "’": "'", "†": r"$^\dagger$"}   # † is the saturated-sink mark of the Results
# A cross key that names both conditions, "excluded (K2: ...; K1: thermodynamically excluded†)" (cp6 re-audit G4), is
# qualified by its own parenthesis and keeps the bare word.
QUALIFIED = r"(?! \((?:K2|\$K_2\$):)"


def draft_text(root, fig):
    """The caption paragraph of the draft, without its bold figure number."""
    text = (root / DRAFT_DIR / (fig + ".md")).read_text(encoding="utf-8")
    m = re.search(r"^\*\*Fig\. \d+\*\* (.+)$", text.split("## Draft", 1)[1], re.M)
    if not m:
        raise ValueError(fig + ": no '**Fig. N** ...' paragraph under '## Draft'")
    return m.group(1).strip()


def thermodynamic(text):
    """The class name 'excluded' is always the regime word (standing rule on the vocabulary)."""
    return re.sub(r"(?<!thermodynamically )\bexcluded\b" + QUALIFIED, "thermodynamically excluded", text)


def to_tex(text):
    out = thermodynamic(text)
    for src, dst in _CHEM.items():
        out = out.replace(src, dst)
    for src, dst in _MATH:
        out = out.replace(src, dst)
    out = re.sub(r"\bK([12])\b", r"$K_\1$", out)
    out = re.sub(r"(\\Num[A-Za-z]+) ", r"\1\\ ", out)  # a macro name swallows the space after it
    for src, dst in _PLAIN.items():
        out = out.replace(src, dst)
    left = sorted({c for c in out if ord(c) > 127})
    if left:
        raise ValueError("no LaTeX form for " + "".join(left))
    return out


def tex_caption(root, fig):
    return to_tex(draft_text(root, fig))


def paper_captions(root, files=("sections/introduction.tex", "sections/model.tex", "sections/results.tex", "si/main_si.tex")):
    """label -> caption body of every figure environment of the paper."""
    out = {}
    for f in files:
        text = (root / "preprint/paper" / f).read_text(encoding="utf-8")
        for m in re.finditer(r"\\begin\{(figure\*?)\}(.*?)\\end\{\1\}", text, re.S):
            body = m.group(2)
            start = body.index("\\caption{") + len("\\caption{")
            i, depth = start, 1
            while depth:
                depth += {"{": 1, "}": -1}.get(body[i], 0)
                i += 1
            out[re.search(r"\\label\{([^}]*)\}", body).group(1)] = body[start:i - 1].strip()
    return out


def expand_numbers(text, root):
    """Replace each \\NumX in a caption by the value and unit the generated macro prints."""
    numbers = (root / "preprint/generated/numbers.tex").read_text(encoding="utf-8")
    values = {}
    for m in re.finditer(r"\\newcommand\{\\(Num\w+)\}\{\\nacreNum\{([^}]*)\}\{(.*)\}\}\s*$", numbers, re.M):
        unit = re.sub(r"\\mathrm\{([^}]*)\}", r"\1", m.group(3))
        values[m.group(1)] = (m.group(2) + " " + unit).strip()
    return re.sub(r"\\(Num\w+)(?:\\ | |(?![A-Za-z]))", lambda m: values[m.group(1)] + " ", text)


def word_count(text, root):
    return len(expand_numbers(text, root).split())

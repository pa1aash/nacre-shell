"""The generated input tables: parameter table, benchmark table, SI reaction, database and conversion tables (cp6 F3, F4, F8)."""
import re

import yaml

from nacre.preprint import input_tables as it
from nacre.preprint import paths, refs
from preprint_helpers import REPO

GEN = paths.generated(REPO)


def _tex():
    return (GEN / it.OUT_TEX).read_text(encoding="utf-8")


def _body(name):
    tex = _tex()
    start = tex.index("\\newcommand{\\%s}" % name)
    return tex[start:tex.index("\n}\n", start)]


def test_committed_outputs_are_a_fresh_generation():
    assert it.check(REPO) == []


def test_no_digit_in_a_table_outside_macros_formulas_and_keys():
    for name in ("nacreParameterTable", "nacreBenchmarkTable", "nacreReactionTable", "nacreDftTable", "nacreConversionTable"):
        body = _body(name)
        body = re.sub(r"\\ce\{[^}]*\}|\\cite(?:num)?\{[^}]*\}|\\begin\{tabular\}\{.*\}|\\multicolumn\{\d+\}|\\addlinespace\[[^]]*\]"
                      r"|\\setlength\{[^}]*\}\{[^}]*\}|\\Num[A-Za-z]+\{\}|\\log_\{10\}|K_\\mathrm\{sp\}|\\mathrm\{kJ\\,mol\^\{-1\}\}"
                      r"|\(\\ce\{[^}]*\}\)\$_n\$", "", body)
        assert not re.search(r"[0-9]", body), (name, re.findall(r".{20}[0-9].{20}", body)[:3])


def test_table_two_carries_the_dissolution_inputs_with_cited_sources():
    body = _body("nacreParameterTable")
    keys = [k for _t, members in it.PARAM_GROUPS for _j, k, _s in members]
    rows = [l for l in body.splitlines() if l.endswith(" \\\\") and not l.startswith(("quantity", "\\multicolumn"))]
    assert len(keys) == 17 and len(rows) == len(keys)
    bib = refs.source(REPO).read_text(encoding="utf-8")
    assert re.findall(r"\\citenum\{([^}]*)\}", body)
    for key in re.findall(r"\\citenum\{([^}]*)\}", body):
        for k in key.split(","):
            assert re.search(r"@\w+\{%s," % re.escape(k), bib), k


def test_table_three_names_the_governing_reaction_or_why_there_is_none():
    body = _body("nacreBenchmarkTable")
    rows = [l for l in body.splitlines() if l.endswith(" \\\\") and not l.startswith(("phase", "\\multicolumn"))]
    assert rows and all(("\\ce{" in r and "->" in r) or "undetermined:" in r for r in rows)
    assert "calcium carbonate (control)" in body and "(comparator)" not in body


def test_speciation_follows_the_registered_acid_constants():
    p = yaml.safe_load((REPO / it.INPUTS["params"]).read_text(encoding="utf-8"))["params"]
    k2 = p["pk2_carbonic"]["value"]
    a3 = p["pka3_h3po4"]["value"]
    lo = p["ph_slurry"]["range"]["min"]
    nums = {n.name: n.value for n in it.speciation(it.read_inputs(REPO)[0])}
    # the leading term alone: CO3^2- / (CO3^2- + HCO3-) and PO4^3- / (PO4^3- + HPO4^2-)
    assert abs(nums["NumSpecCarbonateLow"] - 100 / (1 + 10 ** (k2 - lo))) < 0.1
    assert abs(nums["NumSpecPhosphateLow"] - 100 / (1 + 10 ** (a3 - lo))) < 0.01
    assert nums["NumSpecCarbonateLow"] > nums["NumSpecPhosphateLow"]
    assert nums["NumSpecPhosphateMid"] > 100 * nums["NumSpecPhosphateLow"] / 100


def test_methods_sets_both_tables_and_no_pending_marker():
    methods = (paths.paper(REPO) / "sections" / "methods.tex").read_text(encoding="utf-8")
    for doc in ("main.tex", "si/main_si.tex"):
        assert "\\input{../generated/input_tables}" in (paths.paper(REPO) / doc).read_text(encoding="utf-8"), doc
    assert "\\nacreParameterTable" in methods and "\\nacreBenchmarkTable" in methods
    assert "parameter table generated from the parameter file" not in methods
    assert "benchmark table generated from the benchmark file" not in methods


def test_methods_and_table_three_cite_the_tabulated_data_sources():
    """PH-W8.9 (G2): NIST-JANAF and the NBS Selected Values volumes the SI cites are cited in the main text, in Methods
    'Oxidation onsets' and in the Table 3 caption."""
    bib = refs.source(REPO).read_text(encoding="utf-8")
    janaf = re.search(r"@\w+\{([^,]+),[^@]*doi=\{10\.18434/t42s31\}", bib, re.I).group(1)
    si = (paths.paper(REPO) / "si" / "main_si.tex").read_text(encoding="utf-8")
    nbs = sorted({k for c in re.findall(r"\\cite\{([^}]*)\}", si) for k in c.split(",")
                  if re.search(r"@\w+\{%s,[^@]*10\.6028/nbs" % re.escape(k), bib)})
    assert nbs
    methods = (paths.paper(REPO) / "sections" / "methods.tex").read_text(encoding="utf-8")
    onsets = methods[methods.index("\\paragraph*{Oxidation onsets.}"):]
    onsets = onsets[:onsets.index("\n\n")]
    caption = methods[methods.index("\\caption{Thermochemistry benchmark"):methods.index("\\label{tab:thermo}")]
    for part in (onsets, caption):
        cited = {k for c in re.findall(r"\\cite\{([^}]*)\}", part) for k in c.split(",")}
        assert janaf in cited and set(nbs) <= cited, (cited, janaf, nbs)


def test_carbonate_rows_read_the_ksp_keys_that_k2_binds():
    """PH-W8.9 (G3): the aragonite row read the superseded key; every carbonate row of Table 2 now reads the K_sp key
    that the dissolution test binds in screen.yaml, and the generator refuses a row that does not."""
    import copy

    import pytest

    from nacre.screen import k2_carbonate
    docs, _ = it.read_inputs(REPO)
    bound = k2_carbonate.ksp_keys(docs["screen"])
    assert bound["aragonite"] == "log10_ksp_aragonite_25c_i0"
    table = {pkey for _t, members in it.PARAM_GROUPS for _j, pkey, _s in members}
    assert set(bound.values()) <= table and "log10_ksp_aragonite" not in table
    it.check_k2_keys(docs["screen"])
    stale = copy.deepcopy(docs["screen"])
    stale["bindings"]["R-slurry"]["by_framing"]["aragonite"]["K_sp"] = "log10_ksp_aragonite"
    with pytest.raises(it.InputTableError, match="aragonite"):
        it.check_k2_keys(stale)
    row = next(l for l in _body("nacreParameterTable").splitlines() if l.startswith("solubility product, aragonite"))
    assert "uniform" in row and "& C &" in row and "\\citenum{ball1991users}" in row and "fixed" not in row
    assert re.search(r"@\w+\{ball1991users,[^@]*10\.3133/ofr91183", refs.source(REPO).read_text(encoding="utf-8"), re.I)

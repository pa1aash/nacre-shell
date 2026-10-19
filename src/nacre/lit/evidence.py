"""Evidence-table schema, validator, thread merge and coverage (lit/corpus/README.md defines the columns).

validate_rows() returns a list of "row_id: problem" strings; an empty list means the table is valid.
"""
import csv
import io
import re
from pathlib import Path

from nacre.retrieval import record as R

COLUMNS = ["row_id", "thread", "doi", "locator", "quantity", "symbol", "value", "unit",
           "range_or_uncertainty", "conditions", "method", "grade", "extraction_route", "retrieved_at",
           "contrary", "retro_candidate", "notes"]
THREADS = ("T-A", "T-B", "T-C", "T-D", "T-E", "T-F", "T-G", "T-H", "T-I", "T-J", "T-K",
           "T-L", "T-M", "T-N", "T-O", "T-P", "T-Q")
GRADES = ("A", "B", "C", "D")
ROUTES = ("full text", "SI", "abstract")
METHODS = ("experiment", "computation", "compilation")
QUALITATIVE = "qualitative"

_ROW_ID = re.compile(r"^T[A-Q]-\d{3}$")
_DOI = re.compile(r"^10\.\d{4,9}/\S+$")
_SLUG = re.compile(r"^[a-z][a-z0-9_]*$")
_NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"
_VALUE = re.compile(r"^(?:<=|>=|<|>|≤|≥)?\s*%s$" % _NUM)
_RANGE = re.compile(r"^(?:±\s*%s%%?|\+%s\s*/\s*-%s|%s\s*\.\.\s*%s)$" % ((_NUM,) * 5))
_LOCATOR = re.compile(r"(\bp\.|\bpp\.|\bpage\b|\btable\b|\bfig|\beq|\bsection\b|\bsec\.|\bscheme\b|\babstract\b|\bSI\b|\bS\d)",
                      re.I)
_WHEN = re.compile(r"^\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2})?Z)?$")
_QUOTE = re.compile(r"[\"“]([^\"”]*)[\"”]")

_ureg = None


def ureg():
    global _ureg
    if _ureg is None:
        import pint

        _ureg = pint.UnitRegistry()
    return _ureg


def unit_ok(unit):
    if not unit or not unit.strip():
        return False
    if unit in ("1", "dimensionless"):
        return True
    try:
        ureg().parse_units(unit)
        return True
    except Exception:
        try:
            q = ureg().parse_expression(unit)
            return hasattr(q, "units") and float(getattr(q, "magnitude", 1)) == 1.0
        except Exception:
            return False


def number_range(text):
    """'lo..hi' -> (lo, hi) or None."""
    m = re.match(r"^\s*(%s)\s*\.\.\s*(%s)\s*$" % (_NUM, _NUM), text or "")
    return (float(m.group(1)), float(m.group(2))) if m else None


def scope_patterns(root):
    """Forbidden-claim regexes from charter/scope_guard.md (the ```scope-guard block)."""
    path = Path(root) / "charter" / "scope_guard.md"
    if not path.exists():
        return []
    m = re.search(r"```scope-guard\n(.*?)```", path.read_text(encoding="utf-8"), re.S)
    out = []
    for line in (m.group(1) if m else "").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            pid, rx = line.split(None, 1)
            out.append((pid, re.compile(rx, re.I)))
    return out


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        header = reader.fieldnames or []
        return header, list(reader)


def write_csv(path, rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in COLUMNS})
    Path(path).write_text(buf.getvalue(), encoding="utf-8")


def validate_row(r, patterns=()):
    rid = r.get("row_id") or "?"
    errs = []

    def bad(msg):
        errs.append("%s: %s" % (rid, msg))

    if not _ROW_ID.match(rid):
        bad("row_id must look like TA-001")
    if r.get("thread") not in THREADS:
        bad("thread %r not in %s" % (r.get("thread"), THREADS))
    elif _ROW_ID.match(rid) and rid[:2] != r["thread"].replace("-", ""):
        bad("row_id prefix does not match thread")
    doi = (r.get("doi") or "").strip()
    if not _DOI.match(doi) or R.normalize_doi(doi) != doi.lower():
        bad("DOI syntax: %r" % doi)
    loc = (r.get("locator") or "").strip()
    if not loc:
        bad("locator missing")
    elif not _LOCATOR.search(loc):
        bad("locator %r names no page, table, figure, equation, section, SI item or abstract" % loc)
    if not _SLUG.match(r.get("quantity") or ""):
        bad("quantity must be a lower-case slug")
    unit = (r.get("unit") or "").strip()
    value = (r.get("value") or "").strip()
    rng = (r.get("range_or_uncertainty") or "").strip()
    if unit == QUALITATIVE:
        if not value:
            bad("qualitative row needs a value (the observed outcome)")
    else:
        if not unit_ok(unit):
            bad("unit does not parse: %r" % unit)
        if value and not _VALUE.match(value):
            bad("value is not numeric: %r" % value)
        if rng and not _RANGE.match(rng):
            bad("range_or_uncertainty not one of ±x, ±x%%, +a/-b, lo..hi: %r" % rng)
        if not value and not number_range(rng):
            bad("quantity row needs a numeric value or a lo..hi range")
    if not (r.get("conditions") or "").strip():
        bad("conditions missing (write n.s. for each unstated item)")
    method = (r.get("method") or "").strip()
    if not method.split(":")[0].strip() in METHODS:
        bad("method must start with experiment, computation or compilation: %r" % method)
    grade = r.get("grade")
    if grade not in GRADES:
        bad("grade %r not in A-D" % grade)
    route = r.get("extraction_route")
    if route not in ROUTES:
        bad("extraction_route %r not in %s" % (route, ROUTES))
    if route == "abstract" and grade in ("A", "B", "C"):
        bad("abstract-only rows are capped at grade D")
    if method.startswith("compilation") and grade in ("A", "B"):
        bad("a compilation (secondary citation) is graded C at best")
    if not _WHEN.match(r.get("retrieved_at") or ""):
        bad("retrieved_at must be an ISO date or UTC timestamp")
    if r.get("contrary") not in ("y", "n"):
        bad("contrary must be y or n")
    retro = (r.get("retro_candidate") or "").strip()
    if not (retro == "n" or re.match(r"^y:\s*\S", retro)):
        bad("retro_candidate must be n or 'y: <observed outcome>'")
    for field in ("notes", "conditions", "method", "value"):
        for q in _QUOTE.findall(r.get(field) or ""):
            if len(q.split()) >= 15:
                bad("quote in %s has %d words (limit 14)" % (field, len(q.split())))
    text = " ".join(str(r.get(k) or "") for k in COLUMNS)
    for pid, rx in patterns:
        if rx.search(text):
            bad("matches scope-guard pattern %s" % pid)
    return errs


def validate_rows(rows, header=None, patterns=()):
    errs = []
    if header is not None and list(header) != COLUMNS:
        errs.append("header: expected %s, got %s" % (",".join(COLUMNS), ",".join(header)))
    seen = set()
    for r in rows:
        rid = r.get("row_id")
        if rid in seen:
            errs.append("%s: duplicate row_id" % rid)
        seen.add(rid)
        errs.extend(validate_row(r, patterns))
    return errs


def validate_file(path, root=None):
    header, rows = read_csv(path)
    return validate_rows(rows, header, scope_patterns(root) if root else ())


def _norm_locator(loc):
    return " ".join(re.sub(r"[^a-z0-9.]+", " ", (loc or "").lower()).split())


def _norm_text(s):
    return " ".join((s or "").lower().split())


def _d1_value(r):
    """The value part of the D1 key: the printed value, or the lo..hi range of a range-only row."""
    return r["value"].strip() or r["range_or_uncertainty"].strip()


def merge(thread_rows):
    """thread_rows: iterable of row lists in thread order. Dedupe on doi + locator + quantity.

    One table often prints several values of one quantity (pKa1 and pKa2, one constant per
    species), so a numeric row is a duplicate only when symbol and value also agree (decision D1:
    doi + locator + quantity + symbol + value). A
    qualitative row is a duplicate when another thread already recorded the same doi + locator +
    quantity (two threads reading the same observation); within a thread such rows are distinct
    observations. Returns (merged_rows, duplicates) with duplicates as (dropped_row_id, kept_row_id).
    """
    kept, index, base, dups = [], {}, {}, []
    for rows in thread_rows:
        for r in rows:
            k0 = (r["doi"].lower(), _norm_locator(r["locator"]), r["quantity"])
            if r["unit"] == QUALITATIVE:
                hit = next((rid for rid, thread in base.get(k0, []) if thread != r["thread"]), None)
            else:
                hit = index.get(k0 + (_norm_text(r["symbol"]), _d1_value(r)))
            if hit:
                dups.append((r["row_id"], hit))
                continue
            if r["unit"] != QUALITATIVE:
                index[k0 + (_norm_text(r["symbol"]), _d1_value(r))] = r["row_id"]
            base.setdefault(k0, []).append((r["row_id"], r["thread"]))
            kept.append(r)
    return kept, dups


# ---- target quantities ----------------------------------------------------------------------
# barrier: DG*_het = f(theta) * 16 pi gamma_nw^3 v^2 / (3 (kT ln S)^2), v = V_m / N_A,
# cos theta = (gamma_sw - gamma_sn) / gamma_nw. `role` states where each quantity enters;
# `rank` orders gaps by expected physical leverage (lower is larger).
TARGETS = [
    {"id": "gamma_nuc_water_acc", "label": "ACC-water interfacial free energy", "slugs": ["gamma_acc_water"],
     "rank": 1, "role": "gamma_nw in the barrier prefactor (cubed) and in the Young denominator; ACC framing"},
    {"id": "gamma_nuc_water_calcite", "label": "calcite-water interfacial free energy",
     "slugs": ["gamma_calcite_water"], "rank": 1,
     "role": "gamma_nw in the barrier prefactor (cubed) and in the Young denominator; calcite framing"},
    {"id": "gamma_sub_nuc_or_contact_angle", "label": "substrate-nucleus interfacial energy or measured contact angle",
     "slugs": ["gamma_sub_nuc", "contact_angle_caco3", "gamma_eff_het"], "rank": 2,
     "role": "sets theta through Young and hence f(theta), which multiplies the whole barrier (f ~ theta^4 at small theta)"},
    {"id": "gamma_sub_water_oxide", "label": "hydroxylated alumina or oxyhydroxide-water interfacial energy",
     "slugs": ["gamma_oxide_water"], "rank": 3, "role": "gamma_sw in the Young numerator (bare-oxide control)"},
    {"id": "gamma_sub_water_organic", "label": "catechol- or carboxyl-bearing surface-water interfacial energy",
     "slugs": ["gamma_organic_water"], "rank": 3, "role": "gamma_sw in the Young numerator (templated substrate)"},
    {"id": "molar_volume_calcite", "label": "molar volume of calcite", "slugs": ["molar_volume_calcite"],
     "rank": 4, "role": "v in the barrier prefactor (squared)"},
    {"id": "molar_volume_acc", "label": "molar volume of ACC", "slugs": ["molar_volume_acc"],
     "rank": 4, "role": "v in the barrier prefactor (squared), ACC framing"},
    {"id": "ksp_calcite", "label": "solubility product of calcite", "slugs": ["ksp_calcite"], "rank": 5,
     "role": "ln S = ln(a_Ca a_CO3 / Ksp); ln S enters squared in the denominator"},
    {"id": "ksp_acc", "label": "solubility product of ACC", "slugs": ["ksp_acc"], "rank": 5,
     "role": "ln S for the ACC framing (squared in the denominator)"},
    {"id": "acc_excess_free_energy", "label": "ACC excess free energy relative to calcite",
     "slugs": ["acc_excess_free_energy"], "rank": 5,
     "role": "shifts ln S between framings by -Delta_mu/kT (squared in the denominator)"},
    {"id": "dg_ca_catecholate", "label": "Ca2+-catecholate binding free energy or constant",
     "slugs": ["dg_bind_ca_catecholate", "logk_ca_catecholate"], "rank": 6,
     "role": "Delta_G_seq: local enrichment adds -Delta_G_seq/RT to ln S (C2)"},
    {"id": "dg_ca_carboxylate", "label": "Ca2+-carboxylate binding free energy or constant",
     "slugs": ["dg_bind_ca_carboxylate", "logk_ca_carboxylate"], "rank": 6,
     "role": "Delta_G_seq of the carboxylate control: enrichment term in ln S (C2)"},
    {"id": "ksp_aragonite", "label": "solubility product of aragonite", "slugs": ["ksp_aragonite"], "rank": 7,
     "role": "ln S for a sensitivity polymorph (squared in the denominator)"},
    {"id": "ksp_vaterite", "label": "solubility product of vaterite", "slugs": ["ksp_vaterite"], "rank": 7,
     "role": "ln S for a sensitivity polymorph (squared in the denominator)"},
    {"id": "slurry_ph", "label": "slurry pH", "slugs": ["slurry_ph"], "rank": 8,
     "role": "carbonate speciation (a_CO3 in ln S), catechol protonation, oxide hydroxylation, Pourbaix axis"},
    {"id": "slurry_dic", "label": "slurry dissolved inorganic carbon", "slugs": ["slurry_dic"], "rank": 8,
     "role": "a_CO3 in ln S (logarithmic)"},
    {"id": "slurry_ca", "label": "slurry Ca concentration", "slugs": ["slurry_ca"], "rank": 8,
     "role": "a_Ca in ln S (logarithmic)"},
    {"id": "slurry_ionic_strength", "label": "slurry ionic strength", "slugs": ["slurry_ionic_strength"], "rank": 9,
     "role": "activity coefficients in ln S and screening in Delta_G_seq"},
    {"id": "hydration_free_energy_ca", "label": "Ca2+ hydration free energy", "slugs": ["hydration_free_energy_ca"],
     "rank": 9, "role": "reference state of the Delta_G_seq cycle (C2); benchmark for computed binding"},
    {"id": "pka_catechol", "label": "catechol pKa", "slugs": ["pka_catechol"], "rank": 9,
     "role": "protonation correction in Delta_G_seq at the slurry pH (C2) and binding mode in C1"},
    {"id": "site_density_organic", "label": "binding-site density on the organic layer",
     "slugs": ["site_density_organic"], "rank": 9,
     "role": "converts site free energy to a local concentration (C2 -> S); template coverage (C4)"},
    {"id": "w_adh_catechol_alumina_wet", "label": "work of adhesion of catechol or PDA to alumina in water",
     "slugs": ["w_adh_wet"], "rank": 10, "role": "C1 kill criterion; not in the nucleation barrier"},
    {"id": "incell_potential_range", "label": "in-cell potential range at the collector",
     "slugs": ["incell_potential"], "rank": 10, "role": "R-cell window (C5); not in the nucleation barrier"},
    # day 4 targets (P0-W1.4): post-cp3 keys, d_max inputs, R-cell budgets and the Outlook evidence
    {"id": "water_activity_drying_primary", "label": "water activity in primary (convective) film drying",
     "slugs": ["water_activity_drying_primary"], "rank": 9, "role": "a_w of the primary drying state (F7) in ln S"},
    {"id": "pvdf_surface_energy", "label": "dry surface free energy of PVDF", "slugs": ["pvdf_surface_energy_total"],
     "rank": 10, "role": "PVDF control of the deletion test; not in the template's nucleation barrier"},
    {"id": "cathode_particle_diameter", "label": "cathode secondary-particle diameter",
     "slugs": ["cathode_particle_diameter", "cathode_particle_d50"], "rank": 10,
     "role": "upper bound pi d_p^2/4 of A_patch (C3 b)"},
    {"id": "asperity_contact_area", "label": "asperity contact area of a particle on the foil",
     "slugs": ["asperity_contact_area", "particle_collector_contact_radius"], "rank": 10,
     "role": "lower bound of A_patch (C3 b)"},
    {"id": "template_mass_per_group", "label": "template molar mass per coordinating group",
     "slugs": ["template_mass_per_group"], "rank": 10, "role": "stoichiometric bound on rho_L (Gamma_s cap)"},
    {"id": "ca_ionic_radius", "label": "Ca2+ ionic radius", "slugs": ["ca_ionic_radius"], "rank": 10,
     "role": "site footprint and the 2 r_Ca term of the delta_s bound"},
    {"id": "film_tunnelling_inputs", "label": "CaCO3 film resistivity and tunnelling inputs",
     "slugs": ["resistivity_caco3", "electron_affinity_caco3", "effective_mass_caco3", "tunnel_prefactor_j0"],
     "rank": 10, "role": "d_max of the C4 closure route (R-cell)"},
    {"id": "reduction_limit_thermochemistry", "label": "formation Gibbs energies of the reduction-limit products",
     "slugs": ["dfg_li2co3", "dfg_lial5o8"], "rank": 10, "role": "C5c_red limits and their budget keys"},
    {"id": "al_perchlorate_thermochemistry", "label": "Al(ClO4)3 formation enthalpy and Gibbs energy",
     "slugs": ["dfh_al_clo4_3", "dfg_al_clo4_3"], "rank": 10, "role": "C5c_ox sink of corundum and boehmite"},
    {"id": "anion_anodic_stability", "label": "anodic stability of other biominerals' anions",
     "slugs": ["stability_window"], "rank": 11, "role": "Outlook sentence only; not a screen input"},
]


def coverage(rows):
    """Coverage status per target: covered (>=2 distinct DOIs), single-source or gap."""
    out = []
    for t in TARGETS:
        hits = [r for r in rows if r["quantity"] in t["slugs"] and r["unit"] != QUALITATIVE]
        dois = sorted({r["doi"].lower() for r in hits})
        status = "covered" if len(dois) >= 2 else ("single-source" if dois else "gap")
        grades = {g: sum(1 for r in hits if r["grade"] == g) for g in GRADES}
        out.append({"id": t["id"], "label": t["label"], "slugs": t["slugs"], "status": status,
                    "independent_sources": len(dois), "grades": grades,
                    "best_grade": next((g for g in GRADES if grades[g]), None),
                    "row_ids": [r["row_id"] for r in hits], "dois": dois,
                    "rank": t["rank"], "role": t["role"]})
    return out

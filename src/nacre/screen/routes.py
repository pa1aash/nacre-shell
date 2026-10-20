"""Extension points of the route layer (in-situ polyphosphate films): named, documented, NOT implemented.

The route layer is a set of films formed in place: Al3+-triggered gelation of a polyphosphate and a Ca-polyphosphate
coacervate that dries to an amorphous glass. W3 derives its evaluators later (theory/claims_redirect.md will gain
the sections); PH-W4.1 only makes the code ready to receive them. Each function below has the arguments the
evaluator is expected to take, documents what it must return, and raises NotImplementedError. The K evaluators of
nacre.screen.kscreen call ``pending_for`` to list, beside every result, which of these a mineral still needs.

Contract for an implementation, common to all three:
    * the return value is a record with a ``verdict`` in (feasible, falsified, inconclusive) from the shared
      band-mass rule (nacre.screen.decision.verdict_from_mass) at p_cred, on draws that share their inputs with
      the solid-like evaluators;
    * a draw outside the admissible set is refused and counted, never clipped (D27);
    * nothing here sets a prior, a threshold or a margin; margins come from configs/preprint/screen.yaml k_screen.
"""

NAMES = ("liquid_precursor_wetting", "formation_accessibility", "hydrolysis_descriptor")


def liquid_precursor_wetting(mineral, samples, p_cred, m_S=None, **inputs):
    """Wetting of a liquid precursor (coacervate) on the Al oxide: replaces K4's solid-like S_spread for
    ``phase_state == "liquid_precursor"``.

    Expected inputs: the liquid-precursor / water, precursor / oxide and oxide / water interfacial energies and
    the precursor viscosity at the drying state. Expected output: the spreading record
    {verdict, P_good, P_bad, quantity, edge, notes} for the film that dries from it.
    """
    raise NotImplementedError("route evaluator liquid_precursor_wetting is not implemented (PH-W3.2a derives it)")


def formation_accessibility(mineral, samples, p_cred, **inputs):
    """Accessibility of in-situ formation: whether the film-forming reaction (Al3+-triggered gelation, Ca-polyphosphate
    coacervation) proceeds at the registered dose, pH and ionic strength within the processing time.

    Replaces K3's nucleation window for a route whose phase is formed by gelation or coacervation, not by
    nucleation. Expected output: {verdict, window, falsified_doses, notes} along the dose axis of K3.
    """
    raise NotImplementedError("route evaluator formation_accessibility is not implemented (PH-W3.2a derives it)")


def hydrolysis_descriptor(mineral, samples, **inputs):
    """Hydrolysis of a condensed phosphate (chain length ``mineral.chain_length_n``) at the slurry pH and drying
    state: a DESCRIPTOR (reported, never decisive), like adhesion and Ca binding.

    Expected output: {descriptor: half-life or fraction hydrolysed, chain_length_n, notes}.
    """
    raise NotImplementedError("route descriptor hydrolysis_descriptor is not implemented (PH-W3.2a derives it)")


ROUTE_EVALUATORS = {"liquid_precursor_wetting": liquid_precursor_wetting,
                    "formation_accessibility": formation_accessibility,
                    "hydrolysis_descriptor": hydrolysis_descriptor}


def pending_for(mineral):
    """The extension points a mineral needs before its route is evaluated (empty for a solid-like nucleus)."""
    out = []
    if mineral.phase_state == "liquid_precursor":
        out += ["liquid_precursor_wetting", "formation_accessibility"]
    if mineral.chain_length_n is not None:
        if "formation_accessibility" not in out:
            out.append("formation_accessibility")
        out.append("hydrolysis_descriptor")
    return out

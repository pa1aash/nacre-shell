"""Per-link threshold evaluator (interface only).

Thresholds and the decision rule on the propagated distributions are frozen in P0-W4.2,
written from physics before any screen runs (rule R7). Until then this module defines the
interface and refuses to evaluate, so no verdict can be produced from an unfrozen rule.

Interface
    load_thresholds(path) -> dict
        Read the frozen per-link thresholds (configs/preprint/thresholds.yaml, written in
        W4.2) with their physical justification and freeze commit.
    evaluate_link(link, samples, thresholds) -> dict
        Fraction of prior-weighted mass of the link's decisive quantity in each verdict
        band (feasible / inconclusive / falsified) and the registered statistic; the
        result fills ``threshold_evaluation`` of the link in the results summary.
"""


class ThresholdsNotFrozen(RuntimeError):
    """Raised by every evaluator call until the thresholds are frozen (P0-W4.2)."""


_MESSAGE = ("per-link thresholds are not frozen: they are written from physics in P0-W4.2 "
            "before any screen runs")


def load_thresholds(path):
    """Load the frozen per-link thresholds from path. Not available before P0-W4.2."""
    raise ThresholdsNotFrozen(_MESSAGE)


def evaluate_link(link, samples, thresholds):
    """Verdict-band masses of one link's decisive quantity. Not available before P0-W4.2."""
    raise ThresholdsNotFrozen(_MESSAGE)

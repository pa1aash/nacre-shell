"""Command line of the screen: ``python -m nacre.screen smoke --mock``."""
import argparse
import sys
from pathlib import Path

from nacre._util import repo_root
from nacre.screen import smoke
from nacre.screen.priors import MockPriorsRefused

DEFAULT_PRIORS = Path("configs") / "preprint" / "mock_priors.yaml"
DEFAULT_OUT = Path("results") / "preprint" / "screen" / "mock" / "summary.json"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m nacre.screen")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sm = sub.add_parser("smoke", help="smoke run on mock priors")
    sm.add_argument("--priors", default=str(DEFAULT_PRIORS))
    sm.add_argument("--out", default=str(DEFAULT_OUT))
    sm.add_argument("--mock", action="store_true", help="allow a prior file marked mock: true")
    sm.add_argument("--draws", type=int, default=4096)
    sm.add_argument("--sobol-base", type=int, default=512)
    sm.add_argument("--bootstrap", type=int, default=200)
    sm.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)
    root = repo_root()
    try:
        path, _ = smoke.run(root, root / args.priors, root / args.out, draws=args.draws,
                            sobol_base=args.sobol_base, bootstrap=args.bootstrap, seed=args.seed,
                            allow_mock=args.mock)
    except MockPriorsRefused as exc:
        print("refused: %s" % exc, file=sys.stderr)
        return 2
    print("wrote %s" % path.relative_to(root))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""pre-merge-commit: attribution scan and identity check only."""
import sys

import _scan


def main():
    failures = 0
    for problem in _scan.identity_problems():
        _scan.report("identity", "git config", None, problem)
        failures += 1
    failures += _scan.scan_staged()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

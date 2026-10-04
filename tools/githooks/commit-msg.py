"""commit-msg: reject banned strings and trailer lines in the message."""
import sys

import _scan


def main(argv):
    with open(argv[1], encoding="utf-8", errors="replace") as fh:
        message = fh.read()
    return 1 if _scan.check_message(message, "commit message") else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

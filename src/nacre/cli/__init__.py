"""The nacre command line.

Subcommands are discovered, so parallel lanes never edit this file:
  - nacre/cli/commands/<name>.py with `register(subparsers)`;
  - nacre/<pkg>/cli.py with `register(subparsers)` for every subpackage.
A discovery failure prints a warning and continues.
"""
import argparse
import importlib
import pkgutil
import sys

import nacre


def _warn(msg):
    print("warning: " + msg, file=sys.stderr)


def _discover(subparsers):
    from nacre.cli import commands
    for info in pkgutil.iter_modules(commands.__path__):
        name = "nacre.cli.commands." + info.name
        try:
            importlib.import_module(name).register(subparsers)
        except Exception as exc:
            _warn("command module %s failed to load: %s" % (name, exc))
    for info in pkgutil.iter_modules(nacre.__path__):
        if not info.ispkg or info.name == "cli":
            continue
        name = "nacre.%s.cli" % info.name
        try:
            mod = importlib.import_module(name)
        except ModuleNotFoundError as exc:
            if exc.name != name:
                _warn("%s failed to load: %s" % (name, exc))
            continue
        except Exception as exc:
            _warn("%s failed to load: %s" % (name, exc))
            continue
        register = getattr(mod, "register", None)
        if register is None:
            continue
        try:
            register(subparsers)
        except Exception as exc:
            _warn("%s register failed: %s" % (name, exc))


def build_parser():
    parser = argparse.ArgumentParser(prog="nacre", description="Nacre Shell repository tooling.")
    subparsers = parser.add_subparsers(dest="command", metavar="<command>")
    _discover(subparsers)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 2
    rc = func(args)
    sys.exit(rc or 0)

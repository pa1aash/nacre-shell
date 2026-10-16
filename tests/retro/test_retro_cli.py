"""`nacre retro check` (lane p0-w2)."""
import argparse

from nacre.retro import cli


def test_retro_check_command_passes_on_committed_files(capsys):
    parser = argparse.ArgumentParser()
    cli.register(parser.add_subparsers(dest="command"))
    args = parser.parse_args(["retro", "check"])
    assert args.func(args) == 0
    out = capsys.readouterr().out
    assert "retro check: PASS" in out
    assert "k = 10 of N = 12" in out

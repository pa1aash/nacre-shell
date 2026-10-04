"""Full-history backstop scan, run in CI.

Checks every commit message and identity, every annotated tag, and every text
blob reachable from any ref, against rules R1 and R2.
"""
import subprocess
import sys

import _scan

SYNTHETIC_MERGE_COMMITTER = "noreply@github.com"


def blobs(objects):
    """Yield (sha, type, data) for the given object ids using one cat-file process."""
    proc = subprocess.Popen(["git", "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    for sha in objects:
        proc.stdin.write((sha + "\n").encode())
        proc.stdin.flush()
        header = proc.stdout.readline().decode().split()
        if len(header) != 3:
            continue
        data = proc.stdout.read(int(header[2]))
        proc.stdout.read(1)
        yield header[0], header[1], data
    proc.stdin.close()
    proc.wait()


def main():
    failures = 0
    commits = _scan.git_out("rev-list", "--all").split()
    for sha in commits:
        short = sha[:12]
        _, ids = _scan.git("show", "-s", "--format=%an%x00%ae%x00%cn%x00%ce%x00%P", sha)
        an, ae, cn, ce, parents = (ids.strip("\n").split("\0") + [""] * 5)[:5]
        synthetic = ce == SYNTHETIC_MERGE_COMMITTER and len(parents.split()) > 1
        if not synthetic:
            for role, name, email in (("author", an, ae), ("committer", cn, ce)):
                if not _scan.ident_ok(name, email):
                    _scan.report("identity", "commit " + short, None, "%s is %s <%s>" % (role, name, email))
                    failures += 1
        failures += _scan.check_message(_scan.git_out("show", "-s", "--format=%B", sha), "commit %s message" % short)

    names = {}
    for line in _scan.git_out("rev-list", "--objects", "--all").splitlines():
        sha, _, path = line.partition(" ")
        names.setdefault(sha, path)
    for sha, kind, data in blobs(list(names)):
        path = names.get(sha, "")
        if kind == "blob":
            for rule in _scan.scan_path(path) if path else []:
                _scan.report(rule, path, None, "path of blob " + sha[:12])
                failures += 1
            for no, rule in _scan.scan_bytes(data):
                _scan.report(rule, path or sha[:12], no, "blob " + sha[:12])
                failures += 1
        elif kind == "tag":
            text = data.decode("utf-8", "replace")
            header, _, message = text.partition("\n\n")
            for ln in header.split("\n"):
                if ln.startswith("tagger "):
                    name, email = _scan.parse_ident(ln[len("tagger "):])
                    if not _scan.ident_ok(name, email):
                        _scan.report("identity", "tag object " + sha[:12], None, "tagger is %s <%s>" % (name, email))
                        failures += 1
            failures += _scan.check_message(message.split("-----BEGIN", 1)[0], "tag object %s message" % sha[:12])
    print("ci_scan: %d commits, %d objects, %d violations" % (len(commits), len(names), failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

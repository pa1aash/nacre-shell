"""pre-push: audit every new commit and tag before it leaves the machine."""
import sys

import _scan


def check_commit(sha):
    n = 0
    short = sha[:12]
    _, ids = _scan.git("show", "-s", "--format=%an%x00%ae%x00%cn%x00%ce", sha)
    an, ae, cn, ce = (ids.strip("\n").split("\0") + [""] * 4)[:4]
    for role, name, email in (("author", an, ae), ("committer", cn, ce)):
        if not _scan.ident_ok(name, email):
            _scan.report("identity", "commit " + short, None,
                         "%s is %s <%s>" % (role, name, email))
            n += 1
    n += _scan.check_message(_scan.git_out("show", "-s", "--format=%B", sha), "commit %s message" % short)
    header = _scan.git_out("cat-file", "commit", sha).split("\n\n", 1)[0]
    if not any(ln.startswith("gpgsig") for ln in header.split("\n")):
        _scan.report("signature", "commit " + short, None, "no signature header")
        n += 1
    is_merge = len(header.split("\nparent ")) > 2
    if not is_merge:
        names = _scan.git_out("diff-tree", "--root", "-r", "-z", "--name-only",
                              "--diff-filter=ACMR", "--no-renames", "--no-commit-id", sha)
        for path in [p for p in names.split("\0") if p]:
            for rule in _scan.scan_path(path):
                _scan.report(rule, path, None, "path in commit " + short)
                n += 1
            rc, data = _scan.git("cat-file", "blob", "%s:%s" % (sha, path), raw=True)
            if rc == 0:
                for no, rule in _scan.scan_bytes(data):
                    _scan.report(rule, path, no, "content in commit " + short)
                    n += 1
    return n


def check_tag(ref, sha):
    n = 0
    if _scan.git_out("cat-file", "-t", sha).strip() != "tag":
        _scan.report("tag", ref, None, "lightweight tag; only annotated, signed tags may be pushed")
        return 1
    body = _scan.git_out("cat-file", "tag", sha)
    header, _, message = body.partition("\n\n")
    for ln in header.split("\n"):
        if ln.startswith("tagger "):
            name, email = _scan.parse_ident(ln[len("tagger "):])
            if not _scan.ident_ok(name, email):
                _scan.report("identity", ref, None, "tagger is %s <%s>" % (name, email))
                n += 1
    if "-----BEGIN SSH SIGNATURE-----" not in message and "-----BEGIN PGP SIGNATURE-----" not in message:
        _scan.report("signature", ref, None, "tag is not signed")
        n += 1
    n += _scan.check_message(message.split("-----BEGIN", 1)[0], "tag %s message" % ref)
    return n


def main():
    failures = 0
    for line in sys.stdin.read().splitlines():
        parts = line.split()
        if len(parts) != 4:
            continue
        local_ref, local_sha, remote_ref, remote_sha = parts
        if _scan.ZERO_SHA.match(local_sha):
            continue
        if _scan.ZERO_SHA.match(remote_sha):
            rng = [local_sha, "--not", "--remotes"]
        else:
            rng = ["%s..%s" % (remote_sha, local_sha)]
        if remote_ref.startswith("refs/tags/"):
            failures += check_tag(remote_ref, local_sha)
        for sha in _scan.git_out("rev-list", *rng).split():
            failures += check_commit(sha)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

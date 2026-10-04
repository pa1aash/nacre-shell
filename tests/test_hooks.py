"""Hook self-test in a scratch repo wired to the real hook scripts."""
import sys

import pytest

from conftest import (COAUTHOR, HOOKS_SRC, LOCAL_GUIDE, LOCAL_SETTINGS, MAKER, PRODUCT, R1_EMAIL, R1_NAME,
                      git, run)

ZERO = "0" * 40


def commit(repo, files, message="phase0(test): change", branch=None, extra=()):
    if branch:
        git(repo, "checkout", "-q", "-B", branch)
    for rel, text in files.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        git(repo, "add", "-f", rel)
    return git(repo, "commit", "-q", "-m", message, *extra)


def pre_push(repo, ref, sha, remote_sha=ZERO):
    line = "%s %s %s %s\n" % (ref, sha, ref, remote_sha)
    return run([sys.executable, str(HOOKS_SRC / "pre-push.py"), "origin", "url"], repo, input=line)


def root_commit(repo):
    return git(repo, "rev-list", "--max-parents=0", "HEAD").stdout.strip()


def head(repo):
    return git(repo, "rev-parse", "HEAD").stdout.strip()


# --- expected rejection -------------------------------------------------------

@pytest.mark.parametrize("word", [PRODUCT, PRODUCT.upper(), MAKER, MAKER.capitalize(), COAUTHOR, COAUTHOR.lower()])
def test_a_banned_word_in_message_rejected(hook_repo, word):
    r = commit(hook_repo, {"a.txt": "x\n"}, "phase0(test): mentions %s here" % word)
    assert r.returncode != 0
    assert "REJECTED [banned-" in r.stderr and "commit message:1" in r.stderr


def test_b_coauthor_trailer_rejected(hook_repo):
    msg = "phase0(test): change\n\nbody\n\n%s: Someone <s@example.com>" % COAUTHOR
    r = commit(hook_repo, {"a.txt": "x\n"}, msg)
    assert r.returncode != 0 and "banned-coauthor-trailer" in r.stderr


def test_b_generic_trailer_rejected(hook_repo):
    r = commit(hook_repo, {"a.txt": "x\n"}, "phase0(test): change\n\nbody\n\nSigned-off-by: A <a@example.com>")
    assert r.returncode != 0 and "git-trailer" in r.stderr and ":5" in r.stderr


def test_subject_with_colon_is_not_a_trailer(hook_repo):
    r = commit(hook_repo, {"a.txt": "x\n"}, "fix: plain subject line")
    assert r.returncode == 0, r.stderr


def test_c_banned_content_rejected(hook_repo):
    r = commit(hook_repo, {"a.txt": "line one\nsee %s\n" % PRODUCT})
    assert r.returncode != 0 and "a.txt:2" in r.stderr


def test_c_binary_file_is_skipped(hook_repo):
    p = hook_repo / "b.bin"
    p.write_bytes(b"\0\1\2" + PRODUCT.encode())
    git(hook_repo, "add", "b.bin")
    assert git(hook_repo, "commit", "-q", "-m", "phase0(test): binary").returncode == 0


@pytest.mark.parametrize("rel", [LOCAL_GUIDE, LOCAL_SETTINGS + "/settings.json", "sub/" + LOCAL_GUIDE])
def test_d_local_only_paths_rejected(hook_repo, rel):
    r = commit(hook_repo, {rel: "harmless\n"})
    assert r.returncode != 0 and "local-only-name" in r.stderr


def _bad_commit(repo, name, email):
    (repo / "z.txt").write_text("z\n")
    git(repo, "add", "z.txt")
    env = {"GIT_AUTHOR_NAME": name, "GIT_AUTHOR_EMAIL": email, "GIT_COMMITTER_NAME": name,
           "GIT_COMMITTER_EMAIL": email, "PATH": __import__("os").environ["PATH"], "HOME": str(repo)}
    r = git(repo, "commit", "-q", "--no-verify", "-m", "phase0(test): bad identity", env=env)
    assert r.returncode == 0, r.stderr
    return head(repo)


def test_e_wrong_author_email_rejected_on_push(hook_repo):
    sha = _bad_commit(hook_repo, R1_NAME, "someone@example.com")
    r = pre_push(hook_repo, "refs/heads/main", sha)
    assert r.returncode != 0 and "[identity]" in r.stderr and "someone@example.com" in r.stderr


def test_e_wrong_identity_rejected_at_commit(hook_repo):
    git(hook_repo, "config", "user.email", "someone@example.com")
    r = commit(hook_repo, {"a.txt": "x\n"})
    assert r.returncode != 0 and "[identity]" in r.stderr


def test_f_unsigned_commit_rejected_on_push(hook_repo):
    assert commit(hook_repo, {"a.txt": "x\n"}).returncode == 0
    r = pre_push(hook_repo, "refs/heads/main", head(hook_repo))
    assert r.returncode != 0 and "[signature]" in r.stderr and "[identity]" not in r.stderr


def test_push_rejects_banned_content_in_history(hook_repo, ssh_key):
    _sign_config(hook_repo, ssh_key)
    assert commit(hook_repo, {"a.txt": "x\n"}, extra=("--no-verify",)).returncode == 0
    (hook_repo / "a.txt").write_text("x\n%s\n" % MAKER)
    git(hook_repo, "add", "a.txt")
    assert git(hook_repo, "commit", "-q", "--no-verify", "-m", "phase0(test): later").returncode == 0
    r = pre_push(hook_repo, "refs/heads/main", head(hook_repo))
    assert r.returncode != 0 and "a.txt:2" in r.stderr and "banned-maker-name" in r.stderr


def test_g_lane_b_cannot_touch_src_physics(hook_repo):
    r = commit(hook_repo, {"src/nacre/physics/x.py": "x = 1\n"}, branch="lane/b-test")
    assert r.returncode != 0 and "[lane-ownership] src/nacre/physics/x.py" in r.stderr


def test_h_lane_a_charter_cannot_touch_paper(hook_repo):
    r = commit(hook_repo, {"paper/main.tex": "x\n"}, branch="lane/a-charter")
    assert r.returncode != 0 and "[lane-ownership] paper/main.tex" in r.stderr


def test_i_registration_frozen_and_deviations_append_only(hook_repo):
    base = "line one\nline two\n"
    assert commit(hook_repo, {"registration/deviations.md": base, "registration/prereg.md": "p\n"}).returncode == 0
    git(hook_repo, "tag", "prereg-v1")
    r = commit(hook_repo, {"registration/deviations.md": "line one\nCHANGED\n"})
    assert r.returncode != 0 and "[frozen-path] registration/deviations.md" in r.stderr
    git(hook_repo, "reset", "-q", "--hard")
    r = commit(hook_repo, {"registration/prereg.md": "edited\n"})
    assert r.returncode != 0 and "[frozen-path] registration/prereg.md" in r.stderr
    git(hook_repo, "reset", "-q", "--hard")
    r = commit(hook_repo, {"registration/deviations.md": base + "2026-10-05 added\n"})
    assert r.returncode == 0, r.stderr


def test_frozen_inactive_before_tag(hook_repo):
    assert commit(hook_repo, {"registration/prereg.md": "p\n"}).returncode == 0
    assert commit(hook_repo, {"registration/prereg.md": "q\n"}).returncode == 0


def test_j_unknown_branch_rejected(hook_repo):
    r = commit(hook_repo, {"a.txt": "x\n"}, branch="feature/x")
    assert r.returncode != 0 and "[branch]" in r.stderr


def test_k_waves_yaml_main_only(hook_repo):
    r = commit(hook_repo, {"ops/waves.yaml": "waves: []\n"}, branch="lane/a-charter")
    assert r.returncode != 0 and "[lane-ownership] ops/waves.yaml" in r.stderr
    assert commit(hook_repo, {"ops/waves.yaml": "waves: []\n"}, branch="main").returncode == 0


# --- expected acceptance ------------------------------------------------------

def test_clean_commit_on_a_charter(hook_repo):
    r = commit(hook_repo, {"charter/x.yaml": "a: 1\n"}, branch="lane/a-charter")
    assert r.returncode == 0, r.stderr


def test_clean_commit_on_b_test(hook_repo):
    r = commit(hook_repo, {"paper/x.tex": "x\n", "ops/state/b-test.json": "{}\n"}, branch="lane/b-test")
    assert r.returncode == 0, r.stderr


def test_b_lane_cannot_write_another_lanes_state(hook_repo):
    r = commit(hook_repo, {"ops/state/b-other.json": "{}\n"}, branch="lane/b-test")
    assert r.returncode != 0 and "ops/state/b-other.json" in r.stderr


# --- signed pushes ------------------------------------------------------------

def _sign_config(repo, key):
    git(repo, "config", "gpg.format", "ssh")
    git(repo, "config", "user.signingkey", str(key) + ".pub")
    git(repo, "config", "commit.gpgsign", "true")


def test_signed_commit_passes_push(hook_repo, ssh_key):
    _sign_config(hook_repo, ssh_key)
    r = commit(hook_repo, {"a.txt": "x\n"})
    assert r.returncode == 0, r.stderr
    r = pre_push(hook_repo, "refs/heads/main", head(hook_repo), root_commit(hook_repo))
    assert r.returncode == 0, r.stderr


def test_tag_must_be_annotated_and_signed(hook_repo, ssh_key):
    _sign_config(hook_repo, ssh_key)
    assert commit(hook_repo, {"a.txt": "x\n"}).returncode == 0
    sha = head(hook_repo)
    git(hook_repo, "tag", "light")
    r = pre_push(hook_repo, "refs/tags/light", sha)
    assert r.returncode != 0 and "lightweight" in r.stderr
    git(hook_repo, "-c", "tag.gpgsign=false", "tag", "-a", "plain", "-m", "unsigned")
    tag_sha = git(hook_repo, "rev-parse", "plain").stdout.strip()
    r = pre_push(hook_repo, "refs/tags/plain", tag_sha)
    assert r.returncode != 0 and "tag is not signed" in r.stderr
    git(hook_repo, "-c", "user.signingkey=" + str(ssh_key) + ".pub", "tag", "-s", "-a", "good", "-m", "signed")
    tag_sha = git(hook_repo, "rev-parse", "good").stdout.strip()
    r = pre_push(hook_repo, "refs/tags/good", tag_sha, root_commit(hook_repo))
    assert r.returncode == 0, r.stderr


def _diverge(repo, side_text):
    commit(repo, {"a.txt": side_text}, branch="lane/b-test", message="phase0(test): side",
           extra=("--no-verify",))
    git(repo, "checkout", "-q", "main")
    assert commit(repo, {"b.txt": "y\n"}, message="phase0(test): main side").returncode == 0


def test_merge_commit_skips_ownership(hook_repo):
    _diverge(hook_repo, "x\n")
    # lane/b-test owns nothing under a.txt, yet merges carry no ownership check
    r = git(hook_repo, "merge", "--no-ff", "-m", "ops(test): merge", "lane/b-test")
    assert r.returncode == 0, r.stderr + r.stdout


def test_merge_commit_hook_scans_content(hook_repo):
    _diverge(hook_repo, "see %s\n" % PRODUCT)
    r = git(hook_repo, "merge", "--no-ff", "-m", "ops(test): merge", "lane/b-test")
    assert r.returncode != 0 and "a.txt:1" in r.stderr

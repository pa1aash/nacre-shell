import hashlib
import io
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
import yaml

from nacre.report import template
from nacre.report.fetch import Fetcher

# A synthetic stand-in with the same marker structure the renderer relies on.
FAKE_MAIN = r"""\documentclass{article}
%%%%%%%%% Preamble of the bibliography, can be commented or deleted
\def\bibpreamble{sample text}
%%%%%%%%%
\begin{document}
\textbf{This is the title$^\dag$}
Full Name,$^{\ast}$\textit{$^{a}$} Full Name,\textit{$^{b\ddag}$} and Full Name\textit{$^{a}$}
\noindent\normalsize{The abstract should be a single paragraph.} \\%The abstrast goes here
%%%FOOTNOTES%%%
\footnotetext{sample}
%%%END OF FOOTNOTES%%%
%%%MAIN TEXT%%%%
Sample body.
\end{document}
"""


def _zip(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return buf.getvalue()


FILES = {"main.tex": FAKE_MAIN.encode(), "rsc.bst": b"bst", "head_foot/LF.pdf": b"pdf"}
ARCHIVE = _zip(FILES)


class _H(BaseHTTPRequestHandler):
    body = ARCHIVE
    status = 200

    def log_message(self, *a):
        pass

    def do_GET(self):
        self.send_response(self.status)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Length", str(len(self.body)))
        self.end_headers()
        self.wfile.write(self.body)


@pytest.fixture()
def repo(tmp_path):
    _H.body, _H.status = ARCHIVE, 200
    srv = HTTPServer(("127.0.0.1", 0), _H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = "http://127.0.0.1:%d/t.zip" % srv.server_address[1]
    spec = {"archive_url": url, "archive_sha256": hashlib.sha256(ARCHIVE).hexdigest(),
            "files": [{"path": k, "sha256": hashlib.sha256(v).hexdigest()} for k, v in FILES.items()]}
    (tmp_path / "charter" / "venue").mkdir(parents=True)
    (tmp_path / "charter" / "venue" / "template.yaml").write_text(yaml.safe_dump(spec), encoding="utf-8")
    (tmp_path / "paper").mkdir()
    yield tmp_path
    srv.shutdown()
    srv.server_close()


def _fetcher(root):
    return Fetcher(venue_dir=root / "f", retries=0, sleep=lambda s: None, timeout=5)


def test_download_unpack_verify_and_render(repo):
    msgs = []
    assert template.ensure(repo, fetcher=_fetcher(repo), out=msgs.append) == 3
    assert (repo / "paper" / "rsc_template" / "head_foot" / "LF.pdf").read_bytes() == b"pdf"
    assert "downloaded" in msgs[0]
    head = (repo / "paper" / "build" / "rsc_head.tex").read_text(encoding="utf-8")
    for token in ("\\nacreTitle\\nacreTitleMark", "\\nacreAuthors", "\\nacreAbstract", "\\nacreFootnotes"):
        assert token in head
    assert "Sample body" not in head and "bibpreamble" not in head and "This is the title" not in head


def test_second_run_verifies_present_files(repo):
    template.ensure(repo, fetcher=_fetcher(repo), out=lambda m: None)
    msgs = []
    template.ensure(repo, out=msgs.append)
    assert "present: 3 files verified" in msgs[0]


def test_modified_file_fails_loudly_and_is_not_patched(repo):
    template.ensure(repo, fetcher=_fetcher(repo), out=lambda m: None)
    target = repo / "paper" / "rsc_template" / "rsc.bst"
    target.write_bytes(b"edited")
    with pytest.raises(template.TemplateError) as exc:
        template.ensure(repo, out=lambda m: None)
    assert "differs: rsc.bst" in str(exc.value)
    assert target.read_bytes() == b"edited"


def test_extra_and_missing_files_are_reported(repo):
    template.ensure(repo, fetcher=_fetcher(repo), out=lambda m: None)
    d = repo / "paper" / "rsc_template"
    (d / "rsc.bst").unlink()
    (d / "extra.txt").write_text("x")
    with pytest.raises(template.TemplateError) as exc:
        template.ensure(repo, out=lambda m: None)
    assert "missing: rsc.bst" in str(exc.value) and "unexpected: extra.txt" in str(exc.value)


def test_archive_hash_mismatch_refuses_download(repo):
    _H.body = _zip({"main.tex": b"other"})
    with pytest.raises(template.TemplateError) as exc:
        template.ensure(repo, fetcher=_fetcher(repo), out=lambda m: None)
    assert "differs from recorded" in str(exc.value)
    assert not (repo / "paper" / "rsc_template").exists()


def test_unsafe_archive_paths_rejected(tmp_path):
    with pytest.raises(template.TemplateError):
        template._safe_unpack(_zip({"../evil.txt": b"x"}), tmp_path / "out")


def test_layout_change_is_detected(tmp_path):
    (tmp_path / "main.tex").write_text("\\documentclass{article}\n", encoding="utf-8")
    with pytest.raises(template.TemplateError):
        template.render_head(tmp_path)

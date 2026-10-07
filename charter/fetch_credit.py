"""Fetch the CRediT contributor roles from the NISO site into charter/credit_taxonomy.md.

Rule R3: the taxonomy is third-party canonical text, so it is downloaded, never typed.
The role list comes from the NISO CRediT home page; each definition comes from the
"Definition" paragraph of that role's own page. Text is extracted from the HTML by
stripping tags and unescaping entities; nothing else is changed.

Run: uv run python charter/fetch_credit.py
"""
import hashlib
import html
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HOME = "https://credit.niso.org/"
OUT = Path(__file__).resolve().parent / "credit_taxonomy.md"
AGENT = "nacre-shell-charter-fetch/1 (headless; urllib)"
ROLE_LINK = re.compile(r'href="https?://credit\.niso\.org/contributor-roles/([a-z0-9-]+)/"')
TITLE = re.compile(r'<h1 class="entry-title">(.*?)</h1>', re.S)
DEFINITION = re.compile(r"<strong>Definition</strong>\s*:\s*(.*?)</p>", re.S)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = resp.read()
        status = resp.status
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return body, status, stamp, hashlib.sha256(body).hexdigest()


def text(fragment):
    return html.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


def main():
    home, status, stamp, digest = fetch(HOME)
    slugs = list(dict.fromkeys(ROLE_LINK.findall(home.decode("utf-8"))))
    if not slugs:
        sys.exit("no contributor-role links found on %s" % HOME)
    rows = []
    for slug in slugs:
        url = "https://credit.niso.org/contributor-roles/%s/" % slug
        body, st, ts, sha = fetch(url)
        page = body.decode("utf-8")
        name, definition = TITLE.search(page), DEFINITION.search(page)
        if not (name and definition):
            sys.exit("could not find the role name or definition on %s" % url)
        rows.append((text(name.group(1)), text(definition.group(1)), url, ts, sha, st))

    lines = [
        "# CRediT contributor role taxonomy (fetched)",
        "",
        "Fetched headlessly by `charter/fetch_credit.py` (rule R3: canonical third-party text is downloaded, "
        "never typed). Role names are the `<h1>` titles of the role pages linked from the NISO CRediT home page; "
        "each definition is the text of that page's \"Definition\" paragraph with HTML tags stripped and entities "
        "unescaped. Nothing else is edited, including the publisher's punctuation and any invisible characters.",
        "",
        "Source: NISO, Contributor Role Taxonomy (CRediT), ANSI/NISO standard, licensed CC BY 4.0 by its publisher "
        "(as stated on the home page). Attribution: credit.niso.org.",
        "",
        "| Page | URL | Retrieved (UTC) | sha256 of fetched bytes | HTTP |",
        "|---|---|---|---|---|",
        "| home (role list) | %s | %s | %s | %d |" % (HOME, stamp, digest, status),
    ]
    lines += ["| %s | %s | %s | %s | %d |" % (r[0], r[2], r[3], r[4], r[5]) for r in rows]
    lines += ["", "## Roles and definitions (verbatim)", ""]
    for name, definition, *_ in rows:
        lines += ["### %s" % name, "", definition, ""]
    lines += [
        "## Machine-readable role list",
        "",
        "Generated from the role pages above; `tests/charter/test_charter.py` checks `charter/credit.yaml` against it.",
        "",
        "```yaml credit-roles",
    ]
    lines += ['- "%s"' % name.replace('"', '\\"') for name, *_ in rows]
    lines += ["```", ""]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("wrote %s (%d roles)" % (OUT.name, len(rows)))


if __name__ == "__main__":
    main()

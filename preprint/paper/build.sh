#!/usr/bin/env zsh
# Build the P0 preprint and its Supplementary Information with latexmk.
#
#   ./build.sh [draft|release]      (default: draft; runs from any directory)
#
# draft    placeholders, pending author fields, missing inputs and mock numbers render with
#          visible markers; the PDFs go to build/draft/.
# release  `nacre preprint prepare --mode release` runs the release guard first and refuses
#          on any problem: the local-only AI disclosure (<repo-root>/.local/p0/ai_ack.tex)
#          missing, any placeholder or TBD left, any mock macro used, or a linter failure. The
#          LaTeX layer stops on the same markers at use time. The PDFs go to build/release/.
#
# Both modes run lint-numbers and lint-scope and stop if either fails.
set -euo pipefail

mode=${1:-draft}
if [[ $mode != draft && $mode != release ]]; then
  print -u2 "usage: build.sh [draft|release]"
  exit 2
fi

here=${0:A:h}
root=$(git -C "$here" rev-parse --show-toplevel)
cd "$here"

uv run --project "$root" nacre preprint prepare --mode "$mode"
uv run --project "$root" nacre preprint lint-numbers
uv run --project "$root" nacre preprint lint-scope

tpl=$(<build/template_dir.txt)
# The template is referenced in place, never copied; a trailing colon keeps the default paths.
export TEXINPUTS=".:$tpl:"
export BSTINPUTS=".:$tpl:"
export BIBINPUTS=".:$root/paper:"

out=build/$mode
rm -rf "$out"   # every build starts clean, so a stale failure never masks the current state
rc=0
for src in main.tex si/main_si.tex; do
  dir=$out
  [[ $src == si/* ]] && dir=$out/si
  mkdir -p "$dir"
  if ! latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir="$dir" "$src" >"$dir/$src:t:r.latexmk.txt" 2>&1; then
    log=$dir/$src:t:r.log
    print -u2 "build $mode: $src FAILED"
    if [[ -f $log ]]; then
      grep -E '^!|NACRE release guard' "$log" | head -20 >&2 || true
    fi
    rc=1
    continue
  fi
  log=$dir/$src:t:r.log
  pages=$(grep -Eo 'Output written on .* \(([0-9]+) pages?' "$log" | grep -Eo '\([0-9]+' | tr -d '(' || true)
  warn=$(grep -Ec 'LaTeX Warning: (Reference|Citation).*undefined' "$log" || true)
  print "build $mode: $src -> $dir/$src:t:r.pdf (${pages:-?} pages, $warn undefined reference warning(s))"
  if [[ $mode == release && $warn != 0 ]]; then
    print -u2 "build release: undefined references in $src"
    rc=1
  fi
done
exit $rc

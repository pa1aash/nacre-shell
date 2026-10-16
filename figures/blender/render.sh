#!/bin/zsh
# Render one scene headlessly with the memory guard of rule R10.
#   figures/blender/render.sh <scene> <out.png>
# Before rendering it reads `memory_pressure | tail -1`; below 20 % free it waits 5 minutes and
# re-checks, for at most 30 minutes, then exits 3. Writes <out>.run.txt beside the image with the
# reading at start, wall time and peak resident memory of the renderer.
set -eu
scene=${1:?scene name}
out=${2:?output png}
here=${0:A:h}
repo=${here:h:h}
blender=${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}

free_pct() { memory_pressure | tail -1 | sed -E 's/.*: *([0-9]+)%.*/\1/'; }

waited=0
reading=$(memory_pressure | tail -1)
pct=$(free_pct)
while (( pct < 20 )); do
  if (( waited >= 30 )); then
    print -u2 "BLOCKED: memory free ${pct}% after ${waited} min (${reading})"
    exit 3
  fi
  print "memory free ${pct}% < 20%; waiting 5 min"
  sleep 300
  waited=$(( waited + 5 ))
  reading=$(memory_pressure | tail -1)
  pct=$(free_pct)
done

mkdir -p "${out:h}"
log="${out:r}.run.txt"
start=$(date +%s)
rc=0
/usr/bin/time -l "$blender" -b --threads 4 -P "$here/scene.py" -- --scene "$scene" --out "$out" \
  > "${out:r}.blender.out" 2> "${out:r}.time.out" || rc=$?
end=$(date +%s)
peak=$(grep -E 'maximum resident set size' "${out:r}.time.out" | awk '{print $1}')
{
  print "scene: $scene"
  print "memory at start: $reading (waited ${waited} min)"
  print "wall seconds: $(( end - start ))"
  print "peak resident bytes (renderer): $peak"
  print "exit status: $rc"
} > "$log"
rm -f "${out:r}.time.out"
cat "$log"
grep -E '^RENDERED' "${out:r}.blender.out" || { tail -20 "${out:r}.blender.out"; exit 1; }
rm -f "${out:r}.blender.out"

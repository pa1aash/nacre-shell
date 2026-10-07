#!/bin/bash
# In-image smoke test for the gpu role (CPU mode is enough; the CI runner has no GPU).
set -euo pipefail
nacre --help >/dev/null
python - <<'PY'
import torch, mace, chgnet, ase, torch_sim, plumed, numpy, scipy, pymatgen, nacre, lammps
from importlib.metadata import version
for name in ("torch", "mace-torch", "chgnet", "ase", "torch-sim-atomistic", "plumed", "numpy", "scipy", "pymatgen"):
    print(f"{name} {version(name)}")
print("torch cuda build:", torch.version.cuda)
import mace.calculators.lammps_mliap_mace  # MACE side of pair_style mliap unified
plumed.Plumed()  # loads libplumedKernel through PLUMED_KERNEL
print("plumed kernel loaded")
PY
# lmp links libcuda.so.1, which the NVIDIA container runtime injects on GPU hosts. On a GPU-less
# CI runner an empty stub is enough for `lmp -h`, which never initialises Kokkos.
stub=$(mktemp -d)
gcc -shared -o "$stub/libcuda.so.1" -x c /dev/null
if ! ldconfig -p | grep -q 'libcuda.so.1'; then export LD_LIBRARY_PATH="$stub:$LD_LIBRARY_PATH"; fi
lmp -h > /tmp/lmp_help.txt
grep -E '(^|[[:space:]])mliap([[:space:]]|$)' /tmp/lmp_help.txt >/dev/null && echo "lmp lists pair_style mliap"
grep -E '(^|[[:space:]])plumed([[:space:]]|$)' /tmp/lmp_help.txt >/dev/null && echo "lmp lists fix plumed"
grep -iE 'KOKKOS|PYTHON|ML-IAP|PLUMED' /tmp/lmp_help.txt | head -8

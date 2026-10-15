#!/bin/bash
# In-image smoke test for the cpu role: version prints plus a 1-SCF-step H2 run with a
# pseudopotential downloaded now (pseudopotentials are never baked into the image).
set -euo pipefail
nacre --help >/dev/null
python -c "import ase, pymatgen, nacre, qe_tools; print('python helpers import ok')"
mpirun --version | head -1
work=$(mktemp -d); cd "$work"
curl -fsSL -o H.pbe-rrkjus.UPF https://pseudopotentials.quantum-espresso.org/upf_files/H.pbe-rrkjus.UPF
cat > h2.in <<'IN'
&control
  calculation='scf', prefix='h2', pseudo_dir='.', outdir='./tmp'
/
&system
  ibrav=1, celldm(1)=12.0, nat=2, ntyp=1, ecutwfc=25
/
&electrons
  electron_maxstep=1
/
ATOMIC_SPECIES
H 1.008 H.pbe-rrkjus.UPF
ATOMIC_POSITIONS angstrom
H 0.0 0.0 0.0
H 0.0 0.0 0.74
K_POINTS gamma
IN
OMP_NUM_THREADS=2 mpirun -np 2 pw.x -in h2.in > h2.out 2>&1 || { cat h2.out; exit 1; }
grep -m1 'Program PWSCF' h2.out
grep -E 'Number of MPI processes|Threads/MPI process' h2.out
grep -m1 'total energy' h2.out
grep -q 'JOB DONE' h2.out && echo "pw.x H2 smoke: JOB DONE"

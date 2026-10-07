# Pinned versions

Every choice below is pinned in `env/*/Dockerfile`, `env/*/uv.lock` or `env/*/pyproject.toml`, with a one-line reason. Resolved digests of the built images are in `env/digests.yaml`.

## Base images and tooling

| Component | Pin | Reason |
|---|---|---|
| gpu build base | `nvidia/cuda:12.9.2-cudnn-devel-ubuntu24.04` @ `sha256:5a480db8cbf90098ca816d7e77f07ce5cb4c43353530b6a84915c2dd99c4e0b6` | CUDA 12.x with nvcc for the Kokkos/CUDA LAMMPS build; newest 12.x line, matches the cu129 torch wheels |
| gpu runtime base | `nvidia/cuda:12.9.2-cudnn-runtime-ubuntu24.04` @ `sha256:070f8f2672df1b05b84c0409a5fd1d54ddfd646e5b9d8dee7878131271b563fc` | same CUDA and cuDNN as the build base, without the compiler toolchain |
| cpu base | `ubuntu:24.04` @ `sha256:534baea6a22c03a63003dbc8dbe78fe34bc0d7e595d9a9dc9834884ff530eb55` | plain LTS userland for Quantum ESPRESSO; Python 3.12 matches the repository |
| apt packages | Ubuntu snapshot `20260901T000000Z` (snapshot.ubuntu.com) | one dated mirror state pins every apt package without per-package version strings |
| uv | `ghcr.io/astral-sh/uv:0.12.23` @ `sha256:61d393e44e249f2e4b526b6c7ddcecce245946826e608e11c93ad4f5bba55b21` | resolves nothing at build time; installs strictly from the lockfile (`--frozen`) |
| Python | 3.12 (Ubuntu 24.04 `python3.12`) | `requires-python = ">=3.12,<3.13"` in the repository |

## Source builds (tag plus commit)

| Component | Tag | Commit | Reason |
|---|---|---|---|
| LAMMPS | `stable_30Sep2026` | `8de817dd79bfe4525d5d39246a212d833e6dee07` | latest stable release; has ML-IAP (python unified), KOKKOS and the PLUMED package |
| PLUMED | `v2.10.1` | `ab928db10f5e6756189cf74fa12df24cda43a027` | latest 2.10 release; built shared with all modules, python bindings from PyPI `plumed==2.10.0` |
| Quantum ESPRESSO | `qe-7.6` | `9f93ddec427d2b9a45bb72d828c6d324f62fcabd` | newest release tag at pin time; built with CMake, MPI and OpenMP |
| MPI flavour (cpu) | OpenMPI from the apt snapshot | n/a | recorded choice: OpenMPI, not MPICH; ships `mpirun` and works unprivileged in containers with the vader/CMA workaround set in the image |

LAMMPS has no ML-MACE package in this release. MACE runs through ML-IAP: `pair_style mliap unified` loads a model from `mace.calculators.lammps_mliap_mace`. The smoke test therefore checks that `lmp -h` lists `mliap` (not a `mace` pair style) and the `plumed` fix. LAMMPS is built without MPI (single GPU per pod) and with Kokkos architecture `AMPERE80`; other architectures run through PTX JIT.

## Python dependencies (uv lockfile per image)

The lockfiles are `env/gpu/uv.lock` and `env/cpu/uv.lock`; the nacre package is installed from the build context, not from the lockfile.

| Package | Version | Image | Reason |
|---|---|---|---|
| torch | 2.13.0+cu129 | gpu | newest torch built for CUDA 12.9 on the PyTorch index; matches the base image |
| mace-torch | 0.3.16 | gpu | MACE-MP-0 foundation model and its LAMMPS ML-IAP interface |
| e3nn | 0.4.4 | gpu | exact pin required by mace-torch 0.3.16 |
| chgnet | 0.4.2 | gpu | CHGNet universal potential, latest release |
| torch-sim-atomistic | 0.6.2 | gpu | TorchSim MD engine candidate |
| plumed (python) | 2.10.0 | gpu | PLUMED python bindings; kernel is the source-built v2.10.1 via `PLUMED_KERNEL` |
| cupy-cuda12x | 14.2.0 | gpu | required by ML-IAP Kokkos unified models |
| cython | 3.3.0 | gpu | needed to build the LAMMPS ML-IAP python bridge and plumed |
| ase | 3.29.0 | gpu, cpu | ASE MD engine and I/O, latest release |
| pymatgen | 2026.9.24 | gpu, cpu | structure handling, latest release |
| numpy | 2.5.3 | gpu, cpu | resolved by uv, compatible with every pin above |
| scipy | 1.18.1 | gpu, cpu | resolved by uv |
| pyyaml | 6.0.3 | gpu, cpu | dependency of the nacre package |
| qe-tools | 2.3.0 | cpu | Quantum ESPRESSO input/output helpers |

## CI actions (pinned to full release tags)

| Action | Tag | Reason |
|---|---|---|
| actions/checkout | v7.0.1 | latest release |
| docker/setup-buildx-action | v4.4.1 | latest release |
| docker/login-action | v4.6.0 | latest release |
| docker/build-push-action | v7.4.0 | latest release |
| actions/upload-artifact | v7.0.1 | latest release |
| actions/download-artifact | v8.0.1 | latest release |

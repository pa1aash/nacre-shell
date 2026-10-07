# syntax=docker/dockerfile:1.7
# nacre gpu image: MLIP + MD + enhanced sampling. Build context is the repository root:
#   docker buildx build -f env/gpu/Dockerfile .
# Built in CI only (linux/amd64); never built on a laptop.

ARG CUDA_DEVEL=nvidia/cuda@sha256:5a480db8cbf90098ca816d7e77f07ce5cb4c43353530b6a84915c2dd99c4e0b6
ARG CUDA_RUNTIME=nvidia/cuda@sha256:070f8f2672df1b05b84c0409a5fd1d54ddfd646e5b9d8dee7878131271b563fc
ARG UV_IMAGE=ghcr.io/astral-sh/uv@sha256:61d393e44e249f2e4b526b6c7ddcecce245946826e608e11c93ad4f5bba55b21

FROM ${UV_IMAGE} AS uv

# ---------------------------------------------------------------- build base
# nvidia/cuda 12.9.2 + cuDNN, Ubuntu 24.04; apt is pinned to a dated snapshot.
FROM ${CUDA_DEVEL} AS devel
ARG APT_SNAPSHOT=20261006T000000Z
ENV DEBIAN_FRONTEND=noninteractive
RUN sed -i -E "s#https?://(archive|security)\.ubuntu\.com/ubuntu/?#https://snapshot.ubuntu.com/ubuntu/${APT_SNAPSHOT}/#" /etc/apt/sources.list.d/ubuntu.sources \
 && apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential cmake ninja-build pkg-config git ca-certificates curl \
      python3.12 python3.12-dev python3.12-venv \
      libgsl-dev libblas-dev liblapack-dev zlib1g-dev libfftw3-dev \
 && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------- python venv
FROM devel AS pyenv
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv UV_PYTHON=/usr/bin/python3.12 UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy
WORKDIR /build/env
COPY env/gpu/pyproject.toml env/gpu/uv.lock ./
RUN uv sync --frozen --no-install-project
# The nacre package comes from the build context, not from the lockfile.
COPY pyproject.toml README.md /build/nacre/
COPY src /build/nacre/src
RUN uv pip install --python /opt/venv/bin/python --no-deps /build/nacre

# ---------------------------------------------------------------- PLUMED
FROM devel AS plumed
ARG PLUMED_TAG=v2.10.1
ARG PLUMED_COMMIT=ab928db10f5e6756189cf74fa12df24cda43a027
ARG BUILD_JOBS=4
RUN git clone --branch "${PLUMED_TAG}" https://github.com/plumed/plumed2.git /src/plumed2 \
 && cd /src/plumed2 \
 && test "$(git rev-parse HEAD)" = "${PLUMED_COMMIT}" \
 && ./configure --prefix=/opt/plumed --disable-mpi --enable-modules=all --enable-shared \
 && make -j"${BUILD_JOBS}" \
 && make install

# ---------------------------------------------------------------- LAMMPS
# Mainline LAMMPS has no ML-MACE package. MACE runs through ML-IAP (pair_style mliap
# unified) with Kokkos/CUDA; PLUMED enters through the PLUMED package (fix plumed).
FROM devel AS lammps
ARG LAMMPS_TAG=stable_30Sep2026
ARG LAMMPS_COMMIT=8de817dd79bfe4525d5d39246a212d833e6dee07
ARG KOKKOS_ARCH=AMPERE80
ARG BUILD_JOBS=4
COPY --from=pyenv /opt/venv /opt/venv
COPY --from=plumed /opt/plumed /opt/plumed
ENV PKG_CONFIG_PATH=/opt/plumed/lib/pkgconfig LD_LIBRARY_PATH=/opt/plumed/lib PATH=/opt/venv/bin:/usr/local/cuda/bin:${PATH}
RUN git clone --branch "${LAMMPS_TAG}" --depth 1 https://github.com/lammps/lammps.git /src/lammps \
 && cd /src/lammps \
 && test "$(git rev-parse HEAD)" = "${LAMMPS_COMMIT}"
RUN cmake -S /src/lammps/cmake -B /build/lammps -G Ninja \
      -D CMAKE_BUILD_TYPE=Release \
      -D CMAKE_INSTALL_PREFIX=/opt/lammps \
      -D CMAKE_CXX_COMPILER=/src/lammps/lib/kokkos/bin/nvcc_wrapper \
      -D BUILD_MPI=no -D BUILD_OMP=yes -D BUILD_SHARED_LIBS=yes -D LAMMPS_EXCEPTIONS=yes \
      -D PKG_KOKKOS=yes -D Kokkos_ENABLE_CUDA=yes -D Kokkos_ENABLE_OPENMP=yes -D Kokkos_ARCH_${KOKKOS_ARCH}=yes \
      -D PKG_PYTHON=yes -D Python_EXECUTABLE=/opt/venv/bin/python \
      -D PKG_ML-IAP=yes -D PKG_ML-SNAP=yes -D MLIAP_ENABLE_PYTHON=yes \
      -D PKG_PLUMED=yes -D PLUMED_MODE=shared -D DOWNLOAD_PLUMED=no \
      -D PKG_MOLECULE=yes -D PKG_KSPACE=yes -D PKG_MANYBODY=yes -D PKG_RIGID=yes -D PKG_EXTRA-FIX=yes -D PKG_EXTRA-PAIR=yes -D PKG_EXTRA-DUMP=yes -D PKG_EXTRA-MOLECULE=yes -D PKG_MISC=yes -D PKG_REPLICA=yes \
 && cmake --build /build/lammps -j"${BUILD_JOBS}" \
 && cmake --install /build/lammps \
 && cmake --build /build/lammps --target install-python

# ---------------------------------------------------------------- final image
FROM ${CUDA_RUNTIME} AS final
ARG APT_SNAPSHOT=20261006T000000Z
ENV DEBIAN_FRONTEND=noninteractive
RUN sed -i -E "s#https?://(archive|security)\.ubuntu\.com/ubuntu/?#https://snapshot.ubuntu.com/ubuntu/${APT_SNAPSHOT}/#" /etc/apt/sources.list.d/ubuntu.sources \
 && apt-get update \
 && apt-get install -y --no-install-recommends \
      python3.12 openssh-server openssh-client git curl ca-certificates less procps \
      libgomp1 libgsl27 libblas3 liblapack3 libfftw3-double3 zlib1g build-essential python3.12-dev \
 && rm -rf /var/lib/apt/lists/* \
 && (userdel -r ubuntu 2>/dev/null || true) \
 && useradd -m -u 1000 -s /bin/bash nacre

COPY --from=lammps /opt/venv /opt/venv
COPY --from=lammps /opt/lammps /opt/lammps
COPY --from=plumed /opt/plumed /opt/plumed
COPY env/common/entrypoint.sh /usr/local/bin/nacre-entrypoint
COPY env/common/sshd_config /etc/ssh/sshd_config
ENV PATH=/opt/venv/bin:/opt/lammps/bin:/opt/plumed/bin:/usr/local/cuda/bin:${PATH} \
    LD_LIBRARY_PATH=/opt/lammps/lib:/opt/lammps/lib64:/opt/plumed/lib \
    PLUMED_KERNEL=/opt/plumed/lib/libplumedKernel.so \
    LAMMPS_POTENTIALS=/opt/lammps/share/lammps/potentials \
    PYTHONUNBUFFERED=1

ARG GIT_SHA=unknown
ARG BUILD_DATE=unknown
LABEL org.opencontainers.image.title="nacre-shell-gpu" \
      org.opencontainers.image.source="https://github.com/pa1aash/nacre-shell" \
      org.opencontainers.image.revision="${GIT_SHA}" \
      org.opencontainers.image.created="${BUILD_DATE}"

WORKDIR /home/nacre
EXPOSE 22
ENTRYPOINT ["/usr/local/bin/nacre-entrypoint"]
CMD []

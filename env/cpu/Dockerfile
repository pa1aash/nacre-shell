# syntax=docker/dockerfile:1.7
# nacre cpu image: Quantum ESPRESSO (MPI + OpenMP, OpenMPI) for plane-wave DFT labels.
# Build context is the repository root:  docker buildx build -f env/cpu/Dockerfile .
# Built in CI only (linux/amd64); never built on a laptop. SSSP pseudopotentials are not baked in.

ARG UBUNTU=ubuntu@sha256:534baea6a22c03a63003dbc8dbe78fe34bc0d7e595d9a9dc9834884ff530eb55
ARG UV_IMAGE=ghcr.io/astral-sh/uv@sha256:61d393e44e249f2e4b526b6c7ddcecce245946826e608e11c93ad4f5bba55b21

FROM ${UV_IMAGE} AS uv

# ---------------------------------------------------------------- build base
FROM ${UBUNTU} AS devel
ARG APT_SNAPSHOT=20260901T000000Z
ENV DEBIAN_FRONTEND=noninteractive
RUN sed -i -E "s#https?://(archive|security)\.ubuntu\.com/ubuntu/?#http://snapshot.ubuntu.com/ubuntu/${APT_SNAPSHOT}/#" /etc/apt/sources.list.d/ubuntu.sources \
 && apt-get update \
 && apt-get install -y --no-install-recommends \
      build-essential gfortran cmake ninja-build pkg-config git ca-certificates curl \
      openmpi-bin libopenmpi-dev libfftw3-dev libfftw3-mpi-dev libopenblas-dev liblapack-dev \
      libscalapack-openmpi-dev \
      python3.12 python3.12-dev python3.12-venv \
 && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------- python venv
FROM devel AS pyenv
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv UV_PYTHON=/usr/bin/python3.12 UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy
WORKDIR /build/env
COPY env/cpu/pyproject.toml env/cpu/uv.lock ./
RUN uv sync --frozen --no-install-project
# The nacre package comes from the build context, not from the lockfile.
COPY pyproject.toml README.md /build/nacre/
COPY src /build/nacre/src
RUN uv pip install --python /opt/venv/bin/python --no-deps /build/nacre

# ---------------------------------------------------------------- Quantum ESPRESSO
FROM devel AS qe
ARG QE_TAG=qe-7.6
ARG QE_COMMIT=9f93ddec427d2b9a45bb72d828c6d324f62fcabd
ARG BUILD_JOBS=4
RUN git clone --branch "${QE_TAG}" --recurse-submodules --shallow-submodules --depth 1 https://github.com/QEF/q-e.git /src/q-e \
 && cd /src/q-e \
 && test "$(git rev-parse HEAD)" = "${QE_COMMIT}"
RUN cmake -S /src/q-e -B /build/qe -G Ninja \
      -D CMAKE_BUILD_TYPE=Release \
      -D CMAKE_INSTALL_PREFIX=/opt/qe \
      -D CMAKE_Fortran_COMPILER=mpif90 -D CMAKE_C_COMPILER=mpicc \
      -D QE_ENABLE_MPI=ON -D QE_ENABLE_OPENMP=ON -D QE_ENABLE_SCALAPACK=ON \
      -D QE_FFTW_VENDOR=FFTW3 -D QE_LAPACK_INTERNAL=OFF \
 && cmake --build /build/qe -j"${BUILD_JOBS}" \
 && cmake --install /build/qe

# ---------------------------------------------------------------- final image
FROM ${UBUNTU} AS final
ARG APT_SNAPSHOT=20260901T000000Z
ENV DEBIAN_FRONTEND=noninteractive
RUN sed -i -E "s#https?://(archive|security)\.ubuntu\.com/ubuntu/?#http://snapshot.ubuntu.com/ubuntu/${APT_SNAPSHOT}/#" /etc/apt/sources.list.d/ubuntu.sources \
 && apt-get update \
 && apt-get install -y --no-install-recommends \
      python3.12 openssh-server openssh-client git curl ca-certificates less procps \
      openmpi-bin libgfortran5 libgomp1 libfftw3-double3 libfftw3-mpi3 libopenblas0 liblapack3 libscalapack-openmpi2.2 \
 && rm -rf /var/lib/apt/lists/* \
 && (userdel -r ubuntu 2>/dev/null || true) \
 && useradd -m -u 1000 -s /bin/bash nacre

COPY --from=pyenv /opt/venv /opt/venv
COPY --from=qe /opt/qe /opt/qe
COPY env/common/entrypoint.sh /usr/local/bin/nacre-entrypoint
COPY env/common/sshd_config /etc/ssh/sshd_config
# Containers rarely allow CMA; OMP_NUM_THREADS defaults to 1 so MPI x OpenMP is set explicitly.
ENV PATH=/opt/venv/bin:/opt/qe/bin:${PATH} \
    OMPI_MCA_btl_vader_single_copy_mechanism=none \
    OMPI_MCA_rmaps_base_oversubscribe=1 \
    OMP_NUM_THREADS=1 \
    ESPRESSO_PSEUDO=/home/nacre/pseudo \
    PYTHONUNBUFFERED=1

ARG GIT_SHA=unknown
ARG BUILD_DATE=unknown
LABEL org.opencontainers.image.title="nacre-shell-cpu" \
      org.opencontainers.image.source="https://github.com/pa1aash/nacre-shell" \
      org.opencontainers.image.revision="${GIT_SHA}" \
      org.opencontainers.image.created="${BUILD_DATE}"

WORKDIR /home/nacre
EXPOSE 22
ENTRYPOINT ["/usr/local/bin/nacre-entrypoint"]
CMD []

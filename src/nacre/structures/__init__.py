"""Builders for the illustrative atomistic structures of the preprint figures.

Every structure written here is an illustrative construction for Figures 1 and 2,
not a simulated structure. Each builder returns an ``ase.Atoms`` whose ``info``
carries the metadata written by :func:`nacre.structures.meta.write_structure`.

Run ``python -m nacre.structures.build`` to (re)build every target listed in
``structures/preprint/build.yaml``.
"""

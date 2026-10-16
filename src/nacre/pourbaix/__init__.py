"""Thermodynamic stability screens for claim C5.

R-slurry: a multi-element aqueous Pourbaix diagram for Al-Ca-C-O-H. R-cell: a Li-referenced
stability window, with lithiation limits from the Li-open grand potential and oxidation limits
from explicit oxidation reactions. Both are thermodynamic proxies: they say which phases are
stable at equilibrium, not how fast anything corrodes or dissolves.

All energies come from the offline cache under results/preprint/pourbaix/cache/, which
`python -m nacre.pourbaix.cache fetch` fills from the Materials Project API and NIST-JANAF.
"""

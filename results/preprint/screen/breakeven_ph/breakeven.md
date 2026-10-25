# Break-even ratio r* of the saturated-sink exclusions (PH-W4.9)

r* = exp[(E_c - E_ub - m_expt) / (2 R T / F)], T = 298.15 K, nu_salt = 1: the exclusion of a row at a cutoff edge E_c stands while a_pm,sat / a_pm < r* (claims_redirect Section 2h; m_sink = 2 nu (R T / F) ln(a_pm,sat / a_pm)). One decade of the ratio costs 2 ln10 R T / F = 118.3 mV of headroom. E_ub and m_expt are the ALL row of ladder_v3.csv.

| phase | framing | stage | class | E_c (V) | E_ub (V) | m_expt (V) | headroom (mV) | r* |
|---|---|---|---|---|---|---|---|---|
| brushite | crystalline | slurry | C_hi | 4.4 | 4.2658 | 0.1665 | -32.3 | not excluded without correction |
| brushite | crystalline | slurry | C_hi | 4.5 | 4.2658 | 0.1665 | 67.7 | 3.73 |
| ACP | crystalline | slurry | C_mid | 4.2 | 4.0223 | 0.148 | 29.7 | 1.78 |
| ACP | crystalline | slurry | C_mid | 4.3 | 4.0223 | 0.148 | 129.7 | 12.5 |
| ACP | crystalline | slurry | C_hi | 4.4 | 4.0223 | 0.148 | 229.7 | 87.4 |
| ACP | crystalline | slurry | C_hi | 4.5 | 4.0223 | 0.148 | 329.7 | 612 |
| HAp | crystalline | slurry | C_mid | 4.2 | 4.0674 | 0.1244 | 8.2 | 1.17 |
| HAp | crystalline | slurry | C_mid | 4.3 | 4.0674 | 0.1244 | 108.2 | 8.21 |
| HAp | crystalline | slurry | C_hi | 4.4 | 4.0674 | 0.1244 | 208.2 | 57.5 |
| HAp | crystalline | slurry | C_hi | 4.5 | 4.0674 | 0.1244 | 308.2 | 403 |
| b-TCP | crystalline | slurry | C_mid | 4.2 | 4.0223 | 0.148 | 29.7 | 1.78 |
| b-TCP | crystalline | slurry | C_mid | 4.3 | 4.0223 | 0.148 | 129.7 | 12.5 |
| b-TCP | crystalline | slurry | C_hi | 4.4 | 4.0223 | 0.148 | 229.7 | 87.4 |
| b-TCP | crystalline | slurry | C_hi | 4.5 | 4.0223 | 0.148 | 329.7 | 612 |
| a-TCP | crystalline | slurry | C_mid | 4.2 | 3.981 | 0.1654 | 53.6 | 2.84 |
| a-TCP | crystalline | slurry | C_mid | 4.3 | 3.981 | 0.1654 | 153.6 | 19.9 |
| a-TCP | crystalline | slurry | C_hi | 4.4 | 3.981 | 0.1654 | 253.6 | 139 |
| a-TCP | crystalline | slurry | C_hi | 4.5 | 3.981 | 0.1654 | 353.6 | 974 |
| Ca2SiO4 | crystalline | comparator | C_mid | 4.2 | 3.4561 | 0.0937 | 650.2 | 3.13e+05 |
| Ca2SiO4 | crystalline | comparator | C_mid | 4.3 | 3.4561 | 0.0937 | 750.2 | 2.19e+06 |
| Ca2SiO4 | crystalline | comparator | C_hi | 4.4 | 3.4561 | 0.0937 | 850.2 | 1.53e+07 |
| Ca2SiO4 | crystalline | comparator | C_hi | 4.5 | 3.4561 | 0.0937 | 950.2 | 1.07e+08 |
| CaCO3 | crystalline | control | C_mid | 4.2 | 3.9378 | 0.087 | 175.2 | 30.3 |
| CaCO3 | crystalline | control | C_mid | 4.3 | 3.9378 | 0.087 | 275.2 | 212 |
| CaCO3 | crystalline | control | C_hi | 4.4 | 3.9378 | 0.087 | 375.2 | 1.48e+03 |
| CaCO3 | crystalline | control | C_hi | 4.5 | 3.9378 | 0.087 | 475.2 | 1.04e+04 |

Provenance: code sha 9863ef632871a3c0a19a6edecd029cc3b5b778f1; ladder sha256 595636ef1c7cfd774e27040f7a60f5f32ff7e55569525a7a84e009ef37354d6b; thresholds copy sha256 5444a4a090dad6b532566499d63f405b8710e3b9470a0f4c99fdba35b096c74b.

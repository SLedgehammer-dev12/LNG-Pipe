# Ticket 01: Thermodynamic Real-Fluid Engine for Cryogenic LNG

Status: resolved
Blocked by: none

## What it delivers
Implement `core/fluids.py` using CoolProp Helmholtz EOS to calculate exact cryogenic fluid properties:
- Fluid density $\rho(T, P)$
- Specific heat $c_p(T, P)$
- Dynamic viscosity $\mu(T, P)$
- Thermal conductivity $k(T, P)$
- Saturation vapor pressure $P_{sat}(T)$
- Pure methane ($CH_4$) and multi-component mixtures (Methane, Ethane, Propane, Nitrogen)
- Fallback analytical / Peng-Robinson correlations in case CoolProp encounters numeric issues near critical point.

## Verification
- Unit test suite verifying properties at $T = 111.5\text{ K}$, $P = 1.013\text{ bar}$ against published NIST data ($\rho \approx 422.6\text{ kg/m}^3$, $P_{sat} \approx 101.3\text{ kPa}$).

# Ticket 02: Multi-Layer Radial Thermal Resistance Network

Status: resolved
Blocked by: 01

## What it delivers
Implement `core/heat_transfer.py` calculating heat ingress per meter $q'$ ($W/m$):
- Internal forced convection $h_i$ (Dittus-Boelter / Gnielinski correlation using Reynolds and Prandtl numbers).
- Cryogenic pipe metal conduction: Stainless Steel 304L/316L, Invar, 9% Ni Steel ($k_{pipe}(T)$).
- Multi-layer insulation sheath: Aerogel, PIR/PUR foam, Cellular glass, Elastomeric foam, Vacuum jacket with radiation shielding ($k_{ins}$).
- External ambient convection $h_o$ (Churchill-Chu natural convection or forced wind convection) + surface radiation (Stefan-Boltzmann with surface emissivity $\varepsilon$).
- Radial thermal resistance summation: $R'_{total} = R'_{int} + R'_{pipe} + \sum R'_{ins,j} + R'_{ext}$.
- Heat flux: $q' = (T_{amb} - T_{fluid}) / R'_{total}$.

## Verification
- Test radial temperature drop: $T_{fluid} < T_{pipe,inner} < T_{pipe,outer} < T_{ins,outer} < T_{amb}$.
- Verify that doubling insulation thickness substantially reduces heat ingress $q'$.

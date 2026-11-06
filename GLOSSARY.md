# LNG Pipeline Domain Glossary

Core domain model vocabulary for LNG cryogenic pipeline thermal-hydraulic modeling. Maintained and updated through the `/domain-modeling` and `/grill-with-docs` skills.

## Rules

- **Be opinionated**: When multiple terms exist for the same domain concept, define the canonical one and list discarded alternatives under `_Avoid_`.
- **Keep definitions tight**: 1-2 sentences defining what the concept IS.
- **Domain-specific terms only**: Standard software engineering patterns (ORM, REST, timeout) do not belong here; only terms native to cryogenic fluid mechanics, thermodynamics, and pipeline engineering belong here.

## Language

**LNG (Liquefied Natural Gas)**:
Cryogenic liquid hydrocarbon mixture composed predominantly of methane ($CH_4$, typically 90–99 mol%), with small fractions of ethane ($C_2H_6$), propane ($C_3H_8$), and nitrogen ($N_2$), transported at temperatures near its boiling point (110–123 K / -163 to -150 °C).
_Avoid_: CNG, LPG, NGL

**Saturation Vapor Pressure ($P_{sat}$)**:
The thermodynamic equilibrium vapor pressure exerted by the LNG mixture over its liquid phase at the local bulk temperature $T(x)$.
_Avoid_: Head pressure, static pressure

**Flashing Margin (Cavitation / Boiling Margin)**:
The local pressure difference between total static fluid pressure and saturation vapor pressure: $\Delta P_{flash}(x) = P(x) - P_{sat}(T(x))$.
_Avoid_: Safety buffer, head loss

**Boil-Off Gas (BOG)**:
Vapor generated when heat ingress into the pipeline causes the local fluid temperature and enthalpy to cross into the two-phase vapor-liquid dome.
_Avoid_: Evaporated gas, blow-off

**Radial Thermal Resistance Network ($R'_{th}$)**:
The sum of conductive, convective, and radiative thermal resistances per meter of pipe length between ambient surroundings and flowing LNG.
_Avoid_: Overall U-value, insulation loss

**Darcy Friction Factor ($f$)**:
Dimensionless flow resistance coefficient calculated via the Colebrook-White equation or Churchill correlation across laminar, transition, and fully turbulent regimes.
_Avoid_: Roughness factor, drag coefficient

**3D Cylindrical Finite-Volume Mesh ($r, \theta, z$)**:
Volumetric discretization of the pipe flow and pipe wall into radial shells ($r$), azimuthal sectors ($\theta$), and axial marching slices ($z$).
_Avoid_: Cartesian grid, 1D line element

**Thermal Boundary Layer ($\delta_t$)**:
The near-wall annular fluid layer across which temperature gradients between the warm pipe wall and the subcooled liquid core develop.
_Avoid_: Film thickness, surface layer

**Wall Flashing (Near-Wall Nucleation)**:
Localized vaporization initiated at the inner pipe surface where fluid temperature $T(r=R, \theta, z)$ is highest, before bulk core saturation is reached.
_Avoid_: Surface cavitation, bubble creep

# 0003: 3D Cylindrical Finite-Volume Marching Thermal-Hydraulic Solver

We adopt a 3D cylindrical $(r, \theta, z)$ finite-volume marching numerical solver to resolve radial thermal boundary layers, azimuthal stratification, and localized near-wall flashing alongside total hydraulic pressure loss.

## Context

A 1D lumped model averages fluid temperature across the entire pipe cross-section ($T_b(z)$). In cryogenic LNG pipelines exposed to ambient heat ingress, heat flows radially inward from the insulation and pipe wall into the fluid. Consequently, the liquid layer immediately adjacent to the inner pipe wall ($r \to R_{in}$) is significantly warmer than the cryogenic core ($r \to 0$).

As saturation vapor pressure $P_{sat}$ rises exponentially with temperature ($P_{sat} \propto \exp(-H_{vap}/RT)$), **flashing and bubble nucleation initiate at the pipe wall long before the bulk liquid reaches saturation**. 1D models fail to detect this early wall boiling, leading to unexpected two-phase slugging or pump cavitation. Additionally, inclination and solar/wind orientation create azimuthal ($\theta$) non-uniformities.

## Decision

1. **Cylindrical Coordinate Grid ($r, \theta, z$)**:
   - Axial marching coordinate $z \in [0, L]$ with $N_z$ slices.
   - Radial coordinate $r \in [0, R_{in}]$ with $N_r$ annular control volumes inside the fluid, plus cells in the pipe metal wall and insulation.
   - Azimuthal coordinate $\theta \in [0, 2\pi)$ with $N_\theta$ angular sectors.
2. **Coupled Energy & Momentum Governing Equations**:
   - Momentum: Axial velocity profile $u_z(r, \theta)$ modeled via turbulent power-law / 1/7th velocity profile for high Reynolds flow. Wall shear stress $\tau_w(\theta, z) = \mu_{eff} \left.\frac{\partial u_z}{\partial r}\right|_w$ integrated along the perimeter determines the exact hydraulic frictional pressure drop $\frac{dP}{dz} = - \frac{1}{A} \oint \tau_w dS - \rho_m g \sin(\theta)$.
   - Energy: Convection-diffusion equation solved in each cell $(i, j, k)$:
     $$\rho c_p u_z \frac{\partial T}{\partial z} = \frac{1}{r}\frac{\partial}{\partial r}\left( r k_{eff} \frac{\partial T}{\partial r} \right) + \frac{1}{r^2}\frac{\partial}{\partial \theta}\left( k_{eff} \frac{\partial T}{\partial \theta} \right)$$
     where $k_{eff} = k_{fluid} + k_{turb}$.
3. **Dual Flashing Detection**:
   - **Bulk Flashing**: $P(z) \le P_{sat}(T_{bulk}(z))$.
   - **Near-Wall Flashing**: $P(z) \le P_{sat}(T_{wall}(z))$. Accurately predicts the early onset of boundary-layer micro-boiling.

## Consequences

- Pinpoints exact location and radial depth of thermal boundary layers and wall boiling onset.
- Preserves fast sub-second interactive execution via vectorized NumPy tensor operations.
- Enhances 3D WebGL Three.js visualizer with true volumetric $(r, \theta, z)$ temperature contour fields.

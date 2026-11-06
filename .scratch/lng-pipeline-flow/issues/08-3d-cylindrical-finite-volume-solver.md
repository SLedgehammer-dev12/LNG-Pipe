# Ticket 08: 3D Cylindrical Finite-Volume Marching Thermal-Hydraulic Solver

Status: resolved
Blocked by: 01, 02

## What it delivers
Implement `core/solver_3d.py`:
- 3D structured cylindrical grid: $r \in [0, R_{in}]$, $\theta \in [0, 2\pi)$, $z \in [0, L]$.
- Turbulent velocity profile $u_z(r) = u_{max} (1 - r/R_{in})^{1/7}$ matching total mass flow rate $\dot{m}$.
- Frictional pressure gradient $\frac{dP}{dz}$ derived from wall shear stress and Darcy friction factor, plus hydrostatic inclination gradient $\rho g \sin(\theta)$.
- 2D cross-sectional thermal diffusion marching along $z$:
  - Cell energy balance with radial conduction, azimuthal conduction, and axial advection $\rho c_p u_z \frac{\partial T}{\partial z}$.
  - Inner wall boundary condition coupled with pipe metal and multi-layer insulation radial heat ingress $q''(\theta, z)$.
- Compute full 3D fields:
  - $T(r_i, \theta_j, z_k)$
  - $P(z_k)$
  - $P_{sat}(r_i, \theta_j, z_k)$
  - Near-wall vs bulk flashing points: $x_{flash,wall}$ vs $x_{flash,bulk}$.

## Verification
- Cross-sectional energy integral must balance cumulative radial heat leak: $\int_A \rho c_p u_z (T(r,\theta,L) - T_{in}) dA \approx Q_{tot}$.
- Wall temperature $T(r=R)$ must exceed core temperature $T(r=0)$ under heating ($T_{amb} > T_{fluid}$).
- Near-wall flashing $x_{flash,wall} \le x_{flash,bulk}$ (wall boils earlier than bulk core).

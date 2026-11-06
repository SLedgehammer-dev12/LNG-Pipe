# Ticket 03: 1D Finite-Volume Thermal-Hydraulic Pipeline Solver

Status: resolved
Blocked by: 01, 02

## What it delivers
Implement `core/solver.py` dividing pipeline of length $L$ into $N$ control volumes:
- For each slice $i \in [0, N-1]$:
  - Local velocity: $v_i = \dot{m} / (\rho_i \cdot A_{flow})$.
  - Churchill friction factor $f_i(Re_i, \varepsilon / D_i)$.
  - Frictional pressure drop: $dP_{fric} = f_i \frac{dx}{D_i} \frac{\rho_i v_i^2}{2}$.
  - Hydrostatic pressure change: $dP_{hydro} = \rho_i g \sin(\theta) dx$.
  - Total pressure update: $P_{i+1} = P_i - dP_{fric} - dP_{hydro}$.
  - Heat ingress $q'_i$ from radial thermal network.
  - Temperature rise: $dT = \frac{q'_i dx}{\dot{m} c_{p,i}} \implies T_{i+1} = T_i + dT$.
  - Saturation vapor pressure update: $P_{sat,i+1} = P_{sat}(T_{i+1})$.
  - Flashing margin: $\Delta P_{margin,i+1} = P_{i+1} - P_{sat,i+1}$.
- Detect flashing point $x_{flash}$ where $\Delta P_{margin} \le 0$ (boiling onset).
- Track cumulative heat ingress $Q_{tot} = \sum q'_i dx$.

## Verification
- First Law balance: $\dot{m} \cdot (h_{out} - h_{in}) \approx Q_{tot}$.
- Second Law monotonicity: $dT/dx > 0$ when $T_{amb} > T_{fluid}$.
- Zero flow / zero heat leak asymptotic tests.

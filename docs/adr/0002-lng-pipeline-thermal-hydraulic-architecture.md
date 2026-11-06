# 0002: LNG Pipeline Thermal-Hydraulic Solver & Visualization Architecture

We adopt a 1D finite-volume marching numerical solver coupled with CoolProp Helmholtz EOS real-fluid thermodynamics and a modern Streamlit + Three.js interactive UI.

## Context

LNG pipeline transfer involves cryogenic fluids (typically 111–125 K) flowing through long pipelines exposed to ambient conditions. Ingress of heat increases bulk fluid temperature, which exponentially raises saturation vapor pressure $P_{sat}$. Simultaneously, friction drops total pressure $P$. If $P(x) \le P_{sat}(T(x))$, flashing occurs, threatening pump cavitation, slug formation, and structural vibration.

## Decision

1. **Fluid Thermophysical Model**: We use **CoolProp** (Helmholtz Energy formulation) for real cryogenic fluid density $\rho(T, P)$, specific heat $c_p(T, P)$, viscosity $\mu(T, P)$, thermal conductivity $k(T, P)$, and saturation vapor pressure $P_{sat}(T)$.
2. **Coupled 1D Finite-Volume Discretization**: We divide pipe length $L$ into $N$ control volumes ($N \ge 100$). For each cell $i$:
   - Compute radial heat ingress: $q'_i = \frac{T_{amb} - T_i}{R'_{conv,int} + R'_{cond,pipe} + \sum R'_{cond,ins} + R'_{ext}}$
   - Energy conservation: $\frac{dT}{dx} = \frac{q'_i}{\dot{m} \cdot c_{p,i}}$
   - Momentum conservation: $\frac{dP}{dx} = - f_i \frac{\rho_i v_i^2}{2 D_i} - \rho_i g \sin(\theta)$
   - Monitor Flashing Margin: $\Delta P_{margin,i} = P_i - P_{sat}(T_i)$
3. **Interactive User Experience**: Streamlit web interface with responsive input parameter sidebars, Plotly 2D hydraulic/thermal gradients, and an embedded custom **Three.js WebGL 3D Pipe Cutaway** component for real-time visualization of temperature fields, flow velocity vectors, and insulation layers.
4. **Professional Output**: Automated PDF report generation (via ReportLab) with compliance checks against cryogenic codes (ASME B31.3 Chapter IX and EN 1473).

## Consequences

- Highly accurate, physically sound predictions matching real field data.
- Instant visual feedback on whether a pipeline design will flash before reaching the discharge destination.

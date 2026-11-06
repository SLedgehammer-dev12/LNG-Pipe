# Spec: LNG Cryogenic Pipeline Thermal-Hydraulic Modeling & Interactive Simulation

Status: ready-for-agent

## Problem Statement

When cryogenic Liquefied Natural Gas (LNG) flows through industrial transport pipelines (e.g. from marine loading arms to onshore tanks, or between process units), environmental heat ingress warms the fluid. Because saturation vapor pressure ($P_{sat}$) increases exponentially with temperature while fluid friction reduces static pressure ($P$), designers and operators need exact predictions of bulk temperature, total pressure, and vapor pressure profiles along the pipe length to prevent boil-off gas (BOG) formation, cavitation in downstream equipment, and overpressure events. Current spreadsheet tools lack rigorous real-fluid equations of state, multi-layer radial insulation heat transfer, and intuitive 2D/3D visual inspection.

## Solution

A web application built with Streamlit, CoolProp, Plotly, and Three.js WebGL:
1. **Thermodynamic Engine**: CoolProp Helmholtz energy EOS computing real thermophysical properties ($\rho, c_p, \mu, k, P_{sat}$) for pure methane and multi-component LNG mixtures ($CH_4, C_2H_6, C_3H_8, N_2$).
2. **1D Finite-Volume Thermal-Hydraulic Solver**: Marches along pipe length $L$ in $N$ discrete control volumes, computing coupled radial heat transfer (internal convection, pipe wall, multi-layer insulation, external convection and radiation) and momentum drop (Churchill / Colebrook friction factor, hydrostatic head).
3. **Flashing & Cavitation Alert**: Flags the exact coordinate $x_{flash}$ where total pressure falls below saturation pressure ($P(x) \le P_{sat}(T(x))$), computing local vaporization onset, net positive suction head (NPSH) margin, and vapor quality.
4. **Interactive 2D & 3D Visualization**:
   - 2D Plotly curves: $T(x)$, $P(x)$ vs $P_{sat}(x)$, Flashing Margin $\Delta P(x)$, and Radial Temperature Distribution through insulation layers.
   - Interactive Three.js 3D Pipe Cutaway component: Shows internal flowing fluid stream with velocity color gradient, pipe metal, insulation sheath, thermal contours, and flashing alert marker.
5. **Professional PDF/Excel Reporting**: One-click generation of engineering reports including ASME B31.3 / EN 1473 guidance checks, design margins, and input/output summaries.

## User Stories

1. As a cryogenic piping engineer, I want to define pipe geometry (internal diameter, wall thickness, pipe roughness, length, inclination angle) so that accurate hydraulic friction and elevation head are modeled.
2. As a process engineer, I want to specify inlet conditions (temperature in °C or K, pressure in bar or kPa, mass flow rate in kg/s or t/h) so that real plant operating scenarios can be evaluated.
3. As a pipeline designer, I want to select pipe material (e.g. Stainless Steel 304L/316L, 9% Nickel Steel, Invar) and configure multi-layer insulation (PIR foam, Cryogenic Aerogel, Cellular Glass, Vacuum Jacketed) with individual thicknesses and thermal conductivities so that realistic heat ingress is calculated.
4. As an engineer, I want to select LNG fluid composition (pure methane or custom mole fractions of C1, C2, C3, N2) so that non-ideal mixture thermodynamic properties are correctly captured.
5. As an operator, I want to see a direct comparison plot of Total Static Pressure $P(x)$ vs Saturation Vapor Pressure $P_{sat}(x)$ along the pipeline to immediately detect if and where boiling or cavitation occurs.
6. As a visual inspector, I want to interact with a 3D cutaway model of the pipeline in my browser to rotate, pan, and observe fluid flow, thermal layers, and critical warning zones.
7. As a project manager, I want to export a stamped PDF engineering calculation report summarizing design inputs, governing equations, outlet conditions, and safety margins.

## Implementation Decisions

1. **Architecture & Seams**:
   - `core/fluids.py`: CoolProp wrapper for cryogenic real fluid thermophysical properties.
   - `core/heat_transfer.py`: Multi-layer radial conduction, internal Dittus-Boelter / Gnielinski convection, and external Churchill-Chu natural/forced convection + radiation.
   - `core/hydraulic.py`: Churchill friction factor (valid for laminar, transition, and rough turbulent) and 1D momentum conservation.
   - `core/solver.py`: 1D finite-volume marching solver coupling heat transfer and hydraulics over $N$ axial slices.
   - `components/pipe_3d_viewer.py`: Streamlit custom component hosting Three.js WebGL 3D pipe cutaway visualizer.
   - `components/charts_2d.py`: Plotly interactive charts for $P$ vs $P_{sat}$, $T(x)$, radial gradient, and phase envelope.
   - `reports/pdf_report.py`: ReportLab automated engineering summary sheet.
   - `app.py`: Streamlit entry point organizing inputs, calculations, 2D/3D views, and report downloads.

## Testing Decisions

- Unit tests for `core/fluids.py` verifying CoolProp values against NIST REFPROP reference points for pure methane at 111.5 K and 1 bar.
- Physical invariant tests in `test_solver.py`:
  - First Law energy conservation: $\Delta H = Q_{total} = \dot{m} \int c_p dT$.
  - Second Law monotonicity: Fluid temperature strictly increases along pipe when $T_{amb} > T_{fluid}$.
  - Degeneracy limit: Zero heat transfer ($k_{ins} \to 0$ or vacuum) produces flat temperature profile ($T_{out} = T_{in}$).
  - Friction monotonicity: Higher mass flow rate yields greater pressure drop ($\partial \Delta P / \partial \dot{m} > 0$).
  - Flashing detection test: Ensure solver accurately marks $x_{flash}$ when $P \le P_{sat}$.

## Out of Scope

- Dynamic transient water hammer / thermal shock calculations (steady-state 1D flow only).
- Cryogenic cooldown simulation over time (steady-state operating conditions only).

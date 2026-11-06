# Ticket 06: Professional PDF Engineering Report Generator

Status: resolved
Blocked by: 03

## What it delivers
Implement `reports/pdf_report.py` using ReportLab to export clean, branded engineering calculation sheets:
1. **Executive Summary**: Project name, date, user info, pipe tag ID, pass/fail status for cryogenic boiling.
2. **Design Inputs Table**: Pipe geometry (ID, OD, thickness, length, slope), insulation schedule, fluid composition, inlet $T$ and $P$, flow rate, ambient environment.
3. **Calculation Results Table**: Outlet temperature, total pressure drop, outlet vapor pressure, minimum flashing margin, total heat leak ($kW$ and $W/m$).
4. **Code Compliance & Safety Verification**: ASME B31.3 Chapter IX Cryogenic Piping and EN 1473 recommendations (minimum velocity, maximum flow velocity to avoid electrostatic buildup, boil-off risk).
5. **Chart Embeddings**: Summary graphics and signature approval box.

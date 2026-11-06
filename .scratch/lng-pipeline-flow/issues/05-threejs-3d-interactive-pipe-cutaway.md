# Ticket 05: Three.js WebGL Interactive 3D Pipe Cutaway Component

Status: resolved
Blocked by: 03

## What it delivers
Implement `components/pipe_3d_viewer.py` containing a custom Three.js WebGL visualizer:
1. **Interactive 3D Pipeline Mesh**:
   - Cylindrical cutaway exposing the inner liquid core, metal pipe wall, and multi-layer insulation jackets.
   - Orbit controls (rotate, pan, zoom).
2. **Dynamic Thermal & Flow Effects**:
   - Liquid core color gradient mapped from inlet temperature (deep cryogenic blue) to outlet temperature (warming cyan / orange).
   - Animated flow particles or stream lines indicating flow direction and velocity.
   - Flashing marker / pulsating red beacon at $x_{flash}$ if boiling onset occurs.
3. **Layer Inspection Toggles**:
   - Buttons to toggle cutaway angles (90°, 180°, solid), show/hide insulation layers, toggle heat flux arrows penetrating the pipe radially.
   - Live telemetry HUD displaying local $(T, P, P_{sat}, \Delta P_{margin})$ under the cursor.

# Ticket 09: LNG Jetty-to-Tank Piping 2D Schematic & 3D Interactive Layout

Status: resolved
Blocked by: 07

## What it delivers
1. `components/pipeline_schematic_2d.py`:
   - Interactive 2D schematic of the entire LNG transfer and cooldown loop:
     * LNG Carrier (Gemi) at Berth
     * LUP Platform / Dolfeni with Marine Loading Arms (MLA) and ESDV-1
     * APD Dolphins (Approach Platform Dolphins) supporting the trestle
     * Omega Dolfenleri with $\Omega$-shaped expansion loops and Thermal Relief Valves (TRV)
     * Onshore Battery Limits and Kara LNG Tankı
     * Sirkülasyon Pompası (Recirculation pump) sending subcooled LNG back to LUP
     * Vapor Return Line (VRL) and BOG compressor
   - Visual telemetry nodes with live temperature, pressure, and flow indicators.
2. `components/terminal_3d_viewer.py`:
   - Three.js WebGL 3D world:
     * Sea surface, berthed LNG ship, LUP platform, APD piles, Omega loop dolphins, shoreline, and onshore storage tank.
     * Animated flow particles traveling from ship to tank, and back via the circulation return pipe.
     * Clickable equipment with inspection callouts.

## Verification
- Unit test ensuring HTML string generation for both 2D schematic and 3D terminal world (`tests/test_schematic.py`).
- Integrated into Streamlit UI in dedicated tabs ("🗺️ Terminal Hat Şematiği (2D P&ID)" and "⚓ 3D Terminal Dijital İkiz (Three.js)").
- All 15 tests in `tests/` pass.

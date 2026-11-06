# 0004: LNG Terminal Jetty-to-Tank Piping Schematic & 3D Interactive Layout

We integrate an interactive 2D P&ID schematic and a 3D Three.js digital twin layout representing the complete transfer and recirculation route between the LNG carrier, jetty dolphins, expansion loops, and onshore storage tank.

## Context

A real cryogenic marine transfer system is not just an isolated straight pipe. It forms a complete terminal loop:
1. **Berth & LUP Dolphin**: Marine Loading Arms (MLA) with Emergency Release Couplers (PERC) connect the LNG carrier to the Loading/Unloading Platform.
2. **Approach Trestle & APD Dolphins**: Fixed pile dolphins carrying the insulated pipe rack across open water toward the shore.
3. **Omega Dolphins ($\Omega$-Loops)**: Elevated expansion loops placed at regular intervals to absorb ~3 meters of thermal contraction per kilometer when cooling from +25 °C down to -162 °C without over-stressing pipe anchors.
4. **Onshore Cryogenic Storage Tank**: Full-containment atmospheric LNG tank with top-entry submerged pumps.
5. **Recirculation & Cooldown Loop**: A continuous recirculation circuit driven by an in-tank or onshore circulation pump that sends subcooled LNG back to the jetty during non-discharge standby to prevent pipe warm-up, vapor lock, and catastrophic thermal shock when a vessel arrives.

## Decision

1. **2D Interactive P&ID Flow Schematic (`components/pipeline_schematic_2d.py`)**:
   - SVG / HTML5 interactive canvas rendering the complete flow circuit:
     * LNG Carrier $\to$ LUP Dolphin (with Marine Loading Arms & ESDV-1)
     * APD Dolphins 1 & 2 $\to$ Omega Dolphin 1 ($\Omega$-Loop with TRV)
     * APD Dolphins 3 & 4 $\to$ Omega Dolphin 2 ($\Omega$-Loop with TRV)
     * Shoreline Boundary Limit $\to$ Kara LNG Depolama Tankı (Full containment)
     * Sirkülasyon Pompası (Recirculation pump) $\to$ Jetty Return Line $\to$ Vessel/LUP Quench.
   - Live telemetry overlays: local temperature, pressure, flow rate, and valve open/closed states.
2. **3D Three.js Terminal Digital Twin (`components/terminal_3d_viewer.py`)**:
   - Three.js WebGL scene modeling the complete marine environment:
     * Realistic sea water surface with gentle wave motion.
     * 3D LNG Carrier berthed alongside mooring dolphins.
     * LUP Platform with articulated loading arms.
     * Concrete pile APD dolphins supporting the approach trestle.
     * Prominent 3D $\Omega$-shaped expansion loops over specialized Omega dolphins.
     * Onshore terrain with the cylindrical Full-Containment LNG Tank.
     * Dual pipeline run: Main LNG Unloading line (blue $\to$ teal) and Cooldown Recirculation line (cyan).
     * Interactive camera orbit, clickable equipment hotspots, and layer toggles.

## Consequences

- Bridges the gap between pure 1D/3D numerical solvers and real-world cryogenic terminal layout.
- Enables operators and engineers to visualize exactly where thermal expansion loops, dolphins, and safety relief valves reside along the transfer corridor.

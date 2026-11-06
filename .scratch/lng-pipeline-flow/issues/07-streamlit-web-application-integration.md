# Ticket 07: Streamlit Web Application Integration

Status: resolved
Blocked by: 04, 05, 06

## What it delivers
Implement `app.py`:
1. **Modern Layout & Ergonomics**:
   - Clean industrial sidebar with collapsible sections: Pipeline Geometry, Fluid & Inflow Conditions, Insulation Schedule, Ambient Conditions.
   - Preset selector: "Marine Jetty Transfer Line (DN250, 500m)", "LNG Bunkering Hose/Pipe (DN100, 50m)", "Long Distance Onshore Cryoline (DN400, 2000m)".
2. **Main KPI Cards**:
   - Outlet Temperature $T_{out}$ & $\Delta T$
   - Total Pressure Drop $\Delta P$
   - Vapor Pressure Rise $\Delta P_{sat}$
   - Minimum Flashing Margin $\Delta P_{min}$ (with Green/Red alert status)
   - Total Heat Ingress $Q_{total}$ ($kW$)
3. **Tabbed Viewports**:
   - **Tab 1: 3D Interactive Pipeline**: Embedded Three.js cutaway viewer.
   - **Tab 2: 2D Profiles & Flashing Analytics**: $P$ vs $P_{sat}$, $T(x)$, margin, radial gradient.
   - **Tab 3: Axial Data Inspection Table**: Paginated / downloadable CSV of slice-by-slice values.
   - **Tab 4: Professional Documentation & Export**: Instant PDF engineering report download & Excel export.

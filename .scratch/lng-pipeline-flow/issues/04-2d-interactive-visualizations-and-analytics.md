# Ticket 04: 2D Interactive Visualizations & Analytics

Status: resolved
Blocked by: 03

## What it delivers
Implement `components/charts_2d.py` providing rich Plotly interactive diagrams:
1. **Total Pressure vs Saturation Vapor Pressure ($P$ vs $P_{sat}$)** along length $x$:
   - Displays $P(x)$, $P_{sat}(x)$, with a shaded danger area if $P(x) \le P_{sat}(x)$ and an annotation marking $x_{flash}$.
2. **Bulk Temperature Profile ($T(x)$)** along pipe length with ambient reference line.
3. **Flashing / Cavitation Margin ($\Delta P_{margin}(x)$)** with clear zero-threshold boundary line.
4. **Radial Insulation Temperature Distribution**:
   - Bar / line plot showing temperature across fluid $\to$ inner pipe $\to$ outer pipe $\to$ insulation layer 1 $\to$ insulation layer 2 $\to$ ambient.
5. **Thermodynamic $P-T$ Phase Envelope**:
   - Shows operating trajectory $(P(x), T(x))$ plotted relative to the saturation curve $P_{sat}(T)$.

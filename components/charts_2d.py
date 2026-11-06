"""Interactive 2D Plotly engineering charts for LNG pipeline flow."""

from typing import Dict, Any, Union
import math
import numpy as np
import plotly.graph_objects as go
from core.solver import PipelineSimulationResults
from core.solver_3d import Simulation3DResults


def _apply_theme(fig: go.Figure) -> go.Figure:
    """Applies clean, high-contrast engineering dark styling."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0e1117",
        plot_bgcolor="#161b22",
        margin=dict(l=40, r=40, t=50, b=40),
        font=dict(family="Inter, -apple-system, sans-serif", size=12, color="#c9d1d9"),
        legend=dict(
            bgcolor="rgba(22, 27, 34, 0.8)",
            bordercolor="rgba(255, 255, 255, 0.1)",
            borderwidth=1
        ),
        hovermode="x unified"
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="#21262d")
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="#21262d")
    return fig


def create_pressure_comparison_chart(results: Union[PipelineSimulationResults, Simulation3DResults]) -> go.Figure:
    """Plots Total Static Pressure vs Saturation Vapor Pressure along pipe length."""
    x = results.distance_m
    p_bar = [p / 1e5 for p in results.pressure_pa]

    fig = go.Figure()

    # Total Pressure
    fig.add_trace(go.Scatter(
        x=x,
        y=p_bar,
        mode="lines",
        name="Toplam Statik Basınç P(x)",
        line=dict(color="#58a6ff", width=3),
        hovertemplate="Toplam Basınç: %{y:.3f} bar<extra></extra>"
    ))

    if isinstance(results, Simulation3DResults):
        p_sat_wall_bar = [p / 1e5 for p in results.wall_vapor_pressure_pa]
        p_sat_bulk_bar = [p / 1e5 for p in results.bulk_vapor_pressure_pa]

        fig.add_trace(go.Scatter(
            x=x,
            y=p_sat_wall_bar,
            mode="lines",
            name="Çeper Doyma Basıncı Psat(T_wall) [3D]",
            line=dict(color="#f85149", width=2.5, dash="dash"),
            hovertemplate="Çeper Psat: %{y:.3f} bar<extra></extra>"
        ))
        fig.add_trace(go.Scatter(
            x=x,
            y=p_sat_bulk_bar,
            mode="lines",
            name="Yığın Doyma Basıncı Psat(T_bulk)",
            line=dict(color="#d29922", width=1.5, dash="dot"),
            hovertemplate="Yığın Psat: %{y:.3f} bar<extra></extra>"
        ))

        if results.has_wall_flashed and results.wall_flashing_point_m is not None:
            fig.add_vline(
                x=results.wall_flashing_point_m,
                line_width=2,
                line_dash="dot",
                line_color="#ff7b72",
                annotation_text=f"⚠️ Çeperde Flaş / Kaynama Başlangıcı ({results.wall_flashing_point_m} m)",
                annotation_position="top left",
                annotation_font=dict(color="#ff7b72", size=11)
            )
    else:
        p_sat_bar = [p / 1e5 for p in results.vapor_pressure_pa]
        fig.add_trace(go.Scatter(
            x=x,
            y=p_sat_bar,
            mode="lines",
            name="Doyma Buhar Basıncı Psat(T)",
            line=dict(color="#f85149", width=2.5, dash="dash"),
            hovertemplate="Buhar Basıncı: %{y:.3f} bar<extra></extra>"
        ))

        if results.has_flashed and results.flashing_point_m is not None:
            fig.add_vline(
                x=results.flashing_point_m,
                line_width=2,
                line_dash="dot",
                line_color="#ff7b72",
                annotation_text=f"⚠️ Flaş / Kaynama Başlangıcı ({results.flashing_point_m} m)",
                annotation_position="top left",
                annotation_font=dict(color="#ff7b72", size=11)
            )

    fig.update_layout(
        title=dict(text="<b>Toplam Basınç ve Doyma Buhar Basıncı Profili (P vs Psat)</b>", x=0.05),
        xaxis_title="Boru Uzunluğu x (m)",
        yaxis_title="Basınç (bar)"
    )
    return _apply_theme(fig)


def create_temperature_profile_chart(results: Union[PipelineSimulationResults, Simulation3DResults], temp_unit: str = "C") -> go.Figure:
    """Plots Bulk LNG temperature, center core, and wall temperatures."""
    x = results.distance_m
    t_offset = 273.15 if temp_unit == "C" else 0.0
    t_unit_str = "°C" if temp_unit == "C" else "K"

    fig = go.Figure()

    if isinstance(results, Simulation3DResults):
        t_bulk = [t - t_offset for t in results.bulk_temperature_k]
        t_center = [t - t_offset for t in results.center_temperature_k]
        t_wall = [t - t_offset for t in results.wall_temperature_k]

        fig.add_trace(go.Scatter(
            x=x, y=t_wall, mode="lines",
            name="İç Çeper Sıcaklığı T_wall(x) [3D]",
            line=dict(color="#f85149", width=2.5),
            hovertemplate=f"Çeper Sıcaklığı: %{{y:.2f}} {t_unit_str}<extra></extra>"
        ))
        fig.add_trace(go.Scatter(
            x=x, y=t_bulk, mode="lines",
            name="Yığın Sıvı Sıcaklığı T_bulk(x)",
            line=dict(color="#3fb950", width=2.5),
            hovertemplate=f"Yığın Sıcaklık: %{{y:.2f}} {t_unit_str}<extra></extra>"
        ))
        fig.add_trace(go.Scatter(
            x=x, y=t_center, mode="lines",
            name="Merkez Hattı Sıcaklığı T_center(x)",
            line=dict(color="#58a6ff", width=2.0, dash="dash"),
            hovertemplate=f"Merkez Çekirdek: %{{y:.2f}} {t_unit_str}<extra></extra>"
        ))
    else:
        t_fluid = [t - t_offset for t in results.temperature_k]
        t_pipe_in = [r["pipe_inner"] - t_offset for r in results.radial_temperatures]
        t_ins_out = [r["insulation_outer"] - t_offset for r in results.radial_temperatures]

        fig.add_trace(go.Scatter(
            x=x, y=t_fluid, mode="lines",
            name="LNG Akışkan Sıcaklığı T(x)",
            line=dict(color="#3fb950", width=3),
            hovertemplate=f"Akışkan Sıcaklığı: %{{y:.2f}} {t_unit_str}<extra></extra>"
        ))
        fig.add_trace(go.Scatter(
            x=x, y=t_pipe_in, mode="lines",
            name="Boru İç Çeper Sıcaklığı",
            line=dict(color="#79c0ff", width=1.5, dash="dot"),
            hovertemplate=f"İç Çeper: %{{y:.2f}} {t_unit_str}<extra></extra>"
        ))
        fig.add_trace(go.Scatter(
            x=x, y=t_ins_out, mode="lines",
            name="İzolasyon Dış Yüzey Sıcaklığı",
            line=dict(color="#d29922", width=1.5, dash="dash"),
            hovertemplate=f"İzolasyon Dışı: %{{y:.2f}} {t_unit_str}<extra></extra>"
        ))

    fig.update_layout(
        title=dict(text=f"<b>Boru Boyunca Termal Profil [{t_unit_str}]</b>", x=0.05),
        xaxis_title="Boru Uzunluğu x (m)",
        yaxis_title=f"Sıcaklık ({t_unit_str})"
    )
    return _apply_theme(fig)


def create_flashing_margin_chart(results: PipelineSimulationResults) -> go.Figure:
    """Plots Flashing / Cavitation Margin (P - Psat) with zero-line safety boundary."""
    x = results.distance_m
    margins_bar = [m / 1e5 for m in results.flashing_margin_pa]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=x,
        y=margins_bar,
        mode="lines",
        name="Flaş / Kavitasyon Güvenlik Marjı (P - Psat)",
        line=dict(color="#a371f7", width=2.5),
        fill="tozeroy",
        fillcolor="rgba(163, 113, 247, 0.15)",
        hovertemplate="Güvenlik Marjı: %{y:.3f} bar<extra></extra>"
    ))

    # Zero boundary line
    fig.add_hline(
        y=0.0,
        line_width=2,
        line_color="#f85149",
        line_dash="solid",
        annotation_text="Kavitasyon / Flaş Sınırı (ΔP = 0)",
        annotation_position="bottom right",
        annotation_font=dict(color="#f85149", size=11)
    )

    fig.update_layout(
        title=dict(text="<b>Flaş ve Kavitasyon Güvenlik Marjı ΔP(x) = P(x) - Psat(T)</b>", x=0.05),
        xaxis_title="Boru Uzunluğu x (m)",
        yaxis_title="Güvenlik Marjı (bar)"
    )
    return _apply_theme(fig)


def create_radial_cross_section_heatmap(results_3d, slice_index: int = -1) -> go.Figure:
    """
    Renders 2D cross-sectional contour heatmap T(r, theta) of the pipe cross section at slice_index.
    Reveals the cryogenic core and warm thermal boundary layer at the pipe inner wall.
    """
    idx = max(0, min(slice_index, len(results_3d.distance_m) - 1))
    dist = results_3d.distance_m[idx]
    
    r_coords = results_3d.radial_coords_m * 1000.0  # mm
    theta_coords = results_3d.azimuthal_coords_rad
    temp_grid = results_3d.temp_field_k[idx, :, :] - 273.15  # to °C
    
    # Create polar contour plot
    # Interpolate into regular 2D Cartesian grid (x, y) for smooth contour
    nr = len(r_coords)
    nt = len(theta_coords)
    r_max = r_coords[-1]
    
    grid_size = 45
    x_lin = np.linspace(-r_max, r_max, grid_size)
    y_lin = np.linspace(-r_max, r_max, grid_size)
    X, Y = np.meshgrid(x_lin, y_lin)
    R_grid = np.sqrt(X**2 + Y**2)
    Theta_grid = (np.arctan2(Y, X) + 2.0 * np.pi) % (2.0 * np.pi)
    
    Z_temp = np.full((grid_size, grid_size), np.nan)
    
    for i in range(grid_size):
        for j in range(grid_size):
            r_val = R_grid[i, j]
            if r_val <= r_max:
                # Radial index
                r_norm = min(1.0, max(0.0, r_val / r_max))
                r_idx = min(nr - 1, int(r_norm * (nr - 1)))
                th_val = Theta_grid[i, j]
                th_idx = min(nt - 1, int((th_val / (2.0 * math.pi)) * nt))
                Z_temp[i, j] = temp_grid[r_idx, th_idx]
                
    fig = go.Figure(data=go.Contour(
        x=x_lin,
        y=y_lin,
        z=Z_temp,
        colorscale="Viridis",
        colorbar=dict(title="T (°C)"),
        contours=dict(showlines=True),
        hovertemplate="X: %{x:.1f} mm<br>Y: %{y:.1f} mm<br>Sıcaklık: %{z:.2f} °C<extra></extra>"
    ))
    
    fig.update_layout(
        title=dict(text=f"<b>Boru Enine Kesit 3D Termal Dağılımı T(r, θ) [x = {dist:.1f} m]</b>", x=0.05),
        xaxis_title="X Koordinatı (mm)",
        yaxis_title="Y Koordinatı (mm)",
        yaxis=dict(scaleanchor="x", scaleratio=1),
        width=550,
        height=480
    )
    return _apply_theme(fig)

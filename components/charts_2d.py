"""Interactive 2D Plotly engineering charts for LNG pipeline flow."""

from typing import Dict, Any
import numpy as np
import plotly.graph_objects as go
from core.solver import PipelineSimulationResults


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


def create_pressure_comparison_chart(results: PipelineSimulationResults) -> go.Figure:
    """Plots Total Static Pressure vs Saturation Vapor Pressure along pipe length."""
    x = results.distance_m
    p_bar = [p / 1e5 for p in results.pressure_pa]
    p_sat_bar = [p / 1e5 for p in results.vapor_pressure_pa]

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

    # Saturation Vapor Pressure
    fig.add_trace(go.Scatter(
        x=x,
        y=p_sat_bar,
        mode="lines",
        name="Doyma Buhar Basıncı Psat(T)",
        line=dict(color="#f85149", width=2.5, dash="dash"),
        hovertemplate="Buhar Basıncı: %{y:.3f} bar<extra></extra>"
    ))

    # Highlight flashing point if boiling occurred
    if results.has_flashed and results.flashing_point_m is not None:
        idx = next((i for i, d in enumerate(x) if d >= results.flashing_point_m), -1)
        if idx >= 0:
            fig.add_vline(
                x=results.flashing_point_m,
                line_width=2,
                line_dash="dot",
                line_color="#ff7b72",
                annotation_text=f"⚠️ Flaş/Kaynama Başlangıcı ({results.flashing_point_m} m)",
                annotation_position="top left",
                annotation_font=dict(color="#ff7b72", size=11)
            )

    fig.update_layout(
        title=dict(text="<b>Toplam Basınç ve Doyma Buhar Basıncı Profili (P vs Psat)</b>", x=0.05),
        xaxis_title="Boru Uzunluğu x (m)",
        yaxis_title="Basınç (bar)"
    )
    return _apply_theme(fig)


def create_temperature_profile_chart(results: PipelineSimulationResults, temp_unit: str = "C") -> go.Figure:
    """Plots Bulk LNG temperature and pipe/insulation wall temperatures."""
    x = results.distance_m
    
    if temp_unit == "C":
        t_fluid = [t - 273.15 for t in results.temperature_k]
        t_unit_str = "°C"
        t_pipe_in = [r["pipe_inner"] - 273.15 for r in results.radial_temperatures]
        t_ins_out = [r["insulation_outer"] - 273.15 for r in results.radial_temperatures]
    else:
        t_fluid = results.temperature_k
        t_unit_str = "K"
        t_pipe_in = [r["pipe_inner"] for r in results.radial_temperatures]
        t_ins_out = [r["insulation_outer"] for r in results.radial_temperatures]

    fig = go.Figure()

    # Fluid temperature
    fig.add_trace(go.Scatter(
        x=x,
        y=t_fluid,
        mode="lines",
        name=f"LNG Akışkan Sıcaklığı T(x)",
        line=dict(color="#3fb950", width=3),
        hovertemplate=f"Akışkan Sıcaklığı: %{{y:.2f}} {t_unit_str}<extra></extra>"
    ))

    # Pipe inner surface
    fig.add_trace(go.Scatter(
        x=x,
        y=t_pipe_in,
        mode="lines",
        name="Boru İç Çeper Sıcaklığı",
        line=dict(color="#79c0ff", width=1.5, dash="dot"),
        hovertemplate=f"İç Çeper: %{{y:.2f}} {t_unit_str}<extra></extra>"
    ))

    # Outer insulation surface
    fig.add_trace(go.Scatter(
        x=x,
        y=t_ins_out,
        mode="lines",
        name="İzolasyon Dış Yüzey Sıcaklığı",
        line=dict(color="#d29922", width=1.5, dash="dash"),
        hovertemplate=f"İzolasyon Dışı: %{{y:.2f}} {t_unit_str}<extra></extra>"
    ))

    fig.update_layout(
        title=dict(text=f"<b>Boru Boyunca Termal Profil T(x) [{t_unit_str}]</b>", x=0.05),
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


def create_radial_temperature_chart(results: PipelineSimulationResults, slice_index: int = 0) -> go.Figure:
    """Radial temperature distribution across pipe wall and insulation layers at specific station."""
    idx = max(0, min(slice_index, len(results.radial_temperatures) - 1))
    radial = results.radial_temperatures[idx]
    dist = results.distance_m[idx]

    labels = ["LNG Akışkanı", "Boru İç Yüzeyi", "Boru Dış Yüzeyi"]
    temps_c = [
        radial["fluid"] - 273.15,
        radial["pipe_inner"] - 273.15,
        radial["pipe_outer"] - 273.15
    ]

    ins_temps = radial.get("insulation_interfaces", [])
    for i, t in enumerate(ins_temps):
        labels.append(f"İzolasyon Katmanı {i+1}")
        temps_c.append(t - 273.15)

    labels.append("Ortam Sıcaklığı")
    temps_c.append(radial["ambient"] - 273.15)

    fig = go.Figure(go.Scatter(
        x=labels,
        y=temps_c,
        mode="lines+markers",
        marker=dict(size=10, color=temps_c, colorscale="Viridis", showscale=True, colorbar=dict(title="T (°C)")),
        line=dict(color="#58a6ff", width=2.5),
        hovertemplate="%{x}: <b>%{y:.1f} °C</b><extra></extra>"
    ))

    fig.update_layout(
        title=dict(text=f"<b>Radyal Katman Sıcaklık Dağılımı (x = {dist} m noktasında)</b>", x=0.05),
        xaxis_title="Radyal Katman",
        yaxis_title="Sıcaklık (°C)"
    )
    return _apply_theme(fig)

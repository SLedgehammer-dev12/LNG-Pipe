"""LNG Cryogenic Pipeline Thermal-Hydraulic Flow Simulator (3D & 1D Web Application)."""

import streamlit as st
import pandas as pd
import numpy as np

from core.fluids import FluidManager
from core.heat_transfer import InsulationLayer, PipeThermalModel
from core.solver import PipelineSolver, PipelineSimulationConfig, PipelineSimulationResults
from core.solver_3d import PipelineSolver3D, Solver3DConfig, Simulation3DResults
from components.charts_2d import (
    create_pressure_comparison_chart,
    create_temperature_profile_chart,
    create_flashing_margin_chart,
    create_radial_cross_section_heatmap,
)
from components.pipe_3d_viewer import generate_3d_pipe_html
from components.pipeline_schematic_2d import generate_schematic_2d_html
from components.terminal_3d_viewer import generate_terminal_3d_html
from reports.pdf_report import generate_pdf_report

st.set_page_config(
    page_title="LNG Boru Akışı 3D/1D Termo-Hidrolik Simülatörü",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark industrial engineering theme
st.markdown("""
<style>
    .reportview-container { background: #0e1117; }
    .main-header {
        font-family: 'Inter', sans-serif;
        font-weight: 800;
        font-size: 26px;
        color: #58a6ff;
        margin-bottom: 2px;
    }
    .sub-header {
        font-size: 13px;
        color: #8b949e;
        margin-bottom: 18px;
    }
    .metric-card {
        background: #161b22;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 10px;
    }
    .metric-title {
        font-size: 11px;
        color: #8b949e;
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    .metric-value {
        font-size: 22px;
        font-weight: 700;
        color: #f0f6fc;
        margin-top: 4px;
        font-family: monospace;
    }
    .metric-delta {
        font-size: 12px;
        font-weight: 600;
        margin-top: 2px;
    }
    .delta-up { color: #f85149; }
    .delta-down { color: #58a6ff; }
    .delta-safe { color: #3fb950; }
    .status-alert-box {
        background: rgba(218, 54, 51, 0.15);
        border: 1px solid #da3633;
        border-radius: 8px;
        padding: 12px 16px;
        color: #f85149;
        font-weight: 600;
        margin-bottom: 15px;
    }
    .status-safe-box {
        background: rgba(35, 134, 54, 0.15);
        border: 1px solid #238636;
        border-radius: 8px;
        padding: 12px 16px;
        color: #3fb950;
        font-weight: 600;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# Preset definitions
PRESETS = {
    "Özel Yapılandırma": None,
    "Marine Jetty Yükleme Hattı (DN250, 500m, 5 bar)": {
        "length_m": 500.0, "diameter_mm": 250.0, "thickness_mm": 6.35, "inlet_t_c": -161.5,
        "inlet_p_bar": 5.0, "mass_flow": 80.0, "ins_type": "PIR Köpük", "ins_thick_mm": 80.0, "incline": 0.0
    },
    "LNG Bunkering İkmal Hortumu/Borusu (DN100, 60m, 4 bar)": {
        "length_m": 60.0, "diameter_mm": 100.0, "thickness_mm": 4.5, "inlet_t_c": -161.0,
        "inlet_p_bar": 4.0, "mass_flow": 25.0, "ins_type": "Kriyojenik Aerogel", "ins_thick_mm": 35.0, "incline": 5.0
    },
    "Vakum Ceketli Transfer Hattı (DN150, 200m, 6 bar)": {
        "length_m": 200.0, "diameter_mm": 150.0, "thickness_mm": 5.0, "inlet_t_c": -162.0,
        "inlet_p_bar": 6.0, "mass_flow": 45.0, "ins_type": "Vakum Ceketli MLI", "ins_thick_mm": 25.0, "incline": 0.0
    },
    "Kritik Düşük Basınç Testi (Çeperde Kaynama Başlangıcı)": {
        "length_m": 350.0, "diameter_mm": 125.0, "thickness_mm": 4.5, "inlet_t_c": -160.0,
        "inlet_p_bar": 1.45, "mass_flow": 12.0, "ins_type": "Hücresel Cam (Foamglas)", "ins_thick_mm": 30.0, "incline": 2.0
    }
}

INSULATION_DATA = {
    "PIR Köpük": {"k": 0.024, "desc": "Poliizosiyanürat sert köpük (en yaygın endüstriyel izolasyon)"},
    "Kriyojenik Aerogel": {"k": 0.015, "desc": "Yüksek performanslı nano-gözenekli esnek örtü"},
    "Hücresel Cam (Foamglas)": {"k": 0.040, "desc": "Tamamen yanmaz, su buharı geçirmez rijit cam blok"},
    "Vakum Ceketli MLI": {"k": 0.002, "desc": "Çok katmanlı yansıtıcı folyo + yüksek vakum (< 1e-4 mbar)"}
}

PIPE_MATERIALS = {
    "Paslanmaz Çelik 304L/316L": 15.0,
    "%9 Nikel Çeliği (Cryogenic 9% Ni)": 28.0,
    "Invar 36 (Düşük Genleşmeli)": 10.5,
    "Alüminyum 5083-O": 120.0
}

# --- SIDEBAR INPUTS ---
st.sidebar.markdown("### ⚙️ Simülasyon Yapılandırması")

solver_mode = st.sidebar.radio(
    "Çözücü Boyut ve Hassasiyet Modu",
    ["🚀 3D Sonlu Hacimler (Silindirik r, θ, z - Tavsiye Edilen)", "⚡ 1D Sonlu Hacimler (Hızlı Mod)"],
    index=0
)
is_3d_mode = "3D" in solver_mode

selected_preset_name = st.sidebar.selectbox("Hızlı Senaryo Seçimi", list(PRESETS.keys()))
preset = PRESETS[selected_preset_name]

with st.sidebar.expander("📏 Boru Geometrisi & Hat Rotası", expanded=True):
    length_m = st.number_input("Boru Uzunluğu L (m)", min_value=5.0, max_value=10000.0, value=preset["length_m"] if preset else 300.0, step=25.0)
    diameter_mm = st.number_input("Boru İç Çapı ID (mm)", min_value=25.0, max_value=1200.0, value=preset["diameter_mm"] if preset else 200.0, step=10.0)
    wall_thickness_mm = st.number_input("Boru Et Kalınlığı (mm)", min_value=1.5, max_value=30.0, value=preset["thickness_mm"] if preset else 6.0, step=0.5)
    inclination_deg = st.number_input("Hat Eğim Açısı θ (°)", min_value=-90.0, max_value=90.0, value=preset["incline"] if preset else 0.0, step=1.0, help="Pozitif = Yokuş yukarı (hidrostatik basınç kaybı ekler)")
    pipe_mat_name = st.selectbox("Boru Malzemesi", list(PIPE_MATERIALS.keys()))
    roughness_um = st.number_input("Boru İç Pürüzlülüğü ε (µm)", min_value=1.0, max_value=500.0, value=45.0, step=5.0)

with st.sidebar.expander("❄️ Kriyojenik Akışkan & Giriş Koşulları", expanded=True):
    fluid_type_choice = st.radio("Akışkan Kompozisyonu", ["Saf Metan (%100 CH4)", "Standart Ticari LNG Karışımı"])
    inlet_t_c = st.number_input("Giriş Sıcaklığı T_in (°C)", min_value=-182.0, max_value=-100.0, value=preset["inlet_t_c"] if preset else -161.5, step=0.5)
    inlet_p_bar = st.number_input("Giriş Toplam Basıncı P_in (bar)", min_value=1.013, max_value=60.0, value=preset["inlet_p_bar"] if preset else 5.0, step=0.5)
    mass_flow_kg_s = st.number_input("Kütlesel Debi m (kg/s)", min_value=0.5, max_value=2000.0, value=preset["mass_flow"] if preset else 40.0, step=5.0)

with st.sidebar.expander("🛡️ Kriyojenik İzolasyon Katmanı", expanded=True):
    ins_choice = st.selectbox("İzolasyon Malzemesi", list(INSULATION_DATA.keys()), index=list(INSULATION_DATA.keys()).index(preset["ins_type"]) if preset and preset["ins_type"] in INSULATION_DATA else 0)
    ins_thickness_mm = st.number_input("İzolasyon Kalınlığı (mm)", min_value=5.0, max_value=300.0, value=preset["ins_thick_mm"] if preset else 60.0, step=5.0)
    st.caption(f"ℹ️ {INSULATION_DATA[ins_choice]['desc']} (k = {INSULATION_DATA[ins_choice]['k']} W/m·K)")

with st.sidebar.expander("☀️ Çevre ve Dış Ortam", expanded=False):
    amb_temp_c = st.slider("Ortam Sıcaklığı T_amb (°C)", min_value=-20.0, max_value=55.0, value=25.0, step=1.0)
    wind_speed_m_s = st.slider("Rüzgar Hızı (m/s)", min_value=0.5, max_value=30.0, value=3.0, step=0.5)

if is_3d_mode:
    with st.sidebar.expander("🌐 3D Sayısal Izgara Çözünürlüğü", expanded=False):
        n_radial = st.slider("Radyal Katman Sayısı (Nr)", min_value=6, max_value=24, value=12, step=2)
        n_azimuthal = st.slider("Açısal Dilim Sayısı (Nθ)", min_value=6, max_value=24, value=12, step=2)
        n_axial = st.slider("Eksenel Dilim Sayısı (Nz)", min_value=20, max_value=100, value=50, step=10)
else:
    n_radial = 8
    n_azimuthal = 8
    n_axial = 100

# --- EXECUTE SIMULATION ---
@st.cache_data(show_spinner=False)
def run_simulation(length, diam, thick, mat_k, rough, incline, ftype, t_in_c, p_in_bar, flow, ins_name, ins_th, t_amb, wind, use_3d, nr, nt, nz):
    if "Saf Metan" in ftype:
        fm = FluidManager(fluid_type="pure_methane")
    else:
        comp = {"Methane": 0.94, "Ethane": 0.045, "Propane": 0.01, "Nitrogen": 0.005}
        fm = FluidManager(fluid_type="mixture", composition=comp)

    k_ins = INSULATION_DATA[ins_name]["k"]
    layers = [InsulationLayer(name=ins_name, thickness_m=ins_th / 1000.0, thermal_conductivity=k_ins)]
    thermal_model = PipeThermalModel(
        inner_diameter_m=diam / 1000.0,
        wall_thickness_m=thick / 1000.0,
        pipe_conductivity=mat_k,
        insulation_layers=layers,
        ambient_temperature_k=t_amb + 273.15,
        wind_speed_m_s=wind
    )

    base_config = PipelineSimulationConfig(
        length_m=length,
        inner_diameter_m=diam / 1000.0,
        roughness_m=rough * 1e-6,
        inclination_deg=incline,
        inlet_temperature_k=t_in_c + 273.15,
        inlet_pressure_pa=p_in_bar * 1e5,
        mass_flow_rate_kg_s=flow,
        num_cells=nz
    )

    if use_3d:
        cfg_3d = Solver3DConfig(pipeline_config=base_config, n_radial=nr, n_azimuthal=nt, n_axial=nz)
        solver_3d = PipelineSolver3D(fluid_manager=fm, thermal_model=thermal_model, config=cfg_3d)
        return solver_3d.solve()
    else:
        solver_1d = PipelineSolver(fluid_manager=fm, thermal_model=thermal_model, config=base_config)
        return solver_1d.solve()

sim_results = run_simulation(
    length_m, diameter_mm, wall_thickness_mm, PIPE_MATERIALS[pipe_mat_name],
    roughness_um, inclination_deg, fluid_type_choice, inlet_t_c, inlet_p_bar,
    mass_flow_kg_s, ins_choice, ins_thickness_mm, amb_temp_c, wind_speed_m_s,
    is_3d_mode, n_radial, n_azimuthal, n_axial
)

# --- MAIN DISPLAY ---
mode_label = "3D Sonlu Hacimler (Silindirik r, θ, z)" if is_3d_mode else "1D Sonlu Hacimler (Eksenel)"
st.markdown(f'<div class="main-header">❄️ LNG Boru Akışı Termo-Hidrolik Simülatörü <span style="font-size:16px; color:#58a6ff; font-weight:600;">[{mode_label}]</span></div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Cryogenic LNG Pipeline Thermal Ingress, Hydraulic Pressure Drop & Near-Wall / Bulk Flashing Risk Engine</div>', unsafe_allow_html=True)

# Flashing Banner
if is_3d_mode:
    has_flashed = sim_results.has_wall_flashed or sim_results.has_bulk_flashed
    if sim_results.has_wall_flashed and not sim_results.has_bulk_flashed:
        st.markdown(f"""
        <div class="status-alert-box">
            ⚠️ <b>3D ERKEN UYARI: ÇEPERDE KAYNAMA / FLAŞ BAŞLANGICI!</b><br/>
            Boru çeperindeki sınır tabaka akışkan sıcaklığı ({sim_results.wall_temperature_k[-1] - 273.15:.2f} °C), yığın sıvıdan sıcaktır. Hattın <b>{sim_results.wall_flashing_point_m:.1f}. metresinde</b> boru iç çeperinde kavitasyon / mikro-kaynama başlamıştır (Yığın sıvı henüz doymamıştır).
        </div>
        """, unsafe_allow_html=True)
    elif sim_results.has_bulk_flashed:
        st.markdown(f"""
        <div class="status-alert-box">
            🚨 <b>KRİTİK UYARI: TAM YIĞIN BUHARLAŞMASI / FLAŞ!</b><br/>
            Boru hattının <b>{sim_results.bulk_flashing_point_m:.1f}. metresinde</b> yığın sıvı kaynamaya başlamıştır. Kavitasyon, iki fazlı koç darbesi ve buhar tıkanması riski mevcuttur.
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="status-safe-box">
            ✓ <b>GÜVENLİ İŞLETME: HEM ÇEPER HEM YIĞIN TAM SIVI FAZDA</b><br/>
            Boru boyunca en kritik iç çeperde dahi buharlaşma marjı pozitiftir (Minimum güvenlik marjı: {sim_results.min_flashing_margin_pa / 1e5:.2f} bar).
        </div>
        """, unsafe_allow_html=True)
else:
    has_flashed = sim_results.has_flashed
    if sim_results.has_flashed:
        st.markdown(f"""
        <div class="status-alert-box">
            ⚠️ <b>KRİTİK UYARI: BUHARLAŞMA / FLAŞ NOKTASI TESPİT EDİLDİ!</b><br/>
            Boru hattının <b>{sim_results.flashing_point_m:.1f}. metresinde</b> toplam statik basınç doyma buhar basıncının altına düşmüştür.
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="status-safe-box">
            ✓ <b>GÜVENLİ İŞLETME: TEK FAZ SIVI AKIŞI KORUNUYOR</b><br/>
            Minimum güvenlik marjı: {sim_results.min_flashing_margin_pa / 1e5:.2f} bar.
        </div>
        """, unsafe_allow_html=True)

# Top KPI metrics
c1, c2, c3, c4, c5 = st.columns(5)
if is_3d_mode:
    outlet_t_c = sim_results.bulk_temperature_k[-1] - 273.15
    delta_t = sim_results.bulk_temperature_k[-1] - (inlet_t_c + 273.15)
    outlet_p_bar = sim_results.pressure_pa[-1] / 1e5
    outlet_psat_bar = sim_results.wall_vapor_pressure_pa[-1] / 1e5
    delta_psat_bar = (sim_results.wall_vapor_pressure_pa[-1] - sim_results.wall_vapor_pressure_pa[0]) / 1e5
    min_margin_bar = sim_results.min_flashing_margin_pa / 1e5
else:
    outlet_t_c = sim_results.outlet_temperature_k - 273.15
    delta_t = sim_results.outlet_temperature_k - (inlet_t_c + 273.15)
    outlet_p_bar = sim_results.outlet_pressure_pa / 1e5
    outlet_psat_bar = sim_results.outlet_vapor_pressure_pa / 1e5
    delta_psat_bar = (sim_results.outlet_vapor_pressure_pa - sim_results.inlet_vapor_pressure_pa) / 1e5
    min_margin_bar = sim_results.min_flashing_margin_pa / 1e5

delta_p_bar = sim_results.total_pressure_drop_pa / 1e5

with c1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Çıkış Yığın Sıcaklığı</div>
        <div class="metric-value">{outlet_t_c:.2f} °C</div>
        <div class="metric-delta delta-up">▲ +{delta_t:.2f} °C ısınma</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Çıkış Statik Basıncı</div>
        <div class="metric-value">{outlet_p_bar:.2f} bar</div>
        <div class="metric-delta delta-down">▼ -{delta_p_bar:.2f} bar hidrolik kayıp</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Çıkış Buhar Basıncı (Psat)</div>
        <div class="metric-value">{outlet_psat_bar:.2f} bar</div>
        <div class="metric-delta delta-up">▲ +{delta_psat_bar:.2f} bar artış</div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    margin_class = "delta-safe" if min_margin_bar >= 0.5 else "delta-up"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Min. Kavitasyon Marjı</div>
        <div class="metric-value">{min_margin_bar:.2f} bar</div>
        <div class="metric-delta {margin_class}">P - Psat marjı</div>
    </div>
    """, unsafe_allow_html=True)

with c5:
    heat_kw = sim_results.total_heat_ingress_w / 1000.0
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Toplam Isı Girişi Q_tot</div>
        <div class="metric-value">{heat_kw:.1f} kW</div>
        <div class="metric-delta" style="color:#d29922;">{sim_results.total_heat_ingress_w / length_m:.1f} W/m hat kaybı</div>
    </div>
    """, unsafe_allow_html=True)

# --- VIEW TABS ---
tab_schematic, tab_3d_terminal, tab_3d_pipe, tab_charts, tab_table, tab_report = st.tabs([
    "🗺️ Terminal Hat Şematiği (2D P&ID)",
    "⚓ 3D Terminal Dijital İkiz (Three.js)",
    "🔍 3D Boru Kesiti & İzolasyon",
    "📊 2D Termo-Hidrolik Grafikler & Flaş Analizi",
    "📋 Dilim Bazlı Sayısal Tablo",
    "📑 Profesyonel Raporlama (PDF)"
])

with tab_schematic:
    st.markdown("##### 🗺️ İskele (Jetty) - Kara Tankı Transfer & Sirkülasyon Şematiği (P&ID)")
    st.caption("LUP dolfeninden kara depolama tankına ve sirkülasyon pompası (P-201) ile geri dönüş hattına kadar tüm proses hattını inceleyin. Ekipman detayları için üzerlerine tıklayın.")
    html_schematic_2d = generate_schematic_2d_html(sim_results, height_px=620)
    st.components.v1.html(html_schematic_2d, height=640, scrolling=False)

with tab_3d_terminal:
    st.markdown("##### ⚓ 3D Terminal Sahası & Boru Köprüsü Dijital İkizi (Three.js)")
    st.caption("Açık deniz LUP dolfeni, yanaşmış LNG gemisi, APD dolfenleri, 3D Omega termal genleşme döngüleri, kara tankı ve sirkülasyon pompasını 3D uzayda serbestçe gezin.")
    html_terminal_3d = generate_terminal_3d_html(sim_results, height_px=640)
    st.components.v1.html(html_terminal_3d, height=660, scrolling=False)

with tab_3d_pipe:
    st.markdown("##### 🔍 3D Three.js Kriyojenik Kesitli Boru Görselleştirici")
    st.caption("Sol tık ile döndürün, sağ tık ile kaydırın, fare tekerleğiyle yakınlaşın. 180° Kesit ile iç sıvı çekirdeği ve izolasyon katmanlarını inceleyin.")
    html_3d = generate_3d_pipe_html(sim_results, height_px=560)
    st.components.v1.html(html_3d, height=580, scrolling=False)

with tab_charts:
    st.markdown("##### 📈 2D Dinamik Termodinamik & Hidrolik Eğriler")
    
    col_chart_top_1, col_chart_top_2 = st.columns(2)
    with col_chart_top_1:
        st.plotly_chart(create_pressure_comparison_chart(sim_results), use_container_width=True)
    with col_chart_top_2:
        st.plotly_chart(create_temperature_profile_chart(sim_results), use_container_width=True)

    col_chart_bot_1, col_chart_bot_2 = st.columns(2)
    with col_chart_bot_1:
        st.plotly_chart(create_flashing_margin_chart(sim_results), use_container_width=True)
    with col_chart_bot_2:
        if is_3d_mode:
            station_pct = st.slider("3D Enine Kesit İstasyon Konumu (% Uzunluk)", 0, 100, 100, step=10)
            station_idx = int((station_pct / 100.0) * (len(sim_results.distance_m) - 1))
            st.plotly_chart(create_radial_cross_section_heatmap(sim_results, slice_index=station_idx), use_container_width=True)
        else:
            st.info("💡 Boru içi 2D radyal enine kesit sıcaklık konturu (T(r, θ)) için sol panelden '3D Sonlu Hacimler' modunu seçebilirsiniz.")

with tab_table:
    st.markdown("##### 📋 Hat Boyunca Sonlu Hacim Hücre Verileri")
    if is_3d_mode:
        df_data = {
            "Mesafe (m)": sim_results.distance_m,
            "Statik Basınç (bar)": [round(p / 1e5, 3) for p in sim_results.pressure_pa],
            "Yığın Sıcaklık (°C)": [round(t - 273.15, 2) for t in sim_results.bulk_temperature_k],
            "Merkez Hattı Sıcaklığı (°C)": [round(t - 273.15, 2) for t in sim_results.center_temperature_k],
            "İç Çeper Sıcaklığı (°C)": [round(t - 273.15, 2) for t in sim_results.wall_temperature_k],
            "Çeper Psat (bar)": [round(p / 1e5, 3) for p in sim_results.wall_vapor_pressure_pa],
            "Yığın Psat (bar)": [round(p / 1e5, 3) for p in sim_results.bulk_vapor_pressure_pa],
            "Çeper Güvenlik Marjı (bar)": [round(m / 1e5, 3) for m in sim_results.wall_flashing_margin_pa],
            "Yığın Güvenlik Marjı (bar)": [round(m / 1e5, 3) for m in sim_results.bulk_flashing_margin_pa]
        }
    else:
        df_data = {
            "Mesafe (m)": sim_results.distance_m,
            "Sıcaklık (°C)": [round(t - 273.15, 2) for t in sim_results.temperature_k],
            "Toplam Basınç (bar)": [round(p / 1e5, 3) for p in sim_results.pressure_pa],
            "Buhar Basıncı Psat (bar)": [round(p / 1e5, 3) for p in sim_results.vapor_pressure_pa],
            "Güvenlik Marjı (bar)": [round(m / 1e5, 3) for m in sim_results.flashing_margin_pa],
            "Akış Hızı (m/s)": [round(v, 2) for v in sim_results.velocity_m_s],
            "Yoğunluk (kg/m³)": [round(d, 1) for d in sim_results.density_kg_m3],
            "Reynolds": [int(r) for r in sim_results.reynolds],
            "Isı Akısı (W/m)": [round(q, 1) for q in sim_results.heat_ingress_w_m]
        }
    df = pd.DataFrame(df_data)
    st.dataframe(df, use_container_width=True, height=450)
    
    csv_bytes = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Hücre Verilerini CSV Olarak İndir",
        data=csv_bytes,
        file_name=f"lng_pipeline_results_{int(length_m)}m_{'3d' if is_3d_mode else '1d'}.csv",
        mime="text/csv"
    )

with tab_report:
    st.markdown("##### 📑 Profesyonel Mühendislik Hesaplama Raporu (PDF)")
    
    col_rep_1, col_rep_2 = st.columns(2)
    with col_rep_1:
        proj_name_input = st.text_input("Proje Adı", value="LNG Cryogenic Pipeline Hydraulic & Thermal Study")
        tag_id_input = st.text_input("Hat / Ekipman Etiketi (Tag ID)", value="LNG-01-PL-4022")
    with col_rep_2:
        engineer_input = st.text_input("Hazırlayan Mühendis", value="Kıdemli Proses & Kriyojenik Mühendisi")
        report_date = st.text_input("Tarih", value="2026-11-06")

    st.markdown("###### 🔍 Standartlar Uygunluk Özeti (ASME B31.3 & EN 1473)")
    v_approx = mass_flow_kg_s / (422.0 * (np.pi * (diameter_mm / 2000.0) ** 2))
    m_bar = sim_results.min_flashing_margin_pa / 1e5
    
    compliance_rows = [
        {"Kontrol Kriteri": "Akış Hızı (Stratifikasyon & Statik Sınırı)", "Standart": "EN 1473: 0.5 - 4.5 m/s", "Mevcut Değer": f"{v_approx:.2f} m/s", "Durum": "✓ UYGUN" if 0.5 <= v_approx <= 4.5 else "⚠️ UYARI"},
        {"Kontrol Kriteri": "Flaş & Kavitasyon Marjı", "Standart": "P - Psat ≥ 0.5 bar", "Mevcut Değer": f"{m_bar:.2f} bar", "Durum": "✓ UYGUN" if m_bar >= 0.5 else "⚠️ RİSKLİ"},
        {"Kontrol Kriteri": "Faz Korunumu (Tek Faz Sıvı)", "Standart": "Boil-off = 0", "Mevcut Değer": "Tam Sıvı" if not has_flashed else f"Flaş Başlangıcı", "Durum": "✓ UYGUN" if not has_flashed else "❌ KAYNAMA"}
    ]
    st.table(pd.DataFrame(compliance_rows))

    meta_dict = {
        "project_name": proj_name_input,
        "tag_id": tag_id_input,
        "engineer_name": engineer_input,
        "date_str": report_date
    }
    
    pdf_bytes = generate_pdf_report(sim_results, meta_dict)
    st.download_button(
        label="📄 Resmi PDF Mühendislik Hesaplama Raporunu İndir",
        data=pdf_bytes,
        file_name=f"{tag_id_input}_thermal_hydraulic_report.pdf",
        mime="application/pdf"
    )

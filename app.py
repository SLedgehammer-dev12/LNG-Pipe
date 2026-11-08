"""LNG Cryogenic Pipeline Thermal-Hydraulic Flow Simulator (3D & 1D Web Application)."""

import streamlit as st
import pandas as pd
import numpy as np
import json
import math

from core.fluids import (
    FluidManager,
    AVAILABLE_LNG_COMPONENTS,
    COMPONENT_LABELS,
    LNG_COMPONENTS_CATALOG,
)
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
from core.terminal_ops import evaluate_terminal_operations
from core.mechanics import (
    calculate_asme_b31_3_thickness,
    calculate_thermal_contraction_and_omega_loop,
    calculate_joukowsky_surge,
    spec_from_material,
)
from core.pipe_schedule import PIPE_TABLE_GROUPS, inner_diameter_mm, get_wall_thickness_options
from core.units import (
    DEFAULT_UNITS,
    units_for,
    to_si,
    from_si,
    delta_from_si,
    unit_display_label,
    delta_unit_display_label,
)
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
    /* Sidebar input & unit selector horizontal baseline alignment */
    section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] {
        align-items: flex-end !important;
        gap: 6px !important;
    }
    section[data-testid="stSidebar"] .stNumberInput,
    section[data-testid="stSidebar"] .stSelectbox {
        margin-bottom: 2px !important;
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

INSULATION_MATERIALS_CATALOG = {
    "PIR Köpük (Poliizosiyanürat)": {"k": 0.024, "desc": "Standart kriyojenik sert köpük (en yaygın boru yalıtımı)", "default_th": 60.0},
    "Kriyojenik Aerogel (Cryogel Z)": {"k": 0.015, "desc": "Esnek nano-gözenekli aerojel örtü (üstün yalıtım, ince kesit)", "default_th": 20.0},
    "Hücresel Cam (Foamglas ONE)": {"k": 0.040, "desc": "%100 Yanmaz, sıfır su buharı geçirgenliği, rijit yük taşıyıcı", "default_th": 50.0},
    "Vakum Ceketli MLI (Çift Cidarlı)": {"k": 0.002, "desc": "Yüksek vakum (< 1e-4 mbar) + çok katmanlı yansıtıcı kalkan", "default_th": 25.0},
    "PUR Köpük (Poliüretan)": {"k": 0.028, "desc": "Rijit enjeksiyon/sprey kriyojenik köpük", "default_th": 50.0},
    "Armaflex Kriyojenik Kauçuk": {"k": 0.035, "desc": "Esnek, titreşim sönümleyici iç/orta elastromerik katman", "default_th": 25.0},
    "Genleştirilmiş Kriyojenik Perlit": {"k": 0.034, "desc": "Çift cidarlı boru/tank arası perlit dolgusu", "default_th": 75.0},
    "Taşyünü / Yüksek Yoğunluklu Mineral Yün": {"k": 0.038, "desc": "Dış yangın geciktirici (fireproofing) koruma katmanı", "default_th": 40.0},
    "Alüminyum Buhar Kesici Ceket (0.8 mm Cladding)": {"k": 200.0, "desc": "Dış mekanik ve nem bariyeri sacı", "default_th": 0.8},
    "Paslanmaz Çelik Dış Ceket (304 Cladding, 0.5 mm)": {"k": 15.0, "desc": "Deniz ortamı korozyon ve yangın koruma sacı", "default_th": 0.5},
    "Özel Malzeme (Kullanıcı Tanımlı)": {"k": 0.030, "desc": "Kullanıcı tanımlı özel k iletkenlik değeri", "default_th": 30.0}
}

# Compatibility alias
INSULATION_DATA = INSULATION_MATERIALS_CATALOG

MULTI_LAYER_PACKAGES = {
    "Özel Katman Yapılandırması": None,
    "Standart Tek Katman: PIR Köpük (60 mm)": [
        {"name": "PIR Köpük (Poliizosiyanürat)", "thickness_mm": 60.0, "k": 0.024}
    ],
    "Çift Katmanlı Kriyojenik Hibrit (Aerogel + PIR)": [
        {"name": "Kriyojenik Aerogel (Cryogel Z)", "thickness_mm": 20.0, "k": 0.015},
        {"name": "PIR Köpük (Poliizosiyanürat)", "thickness_mm": 50.0, "k": 0.024}
    ],
    "Üç Katmanlı Endüstriyel (Aerogel + Foamglas + Al Ceket)": [
        {"name": "Kriyojenik Aerogel (Cryogel Z)", "thickness_mm": 15.0, "k": 0.015},
        {"name": "Hücresel Cam (Foamglas ONE)", "thickness_mm": 40.0, "k": 0.040},
        {"name": "Alüminyum Buhar Kesici Ceket (0.8 mm Cladding)", "thickness_mm": 0.8, "k": 200.0}
    ],
    "Yangın Korumalı Marin Hat (Foamglas + PIR + Taşyünü + SS Ceket)": [
        {"name": "Hücresel Cam (Foamglas ONE)", "thickness_mm": 40.0, "k": 0.040},
        {"name": "PIR Köpük (Poliizosiyanürat)", "thickness_mm": 50.0, "k": 0.024},
        {"name": "Taşyünü / Yüksek Yoğunluklu Mineral Yün", "thickness_mm": 30.0, "k": 0.038},
        {"name": "Paslanmaz Çelik Dış Ceket (304 Cladding, 0.5 mm)", "thickness_mm": 0.5, "k": 15.0}
    ],
    "Vakum Ceketli MLI (25 mm)": [
        {"name": "Vakum Ceketli MLI (Çift Cidarlı)", "thickness_mm": 25.0, "k": 0.002}
    ]
}

LNG_PRESET_COMPOSITIONS = {
    "Saf Metan (%100 CH4)": {"Methane": 100.0},
    "Standart Ticari LNG (Katar/Cezayir)": {"Methane": 94.2, "Ethane": 4.5, "Propane": 0.8, "Nitrogen": 0.5},
    "Zenginleştirilmiş Ağır LNG (Avustralya/Gorgon - C1–C6+)": {
        "Methane": 88.5, "Ethane": 7.8, "Propane": 2.2, "IsoButane": 0.5,
        "n-Butane": 0.4, "Isopentane": 0.15, "n-Pentane": 0.10, "n-Hexane": 0.05, "Nitrogen": 0.3
    },
    "Kuzey Afrika / Libya Ağır LNG (Yüksek C2–C6+ & N2)": {
        "Methane": 83.2, "Ethane": 11.4, "Propane": 3.2, "IsoButane": 0.6,
        "n-Butane": 0.7, "Isopentane": 0.2, "n-Hexane": 0.1, "Nitrogen": 0.6
    },
    "Yalın Amerikan LNG (Sabine Pass / Henry Hub)": {"Methane": 97.8, "Ethane": 1.8, "Propane": 0.1, "Nitrogen": 0.3},
    "Asit / İnert Gaz İçeren Ham Besleme LNG (CO2 + N2 + Ağır HC)": {
        "Methane": 91.5, "Ethane": 5.0, "Propane": 1.5, "n-Butane": 0.5,
        "Nitrogen": 1.2, "CarbonDioxide": 0.25, "Helium": 0.05
    },
    "Özel Kullanıcı Tanımlı Kompozisyon": None
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

# Reset stored SI values when the preset changes so widget defaults follow the preset.
if st.session_state.get("_last_preset") != selected_preset_name:
    st.session_state["_last_preset"] = selected_preset_name
    st.session_state["_preset_token"] = st.session_state.get("_preset_token", 0) + 1
    for _k in [k for k in st.session_state if k.startswith("si_")]:
        del st.session_state[_k]
preset_token = st.session_state.get("_preset_token", 0)


def unit_input(label, category, key, default_si, min_si=None, max_si=None, step_si=None):
    """Number input with a baseline-aligned adjacent unit dropdown; stores the SI value in session_state."""
    c_val, c_unit = st.columns([2.25, 1.25], vertical_alignment="bottom")
    unit_options = units_for(category)
    with c_unit:
        unit = st.selectbox(
            f"{label} birimi",
            unit_options,
            index=unit_options.index(DEFAULT_UNITS[category]),
            format_func=lambda u, cat=category: unit_display_label(cat, u),
            key=f"unit_{key}",
            label_visibility="collapsed",
        )
    si_prev = st.session_state.get(f"si_{key}", default_si)
    kwargs = {}
    if min_si is not None:
        kwargs["min_value"] = round(from_si(category, min_si, unit), 6)
    if max_si is not None:
        kwargs["max_value"] = round(from_si(category, max_si, unit), 6)
    if step_si is not None:
        kwargs["step"] = round(delta_from_si(category, abs(step_si), unit), 6)
    with c_val:
        disp = st.number_input(
            label,
            value=round(from_si(category, si_prev, unit), 6),
            key=f"num_{key}_{unit}_{preset_token}",
            **kwargs,
        )
    si_new = to_si(category, disp, unit)
    st.session_state[f"si_{key}"] = si_new
    return si_new, unit


with st.sidebar.expander("📏 Boru Geometrisi & Hat Rotası", expanded=True):
    length_m, _ = unit_input(
        "Boru Uzunluğu L", "length", "length",
        preset["length_m"] if preset else 300.0,
        min_si=5.0, max_si=10000.0, step_si=25.0,
    )

    st.markdown("###### 🚢➡️🏭 Gemiden Karaya Ana Boşaltım Hattı")
    geom_mode = st.radio(
        "Boru Boyutlandırma Yöntemi",
        ["ASME Tablosu", "Manuel Giriş"],
        index=0 if preset is None else 1,
        horizontal=True,
        key=f"geom_{preset_token}",
    )
    if geom_mode == "ASME Tablosu":
        geom_group = st.selectbox("Boru Standardı", list(PIPE_TABLE_GROUPS.keys()), index=1, key="main_pipe_std")
        pipe_table = PIPE_TABLE_GROUPS[geom_group]
        dn_keys = list(pipe_table.keys())
        dn_default = dn_keys.index('DN200 (NPS 8")') if 'DN200 (NPS 8")' in dn_keys else 0
        dn_label = st.selectbox("Anma Çapı (DN / NPS)", dn_keys, index=dn_default, key="main_pipe_dn")
        wall_options = get_wall_thickness_options(geom_group, dn_label)
        wall_opt_keys = list(wall_options.keys())
        sched_default = next(
            (k for k in wall_opt_keys if k.startswith("40S") or k.startswith("Sch 40")),
            wall_opt_keys[0],
        )
        schedule_label = st.selectbox(
            "Et Kalınlığı / Schedule (mm)",
            wall_opt_keys,
            index=wall_opt_keys.index(sched_default),
            key="main_pipe_sched",
        )
        od_mm = pipe_table[dn_label]["od_mm"]
        wall_thickness_mm = wall_options[schedule_label]
        diameter_mm = inner_diameter_mm(od_mm, wall_thickness_mm)
        st.caption(f"OD {od_mm:.1f} mm · ID {diameter_mm:.2f} mm · t {wall_thickness_mm:.2f} mm · {geom_group}")
    else:
        diameter_mm, _ = unit_input(
            "Boru İç Çapı ID", "diameter", "diameter",
            preset["diameter_mm"] if preset else 200.0,
            min_si=25.0, max_si=1200.0, step_si=10.0,
        )
        wall_thickness_mm, _ = unit_input(
            "Boru Et Kalınlığı", "diameter", "wall",
            preset["thickness_mm"] if preset else 6.0,
            min_si=1.5, max_si=60.0, step_si=0.5,
        )

    inclination_deg = st.number_input("Hat Eğim Açısı θ (°)", min_value=-90.0, max_value=90.0, value=preset["incline"] if preset else 0.0, step=1.0, key=f"incl_{preset_token}", help="Pozitif = Yokuş yukarı (hidrostatik basınç kaybı ekler)")
    pipe_mat_name = st.selectbox("Boru Malzemesi (ısıl iletkenlik)", list(PIPE_MATERIALS.keys()))
    roughness_um = st.number_input("Boru İç Pürüzlülüğü ε (µm)", min_value=1.0, max_value=500.0, value=45.0, step=5.0)

    st.markdown("###### ↩️🏭➡️🚢 Karadan Gemiye Dönüş (Sirkülasyon) Hattı")
    return_geom_mode = st.radio(
        "Dönüş Hattı Boyutlandırma Yöntemi",
        ["ASME Tablosu", "Manuel Giriş"],
        index=0 if preset is None else 1,
        horizontal=True,
        key=f"ret_geom_{preset_token}",
    )
    if return_geom_mode == "ASME Tablosu":
        ret_group = st.selectbox("Dönüş Hattı Standardı", list(PIPE_TABLE_GROUPS.keys()), index=1, key="ret_pipe_std")
        ret_table = PIPE_TABLE_GROUPS[ret_group]
        ret_dn_keys = list(ret_table.keys())
        ret_dn_default = ret_dn_keys.index('DN100 (NPS 4")') if 'DN100 (NPS 4")' in ret_dn_keys else 0
        ret_dn_label = st.selectbox("Dönüş Hattı Anma Çapı (DN / NPS)", ret_dn_keys, index=ret_dn_default, key="ret_pipe_dn")
        ret_wall_options = get_wall_thickness_options(ret_group, ret_dn_label)
        ret_wall_keys = list(ret_wall_options.keys())
        ret_sched_default = next(
            (k for k in ret_wall_keys if k.startswith("10S") or k.startswith("40S") or k.startswith("Sch 40")),
            ret_wall_keys[0],
        )
        ret_sched_label = st.selectbox(
            "Dönüş Hattı Et Kalınlığı / Schedule (mm)",
            ret_wall_keys,
            index=ret_wall_keys.index(ret_sched_default),
            key="ret_pipe_sched",
        )
        ret_od_mm = ret_table[ret_dn_label]["od_mm"]
        return_wall_thickness_mm = ret_wall_options[ret_sched_label]
        return_diameter_mm = inner_diameter_mm(ret_od_mm, return_wall_thickness_mm)
        st.caption(f"OD {ret_od_mm:.1f} mm · ID {return_diameter_mm:.2f} mm · t {return_wall_thickness_mm:.2f} mm · {ret_group}")
    else:
        return_diameter_mm, _ = unit_input(
            "Dönüş Hattı İç Çapı", "diameter", "return_diameter",
            100.0, min_si=10.0, max_si=800.0, step_si=10.0,
        )
        return_wall_thickness_mm, _ = unit_input(
            "Dönüş Hattı Et Kalınlığı", "diameter", "return_wall",
            3.0, min_si=1.0, max_si=30.0, step_si=0.5,
        )
    return_mass_flow_kg_s, _ = unit_input(
        "Dönüş Hattı Debisi", "mass_flow", "return_flow",
        5.0, min_si=0.0, max_si=500.0, step_si=1.0,
    )
    recirc_suction_p_pa, _ = unit_input(
        "P-201 Emme Basıncı P_emme", "pressure", "recirc_suction_p",
        1.15e5, min_si=1.013e5, max_si=10.0e5, step_si=0.1e5,
    )
    recirc_target_p_pa, _ = unit_input(
        "Sirkülasyon Hedef Basıncı P_hedef", "pressure", "recirc_target_p",
        5.0e5, min_si=1.05e5, max_si=40.0e5, step_si=0.5e5,
    )
    allowable_recirc_dt_k = st.number_input(
        "İzin Verilen Cooldown Isınması ΔT_izin (K)",
        min_value=0.2,
        max_value=5.0,
        value=1.5,
        step=0.1,
        help="EN 1473 / SIGTTO: Sirkülasyon devresinde iki fazlı flaş ve termal tabakalaşmayı (stratification/bowing) önlemek için standart 1.0 - 2.0 K (varsayılan 1.5 K) alınır.",
    )

# Initialize session state for multi-component composition and multi-layer insulation
if "custom_composition" not in st.session_state:
    st.session_state["custom_composition"] = {"Methane": 94.2, "Ethane": 4.5, "Propane": 0.8, "Nitrogen": 0.5}

if "insulation_layers" not in st.session_state:
    st.session_state["insulation_layers"] = [
        {"name": "PIR Köpük (Poliizosiyanürat)", "thickness_mm": 60.0, "k": 0.024}
    ]

with st.sidebar.expander("❄️ Kriyojenik Akışkan & Kompozisyon", expanded=True):
    comp_mode = st.radio("Akışkan Kompozisyon Modu", ["Standart Şablon", "Özel Komponent Listesi Düzenleyici"])

    if comp_mode == "Standart Şablon":
        preset_comp_choice = st.selectbox(
            "LNG Kompozisyon Şablonu",
            [k for k in LNG_PRESET_COMPOSITIONS.keys() if LNG_PRESET_COMPOSITIONS[k] is not None],
            index=1,
        )
        if preset_comp_choice == "Saf Metan (%100 CH4)":
            is_pure_methane = True
            active_composition = {"Methane": 100.0}
        else:
            is_pure_methane = False
            active_composition = LNG_PRESET_COMPOSITIONS[preset_comp_choice]
            summary_comp_str = ", ".join(f"{COMPONENT_LABELS.get(c, c)}: %{v:.2f}" for c, v in active_composition.items())
            st.caption(f"🧪 **Bileşim:** {summary_comp_str}")
    else:
        is_pure_methane = False
        st.markdown("###### 🧪 Çok Bileşenli Kompozisyon Düzenleyici (28 CoolProp Bileşeni)")

        avail_to_add = [c for c in AVAILABLE_LNG_COMPONENTS if c not in st.session_state["custom_composition"]]
        if avail_to_add:
            c_add_col1, c_add_col2 = st.columns([2.6, 1.0], vertical_alignment="bottom")
            with c_add_col1:
                comp_to_add = st.selectbox(
                    "Eklenecek Komponent",
                    avail_to_add,
                    format_func=lambda x: f"{COMPONENT_LABELS.get(x, x)} [{LNG_COMPONENTS_CATALOG.get(x, {}).get('category', '')}]",
                    key="comp_add_sel",
                )
            with c_add_col2:
                if st.button("➕ Ekle", key="btn_add_comp", use_container_width=True):
                    st.session_state["custom_composition"][comp_to_add] = 0.5
                    st.rerun()

        to_delete = None
        for comp_name in list(st.session_state["custom_composition"].keys()):
            col_k1, col_k2, col_k3 = st.columns([3.4, 2.2, 0.9], vertical_alignment="center")
            with col_k1:
                mm_c = LNG_COMPONENTS_CATALOG.get(comp_name, {}).get("molar_mass", 16.04)
                st.markdown(
                    f"<div style='font-size:13px; font-weight:600; line-height:1.2;'>{COMPONENT_LABELS.get(comp_name, comp_name)}<br/>"
                    f"<span style='font-size:10px; color:#8b949e;'>M = {mm_c:.2f} g/mol</span></div>",
                    unsafe_allow_html=True,
                )
            with col_k2:
                val = st.number_input(
                    "Mol %",
                    min_value=0.0,
                    max_value=100.0,
                    value=float(st.session_state["custom_composition"][comp_name]),
                    step=0.1,
                    format="%.2f",
                    key=f"comp_input_{comp_name}",
                    label_visibility="collapsed",
                )
                st.session_state["custom_composition"][comp_name] = val
            with col_k3:
                if comp_name != "Methane" and len(st.session_state["custom_composition"]) > 1:
                    if st.button("🗑️", key=f"del_comp_{comp_name}"):
                        to_delete = comp_name

        if to_delete:
            del st.session_state["custom_composition"][to_delete]
            st.rerun()

        total_mol_pct = sum(st.session_state["custom_composition"].values())
        if abs(total_mol_pct - 100.0) > 0.05:
            st.warning(f"⚠️ Toplam: %{total_mol_pct:.2f} (100% olmalıdır)")
            if st.button("⚖️ 100%'e Otomatik Normalize Et", key="btn_norm_comp"):
                if total_mol_pct > 0:
                    for k in st.session_state["custom_composition"]:
                        st.session_state["custom_composition"][k] = round((st.session_state["custom_composition"][k] / total_mol_pct) * 100.0, 2)
                    st.rerun()
        else:
            st.success(f"✓ Toplam Mol Oranı: %{total_mol_pct:.2f}")

        active_composition = st.session_state["custom_composition"]

    # Guard: if all composition values are zero, default to pure methane
    if sum(active_composition.values()) <= 0.0:
        st.warning("⚠️ Tüm bileşen oranları sıfır. Varsayılan olarak saf metan seçildi.")
        active_composition = {"Methane": 100.0}

    # Display calculated mixture molar mass
    _fm_preview = FluidManager(fluid_type="pure_methane" if is_pure_methane else "mixture", composition=active_composition)
    st.caption(f"⚖️ **Karışım Mol Kütlesi (M_mix):** {_fm_preview.mixture_molar_mass_g_mol():.2f} g/mol ({len(active_composition)} bileşen)")

    inlet_t_k, t_unit = unit_input(
        "Giriş Sıcaklığı T_in", "temperature", "inlet_t",
        (preset["inlet_t_c"] + 273.15) if preset else 111.65,
        min_si=91.15, max_si=173.15, step_si=0.5,
    )
    inlet_p_pa, p_unit = unit_input(
        "Giriş Toplam Basıncı P_in", "pressure", "inlet_p",
        (preset["inlet_p_bar"] * 1e5) if preset else 5e5,
        min_si=1.013e5, max_si=6.0e6, step_si=0.5e5,
    )
    mass_flow_kg_s, flow_unit = unit_input(
        "Kütlesel Debi m", "mass_flow", "mass_flow",
        preset["mass_flow"] if preset else 40.0,
        min_si=0.5, max_si=2000.0, step_si=5.0,
    )
    inlet_t_c = inlet_t_k - 273.15
    inlet_p_bar = inlet_p_pa / 1e5

    # ---- Girdi doğrulama uyarıları (fiziksel sınırlar) ----
    T_TRIPLE_K = 90.7      # Metan üçlü noktası sıcaklığı
    T_CRIT_K = 190.6       # Metan kritik sıcaklığı
    P_TRIPLE_PA = 11696.0  # Metan üçlü noktası basıncı
    P_CRIT_PA = 4.6e6      # Metan kritik basıncı

    if inlet_t_k <= T_TRIPLE_K * 1.05:
        st.warning(
            f"⚠️ Giriş sıcaklığı üçlü noktaya çok yakın ({inlet_t_c:.1f} °C). "
            "EOS sonuçları bu bölgede kesin olmayabilir."
        )
    elif inlet_t_k >= T_CRIT_K * 0.95:
        st.warning(
            f"⚠️ Giriş sıcaklığı kritik noktaya çok yakın ({inlet_t_c:.1f} °C). "
            "Sıvı-buhan ayrımı tanımsız olabilir."
        )

    if inlet_p_pa <= P_TRIPLE_PA * 1.5:
        st.warning(
            f"⚠️ Giriş basıncı üçlü noktaya çok yakın ({inlet_p_bar:.3f} bar). "
            "Akışkan sihhi fazta olmayabilir."
        )
    elif inlet_p_pa >= P_CRIT_PA * 0.95:
        st.warning(
            f"⚠️ Giriş basıncı kritik noktaya çok yakın ({inlet_p_bar:.3f} bar). "
            "Sıvı-gaz ayrımı kalmaz."
        )

with st.sidebar.expander("🛡️ Çok Katmanlı Kriyojenik İzolasyon", expanded=True):
    ins_pack_choice = st.selectbox(
        "Hazır İzolasyon Paketi Şablonu",
        list(MULTI_LAYER_PACKAGES.keys()),
        index=0
    )
    if ins_pack_choice != "Özel Katman Yapılandırması" and MULTI_LAYER_PACKAGES[ins_pack_choice] is not None:
        if st.button("📦 Bu Paketi Katmanlara Uygula", key="apply_pkg_btn"):
            st.session_state["insulation_layers"] = [dict(layer) for layer in MULTI_LAYER_PACKAGES[ins_pack_choice]]
            st.rerun()

    st.markdown("###### 🧱 Katman Yönetimi (İçten Dışa)")
    if st.button("➕ Yeni İzolasyon Katmanı Ekle", key="btn_add_layer"):
        st.session_state["insulation_layers"].append({
            "name": "PIR Köpük (Poliizosiyanürat)",
            "thickness_mm": 40.0,
            "k": 0.024
        })
        st.rerun()

    del_layer_idx = None
    for idx, layer in enumerate(st.session_state["insulation_layers"]):
        is_inner = (idx == 0)
        is_outer = (idx == len(st.session_state["insulation_layers"]) - 1)
        tag_str = " (İç - Boru Temaslı)" if is_inner else (" (Dış - Dış Ortam)" if is_outer else "")
        st.markdown(f"**Katman #{idx + 1}{tag_str}**")

        c_mat, c_del = st.columns([5, 1])
        with c_mat:
            mat_keys = list(INSULATION_MATERIALS_CATALOG.keys())
            curr_idx = mat_keys.index(layer["name"]) if layer["name"] in mat_keys else 0
            selected_mat = st.selectbox(
                f"Malzeme #{idx+1}",
                mat_keys,
                index=curr_idx,
                key=f"layer_mat_{idx}",
                label_visibility="collapsed"
            )
            if selected_mat != layer["name"]:
                layer["name"] = selected_mat
                layer["k"] = INSULATION_MATERIALS_CATALOG[selected_mat]["k"]
                st.rerun()
        with c_del:
            if len(st.session_state["insulation_layers"]) > 1:
                if st.button("🗑️", key=f"del_layer_{idx}"):
                    del_layer_idx = idx

        c_th, c_k = st.columns(2)
        with c_th:
            layer["thickness_mm"] = st.number_input(
                f"Kalınlık (mm) #{idx+1}",
                min_value=0.1,
                max_value=300.0,
                value=float(layer["thickness_mm"]),
                step=5.0,
                key=f"layer_th_{idx}"
            )
        with c_k:
            layer["k"] = st.number_input(
                f"İletkenlik k (W/m·K) #{idx+1}",
                min_value=0.001,
                max_value=250.0,
                value=float(layer["k"]),
                format="%.4f",
                key=f"layer_k_{idx}"
            )

        st.caption(f"ℹ️ {INSULATION_MATERIALS_CATALOG.get(layer['name'], {}).get('desc', '')}")
        st.markdown("<hr style='margin:4px 0; border-color:rgba(255,255,255,0.08);'/>", unsafe_allow_html=True)

    if del_layer_idx is not None:
        st.session_state["insulation_layers"].pop(del_layer_idx)
        st.rerun()

    total_ins_thick_mm = sum(l["thickness_mm"] for l in st.session_state["insulation_layers"])
    st.info(f"🛡️ **Toplam İzolasyon:** {total_ins_thick_mm:.1f} mm ({len(st.session_state['insulation_layers'])} Katman)")

with st.sidebar.expander("☀️ Çevre ve Dış Ortam", expanded=False):
    amb_temp_k, _ = unit_input(
        "Ortam Sıcaklığı T_amb", "temperature", "amb_t",
        298.15, min_si=253.15, max_si=328.15, step_si=1.0,
    )
    amb_temp_c = amb_temp_k - 273.15
    wind_speed_m_s, _ = unit_input(
        "Rüzgar Hızı", "velocity", "wind",
        3.0, min_si=0.5, max_si=30.0, step_si=0.5,
    )

with st.sidebar.expander("📐 ASME B31.3, Pompa & Kara Tankı (BOG)", expanded=False):
    design_p_pa, _ = unit_input(
        "Tasarım Basıncı P_design", "pressure", "design_p",
        20e5, min_si=2e5, max_si=100e5, step_si=2e5,
    )
    design_p_bar = design_p_pa / 1e5
    valve_closure_time_s = st.slider("ESDV-101 Vana Kapanma Süresi (s)", min_value=0.5, max_value=30.0, value=15.0, step=0.5, help="SIGTTO tavsiyesi: Akustik koç darbesini önlemek için t >= 15-20 s")
    anchor_dist_m, _ = unit_input(
        "Sabit Mesnet Aralığı", "length", "anchor",
        min(float(length_m), 180.0), min_si=20.0, max_si=500.0, step_si=10.0,
    )
    st.markdown("###### ⚙️ Pompa & Elektrik Motoru Verimleri")
    c_pe1, c_pe2 = st.columns(2)
    with c_pe1:
        recirc_pump_eff_pct = st.number_input(
            "P-201 Pompa Verimi η_p (%)",
            min_value=20.0, max_value=95.0, value=70.0, step=1.0,
            key="recirc_pump_eff_pct",
        )
        unload_pump_eff_pct = st.number_input(
            "Kargo Pompa Verimi η_p (%)",
            min_value=20.0, max_value=95.0, value=75.0, step=1.0,
            key="unload_pump_eff_pct",
        )
    with c_pe2:
        recirc_motor_eff_pct = st.number_input(
            "P-201 Motor Verimi η_m (%)",
            min_value=50.0, max_value=99.0, value=90.0, step=1.0,
            key="recirc_motor_eff_pct",
        )
        unload_motor_eff_pct = st.number_input(
            "Kargo Motor Verimi η_m (%)",
            min_value=50.0, max_value=99.0, value=92.0, step=1.0,
            key="unload_motor_eff_pct",
        )
    st.markdown("###### 🛢️ Kara LNG Depolama Tankı (T-201) BOG Girdileri")
    tank_volume_m3 = st.number_input(
        "Kara Tankı Sıvı LNG Hacmi V_tank (m³)",
        min_value=0.0, max_value=500000.0, value=160000.0, step=10000.0,
        help="Tam saha (Total Terminal) BOG kompresör yükü hesabında kara tankı ısı kazancını dahil eder.",
    )
    tank_bor_pct_day = st.number_input(
        "Tank Günlük Kaynama Oranı BOR_tank (%/gün)",
        min_value=0.0, max_value=0.50, value=0.05, step=0.005, format="%.3f",
        help="Modern tam kuşatmalı (Full Containment) kriyojenik kara tankları için tipik tasarım değeri %0.04 - %0.05/gün'dür.",
    )

if is_3d_mode:
    with st.sidebar.expander("🌐 3D Sayısal Izgara Çözünürlüğü", expanded=False):
        n_radial = st.slider("Radyal Katman Sayısı (Nr)", min_value=6, max_value=24, value=12, step=2)
        n_azimuthal = st.slider("Açısal Dilim Sayısı (Nθ)", min_value=6, max_value=24, value=12, step=2)
        n_axial = st.slider("Eksenel Dilim Sayısı (Nz)", min_value=20, max_value=100, value=50, step=10)
        theme = st.selectbox("🌞 / 🌙 Tema", ["Gündüz", "Gece"], index=0)
else:
    n_radial = 8
    n_azimuthal = 8
    n_axial = 100
    theme = "Gündüz"


# --- GÖSTERİM BİRİM DÖNÜŞÜMLERİ (hesaplama içeri K / Pa / kg/s kalır) ---
def _t_show(temp_k, unit):
    return from_si("temperature", temp_k, unit)


def _p_show(pa, unit):
    return from_si("pressure", pa, unit)


def _dp_show(pa, unit):
    return delta_from_si("pressure", pa, unit)


def _m_show(kg_s, unit):
    return from_si("mass_flow", kg_s, unit)


# --- EXECUTE SIMULATION ---
@st.cache_data(show_spinner=False)
def run_simulation(
    length, diam, thick, mat_k, rough, incline,
    is_pure, comp_tuple,
    inlet_t_c, p_in_bar, flow,
    layers_tuple,
    t_amb, wind, use_3d, nr, nt, nz
):
    if is_pure:
        fm = FluidManager(fluid_type="pure_methane")
    else:
        raw_comp = dict(comp_tuple)
        tot = sum(raw_comp.values())
        norm_comp = {k: v / tot for k, v in raw_comp.items()} if tot > 0 else {"Methane": 1.0}
        fm = FluidManager(fluid_type="mixture", composition=norm_comp)

    layers = [
        InsulationLayer(name=l_name, thickness_m=l_th / 1000.0, thermal_conductivity=l_k)
        for (l_name, l_th, l_k) in layers_tuple
    ]
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
        inlet_temperature_k=inlet_t_c + 273.15,
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

comp_tuple = tuple(sorted(active_composition.items()))
layers_tuple = tuple((l["name"], l["thickness_mm"], l["k"]) for l in st.session_state["insulation_layers"])

sim_results = run_simulation(
    length_m, diameter_mm, wall_thickness_mm, PIPE_MATERIALS[pipe_mat_name],
    roughness_um, inclination_deg, is_pure_methane, comp_tuple, inlet_t_c, inlet_p_bar,
    mass_flow_kg_s, layers_tuple, amb_temp_c, wind_speed_m_s,
    is_3d_mode, n_radial, n_azimuthal, n_axial
)

# Return (recirculation) line: 1D solve at the user-configured target pressure for real station data.
_ret_eval_flow = return_mass_flow_kg_s if return_mass_flow_kg_s > 0.0 else 5.0
_ret_eval_results = run_simulation(
    length_m, return_diameter_mm, return_wall_thickness_mm, PIPE_MATERIALS[pipe_mat_name],
    roughness_um, inclination_deg, is_pure_methane, comp_tuple, inlet_t_c, recirc_target_p_pa / 1e5,
    _ret_eval_flow, layers_tuple, amb_temp_c, wind_speed_m_s,
    False, 8, 8, max(20, n_axial)
)
return_results = _ret_eval_results if return_mass_flow_kg_s > 0.0 else None

# --- MAIN DISPLAY ---
mode_label = "3D Sonlu Hacimler (Silindirik r, θ, z)" if is_3d_mode else "1D Sonlu Hacimler (Eksenel)"
st.markdown(f'<div class="main-header">❄️ LNG Boru Akışı Termo-Hidrolik Simülatörü <span style="font-size:16px; color:#58a6ff; font-weight:600;">[{mode_label}]</span></div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Cryogenic LNG Pipeline Thermal Ingress, Hydraulic Pressure Drop & Near-Wall / Bulk Flashing Risk Engine</div>', unsafe_allow_html=True)

u_t = t_unit
u_p = unit_display_label("pressure", p_unit)
u_dp = delta_unit_display_label("pressure", p_unit)
u_f = flow_unit

# Flashing Banner
if is_3d_mode:
    has_flashed = sim_results.has_wall_flashed or sim_results.has_bulk_flashed
    wall_t_d = _t_show(sim_results.wall_temperature_k[-1], t_unit)
    if sim_results.has_wall_flashed and not sim_results.has_bulk_flashed:
        st.markdown(f"""
        <div class="status-alert-box">
            ⚠️ <b>3D ERKEN UYARI: ÇEPERDE KAYNAMA / FLAŞ BAŞLANGICI!</b><br/>
            Boru çeperindeki sınır tabaka akışkan sıcaklığı ({wall_t_d:.2f} {u_t}), yığın sıvıdan sıcaktır. Hattın <b>{sim_results.wall_flashing_point_m:.1f}. metresinde</b> boru iç çeperinde kavitasyon / mikro-kaynama başlamıştır (Yığın sıvı henüz doymamıştır).
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
        min_margin_d = _dp_show(sim_results.min_flashing_margin_pa, p_unit)
        st.markdown(f"""
        <div class="status-safe-box">
            ✓ <b>GÜVENLİ İŞLETME: HEM ÇEPER HEM YIĞIN TAM SIVI FAZDA</b><br/>
            Boru boyunca en kritik iç çeperde dahi buharlaşma marjı pozitiftir (Minimum güvenlik marjı: {min_margin_d:.2f} {u_dp}).
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
        min_margin_d = _dp_show(sim_results.min_flashing_margin_pa, p_unit)
        st.markdown(f"""
        <div class="status-safe-box">
            ✓ <b>GÜVENLİ İŞLETME: TEK FAZ SIVI AKIŞI KORUNUYOR</b><br/>
            Minimum güvenlik marjı: {min_margin_d:.2f} {u_dp}.
        </div>
        """, unsafe_allow_html=True)

# Top KPI metrics (iç hesaplama K / Pa / kg/s; gösterim seçilen birimde)
c1, c2, c3, c4, c5 = st.columns(5)
if is_3d_mode:
    outlet_t_k = sim_results.bulk_temperature_k[-1]
    delta_t_k = sim_results.bulk_temperature_k[-1] - (inlet_t_c + 273.15)
    outlet_p_pa = sim_results.pressure_pa[-1]
    outlet_psat_pa = sim_results.wall_vapor_pressure_pa[-1]
    delta_psat_pa = sim_results.wall_vapor_pressure_pa[-1] - sim_results.wall_vapor_pressure_pa[0]
    min_margin_pa = sim_results.min_flashing_margin_pa
else:
    outlet_t_k = sim_results.outlet_temperature_k
    delta_t_k = sim_results.outlet_temperature_k - (inlet_t_c + 273.15)
    outlet_p_pa = sim_results.outlet_pressure_pa
    outlet_psat_pa = sim_results.outlet_vapor_pressure_pa
    delta_psat_pa = sim_results.outlet_vapor_pressure_pa - sim_results.inlet_vapor_pressure_pa
    min_margin_pa = sim_results.min_flashing_margin_pa

delta_p_pa = sim_results.total_pressure_drop_pa

outlet_t_d = _t_show(outlet_t_k, t_unit)
delta_t_d = delta_from_si("temperature", delta_t_k, t_unit)  # sıcaklık farkı: offset yok
outlet_p_d = _p_show(outlet_p_pa, p_unit)
delta_p_d = _dp_show(delta_p_pa, p_unit)
outlet_psat_d = _p_show(outlet_psat_pa, p_unit)
delta_psat_d = _dp_show(delta_psat_pa, p_unit)
min_margin_d = _dp_show(min_margin_pa, p_unit)
heat_kw = sim_results.total_heat_ingress_w / 1000.0

with c1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Çıkış Yığın Sıcaklığı</div>
        <div class="metric-value">{outlet_t_d:.2f} {u_t}</div>
        <div class="metric-delta delta-up">▲ +{delta_t_d:.2f} {u_t} ısınma</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Çıkış Statik Basıncı</div>
        <div class="metric-value">{outlet_p_d:.2f} {u_p}</div>
        <div class="metric-delta delta-down">▼ -{delta_p_d:.2f} {u_dp} hidrolik kayıp</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Çıkış Buhar Basıncı (Psat)</div>
        <div class="metric-value">{outlet_psat_d:.2f} {u_p}</div>
        <div class="metric-delta delta-up">▲ +{delta_psat_d:.2f} {u_dp} artış</div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    margin_class = "delta-safe" if min_margin_pa >= 0.5e5 else "delta-up"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Min. Kavitasyon Marjı</div>
        <div class="metric-value">{min_margin_d:.2f} {u_dp}</div>
        <div class="metric-delta {margin_class}">P - Psat marjı</div>
    </div>
    """, unsafe_allow_html=True)

with c5:
    m_flow_d = _m_show(mass_flow_kg_s, flow_unit)
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Toplam Isı Girişi Q_tot</div>
        <div class="metric-value">{heat_kw:.1f} kW</div>
        <div class="metric-delta" style="color:#d29922;">{sim_results.total_heat_ingress_w / length_m:.1f} W/m hat kaybı | Akış {m_flow_d:.1f} {u_f}</div>
    </div>
    """, unsafe_allow_html=True)

# --- TERMINAL & MECHANICAL INTEGRITY EVALUATION ---
if is_pure_methane:
    fm_eval = FluidManager(fluid_type="pure_methane")
else:
    tot_c = sum(active_composition.values())
    norm_c = {k: v / tot_c for k, v in active_composition.items()} if tot_c > 0 else {"Methane": 1.0}
    fm_eval = FluidManager(fluid_type="mixture", composition=norm_c)

latent_heat_val = fm_eval.get_latent_heat(sim_results.pressure_pa[-1])
rho_avg = sim_results.density_kg_m3[0] if hasattr(sim_results, "density_kg_m3") and len(sim_results.density_kg_m3) > 0 else 425.0

terminal_ops = evaluate_terminal_operations(
    total_heat_w=sim_results.total_heat_ingress_w,
    length_m=length_m,
    inner_diam_m=diameter_mm / 1000.0,
    fluid_density=rho_avg,
    specific_heat=3480.0,
    latent_heat=latent_heat_val,
    delta_t_allowable=allowable_recirc_dt_k,
    pressure_drop_pa=sim_results.total_pressure_drop_pa,
    main_mass_flow_kg_s=mass_flow_kg_s,
    return_heat_w=_ret_eval_results.total_heat_ingress_w,
    return_pressure_drop_pa=_ret_eval_results.total_pressure_drop_pa if return_results is not None else 0.0,
    user_recirc_flow_kg_s=return_mass_flow_kg_s,
    recirc_suction_pressure_pa=recirc_suction_p_pa,
    recirc_target_pressure_pa=recirc_target_p_pa,
    recirc_pump_eff=recirc_pump_eff_pct / 100.0,
    recirc_motor_eff=recirc_motor_eff_pct / 100.0,
    unload_pump_eff=unload_pump_eff_pct / 100.0,
    unload_motor_eff=unload_motor_eff_pct / 100.0,
    tank_volume_m3=tank_volume_m3,
    tank_bor_pct_day=tank_bor_pct_day,
)

d_outer_m = (diameter_mm + 2.0 * wall_thickness_mm) / 1000.0
pipe_spec = spec_from_material(
    pipe_mat_name,
    outer_diameter_m=d_outer_m,
    design_pressure_pa=design_p_bar * 1e5,
    operating_pressure_pa=inlet_p_bar * 1e5,
    pipeline_length_m=length_m,
    fluid_density_kg_m3=rho_avg,
)
asme_mech = calculate_asme_b31_3_thickness(pipe_spec)
v_nom = mass_flow_kg_s / (rho_avg * (np.pi * (diameter_mm / 2000.0) ** 2))
surge_mech = calculate_joukowsky_surge(pipe_spec, v_nom, valve_closure_time_s, wall_thickness_mm / 1000.0)
omega_mech = calculate_thermal_contraction_and_omega_loop(pipe_spec, anchor_distance_m=anchor_dist_m, outer_diameter_m=d_outer_m)

with st.expander("🏭 Terminal Operasyonları & Pompalama / Mekanik Doğrulama", expanded=True):
    # Sirkülasyon Debisi Kontrol Noktası (Checkpoint Banner)
    if terminal_ops.recirc_flow_deficit_warning:
        st.error(terminal_ops.recirc_flow_warning_msg)
    else:
        st.success(terminal_ops.recirc_flow_warning_msg)

    col_t1, col_t2, col_t3, col_t4 = st.columns(4)
    bog_kg_s = terminal_ops.bog_rate_kg_h / 3600.0
    tot_bog_kg_s = terminal_ops.total_terminal_bog_kg_h / 3600.0
    p_test_d = _p_show(asme_mech["hydrostatic_test_pressure_bar"] * 1e5, p_unit)
    surge_d = _dp_show(surge_mech["actual_surge_bar"] * 1e5, p_unit)
    peak_p_d = _p_show(surge_mech["peak_line_pressure_bar"] * 1e5, p_unit)
    surge_limit_d = _p_show(design_p_bar * 1e5 * 1.33, p_unit)
    with col_t1:
        st.markdown(
            f"**Hat & Saha BOG Yükü:**<br/>"
            f"<span style='color:#f0883e; font-size:16px; font-weight:700;'>Hat: {_m_show(bog_kg_s, flow_unit):.2f} {u_f}</span><br/>"
            f"<span style='color:#8b949e; font-size:12px;'>Toplam Terminal BOG: {_m_show(tot_bog_kg_s, flow_unit):.2f} {u_f} ({terminal_ops.total_terminal_bog_nm3_h:.0f} Nm³/h)</span>",
            unsafe_allow_html=True,
        )
    with col_t2:
        st.markdown(
            f"**P-201 Minimum Gerekli Güç:**<br/>"
            f"<span style='color:#39d353; font-size:16px; font-weight:700;'>{terminal_ops.recirc_min_pump_power_kw:.1f} kW (@ {terminal_ops.recirc_min_flow_m3_h:.1f} m³/h)</span><br/>"
            f"<span style='color:#8b949e; font-size:12px;'>Seçilen Debide Güç: {terminal_ops.user_recirc_pump_power_kw:.1f} kW (@ {terminal_ops.user_recirc_flow_m3_h:.1f} m³/h)</span>",
            unsafe_allow_html=True,
        )
    with col_t3:
        # B6: mill undertolerance — worst-case actual thickness (0.875*t_nom) must meet t_required
        t_ok = (wall_thickness_mm * (1.0 - pipe_spec.mill_tolerance)) >= asme_mech["t_required_min_mm"]
        st.markdown(f"**ASME B31.3 Et Kalınlığı:**<br/><span style='color:{'#3fb950' if t_ok else '#f85149'}; font-size:16px; font-weight:700;'>t_req = {asme_mech['t_required_min_mm']:.2f} mm</span><br/><span style='color:#8b949e; font-size:12px;'>Mevcut: {wall_thickness_mm:.1f} mm ({'✓ UYGUN' if t_ok else '⚠️ YETERSİZ'}) | P_test: {p_test_d:.2f} {u_p}</span>", unsafe_allow_html=True)
    with col_t4:
        # B7: surge acceptance vs design pressure (1.33x occasional overpressure allowance), not hard-coded 5 bar
        surge_safe = surge_mech["peak_line_pressure_bar"] <= design_p_bar * 1.33
        st.markdown(f"**ESDV Joukowsky Koç Darbesi:**<br/><span style='color:{'#3fb950' if surge_safe else '#f85149'}; font-size:16px; font-weight:700;'>+{surge_d:.2f} {u_dp}</span><br/><span style='color:#8b949e; font-size:12px;'>P_peak = {peak_p_d:.1f} {u_p} (Güvenli Kapanma ≥ {surge_mech['recommended_min_valve_closure_s']:.0f}s)</span>", unsafe_allow_html=True)

    # Pompalama Önerisi, Verim ve Kara Tankı BOG Analizi Alt Satırı
    st.markdown("---")
    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        st.info(
            f"⚓ **Gemiden Karaya Ana Boşaltım (Cargo Pumps):**\n"
            f"- **Toplam Boşaltım Debisi:** {terminal_ops.unloading_flow_m3_h:.1f} m³/h ({mass_flow_kg_s:.1f} kg/s)\n"
            f"- **Manometrik Basma Yüksekliği (TDH):** {terminal_ops.unloading_pump_head_m:.1f} mLC ({terminal_ops.unloading_pump_head_m * rho_avg * 9.80665 / 1e5:.2f} bar)\n"
            f"- **Verimler:** $\\eta_{{pompa}} = \\%{unload_pump_eff_pct:.0f}$, $\\eta_{{motor}} = \\%{unload_motor_eff_pct:.0f}$\n"
            f"- **Toplam Elektrik Motor Gücü:** **{terminal_ops.unloading_pump_power_kw:.1f} kW**\n"
            f"- **Öneri:** {terminal_ops.unloading_pump_recommendation}"
        )
    with col_p2:
        strat_warn = "⚠️ Akış hızı düşük (Richardson tabakalaşma riski var)" if terminal_ops.stratification_risk else "✓ Akış hızı yeterli (Termal eğilme / tabakalaşma önlendi)"
        p_suct_d = _p_show(recirc_suction_p_pa, p_unit)
        p_targ_d = _p_show(recirc_target_p_pa, p_unit)
        dt_user_str = f"{terminal_ops.user_recirc_delta_t_k:.2f} K" if math.isfinite(terminal_ops.user_recirc_delta_t_k) else "∞ (Akış Yok)"
        st.success(
            f"🔄 **Karadan Gemiye Sirkülasyon Pompası (P-201):**\n"
            f"- **Basınçlandırma Hedefi:** {p_suct_d:.2f} $\\rightarrow$ {p_targ_d:.2f} {u_p} (TDH: {terminal_ops.recirc_pump_head_m:.1f} mLC)\n"
            f"- **Min. Gerekli Cooldown Debisi ($\\Delta T \\le {allowable_recirc_dt_k:.1f}$ K):** **{terminal_ops.recirc_min_flow_kg_s:.2f} kg/s** ({terminal_ops.recirc_min_flow_m3_h:.1f} m³/h)\n"
            f"- **Minimum Gerekli Pompa Gücü:** **{terminal_ops.recirc_min_pump_power_kw:.2f} kW** ($\\eta_p=\\%{recirc_pump_eff_pct:.0f}, \\eta_m=\\%{recirc_motor_eff_pct:.0f}$)\n"
            f"- **Seçilen Debideki Pompa Gücü ({return_mass_flow_kg_s:.2f} kg/s):** **{terminal_ops.user_recirc_pump_power_kw:.2f} kW** (Devre $\\Delta T = {dt_user_str}$)\n"
            f"- **Termal Denge Durumu:** {strat_warn}"
        )
    with col_p3:
        q_loop_kw = (sim_results.total_heat_ingress_w + _ret_eval_results.total_heat_ingress_w) / 1000.0
        q_tank_kw = terminal_ops.tank_heat_ingress_w / 1000.0
        q_pump_kw = terminal_ops.pump_heat_to_lng_w / 1000.0
        st.warning(
            f"🛢️ **Kara LNG Tankı (T-201) & Toplam Terminal BOG Bütçesi:**\n"
            f"- **Boru Devresi Isı Kazancı ($\\dot{{Q}}_{{ana}} + \\dot{{Q}}_{{dönüş}}$):** {q_loop_kw:.2f} kW ({terminal_ops.bog_rate_kg_h:.1f} kg/h)\n"
            f"- **Kara Tankı Isı Kazancı ($V={tank_volume_m3:,.0f}$ m³, BOR=%{tank_bor_pct_day:.3f}/gün):** **{q_tank_kw:.1f} kW** ({terminal_ops.tank_bog_rate_kg_h:.1f} kg/h)\n"
            f"- **P-201 Pompa Şaft Isısı ($\\dot{{Q}}_{{pompa}}$):** {q_pump_kw:.2f} kW\n"
            f"- **Toplam Terminal BOG Kompresör Yükü:** **{terminal_ops.total_terminal_bog_kg_h:.1f} kg/h** ({terminal_ops.total_terminal_bog_nm3_h:.0f} Nm³/h)"
        )

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
    html_schematic_2d = generate_schematic_2d_html(sim_results, height_px=620, length_m=length_m, anchor_dist_m=anchor_dist_m, temp_unit=t_unit, press_unit=p_unit)
    st.components.v1.html(html_schematic_2d, height=640, scrolling=False)

with tab_3d_terminal:
    st.markdown("##### ⚓ 3D Terminal Sahası & Boru Köprüsü Dijital İkizi (Three.js)")
    st.caption("Açık deniz LUP dolfeni, yanaşmış LNG gemisi, APD dolfenleri, 3D Omega termal genleşme döngüleri, kara tankı ve sirkülasyon pompasını 3D uzayda serbestçe gezin.")
    html_terminal_3d = generate_terminal_3d_html(
        sim_results,
        height_px=640,
        main_diameter_mm=diameter_mm,
        main_wall_mm=wall_thickness_mm,
        return_diameter_mm=return_diameter_mm,
        return_wall_mm=return_wall_thickness_mm,
        main_material=pipe_mat_name,
        return_material=pipe_mat_name,
        return_flow_kg_s=return_mass_flow_kg_s,
        return_results=return_results,
        length_m=length_m,
        anchor_dist_m=anchor_dist_m,
        theme=theme,
    )
    st.components.v1.html(html_terminal_3d, height=660, scrolling=False)

with tab_3d_pipe:
    st.markdown("##### 🔍 3D Three.js Kriyojenik Kesitli Boru Görselleştirici")
    st.caption("Sol tık ile döndürün, sağ tık ile kaydırın, fare tekerleğiyle yakınlaşın. 180° Kesit ile iç sıvı çekirdeği ve izolasyon katmanlarını inceleyin.")
    html_3d = generate_3d_pipe_html(sim_results, height_px=560, temp_unit=t_unit, press_unit=p_unit)
    st.components.v1.html(html_3d, height=580, scrolling=False)

with tab_charts:
    st.markdown("##### 📈 2D Dinamik Termodinamik & Hidrolik Eğriler")
    
    col_chart_top_1, col_chart_top_2 = st.columns(2)
    with col_chart_top_1:
        st.plotly_chart(create_pressure_comparison_chart(sim_results, press_unit=p_unit), use_container_width=True)
    with col_chart_top_2:
        st.plotly_chart(create_temperature_profile_chart(sim_results, temp_unit=t_unit), use_container_width=True)

    col_chart_bot_1, col_chart_bot_2 = st.columns(2)
    with col_chart_bot_1:
        st.plotly_chart(create_flashing_margin_chart(sim_results, press_unit=p_unit), use_container_width=True)
    with col_chart_bot_2:
        if is_3d_mode:
            station_pct = st.slider("3D Enine Kesit İstasyon Konumu (% Uzunluk)", 0, 100, 100, step=10)
            station_idx = int((station_pct / 100.0) * (len(sim_results.distance_m) - 1))
            st.plotly_chart(create_radial_cross_section_heatmap(sim_results, slice_index=station_idx, temp_unit=t_unit), use_container_width=True)
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
        if hasattr(sim_results, "void_fraction") and len(sim_results.void_fraction) == len(sim_results.distance_m):
            df_data["Buhar Boşluk Kesri (α)"] = [round(a, 4) for a in sim_results.void_fraction]
            df_data["İki Fazlı Sürtünme Çarpanı (Φ²)"] = [round(phi, 2) for phi in sim_results.two_phase_multiplier]
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
        if hasattr(sim_results, "void_fraction") and len(sim_results.void_fraction) == len(sim_results.distance_m):
            df_data["Buhar Boşluk Kesri (α)"] = [round(a, 4) for a in sim_results.void_fraction]
            df_data["İki Fazlı Sürtünme Çarpanı (Φ²)"] = [round(phi, 2) for phi in sim_results.two_phase_multiplier]
    df = pd.DataFrame(df_data)
    st.dataframe(df, use_container_width=True, height=450)
    
    csv_bytes = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Hücre Verilerini CSV Olarak İndir",
        data=csv_bytes,
        file_name=f"lng_pipeline_results_{int(length_m)}m_{'3d' if is_3d_mode else '1d'}.csv",
        mime="text/csv"
    )

    # JSON dışa aktarma - tüm sonuçları yapılandırılmış biçimde
    json_export = {
        "project": {
            "name": proj_name_input if 'proj_name_input' in dir() else "LNG Pipeline Study",
            "tag_id": tag_id_input if 'tag_id_input' in dir() else "LNG-PL-001",
            "date": report_date if 'report_date' in dir() else "2026-11-06"
        },
        "simulation": {
            "mode": "3D" if is_3d_mode else "1D",
            "length_m": length_m,
            "diameter_mm": diameter_mm,
            "wall_thickness_mm": wall_thickness_mm,
            "inlet_temperature_c": round(inlet_t_c, 2),
            "inlet_pressure_bar": round(inlet_p_bar, 3),
            "mass_flow_kg_s": mass_flow_kg_s,
            "ambient_temperature_c": amb_temp_c,
            "wind_speed_m_s": wind_speed_m_s,
            "fluid": "pure_methane" if is_pure_methane else "mixture",
            "composition": active_composition
        },
        "results": {
            "outlet_temperature_c": round(outlet_t_d, 2),
            "outlet_pressure_bar": round(outlet_p_d, 3),
            "outlet_psat_bar": round(outlet_psat_d, 3),
            "pressure_drop_bar": round(delta_p_d, 3),
            "min_flashing_margin_bar": round(min_margin_d, 3),
            "total_heat_ingress_kw": heat_kw,
            "has_flashed": has_flashed,
            "flashing_point_m": sim_results.flashing_point_m if hasattr(sim_results, 'flashing_point_m') else (sim_results.wall_flashing_point_m if hasattr(sim_results, 'wall_flashing_point_m') else None)
        },
        "cells": df_data
    }
    json_bytes = json.dumps(json_export, indent=2, ensure_ascii=False).encode('utf-8')
    st.download_button(
        label="📥 Sonuçları JSON Olarak İndir",
        data=json_bytes,
        file_name=f"lng_pipeline_results_{int(length_m)}m_{'3d' if is_3d_mode else '1d'}.json",
        mime="application/json"
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
    rho_flow = sim_results.density_kg_m3[0] if (hasattr(sim_results, "density_kg_m3") and len(sim_results.density_kg_m3) > 0) else 425.0
    v_approx = mass_flow_kg_s / (rho_flow * (np.pi * (diameter_mm / 2000.0) ** 2))
    m_bar = sim_results.min_flashing_margin_pa / 1e5
    
    compliance_rows = [
        {"Kontrol Kriteri": "Akış Hızı (Stratifikasyon & Statik Sınırı)", "Standart": "EN 1473: 0.5 - 4.5 m/s", "Mevcut Değer": f"{v_approx:.2f} m/s", "Durum": "✓ UYGUN" if 0.5 <= v_approx <= 4.5 else "⚠️ UYARI"},
        {"Kontrol Kriteri": "Flaş & Kavitasyon Marjı", "Standart": "P - Psat ≥ 0.5 bar", "Mevcut Değer": f"{m_bar:.2f} bar", "Durum": "✓ UYGUN" if m_bar >= 0.5 else "⚠️ RİSKLİ"},
        {"Kontrol Kriteri": "Faz Korunumu (Tek Faz Sıvı)", "Standart": "Boil-off = 0", "Mevcut Değer": "Tam Sıvı" if not has_flashed else f"Flaş Başlangıcı", "Durum": "✓ UYGUN" if not has_flashed else "❌ KAYNAMA"},
        {"Kontrol Kriteri": f"Sirkülasyon Debisi Kontrolü (ΔT ≤ {allowable_recirc_dt_k:.1f} K)", "Standart": f"m ≥ {terminal_ops.recirc_min_flow_kg_s:.2f} kg/s", "Mevcut Değer": f"{return_mass_flow_kg_s:.2f} kg/s ({terminal_ops.user_recirc_flow_m3_h:.1f} m³/h)", "Durum": "✓ UYGUN" if not terminal_ops.recirc_flow_deficit_warning else "⚠️ DÜŞÜK DEBİ"}
    ]
    st.table(pd.DataFrame(compliance_rows))

    meta_dict = {
        "project_name": proj_name_input,
        "tag_id": tag_id_input,
        "engineer_name": engineer_input,
        "date_str": report_date
    }
    
    # Hücre verilerini string'e çevir (PDF tablosu için)
    pdf_cell_data = []
    if df_data:
        headers = list(df_data.keys())
        n_rows = len(df_data[headers[0]]) if headers else 0
        pdf_cell_data = [headers]
        for r in range(n_rows):
            row = []
            for h in headers:
                v = df_data[h][r]
                row.append(str(v) if isinstance(v, float) else str(v))
            pdf_cell_data.append(row)
    pdf_bytes = generate_pdf_report(sim_results, meta_dict, temp_unit=t_unit, press_unit=p_unit, cell_data=pdf_cell_data, terminal_ops=terminal_ops)
    st.download_button(
        label="📄 Resmi PDF Mühendislik Hesaplama Raporunu İndir",
        data=pdf_bytes,
        file_name=f"{tag_id_input}_thermal_hydraulic_report.pdf",
        mime="application/pdf"
    )

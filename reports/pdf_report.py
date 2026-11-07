"""Professional PDF engineering calculation report generator for LNG pipeline flow."""

import io
import math
from typing import Dict, Any
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from core.solver import PipelineSimulationResults
from core.solver_3d import Simulation3DResults
from core.terminal_ops import evaluate_terminal_operations
from core.mechanics import (
    PipelineSpecification,
    calculate_asme_b31_3_thickness,
    calculate_thermal_contraction_and_omega_loop,
    calculate_joukowsky_surge,
)
from core.units import from_si


def generate_pdf_report(results, project_info: Dict[str, Any], temp_unit: str = "°C", press_unit: str = "bar", cell_data: list = None) -> bytes:
    """Generates an executive engineering calculation sheet in PDF format."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    if isinstance(results, Simulation3DResults):
        cfg = results.config.pipeline_config
        outlet_t_k = results.bulk_temperature_k[-1]
        outlet_p_pa = results.pressure_pa[-1]
        outlet_psat_pa = results.wall_vapor_pressure_pa[-1]
        inlet_psat_pa = results.wall_vapor_pressure_pa[0]
        flashed = results.has_wall_flashed
        flash_point_m = results.wall_flashing_point_m or 0.0
        rho_in = results.density_kg_m3[0] if (hasattr(results, "density_kg_m3") and len(results.density_kg_m3) > 0) else 425.0
        rho_out = results.density_kg_m3[-1] if (hasattr(results, "density_kg_m3") and len(results.density_kg_m3) > 0) else 425.0
        flow_area = math.pi * ((cfg.inner_diameter_m / 2.0) ** 2)
        v_in = cfg.mass_flow_rate_kg_s / (rho_in * flow_area)
        v_out = cfg.mass_flow_rate_kg_s / (rho_out * flow_area)
    else:
        cfg = results.config
        outlet_t_k = results.outlet_temperature_k
        outlet_p_pa = results.outlet_pressure_pa
        outlet_psat_pa = results.outlet_vapor_pressure_pa
        inlet_psat_pa = results.inlet_vapor_pressure_pa
        flashed = results.has_flashed
        flash_point_m = results.flashing_point_m or 0.0
        v_in = results.velocity_m_s[0]
        v_out = results.velocity_m_s[-1]

    # Convert all values to display units
    t_in_d = from_si("temperature", cfg.inlet_temperature_k, temp_unit)
    t_out_d = from_si("temperature", outlet_t_k, temp_unit)
    p_in_d = from_si("pressure", cfg.inlet_pressure_pa, press_unit)
    p_out_d = from_si("pressure", outlet_p_pa, press_unit)
    psat_out_d = from_si("pressure", outlet_psat_pa, press_unit)
    psat_in_d = from_si("pressure", inlet_psat_pa, press_unit)
    margin_d = from_si("pressure", results.min_flashing_margin_pa, press_unit)
    delta_t_d = from_si("temperature", outlet_t_k - cfg.inlet_temperature_k, temp_unit)  # delta: no offset
    delta_p_d = from_si("pressure", results.total_pressure_drop_pa, press_unit)
    delta_psat_d = from_si("pressure", outlet_psat_pa - inlet_psat_pa, press_unit)
    heat_kw = results.total_heat_ingress_w / 1000.0

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f2a4a"),
        spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        textColor=colors.HexColor("#555555"),
        spaceAfter=12
    )
    section_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#0f2a4a"),
        spaceBefore=10,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#222222")
    )
    bold_style = ParagraphStyle(
        "BodyBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#0f2a4a")
    )

    story = []

    # Title & Metadata
    proj_name = project_info.get("project_name", "LNG Pipeline Flow Simulation")
    tag_id = project_info.get("tag_id", "LNG-PL-001")
    engineer = project_info.get("engineer_name", "Kıdemli Proses Mühendisi")
    date_str = project_info.get("date_str", "2026-11-06")

    story.append(Paragraph(f"<b>{proj_name}</b>", title_style))
    story.append(Paragraph(f"Ekipman Etiketi: {tag_id} | Mühendis: {engineer} | Tarih: {date_str}", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f2a4a"), spaceAfter=12))

    # Executive Status Banner
    banner_color = colors.HexColor("#d9383a") if flashed else colors.HexColor("#28a745")
    status_text = (
        f"DİKKAT: Boru boyunca {flash_point_m:.1f} m noktasında Flaş / Kaynama Başlangıcı tespit edildi!"
        if flashed else
        "UYGUNDUR: Tüm boru hattı boyunca sıvı tek faz korunmuş olup buharlaşma / kavitasyon riski bulunmamaktadır."
    )
    banner_data = [[Paragraph(f"<b>DURUM: {status_text}</b>", ParagraphStyle("Banner", parent=body_style, textColor=colors.white))]]
    banner_table = Table(banner_data, colWidths=[520])
    banner_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), banner_color),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(banner_table)
    story.append(Spacer(1, 10))

    # 1. Pipeline Design Inputs
    story.append(Paragraph("1. Tasarım Girdileri ve Hat Özellikleri", section_style))
    inputs_data = [
        [Paragraph("Hat Uzunluğu (L)", bold_style), Paragraph(f"{cfg.length_m:.1f} m", body_style),
         Paragraph("İç Çap (ID)", bold_style), Paragraph(f"{cfg.inner_diameter_m * 1000.0:.1f} mm", body_style)],
        [Paragraph("Eğim Açısı", bold_style), Paragraph(f"{cfg.inclination_deg:.1f}°", body_style),
         Paragraph("Mutlak Pürüzlülük", bold_style), Paragraph(f"{cfg.roughness_m * 1e6:.1f} µm", body_style)],
        [Paragraph("Giriş Sıcaklığı (T_in)", bold_style), Paragraph(f"{t_in_d:.2f} {temp_unit}", body_style),
         Paragraph("Giriş Basıncı (P_in)", bold_style), Paragraph(f"{p_in_d:.3f} {press_unit}", body_style)],
        [Paragraph("Kütlesel Debi", bold_style), Paragraph(f"{cfg.mass_flow_rate_kg_s:.2f} kg/s ({cfg.mass_flow_rate_kg_s * 3.6:.1f} t/h)", body_style),
         Paragraph("Akış Hızı (Giriş)", bold_style), Paragraph(f"{v_in:.2f} m/s", body_style)],
    ]
    inputs_table = Table(inputs_data, colWidths=[130, 130, 130, 130])
    inputs_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8f9fa")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(inputs_table)
    story.append(Spacer(1, 10))

    # 2. Key Calculation Results
    story.append(Paragraph("2. Termal ve Hidrolik Hesaplama Sonuçları", section_style))
    results_data = [
        [Paragraph("Çıkış Sıcaklığı (T_out)", bold_style), Paragraph(f"{t_out_d:.2f} {temp_unit}", body_style),
         Paragraph("Sıcaklık Artışı (ΔT)", bold_style), Paragraph(f"{delta_t_d:.2f} {temp_unit}", body_style)],
        [Paragraph("Çıkış Statik Basıncı (P_out)", bold_style), Paragraph(f"{p_out_d:.3f} {press_unit}", body_style),
         Paragraph("Toplam Basınç Düşüşü (ΔP)", bold_style), Paragraph(f"{delta_p_d:.3f} {press_unit}", body_style)],
        [Paragraph("Çıkış Buhar Basıncı (Psat)", bold_style), Paragraph(f"{psat_out_d:.3f} {press_unit}", body_style),
         Paragraph("Buhar Basıncı Artışı (ΔPsat)", bold_style), Paragraph(f"{delta_psat_d:.3f} {press_unit}", body_style)],
        [Paragraph("Min. Kavitasyon/Flaş Marjı", bold_style), Paragraph(f"{margin_d:.3f} {press_unit}", body_style),
         Paragraph("Toplam Isı Girişi (Q_tot)", bold_style), Paragraph(f"{heat_kw:.2f} kW ({results.total_heat_ingress_w / cfg.length_m:.1f} W/m)", body_style)],
    ]
    results_table = Table(results_data, colWidths=[130, 130, 130, 130])
    results_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#ffffff")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(results_table)
    story.append(Spacer(1, 10))

    # 3. Standards & Engineering Compliance Checks (ASME B31.3 / EN 1473)
    story.append(Paragraph("3. Mühendislik Standartları ve Güvenlik Denetimleri (ASME B31.3 / EN 1473)", section_style))
    
    # Velocity bounds: 0.5 m/s to 4.5 m/s
    v_status = "UYGUN" if (0.5 <= v_out <= 4.5) else "UYARI"
    v_msg = f"Akış hızı ({v_out:.2f} m/s) tavsiye edilen 0.5 - 4.5 m/s aralığındadır (Tabakalaşma ve elektrostatik riskleri önler)." if v_status == "UYGUN" else f"Akış hızı ({v_out:.2f} m/s) tavsiye edilen aralığın dışındadır."

    # NPSH / Flashing margin: at least 0.5 bar
    margin_bar = results.min_flashing_margin_pa / 1e5
    m_status = "UYGUN" if margin_bar >= 0.5 else ("DİKKAT" if margin_bar > 0.0 else "KRİTİK")
    m_msg = f"Minimum güvenlik marjı ({margin_bar:.2f} bar) ≥ 0.5 bar tavsiyesini karşılamaktadır." if m_status == "UYGUN" else f"Güvenlik marjı ({margin_bar:.2f} bar) düşüktür veya kaynama başlamıştır."

    checks_data = [
        [Paragraph("Kontrol Parametresi", bold_style), Paragraph("Standart / Tavsiye", bold_style), Paragraph("Değerlendirme", bold_style), Paragraph("Sonuç", bold_style)],
        [Paragraph("Akış Hızı Sınırı", body_style), Paragraph("0.5 - 4.5 m/s (EN 1473)", body_style), Paragraph(v_msg, body_style), Paragraph(f"<b>{v_status}</b>", body_style)],
        [Paragraph("Kavitasyon / Flaş Marjı", body_style), Paragraph("P - Psat ≥ 0.5 bar", body_style), Paragraph(m_msg, body_style), Paragraph(f"<b>{m_status}</b>", body_style)],
        [Paragraph("Faz Değişimi Riski", body_style), Paragraph("Buharlaşma = 0 (Tek Faz)", body_style), Paragraph("Çıkışa kadar tam sıvı faz sağlanmalıdır." if not flashed else "Boru içinde 2 fazlı buhar kabarcıkları oluşmuştur.", body_style), Paragraph("<b>UYGUN</b>" if not flashed else "<b>KAYNAMA</b>", body_style)]
    ]
    checks_table = Table(checks_data, colWidths=[110, 110, 230, 70])
    checks_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f2a4a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(checks_table)
    story.append(Spacer(1, 10))

    # 4. Terminal Operations & Cryogenic Mechanical Integrity (BOG, ASME B31.3, Surge)
    story.append(Paragraph("4. Terminal Operasyonları ve Kriyojenik Mekanik Doğrulama (BOG, ASME B31.3 & Surge)", section_style))

    # Evaluate using robust core domain modules
    rho_eval = results.density_kg_m3[0] if (hasattr(results, "density_kg_m3") and len(results.density_kg_m3) > 0) else 425.0
    t_ops = evaluate_terminal_operations(
        total_heat_w=results.total_heat_ingress_w,
        length_m=cfg.length_m,
        inner_diam_m=cfg.inner_diameter_m,
        fluid_density=rho_eval,
        specific_heat=3480.0,
        latent_heat=510500.0,
        delta_t_allowable=1.5,
        pressure_drop_pa=results.total_pressure_drop_pa
    )

    d_out_eval = cfg.inner_diameter_m + 0.012  # Nominal pipe outer diameter estimation
    spec_eval = PipelineSpecification(
        outer_diameter_m=d_out_eval,
        design_pressure_pa=max(cfg.inlet_pressure_pa * 1.5, 2.0e6),
        operating_pressure_pa=cfg.inlet_pressure_pa,
        pipeline_length_m=cfg.length_m,
        fluid_density_kg_m3=rho_eval
    )
    asme_eval = calculate_asme_b31_3_thickness(spec_eval)
    omega_eval = calculate_thermal_contraction_and_omega_loop(spec_eval, anchor_distance_m=min(cfg.length_m, 200.0), outer_diameter_m=d_out_eval)
    surge_eval = calculate_joukowsky_surge(spec_eval, v_in, valve_closure_time_s=15.0, wall_thickness_m=0.006)

    terminal_data = [
        [Paragraph("Statik Hat BOG Üretim Hızı", bold_style), Paragraph(f"{t_ops.bog_rate_kg_h:.1f} kg/saat ({t_ops.bog_rate_nm3_h:.1f} Nm³/saat)", body_style),
         Paragraph("Min. Cooldown Sirkülasyon Debisi", bold_style), Paragraph(f"{t_ops.recirc_min_flow_m3_h:.1f} m³/saat (P-201: {t_ops.recirc_pump_power_kw:.1f} kW)", body_style)],
        [Paragraph("Hat Isıl Büzülme Miktarı (ΔL)", bold_style), Paragraph(f"{omega_eval['contraction_rate_mm_per_m']:.2f} mm/m ({omega_eval['total_line_contraction_m']:.2f} m/km)", body_style),
         Paragraph("ESDV Kapanma Koç Darbesi (15s)", bold_style), Paragraph(f"+{surge_eval['actual_surge_bar']:.2f} bar (P_peak: {surge_eval['peak_line_pressure_bar']:.1f} bar)", body_style)]
    ]
    terminal_table = Table(terminal_data, colWidths=[130, 130, 130, 130])
    terminal_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8f9fa")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(terminal_table)
    story.append(Spacer(1, 15))

    # 5. Dilim Bazlı Veriler (Özet)
    if cell_data:
        story.append(Paragraph("5. Dilim Bazlı Veriler (Özet)", section_style))
        cell_table = Table(cell_data, colWidths=[130, 130, 130, 130])
        cell_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f2a4a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dee2e6")),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(cell_table)
        story.append(Spacer(1, 15))

    # Signature / Approval Block
    sig_data = [
        [Paragraph("Hesaplayan / Hazırlayan:", body_style), Paragraph("Kontrol Eden / Onaylayan:", body_style)],
        [Paragraph(f"İmza: ____________________<br/>Tarih: {date_str}", body_style), Paragraph("İmza: ____________________<br/>Tarih: _______________", body_style)]
    ]
    sig_table = Table(sig_data, colWidths=[260, 260])
    sig_table.setStyle(TableStyle([
        ("LINEBEFORE", (1, 0), (1, -1), 0.5, colors.HexColor("#cccccc")),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(sig_table)

    doc.build(story)
    return buffer.getvalue()

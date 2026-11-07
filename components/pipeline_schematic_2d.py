"""Interactive 2D P&ID and Pipeline Layout Schematic for LNG Marine Terminal."""

import json
from core.solver import PipelineSimulationResults
from core.solver_3d import Simulation3DResults


def generate_schematic_2d_html(results, height_px: int = 620, length_m: float | None = None, anchor_dist_m: float = 180.0) -> str:
    """Generates an interactive SVG/HTML P&ID schematic of the Jetty-to-Tank circuit."""

    if isinstance(results, Simulation3DResults):
        cfg = results.config.pipeline_config
        t_out = results.bulk_temperature_k[-1] - 273.15
        p_out = results.pressure_pa[-1] / 1e5
        psat_out = results.wall_vapor_pressure_pa[-1] / 1e5
        flashed = results.has_wall_flashed
        flash_m = results.wall_flashing_point_m or 0.0
    else:
        cfg = results.config
        t_out = results.outlet_temperature_k - 273.15
        p_out = results.outlet_pressure_pa / 1e5
        psat_out = results.outlet_vapor_pressure_pa / 1e5
        flashed = results.has_flashed
        flash_m = results.flashing_point_m or 0.0

    t_in = cfg.inlet_temperature_k - 273.15
    p_in = cfg.inlet_pressure_pa / 1e5
    inlet_t_c = t_in
    inlet_p_bar = p_in
    m_flow = cfg.mass_flow_rate_kg_s

    # Dynamic omega count and layout, synchronized with the 3D view.
    route_length = length_m if length_m else cfg.length_m
    omega_count = max(1, min(8, int(round(route_length / max(anchor_dist_m, 50.0)))))
    omega_span_start, omega_span_end = 300.0, 760.0
    slot = (omega_span_end - omega_span_start) / omega_count
    omega_w = min(50.0, slot * 0.78)
    main_path_parts = ["M 140 270", "L 200 270"]
    omega_groups = []
    apd_groups = []
    omega_labels = []
    for k in range(omega_count):
        x0 = omega_span_start + slot * k + (slot - omega_w) / 2.0
        x1 = x0 + omega_w
        cx = (x0 + x1) / 2.0
        frac = (k + 1) / (omega_count + 1)
        t_om = t_in + (t_out - t_in) * frac
        p_om = p_in - (p_in - p_out) * frac
        main_path_parts.extend([
            f"L {x0:.1f} 270", f"L {x0:.1f} 180",
            f"L {x1:.1f} 180", f"L {x1:.1f} 270",
        ])
        omega_groups.append(f"""
      <g class="node-group" onclick="showInfo('Omega-{k+1} Dolfeni (Expansion Loop)', 'Kriyojenik büzülmeyi sönümleyen {k+1}. Omega genleşme döngüsü. Hat soğuduğunda esneyerek gerilimi azaltır.', '{t_om:.1f} °C', '{p_om:.2f} bar', 'Ω-Loop {k+1}')">
        <rect x="{x0-10:.1f}" y="160" width="{omega_w+20:.1f}" height="180" fill="#161b22" stroke="#d29922" stroke-width="1.5" stroke-dasharray="4,2" rx="4" />
        <circle cx="{cx:.1f}" cy="172" r="5" fill="#da3633" />
        <text x="{x0-5:.1f}" y="152" fill="#d29922" font-size="10" font-weight="700">OMEGA-{k+1} DOLFENİ</text>
        <text x="{cx-10:.1f}" y="352" fill="#8b949e" font-size="9" font-weight="600">Ω-Loop {k+1}</text>
      </g>""")
        omega_labels.append((cx, t_om, p_om))
    for k in range(omega_count + 1):
        ax = omega_span_start + slot * k
        apd_groups.append(f"""
      <g class="node-group" onclick="showInfo('APD-{k+1} Dolfeni', 'Yaklaşım köprüsü taşıyıcı dolfeni. Kriyojenik boru köprüsünü taşır.', '{t_in + 0.3:.1f} °C', '{p_in - 0.1:.2f} bar', 'Kazık Çapı: 1200 mm')">
        <rect x="{ax-15:.1f}" y="250" width="30" height="85" fill="#21262d" stroke="#8b949e" stroke-width="1.5" rx="3" />
        <circle cx="{ax:.1f}" cy="310" r="4" fill="#30363d" />
        <text x="{ax-22:.1f}" y="352" fill="#8b949e" font-size="9" font-weight="600">APD-{k+1}</text>
      </g>""")
    main_path_parts.append("L 955 270")
    main_path_d = " ".join(main_path_parts)
    omega_and_apd_html = "".join(omega_groups) + "".join(apd_groups)
    if omega_labels:
        fx, ft, fp = omega_labels[0]
        omega_label_html = (
            f'<rect x="{fx-45:.1f}" y="240" width="95" height="18" fill="rgba(14,17,23,0.85)" rx="3" stroke="#d29922" />\n'
            f'      <text x="{fx-40:.1f}" y="253" fill="#d29922" font-size="9" font-weight="700">Ω-1: {fp:.1f}b | {ft:.1f}°</text>'
        )
    else:
        omega_label_html = ""

    html = f"""
<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; user-select: none; }}
    body {{
      background: #0e1117;
      color: #e6edf3;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      overflow: hidden;
      width: 100%;
      height: {height_px}px;
    }}
    .schematic-container {{
      width: 100%;
      height: 100%;
      position: relative;
      display: flex;
      flex-direction: column;
    }}
    .toolbar {{
      background: #161b22;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
      padding: 8px 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 12px;
    }}
    .toolbar-title {{
      font-weight: 700;
      color: #58a6ff;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .legend-badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      margin-left: 12px;
      font-size: 11px;
      color: #c9d1d9;
    }}
    .legend-line {{
      width: 20px;
      height: 3px;
      border-radius: 2px;
    }}
    svg {{
      width: 100%;
      height: calc(100% - 40px);
      background: #0e1117;
    }}
    .flow-line {{
      stroke-dasharray: 8, 4;
      animation: flowAnimation 1.2s linear infinite;
    }}
    .recirc-line {{
      stroke-dasharray: 6, 3;
      animation: flowReverse 1.5s linear infinite;
    }}
    @keyframes flowAnimation {{
      from {{ stroke-dashoffset: 24; }}
      to {{ stroke-dashoffset: 0; }}
    }}
    @keyframes flowReverse {{
      from {{ stroke-dashoffset: 0; }}
      to {{ stroke-dashoffset: 24; }}
    }}
    .node-group {{
      cursor: pointer;
      transition: all 0.2s ease;
    }}
    .node-group:hover rect, .node-group:hover circle {{
      filter: drop-shadow(0 0 8px #58a6ff);
    }}
    .tooltip-box {{
      position: absolute;
      bottom: 14px;
      right: 14px;
      background: rgba(22, 27, 34, 0.95);
      border: 1px solid #58a6ff;
      border-radius: 8px;
      padding: 12px 16px;
      font-size: 12px;
      max-width: 340px;
      backdrop-filter: blur(8px);
      box-shadow: 0 4px 20px rgba(0,0,0,0.6);
      display: block;
    }}
    .tooltip-title {{
      font-weight: 700;
      color: #58a6ff;
      font-size: 13px;
      margin-bottom: 6px;
    }}
    .tooltip-desc {{
      color: #8b949e;
      line-height: 1.4;
      margin-bottom: 6px;
    }}
    .tooltip-val {{
      font-family: monospace;
      color: #f0f6fc;
      font-weight: 600;
    }}
  </style>
</head>
<body>
  <div class="schematic-container">
    <div class="toolbar">
      <div class="toolbar-title">
        ⚓ LNG Deniz Terminali & İskele-Tank Hat Şematiği (P&ID Şeması)
      </div>
      <div>
        <span class="legend-badge"><div class="legend-line" style="background:#1f6feb;"></div>LNG Tahliye Hattı (Ana Hat)</span>
        <span class="legend-badge"><div class="legend-line" style="background:#39d353;"></div>Sirkülasyon & Soğutma Hattı</span>
        <span class="legend-badge"><div class="legend-line" style="background:#d29922; stroke-dasharray: 3,2;"></div>BOG Buhar Dönüş Hattı</span>
        <span class="legend-badge" style="color:#d29922; font-weight:700;">Hat: {route_length:.0f} m | Ω: {omega_count}</span>
      </div>
    </div>

    <svg viewBox="0 0 1150 540" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <!-- Gradients -->
        <linearGradient id="seaGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#091424" />
          <stop offset="100%" stop-color="#060c16" />
        </linearGradient>
        <linearGradient id="shoreGrad" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stop-color="#1b2430" />
          <stop offset="100%" stop-color="#161b22" />
        </linearGradient>
        <linearGradient id="pipeGrad" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stop-color="#1f6feb" />
          <stop offset="100%" stop-color="#238636" />
        </linearGradient>
        <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#58a6ff"/>
        </marker>
        <marker id="arrowGreen" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#39d353"/>
        </marker>
      </defs>

      <!-- Background: Sea & Onshore Shoreline -->
      <rect x="0" y="0" width="820" height="540" fill="url(#seaGrad)" />
      <rect x="820" y="0" width="330" height="540" fill="url(#shoreGrad)" />
      <line x1="820" y1="0" x2="820" y2="540" stroke="#30363d" stroke-width="2" stroke-dasharray="6,4" />
      <text x="830" y="24" fill="#8b949e" font-size="11" font-weight="700">KARA TESİSİ SINIRI (BATTERY LIMIT)</text>
      <text x="30" y="24" fill="#58a6ff" font-size="11" font-weight="700">DENİZ VE İSKELE YAKLAŞIM HATTI (OFFSHORE JETTY)</text>

      <!-- Trestle Structure Supporting the Pipe -->
      <rect x="180" y="260" width="650" height="14" fill="#21262d" rx="3" stroke="#30363d" />

      <!-- ================= 1. LNG GEMİSİ (CARRIER) ================= -->
      <g class="node-group" onclick="showInfo('LNG Gemisi (Carrier)', 'Kriyojenik membran kargo tanklarına sahip LNG taşıyıcı gemi. -161.5 °C sıcaklıkta ve 1.05-1.25 bar basınçta yük taşır.', '{inlet_t_c:.1f} °C', '{inlet_p_bar:.2f} bar', 'Debi: {m_flow:.1f} kg/s')">
        <!-- Ship Hull -->
        <path d="M 20 200 L 130 200 L 145 270 L 120 330 L 20 330 Z" fill="#161b22" stroke="#58a6ff" stroke-width="2" />
        <!-- Ship Cargo Tanks (Spherical/Membrane style) -->
        <circle cx="55" cy="265" r="24" fill="#0d1117" stroke="#388bfd" stroke-width="1.5" />
        <circle cx="105" cy="265" r="24" fill="#0d1117" stroke="#388bfd" stroke-width="1.5" />
        <text x="35" y="222" fill="#58a6ff" font-size="10" font-weight="700">LNG GEMİSİ</text>
        <text x="44" y="270" fill="#8b949e" font-size="9">Tank 1</text>
        <text x="94" y="270" fill="#8b949e" font-size="9">Tank 2</text>
      </g>

      <!-- ================= 2. LUP DOLFENİ (LOADING/UNLOADING PLATFORM) ================= -->
      <g class="node-group" onclick="showInfo('LUP Dolfeni (Loading Platform)', 'Yükleme/Tahliye platformu. Deniz tipi yükleme kolları (Marine Loading Arms), acil ayırma kuplörleri (PERC) ve ESDV-101 vanasını barındırır.', '{inlet_t_c:.1f} °C', '{inlet_p_bar:.2f} bar', 'Platform Ebat: 25x30m')">
        <!-- Platform foundation -->
        <rect x="160" y="190" width="80" height="150" fill="#1c2128" stroke="#f0883e" stroke-width="2" rx="4" />
        <!-- Marine Loading Arm (MLA) representation -->
        <path d="M 130 250 L 175 220 L 195 250" fill="none" stroke="#f0883e" stroke-width="4" stroke-linecap="round" />
        <!-- ESDV-101 Symbol -->
        <polygon points="190,262 202,270 190,278" fill="#f85149" />
        <polygon points="214,262 202,270 214,278" fill="#f85149" />
        <text x="168" y="210" fill="#f0883e" font-size="10" font-weight="700">LUP DOLFENİ</text>
        <text x="166" y="325" fill="#8b949e" font-size="9">ESDV-101 / MLA</text>
      </g>

      <!-- ================= 3-5. DİNAMİK APD VE OMEGA DOLFENLERİ ================= -->
      {omega_and_apd_html}

      <!-- Shore Isolation Valve Station (ESDV-201) -->
      <g class="node-group" onclick="showInfo('Kara Sınırı İzolasyon İstasyonu', 'Deniz ile karayı ayıran acil durum kapatma vanası (ESDV-201) ve izolasyon flanşı.', '{t_out - 0.2:.1f} °C', '{p_out + 0.1:.2f} bar', 'ESDV-201')">
        <rect x="795" y="245" width="40" height="50" fill="#21262d" stroke="#3fb950" stroke-width="1.5" rx="3" />
        <polygon points="803,266 813,272 803,278" fill="#f85149" />
        <polygon points="823,266 813,272 823,278" fill="#f85149" />
        <text x="792" y="310" fill="#3fb950" font-size="9" font-weight="600">ESDV-201</text>
      </g>

      <!-- ================= 6. KARA LNG TANKI ================= -->
      <g class="node-group" onclick="showInfo('Kara LNG Depolama Tankı', 'Tam kısıtlamalı (Full-Containment) çift cidarlı kriyojenik depolama tankı. 160.000 m³ hacim, -162 °C ve 1.04 bar tasarım basıncı.', '{t_out:.1f} °C', '{p_out:.2f} bar', 'Hacim: 160.000 m³')">
        <!-- Outer Concrete Wall -->
        <rect x="940" y="160" width="160" height="220" fill="#1c2128" stroke="#58a6ff" stroke-width="2.5" rx="8" />
        <!-- Inner 9% Ni Steel Tank -->
        <rect x="955" y="180" width="130" height="190" fill="#0d1117" stroke="#388bfd" stroke-width="1.5" rx="4" />
        <!-- Liquid Level -->
        <rect x="956" y="225" width="128" height="144" fill="rgba(31, 111, 235, 0.3)" rx="2" />
        <text x="965" y="195" fill="#58a6ff" font-size="11" font-weight="700">KARA LNG TANKI</text>
        <text x="980" y="255" fill="#c9d1d9" font-size="10">Full Containment</text>
        <text x="985" y="275" fill="#3fb950" font-size="10">Sıvı LNG (-162°C)</text>
      </g>

      <!-- ================= 7. SİRKÜLASYON POMPASI ================= -->
      <g class="node-group" onclick="showInfo('Kriyojenik Sirkülasyon Pompası (P-201)', 'Tank içindeki soğuk LNG sıvısını alıp iskeleye geri basan sirkülasyon pompası. Gemi olmadığı bekleme durumunda borunun soğuk kalmasını (Cold Standby) sağlar.', '-162.0 °C', '6.5 bar', 'Debi: 20-40 m³/h')">
        <!-- Pump Circle -->
        <circle cx="890" cy="400" r="18" fill="#238636" stroke="#39d353" stroke-width="2" />
        <!-- Pump Impeller triangle -->
        <polygon points="882,392 882,408 898,400" fill="#ffffff" />
        <text x="840" y="435" fill="#39d353" font-size="10" font-weight="700">Sirkülasyon Pompası</text>
        <text x="872" y="450" fill="#8b949e" font-size="9">P-201 (Cooldown)</text>
      </g>

      <!-- ================= PIPING RUNS ================= -->
      <!-- 1. MAIN UNLOADING LINE (GEMİ -> LUP -> OMEGA 1 -> OMEGA 2 -> TANK) -->
      <path class="flow-line" d="{main_path_d}" fill="none" stroke="#1f6feb" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" marker-end="url(#arrow)" />

      <!-- 2. COOLDOWN RECIRCULATION RETURN LINE (TANK -> PUMP -> LUP -> SHIP) -->
      <path class="recirc-line" d="
        M 1020 370
        L 1020 400
        L 908 400
        M 872 400
        L 190 400
        L 190 280
      " fill="none" stroke="#39d353" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" marker-end="url(#arrowGreen)" />

      <!-- 3. BOG VAPOR RETURN LINE (TANK TOP -> SHIP) -->
      <path d="
        M 1020 180
        L 1020 120
        L 170 120
        L 170 230
        L 125 230
      " fill="none" stroke="#d29922" stroke-width="2" stroke-dasharray="5,4" />
      <text x="500" y="112" fill="#d29922" font-size="9" font-weight="600">BOG Buhar Dönüş Hattı (Vapor Return Line)</text>

      <!-- Live telemetry labels on pipe -->
      <rect x="220" y="240" width="85" height="18" fill="rgba(14,17,23,0.85)" rx="3" stroke="#58a6ff" />
      <text x="225" y="253" fill="#58a6ff" font-size="9" font-weight="700">GİRİŞ: {inlet_p_bar:.1f}b | {inlet_t_c:.1f}°</text>

      {omega_label_html}

      <rect x="850" y="240" width="85" height="18" fill="rgba(14,17,23,0.85)" rx="3" stroke="#3fb950" />
      <text x="855" y="253" fill="#3fb950" font-size="9" font-weight="700">ÇIKIŞ: {p_out:.1f}b | {t_out:.1f}°</text>
    </svg>

    <!-- Interactive Inspector Box -->
    <div id="inspector" class="tooltip-box">
      <div id="insp-title" class="tooltip-title">🔍 Ekipman Bilgisi</div>
      <div id="insp-desc" class="tooltip-desc">Şema üzerindeki LUP, APD, Omega dolfenleri, pompa veya tanka tıklayarak detaylı teknik bilgi alabilirsiniz.</div>
      <div id="insp-extra" style="font-size: 11px; color:#c9d1d9;"></div>
    </div>
  </div>

  <script>
    function showInfo(title, desc, val1, val2, extra) {{
      document.getElementById('insp-title').innerText = title;
      document.getElementById('insp-desc').innerText = desc;
      let extraHtml = '';
      if (val1 && val2) {{
        extraHtml += '<div style="margin-top:4px;"><span style="color:#8b949e;">Sıcaklık:</span> <span class="tooltip-val">' + val1 + '</span> | <span style="color:#8b949e;">Basınç:</span> <span class="tooltip-val">' + val2 + '</span></div>';
      }}
      if (extra) {{
        extraHtml += '<div style="margin-top:2px; color:#58a6ff;">' + extra + '</div>';
      }}
      document.getElementById('insp-extra').innerHTML = extraHtml;
    }}
  </script>
</body>
</html>
"""
    return html

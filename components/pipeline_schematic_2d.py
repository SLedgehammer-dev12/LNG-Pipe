"""Interactive 2D P&ID and Pipeline Layout Schematic for LNG Marine Terminal."""

import json
from core.solver import PipelineSimulationResults
from core.solver_3d import Simulation3DResults


def generate_schematic_2d_html(results, height_px: int = 620) -> str:
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

    # Dynamic mid-point estimates for Omega loops
    t_omega1 = t_in + (t_out - t_in) * 0.35
    p_omega1 = p_in - (p_in - p_out) * 0.35
    t_omega2 = t_in + (t_out - t_in) * 0.70
    p_omega2 = p_in - (p_in - p_out) * 0.70

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

      <!-- ================= 3. APD DOLFENLERİ (APPROACH PILES) ================= -->
      <!-- APD-1 -->
      <g class="node-group" onclick="showInfo('APD-1 Dolfeni', 'Yaklaşım köprüsü taşıyıcı dolfeni. Kriyojenik boru köprüsünü ve kablo tavasını taşır.', '{t_in + 0.3:.1f} °C', '{p_in - 0.1:.2f} bar', 'Kazık Çapı: 1200 mm')">
        <rect x="290" y="250" width="30" height="85" fill="#21262d" stroke="#8b949e" stroke-width="1.5" rx="3" />
        <circle cx="305" cy="310" r="4" fill="#30363d" />
        <text x="282" y="352" fill="#8b949e" font-size="9" font-weight="600">APD-1</text>
      </g>

      <!-- ================= 4. OMEGA-1 GENLEŞME DÖNGÜSÜ DOLFENİ ================= -->
      <g class="node-group" onclick="showInfo('Omega-1 Dolfeni (Expansion Loop)', 'Kriyojenik büzülmeyi (~3 mm/m) sönümleyen Omega genleşme döngüsü. Hat soğuduğunda yaklaşık 80-120 mm esner. Tepe noktasında TRV-101 ısıl tahliye vanası bulunur.', '{t_omega1:.1f} °C', '{p_omega1:.2f} bar', 'Genleşme: ~100 mm')">
        <rect x="370" y="160" width="70" height="180" fill="#161b22" stroke="#d29922" stroke-width="1.5" stroke-dasharray="4,2" rx="4" />
        <!-- TRV Valve on Loop Top -->
        <circle cx="405" cy="172" r="5" fill="#da3633" />
        <text x="375" y="152" fill="#d29922" font-size="10" font-weight="700">OMEGA-1 DOLFENİ</text>
        <text x="390" y="352" fill="#8b949e" font-size="9" font-weight="600">Ω-Loop 1</text>
      </g>

      <!-- APD-2 -->
      <g class="node-group" onclick="showInfo('APD-2 Dolfeni', 'İkinci yaklaşım dolfeni. Hat kılavuz kayar mesnetlerini (pipe guides) barındırır.', '{t_omega1 + 0.3:.1f} °C', '{p_omega1 - 0.1:.2f} bar', 'Kayar Mesnet')">
        <rect x="490" y="250" width="30" height="85" fill="#21262d" stroke="#8b949e" stroke-width="1.5" rx="3" />
        <text x="482" y="352" fill="#8b949e" font-size="9" font-weight="600">APD-2</text>
      </g>

      <!-- ================= 5. OMEGA-2 GENLEŞME DÖNGÜSÜ DOLFENİ ================= -->
      <g class="node-group" onclick="showInfo('Omega-2 Dolfeni (Expansion Loop)', 'İkinci genleşme döngüsü dolfeni. Karaya yaklaşırken borunun aşırı gerilmesini ve flanş kaçaklarını önler. TRV-102 emniyet ventili mevcuttur.', '{t_omega2:.1f} °C', '{p_omega2:.2f} bar', 'Genleşme: ~110 mm')">
        <rect x="570" y="160" width="70" height="180" fill="#161b22" stroke="#d29922" stroke-width="1.5" stroke-dasharray="4,2" rx="4" />
        <circle cx="605" cy="172" r="5" fill="#da3633" />
        <text x="575" y="152" fill="#d29922" font-size="10" font-weight="700">OMEGA-2 DOLFENİ</text>
        <text x="590" y="352" fill="#8b949e" font-size="9" font-weight="600">Ω-Loop 2</text>
      </g>

      <!-- APD-3 -->
      <g class="node-group" onclick="showInfo('APD-3 Dolfeni', 'Kara geçişi öncesi son açık deniz dolfeni. Sabit ankraj mesnedini (anchor) taşır.', '{t_omega2 + 0.3:.1f} °C', '{p_omega2 - 0.1:.2f} bar', 'Sabit Ankraj')">
        <rect x="690" y="250" width="30" height="85" fill="#21262d" stroke="#8b949e" stroke-width="1.5" rx="3" />
        <text x="682" y="352" fill="#8b949e" font-size="9" font-weight="600">APD-3</text>
      </g>

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
      <path class="flow-line" d="
        M 140 270 
        L 200 270
        L 380 270
        L 380 180
        L 430 180
        L 430 270
        L 580 270
        L 580 180
        L 630 180
        L 630 270
        L 955 270
      " fill="none" stroke="#1f6feb" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" marker-end="url(#arrow)" />

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

      <rect x="440" y="240" width="95" height="18" fill="rgba(14,17,23,0.85)" rx="3" stroke="#d29922" />
      <text x="445" y="253" fill="#d29922" font-size="9" font-weight="700">Ω-1: {p_omega1:.1f}b | {t_omega1:.1f}°</text>

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

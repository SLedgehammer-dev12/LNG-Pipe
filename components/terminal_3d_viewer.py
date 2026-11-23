"""Interactive Three.js 3D Marine Terminal Digital Twin for LNG Transfer System."""

import json
from core.solver import PipelineSimulationResults
from core.solver_3d import Simulation3DResults, is_3d_results


def generate_terminal_3d_html(
    results,
    height_px: int = 650,
    main_diameter_mm: float | None = None,
    main_wall_mm: float | None = None,
    return_diameter_mm: float = 100.0,
    return_wall_mm: float = 3.0,
    main_material: str = "",
    return_material: str = "",
    return_flow_kg_s: float = 0.0,
    return_results=None,
    length_m: float | None = None,
    anchor_dist_m: float = 180.0,
    theme: str = "Gündüz",
) -> str:
    """Generates a self-contained responsive Three.js 3D WebGL Digital Twin of the LNG Terminal.

    Visualizes:
    - LNG Carrier berthed offshore with mooring & berthing dolphins
    - LUP Dolphin (Loading / Unloading Platform) with Marine Loading Arms (MLAs) & ESDVs
    - APD Dolphins (Approach Trestle Piles)
    - Omega Dolphins with 3D thermal expansion loops & TRVs
    - Onshore Cryogenic LNG Full-Containment Tank
    - P-201 Recirculation Pump and continuous cooldown return line
    - Pipe rack, long-radius elbows, manifold and temperature-gradient pipes
    - Day/Night theme switchable sea, sky and lighting
    - Click-to-inspect fluid state along the pipe
    - Camera presets and interactive inspector
    """

    if is_3d_results(results):
        cfg = results.config.pipeline_config
        t_out = results.bulk_temperature_k[-1] - 273.15
        p_out = results.pressure_pa[-1] / 1e5
        psat_out = results.wall_vapor_pressure_pa[-1] / 1e5
        flashed = results.has_wall_flashed or results.has_bulk_flashed
        flash_m = results.wall_flashing_point_m or results.bulk_flashing_point_m or 0.0
        station_t = results.bulk_temperature_k
        station_p = results.pressure_pa
        station_psat = results.wall_vapor_pressure_pa
        station_margin = results.wall_flashing_margin_pa
    else:
        cfg = results.config
        t_out = results.outlet_temperature_k - 273.15
        p_out = results.outlet_pressure_pa / 1e5
        psat_out = results.outlet_vapor_pressure_pa / 1e5
        flashed = results.has_flashed
        flash_m = results.flashing_point_m or 0.0
        station_t = results.temperature_k
        station_p = results.pressure_pa
        station_psat = results.vapor_pressure_pa
        station_margin = results.flashing_margin_pa

    t_in = cfg.inlet_temperature_k - 273.15
    p_in = cfg.inlet_pressure_pa / 1e5
    m_flow = cfg.mass_flow_rate_kg_s
    margin_min = results.min_flashing_margin_pa / 1e5

    # Decimated station profile for the temperature gradient and click inspector.
    n_st = len(results.distance_m)
    step = max(1, n_st // 60)
    idx = list(range(0, n_st, step))
    if idx[-1] != n_st - 1:
        idx.append(n_st - 1)
    stations = {
        "distance_m": [round(results.distance_m[i], 1) for i in idx],
        "temp_c": [round(station_t[i] - 273.15, 2) for i in idx],
        "pressure_bar": [round(station_p[i] / 1e5, 3) for i in idx],
        "vapor_bar": [round(station_psat[i] / 1e5, 3) for i in idx],
        "margin_bar": [round(station_margin[i] / 1e5, 3) for i in idx],
    }
    if return_results is not None:
        if is_3d_results(return_results):
            rt, rp, rps, rmg = (
                return_results.bulk_temperature_k,
                return_results.pressure_pa,
                return_results.wall_vapor_pressure_pa,
                return_results.wall_flashing_margin_pa,
            )
        else:
            rt, rp, rps, rmg = (
                return_results.temperature_k,
                return_results.pressure_pa,
                return_results.vapor_pressure_pa,
                return_results.flashing_margin_pa,
            )
        rn = len(return_results.distance_m)
        rstep = max(1, rn // 60)
        ridx = list(range(0, rn, rstep))
        if ridx[-1] != rn - 1:
            ridx.append(rn - 1)
        return_stations = {
            "distance_m": [round(return_results.distance_m[i], 1) for i in ridx],
            "temp_c": [round(rt[i] - 273.15, 2) for i in ridx],
            "pressure_bar": [round(rp[i] / 1e5, 3) for i in ridx],
            "vapor_bar": [round(rps[i] / 1e5, 3) for i in ridx],
            "margin_bar": [round(rmg[i] / 1e5, 3) for i in ridx],
        }
    else:
        return_stations = stations
    t_min_c = min(stations["temp_c"])
    t_max_c = max(stations["temp_c"])

    main_id = main_diameter_mm if main_diameter_mm else cfg.inner_diameter_m * 1000.0
    main_wall = main_wall_mm if main_wall_mm else 6.0
    main_mat = main_material or "Paslanmaz Çelik"
    ret_mat = return_material or "Paslanmaz Çelik"
    legend_items = [
        (f"Ana LNG Hattı (ID {main_id:.0f} mm · t {main_wall:.1f} mm)", "#00d2ff"),
        (f"Dönüş Hattı (ID {return_diameter_mm:.0f} mm · t {return_wall_mm:.1f} mm)", "#39d353"),
        ("BOG (Boil-Off Gas) Buhar Hattı", "#38bdf8"),
        ("Flare (Meşale) Hattı & Baca (F-401)", "#f97316"),
        ("Omega Döngüsü & TRV", "#d2a8ff"),
        ("Pipe Rack & Uzun Yarıçap Dirsek", "#8b949e"),
    ]
    legend_html = "".join(
        f'<div class="legend-item"><div class="legend-swatch" style="background:{col};"></div>'
        f'<span>{lbl}</span></div>'
        for lbl, col in legend_items
    )
    legend_html += (
        '<div class="legend-item"><div class="legend-swatch" '
        'style="background:linear-gradient(90deg,#1f6feb,#3fb950,#f85149);"></div>'
        f'<span>Sıcaklık gradyanı: {t_min_c:.1f} … {t_max_c:.1f} °C</span></div>'
    )

    route_length = length_m if length_m else cfg.length_m
    omega_count = max(1, min(8, int(round(route_length / max(anchor_dist_m, 50.0)))))

    telemetry = {
        "length_m": route_length,
        "anchor_dist_m": anchor_dist_m,
        "omega_count": omega_count,
        "length_scale": round(max(0.5, min(2.5, route_length / 300.0)), 3),
        "diameter_mm": main_id,
        "wall_mm": main_wall,
        "mass_flow": m_flow,
        "inlet_t_c": round(t_in, 2),
        "outlet_t_c": round(t_out, 2),
        "inlet_p_bar": round(p_in, 3),
        "outlet_p_bar": round(p_out, 3),
        "outlet_psat_bar": round(psat_out, 3),
        "min_margin_bar": round(margin_min, 3),
        "has_flashed": flashed,
        "flash_point_m": round(flash_m, 1),
        "return_id_mm": return_diameter_mm,
        "return_wall_mm": return_wall_mm,
        "return_flow_kg_s": return_flow_kg_s,
        "main_material": main_mat,
        "return_material": ret_mat,
        "stations": stations,
        "return_stations": return_stations,
    }

    html = f"""
<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; user-select: none; }}
    body {{
      background: #090d13;
      color: #e6edf3;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      overflow: hidden;
      width: 100%;
      height: {height_px}px;
    }}
    #canvas-container {{
      width: 100%;
      height: 100%;
      position: relative;
    }}
    canvas {{
      display: block;
      width: 100%;
      height: 100%;
    }}
    .hud-panel {{
      position: absolute;
      top: 14px;
      left: 14px;
      background: rgba(14, 17, 23, 0.88);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 8px;
      padding: 12px 16px;
      min-width: 280px;
      backdrop-filter: blur(8px);
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
      z-index: 10;
    }}
    .hud-title {{
      font-size: 13px;
      font-weight: 700;
      color: #58a6ff;
      letter-spacing: 0.5px;
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      padding-bottom: 6px;
    }}
    .hud-row {{
      display: flex;
      justify-content: space-between;
      font-size: 11px;
      margin: 4px 0;
      color: #8b949e;
    }}
    .hud-val {{
      font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
      font-weight: 600;
      color: #f0f6fc;
    }}
    .status-badge {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 10px;
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    .status-ok {{ background: rgba(46, 160, 67, 0.2); color: #3fb950; border: 1px solid #2ea043; }}
    .status-warn {{ background: rgba(248, 81, 73, 0.2); color: #f85149; border: 1px solid #f85149; }}
    
    .camera-bar {{
      position: absolute;
      bottom: 14px;
      left: 50%;
      transform: translateX(-50%);
      background: rgba(14, 17, 23, 0.9);
      border: 1px solid rgba(255, 255, 255, 0.15);
      border-radius: 24px;
      padding: 6px 14px;
      display: flex;
      gap: 8px;
      z-index: 10;
      backdrop-filter: blur(8px);
    }}
    .cam-btn {{
      background: #21262d;
      border: 1px solid rgba(255, 255, 255, 0.1);
      color: #c9d1d9;
      font-size: 11px;
      font-weight: 600;
      padding: 5px 12px;
      border-radius: 16px;
      cursor: pointer;
      transition: all 0.2s ease;
    }}
    .cam-btn:hover {{
      background: #30363d;
      color: #58a6ff;
      border-color: #58a6ff;
    }}
    .cam-btn.active {{
      background: #1f6feb;
      color: #ffffff;
      border-color: #58a6ff;
    }}
    .legend-panel {{
      position: absolute;
      top: 14px;
      right: 14px;
      background: rgba(14, 17, 23, 0.88);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 8px;
      padding: 10px 14px;
      font-size: 11px;
      backdrop-filter: blur(8px);
      z-index: 10;
    }}
    .legend-item {{
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 4px 0;
      color: #c9d1d9;
    }}
    .legend-swatch {{
      width: 14px;
      height: 4px;
      border-radius: 2px;
    }}
  </style>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
</head>
<body>
  <div id="canvas-container">
    <div class="hud-panel">
      <div class="hud-title">
        <span>⚓ LNG Terminal & Sirkülasyon Hattı (3D)</span>
      </div>
      <div class="hud-row">
        <span>Gemi / İskele Girişi:</span>
        <span class="hud-val">{t_in:.2f} °C | {p_in:.2f} bar</span>
      </div>
      <div class="hud-row">
        <span>Kara Depo Tankı Girişi:</span>
        <span class="hud-val">{t_out:.2f} °C | {p_out:.2f} bar</span>
      </div>
      <div class="hud-row">
        <span>Buhar Basıncı (P_sat):</span>
        <span class="hud-val">{psat_out:.2f} bar</span>
      </div>
      <div class="hud-row">
        <span>Min. Parlama Marjı (ΔP):</span>
        <span class="hud-val">{margin_min:.2f} bar</span>
      </div>
      <div class="hud-row">
        <span>Hat Uzunluğu / Omega:</span>
        <span class="hud-val">{route_length:.0f} m / {omega_count} adet</span>
      </div>
      <div class="hud-row" style="margin-top:6px; padding-top:6px; border-top:1px dashed rgba(255,255,255,0.1);">
        <span>Parlama Durumu:</span>
        <span class="status-badge {'status-warn' if flashed else 'status-ok'}">
          {'⚠️ PARLAMA' if flashed else '✅ HOMOJEN SIVI'}
        </span>
      </div>
    </div>

    <div class="legend-panel">
      <div style="font-weight:700; color:#8b949e; margin-bottom:6px; text-transform:uppercase; font-size:10px;">Hat Lejantı (Dinamik)</div>
      {legend_html}
    </div>

    <div class="hud-panel" id="pick-panel" style="top:auto; bottom:70px; left:14px; display:none; min-width:250px;">
      <div class="hud-title">🔎 Seçilen Nokta</div>
      <div id="pick-body" style="font-size:11px; line-height:1.55;"></div>
    </div>

    <div class="camera-bar">
      <button class="cam-btn active" onclick="setCameraView('overview', this)">🌐 Genel Bakış</button>
      <button class="cam-btn" onclick="setCameraView('lup', this)">🚢 LUP & Gemi</button>
      <button class="cam-btn" onclick="setCameraView('omega', this)">➰ Omega Dolfenleri</button>
      <button class="cam-btn" onclick="setCameraView('tank', this)">🏢 4x Tank Sahası & Kontrol</button>
      <button class="cam-btn" onclick="setCameraView('roof', this)">🏗️ Çatı Vana & LNG Pit</button>
      <button class="cam-btn" onclick="setCameraView('flare', this)">🔥 BOG & Flare Bacası</button>
      <button class="cam-btn" onclick="resetControls()">⟲ Sıfırla</button>
    </div>
  </div>

  <script>
    const telemetry = {json.dumps(telemetry)};

    const container = document.getElementById('canvas-container');
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0f18);
    scene.fog = new THREE.FogExp2(0x0a0f18, 0.0007);

    const camera = new THREE.PerspectiveCamera(45, container.clientWidth / Math.max(1, container.clientHeight), 0.5, 3000);
    camera.position.set(-180, 110, 240);

    const renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: false }});
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    container.appendChild(renderer.domElement);

    const controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.maxPolarAngle = Math.PI / 2 - 0.02;
    controls.target.set(60, 10, 0);

    // Day/Night theme colors for sea & sky
    const theme = {json.dumps(theme)};
    const isNight = theme === "Gece";
    const ambientIntensity = isNight ? 0.25 : 0.6;
    const fogColor = isNight ? new THREE.Color(0x050a14) : new THREE.Color(0x1a2b3c);

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xdde8f5, ambientIntensity);
    scene.add(ambientLight);

    const sunLight = new THREE.DirectionalLight(0xfff6e6, isNight ? 0.4 : 1.1);
    sunLight.position.set(-150, 250, 150);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.width = 2048;
    sunLight.shadow.mapSize.height = 2048;
    sunLight.shadow.camera.near = 10;
    sunLight.shadow.camera.far = 800;
    const d = 450;
    sunLight.shadow.camera.left = -d;
    sunLight.shadow.camera.right = d;
    sunLight.shadow.camera.top = d;
    sunLight.shadow.camera.bottom = -d;
    scene.add(sunLight);

    const blueFill = new THREE.DirectionalLight(0x388bfd, isNight ? 0.15 : 0.35);
    blueFill.position.set(150, 80, -100);
    scene.add(blueFill);

    // Set scene fog & background based on theme
    scene.fog = new THREE.FogExp2(fogColor, 0.0007);
    scene.background = new THREE.Color(fogColor);

    // Dynamic terminal footprint: ship-to-tank distance follows the user line length.
    const lengthScale = Math.max(0.5, Math.min(2.5, telemetry.length_scale || 1.0));
    const ROUTE_START = -132.0;
    const ROUTE_END = ROUTE_START + 352.0 * lengthScale;
    const TANK_X = ROUTE_END + 80.0;
    const PUMP_X = ROUTE_END + 10.0;
    const SEAWALL_X = 155.0 + (ROUTE_END - 220.0);
    const LAND_X = TANK_X + 80.0;
    const MAIN_Z = 3.5;
    const RET_Z = -3.5;
    const LOOP_EXT = 22.0;
    const OMEGA_W = 22.0;
    const mainRadius = Math.min(3.0, Math.max(0.6, telemetry.diameter_mm / 210.0));
    const retRadius = Math.min(1.8, Math.max(0.4, telemetry.return_id_mm / 210.0));
    const parallelOffset = -Math.max(7.0, mainRadius + retRadius + 3.0);
    const nOmega = Math.max(1, Math.min(8, telemetry.omega_count || 2));
    const omegaSlot = (ROUTE_END - ROUTE_START) / nOmega;
    const omegaCenters = [];
    const omegaStarts = [];
    for (let k = 0; k < nOmega; k++) {{
      const x0 = ROUTE_START + omegaSlot * k + (omegaSlot - OMEGA_W) / 2;
      omegaStarts.push(x0);
      omegaCenters.push(x0 + OMEGA_W / 2);
    }}
    const SCENE_CX = (TANK_X - 150.0) / 2.0;
    const SCENE_SPAN = (TANK_X + 60.0) - (-180.0);
    const OVERVIEW_DIST = Math.max(650.0, SCENE_SPAN * 1.1);
    camera.position.set(SCENE_CX, OVERVIEW_DIST * 0.35, OVERVIEW_DIST * 0.75);
    controls.target.set(SCENE_CX, 10, 0);
    controls.update();

    // Natural irregular coastline function: x_shore(z) in world coordinates
    function getShorelineWorldX(z) {{
      // Flatter near the jetty trestle abutment (|z| < 30), naturally jagged bays/headlands elsewhere
      const coastalMask = 0.35 + 0.65 * Math.min(1.0, Math.pow(Math.abs(z) / 55.0, 1.4));
      const undulation = (
        22.0 * Math.sin(z * 0.0075 + 0.4) +
        14.0 * Math.cos(z * 0.0170 - 0.8) +
        8.5  * Math.sin(z * 0.0390 + 1.5) +
        4.2  * Math.cos(z * 0.0780 - 2.1)
      ) * coastalMask;
      return SEAWALL_X + undulation;
    }}

    // Sea Surface — calm small waves, irregular shoreline foam & turquoise shallows
    const waterGeo = new THREE.PlaneGeometry(5000, 2000, 128, 128);
    const waterCenterX = ROUTE_END * 0.5;
    const deepColor = isNight ? new THREE.Color(0x050a14) : new THREE.Color(0x133c55);
    const shoreColor = isNight ? new THREE.Color(0x1a2b3c) : new THREE.Color(0x3895ab);
    const foamColor = isNight ? new THREE.Color(0x526578) : new THREE.Color(0xdaf2fa);
    const waterMat = new THREE.ShaderMaterial({{
      uniforms: {{
        uTime: {{ value: 0.0 }},
        uSeawallX: {{ value: SEAWALL_X }},
        uDeepColor: {{ value: deepColor }},
        uShoreColor: {{ value: shoreColor }},
        uFoamColor: {{ value: foamColor }},
        uIsNight: {{ value: isNight ? 1.0 : 0.0 }}
      }},
      vertexShader: `
        uniform float uTime;
        uniform float uSeawallX;
        uniform float uIsNight;
        varying float vShoreDist;
        varying vec3 vWorldPos;
        float shoreProfileX(float z) {{
          float mask = 0.35 + 0.65 * min(1.0, pow(abs(z) / 55.0, 1.4));
          float und = (
            22.0 * sin(z * 0.0075 + 0.4) +
            14.0 * cos(z * 0.0170 - 0.8) +
            8.5  * sin(z * 0.0390 + 1.5) +
            4.2  * cos(z * 0.0780 - 2.1)
          ) * mask;
          return uSeawallX + und;
        }}
        void main(){{
          vec3 pos = position;
          float wave = 0.06 * sin(pos.x * 0.022 + uTime * 0.9)
                     + 0.04 * cos(pos.y * 0.030 - uTime * 0.6);
          pos.z += wave;
          vec4 worldPos = modelMatrix * vec4(pos, 1.0);
          vWorldPos = worldPos.xyz;
          vShoreDist = shoreProfileX(worldPos.z) - worldPos.x;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
        }}
      `,
      fragmentShader: `
        uniform float uTime;
        uniform float uIsNight;
        uniform vec3 uDeepColor;
        uniform vec3 uShoreColor;
        uniform vec3 uFoamColor;
        varying float vShoreDist;
        varying vec3 vWorldPos;
        void main(){{
          float shore = smoothstep(0.0, 95.0, max(0.0, vShoreDist));
          vec3 color = mix(uShoreColor, uDeepColor, shore);
          float surfBand = smoothstep(18.0, 0.0, abs(vShoreDist - 2.5));
          float waveFoam = surfBand * (0.38 + 0.35 * sin(uTime * 2.1 + vWorldPos.z * 0.08 - vShoreDist * 0.45));
          color = mix(color, uFoamColor, clamp(waveFoam, 0.0, 0.85));
          if (uIsNight > 0.5) {{
            color *= 0.55;
          }}
          gl_FragColor = vec4(color, 0.96);
        }}
      `,
      transparent: true
    }});
    const waterMesh = new THREE.Mesh(waterGeo, waterMat);
    waterMesh.rotation.x = -Math.PI / 2;
    waterMesh.position.set(waterCenterX, 0, 0);
    waterMesh.receiveShadow = true;
    scene.add(waterMesh);

    // Natural Irregular Onshore Earth Terrain & Coastal Beach/Riprap Slope
    (function buildNaturalCoastAndTerrain() {{
      const nz = 180;
      const nx = 48;
      const zMin = -900.0, zMax = 900.0;
      const landBackX = LAND_X + 420.0;
      const positions = [];
      const colors = [];
      const indices = [];

      // Earth-toned palette (toprak, kum, çakıl ve kıyı florası tonları)
      const colWetSand   = isNight ? new THREE.Color(0x3b3124) : new THREE.Color(0x9e825c);
      const colDryBeach  = isNight ? new THREE.Color(0x4a3d2d) : new THREE.Color(0xc4a77d);
      const colSoilMain  = isNight ? new THREE.Color(0x382b1e) : new THREE.Color(0x8b6843);
      const colTerracotta= isNight ? new THREE.Color(0x3f2a1d) : new THREE.Color(0x9c6b43);
      const colHillScrub = isNight ? new THREE.Color(0x2a3121) : new THREE.Color(0x6e6a44);

      for (let iz = 0; iz <= nz; iz++) {{
        const v = iz / nz;
        const z = zMin + v * (zMax - zMin);
        const xShore = getShorelineWorldX(z);
        for (let ix = 0; ix <= nx; ix++) {{
          const u = ix / nx;
          // Non-linear spacing so shoreline slope has fine resolution
          const uWarp = Math.pow(u, 1.25);
          const x = (xShore - 14.0) + uWarp * (landBackX - (xShore - 14.0));

          // Elevation profile: underwater toe (-3.5m) -> beach slope -> coastal berm (+5.0m) -> inland rolling hills
          let y = 5.0;
          if (u < 0.06) {{
            y = -3.5 + (u / 0.06) * 4.2; // submerged shore toe to water's edge (+0.7m)
          }} else if (u < 0.16) {{
            const s = (u - 0.06) / 0.10;
            y = 0.7 + (3 * s * s - 2 * s * s * s) * 4.3; // natural coastal bank up to +5.0m
          }} else {{
            // Keep terminal plateau flat across the 1x4 tank farm, LNG pit & control building (|z| < 355)
            const padFlatten = Math.min(1.0, Math.max(0.0, (Math.abs(z) - 355.0) / 110.0));
            const hill = (
              7.5 * Math.sin(x * 0.012 + z * 0.009) +
              4.5 * Math.cos(x * 0.025 - z * 0.016) +
              2.2 * Math.sin(z * 0.045)
            ) * padFlatten * Math.min(1.0, (u - 0.16) * 2.2);
            y = 5.0 + Math.max(-0.8, hill);
          }}
          positions.push(x, y, z);

          // Vertex color blending based on shore distance and elevation
          const c = new THREE.Color();
          if (y < 1.1) {{
            c.copy(colWetSand);
          }} else if (u < 0.14) {{
            c.copy(colDryBeach).lerp(colSoilMain, (u - 0.06) / 0.08);
          }} else {{
            const noiseMix = 0.5 + 0.5 * Math.sin(x * 0.018 + z * 0.021);
            c.copy(colSoilMain).lerp(colTerracotta, noiseMix * 0.65);
            if (y > 8.5) {{
              c.lerp(colHillScrub, Math.min(0.65, (y - 8.5) / 10.0));
            }}
          }}
          colors.push(c.r, c.g, c.b);
        }}
      }}

      const rowStride = nx + 1;
      for (let iz = 0; iz < nz; iz++) {{
        for (let ix = 0; ix < nx; ix++) {{
          const a = iz * rowStride + ix;
          const b = a + 1;
          const c = (iz + 1) * rowStride + ix;
          const d = c + 1;
          indices.push(a, c, b);
          indices.push(b, c, d);
        }}
      }}

      const terrainGeo = new THREE.BufferGeometry();
      terrainGeo.setIndex(indices);
      terrainGeo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
      terrainGeo.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
      terrainGeo.computeVertexNormals();

      const terrainMat = new THREE.MeshStandardMaterial({{
        vertexColors: true,
        roughness: 0.92,
        metalness: 0.04
      }});
      const terrainMesh = new THREE.Mesh(terrainGeo, terrainMat);
      terrainMesh.receiveShadow = true;
      terrainMesh.castShadow = true;
      scene.add(terrainMesh);

      // Coastal riprap boulders & rocky outcrops along the irregular shoreline
      const rockMat = new THREE.MeshStandardMaterial({{
        color: isNight ? 0x3b352e : 0x6e5d4b,
        roughness: 0.9,
        metalness: 0.08
      }});
      const rockGeo = new THREE.DodecahedronGeometry(1.0, 1);
      for (let z = -750; z <= 750; z += 11) {{
        if (z > -28 && z < 28) continue; // leave opening for pipe trestle abutment
        const xs = getShorelineWorldX(z);
        const rScale = 1.6 + 1.4 * Math.abs(Math.sin(z * 0.13));
        const rock = new THREE.Mesh(rockGeo, rockMat);
        rock.scale.set(rScale * 1.3, rScale * 0.75, rScale * 1.1);
        rock.position.set(xs - 1.5 + 2.0 * Math.cos(z * 0.29), 0.9, z);
        rock.rotation.set(z * 0.1, z * 0.23, 0);
        rock.castShadow = true;
        rock.receiveShadow = true;
        scene.add(rock);
      }}

      // Compact concrete trestle abutment only where the pipe bridge & road meet the shore
      const abutmentGeo = new THREE.BoxGeometry(12, 8.5, 52);
      const abutmentMat = new THREE.MeshStandardMaterial({{ color: 0x6e7681, roughness: 0.75 }});
      const abutment = new THREE.Mesh(abutmentGeo, abutmentMat);
      abutment.position.set(getShorelineWorldX(0) + 2.0, 2.8, 0);
      abutment.castShadow = true;
      abutment.receiveShadow = true;
      scene.add(abutment);

      // Graded engineered gravel/earth foundation pad under the 1x4 LNG tank farm, LNG pit & control building
      const padGeo = new THREE.BoxGeometry(285, 0.5, 700);
      const padMat = new THREE.MeshStandardMaterial({{
        color: isNight ? 0x352e27 : 0x917c65,
        roughness: 0.92
      }});
      const tankPad = new THREE.Mesh(padGeo, padMat);
      tankPad.position.set(TANK_X + 24.0, 4.82, 20.0);
      tankPad.receiveShadow = true;
      scene.add(tankPad);
    }})();

    // Group for all terminal structures
    const terminalGroup = new THREE.Group();
    scene.add(terminalGroup);

    // Helper for concrete dolphins
    const concreteMat = new THREE.MeshStandardMaterial({{ color: 0x6e7681, roughness: 0.8 }});
    const steelMat = new THREE.MeshStandardMaterial({{ color: 0x30363d, roughness: 0.4, metalness: 0.7 }});
    const yellowMat = new THREE.MeshStandardMaterial({{ color: 0xd29922, roughness: 0.4 }});
    const redValveMat = new THREE.MeshStandardMaterial({{ color: 0xda3633, roughness: 0.3 }});
    const pipeMatMain = new THREE.MeshStandardMaterial({{ color: 0x00d2ff, roughness: 0.2, metalness: 0.8, emissive: 0x004466, emissiveIntensity: 0.3 }});
    const pipeMatRecirc = new THREE.MeshStandardMaterial({{ color: 0x39d353, roughness: 0.2, metalness: 0.8, emissive: 0x005511, emissiveIntensity: 0.3 }});
    const insulationMat = new THREE.MeshStandardMaterial({{ color: 0xd0d7de, roughness: 0.5 }});
    const windowMat = new THREE.MeshStandardMaterial({{ color: 0x0a1a2a, roughness: 0.9 }});
    const railingMat = new THREE.MeshStandardMaterial({{ color: 0xd29922, roughness: 0.5 }});
    const bollardMat = new THREE.MeshStandardMaterial({{ color: 0x6e7681, roughness: 0.6, metalness: 0.8 }});
    const funnelMat = new THREE.MeshStandardMaterial({{ color: 0x8b1a1a, roughness: 0.7 }});

    // Pipe rack under the transfer route (supports supply + return lines)
    (function buildPipeRack() {{
      const rackMat = new THREE.MeshStandardMaterial({{ color: 0x4b5563, roughness: 0.6, metalness: 0.5 }});
      const rack = new THREE.Group();
      const yTop = 12.6;
      const rackLength = ROUTE_END - ROUTE_START + 20;
      const rackCenter = (ROUTE_START + ROUTE_END) / 2;
      [-3, 3].forEach(z => {{
        const beam = new THREE.Mesh(new THREE.BoxGeometry(rackLength, 0.7, 0.7), rackMat);
        beam.position.set(rackCenter, yTop, z);
        rack.add(beam);
      }});
      for (let x = ROUTE_START + 10; x <= ROUTE_END; x += 20) {{
        const cross = new THREE.Mesh(new THREE.BoxGeometry(0.6, 0.6, 7.2), rackMat);
        cross.position.set(x, yTop, 0);
        rack.add(cross);
        [-3, 3].forEach(z => {{
          const leg = new THREE.Mesh(new THREE.BoxGeometry(0.7, yTop, 0.7), rackMat);
          leg.position.set(x, yTop / 2, z);
          rack.add(leg);
        }});
      }}
      terminalGroup.add(rack);
    }})();

    // Manifold skid on LUP: MLAs collect here, then supply/return leave for the pipeline
    const manifold = new THREE.Mesh(
      new THREE.BoxGeometry(6, 3, 40),
      new THREE.MeshStandardMaterial({{ color: 0x8b949e, roughness: 0.3, metalness: 0.85 }})
    );
    manifold.position.set(-132, 14, 0);
    manifold.castShadow = true;
    terminalGroup.add(manifold);

    // Catwalk: personnel access from the LUP along the pipe rack to the onshore area
    (function buildCatwalk() {{
      const cwMat = new THREE.MeshStandardMaterial({{ color: 0x3a4149, roughness: 0.7, metalness: 0.4 }});
      const railMat = new THREE.MeshStandardMaterial({{ color: 0xd29922, roughness: 0.5 }});
      const cwZ = -11.0;
      const cwY = 10.4;
      const cwWidth = 3.4;
      const x0 = -120, x1 = ROUTE_END;
      const len = x1 - x0;
      const cx = (x0 + x1) / 2;
      const deck = new THREE.Mesh(new THREE.BoxGeometry(len, 0.25, cwWidth), cwMat);
      deck.position.set(cx, cwY, cwZ);
      deck.receiveShadow = true;
      terminalGroup.add(deck);
      [-cwWidth / 2, cwWidth / 2].forEach(dz => {{
        const rail = new THREE.Mesh(new THREE.BoxGeometry(len, 1.1, 0.12), railMat);
        rail.position.set(cx, cwY + 0.7, cwZ + dz);
        terminalGroup.add(rail);
      }});
      for (let x = x0 + 10; x <= x1; x += 20) {{
        const leg = new THREE.Mesh(new THREE.BoxGeometry(0.35, cwY, 0.35), cwMat);
        leg.position.set(x, cwY / 2, cwZ);
        terminalGroup.add(leg);
      }}
    }})();

    // Onshore terminal asphalt road network: jetty approach, 4-tank perimeter ring road, inter-tank roads & control building access
    (function buildAccessRoad() {{
      const roadMat = new THREE.MeshStandardMaterial({{ color: 0x262b31, roughness: 0.92 }});
      const curbMat = new THREE.MeshStandardMaterial({{ color: 0x94a3b8, roughness: 0.8 }});
      const dashMat = new THREE.MeshBasicMaterial({{ color: 0xfacc15 }});
      const roadY = 5.18;

      function addRoadSegment(x1, z1, x2, z2, width = 10.5) {{
        const dx = x2 - x1, dz = z2 - z1;
        const len = Math.hypot(dx, dz);
        const angle = Math.atan2(dx, dz);
        const cx = (x1 + x2) / 2.0, cz = (z1 + z2) / 2.0;

        // Concrete shoulder / curb base
        const curb = new THREE.Mesh(new THREE.BoxGeometry(width + 1.4, 0.14, len + 1.4), curbMat);
        curb.position.set(cx, roadY - 0.04, cz);
        curb.rotation.y = angle;
        curb.receiveShadow = true;
        terminalGroup.add(curb);

        // Asphalt surface
        const road = new THREE.Mesh(new THREE.BoxGeometry(width, 0.18, len), roadMat);
        road.position.set(cx, roadY, cz);
        road.rotation.y = angle;
        road.receiveShadow = true;
        terminalGroup.add(road);

        // Center dashed yellow/white lane markings
        const nDashes = Math.floor((len - 8.0) / 11.0);
        for (let i = 0; i < nDashes; i++) {{
          const f = (i + 0.8) / Math.max(1, nDashes);
          const dash = new THREE.Mesh(new THREE.BoxGeometry(0.26, 0.04, 4.5), dashMat);
          dash.position.set(x1 + dx * f, roadY + 0.11, z1 + dz * f);
          dash.rotation.y = angle;
          terminalGroup.add(dash);
        }}
      }}

      const westRoadX = TANK_X - 72.0;
      const eastRoadX = TANK_X + 72.0;
      const northRoadZ = -272.0;
      const southRoadZ = 342.0;

      // 1. Coastal Jetty Approach Road from shore abutment to West Arterial Road
      addRoadSegment(SEAWALL_X + 2.0, 22.0, westRoadX, 22.0, 11.5);
      // 2. West Arterial Road (runs North-South in front of all 4 tanks and the LNG Pit)
      addRoadSegment(westRoadX, northRoadZ, westRoadX, southRoadZ, 11.5);
      // 3. East Arterial Fire & Control Road (runs behind all 4 tanks in front of Control Building)
      addRoadSegment(eastRoadX, northRoadZ, eastRoadX, southRoadZ, 11.5);
      // 4. North & South Perimeter Ring Roads closing the loop around tanks & LNG Pit
      addRoadSegment(westRoadX, northRoadZ, eastRoadX, northRoadZ, 10.5);
      addRoadSegment(westRoadX, southRoadZ, eastRoadX, southRoadZ, 10.5);
      // 5. Inter-Tank Cross Access Roads between T-101/T-102, T-102/T-103, T-103/T-104, and T-104/LNG Pit
      [-130.0, 0.0, 130.0, 260.0].forEach(cz => {{
        addRoadSegment(westRoadX, cz, eastRoadX, cz, 8.5);
      }});
      // 6. Control Building Entrance Spur & Parking Apron
      addRoadSegment(eastRoadX, -32.0, TANK_X + 94.0, -32.0, 9.0);
      addRoadSegment(eastRoadX,  32.0, TANK_X + 94.0,  32.0, 9.0);
      const apron = new THREE.Mesh(new THREE.BoxGeometry(24.0, 0.18, 96.0), roadMat);
      apron.position.set(TANK_X + 90.0, roadY, 0.0);
      apron.receiveShadow = true;
      terminalGroup.add(apron);
    }})();

    function createDolphin(x, z, width, depth, height, pileCount = 4, name = "") {{
      const group = new THREE.Group();
      // Deck slab
      const deckGeo = new THREE.BoxGeometry(width, 3, depth);
      const deck = new THREE.Mesh(deckGeo, concreteMat);
      deck.position.set(0, height, 0);
      deck.castShadow = true;
      deck.receiveShadow = true;
      group.add(deck);

      // Piles into seabed
      const pileRadius = 1.2;
      const pileHeight = height + 15;
      const pileGeo = new THREE.CylinderGeometry(pileRadius, pileRadius, pileHeight, 16);
      
      const offsets = [
        [-width / 2 + 2, -depth / 2 + 2],
        [width / 2 - 2, -depth / 2 + 2],
        [-width / 2 + 2, depth / 2 - 2],
        [width / 2 - 2, depth / 2 - 2]
      ];

      offsets.forEach(([px, pz]) => {{
        const pile = new THREE.Mesh(pileGeo, steelMat);
        pile.position.set(px, height / 2 - 7.5, pz);
        pile.castShadow = true;
        group.add(pile);
      }});

      // Railing
      const railGeo = new THREE.BoxGeometry(width - 0.4, 1.2, depth - 0.4);
      const railEdges = new THREE.EdgesGeometry(railGeo);
      const railLine = new THREE.LineSegments(railEdges, new THREE.LineBasicMaterial({{ color: 0xd29922 }}));
      railLine.position.set(0, height + 1.8, 0);
      group.add(railLine);

      group.position.set(x, 0, z);
      terminalGroup.add(group);
      return group;
    }}

    // 1. LUP Dolphin (Loading / Unloading Platform) — centered at x = -120, set back behind berthing line
    const lupPlatform = createDolphin(-120, 0, 30, 44, 12, 6, "LUP Dolphin");

    // Helper: Properly Scaled Quick Release Hook (QRH - Hızlı Bırakma Kancası) + Electric Capstan Winch
    const qrhBaseMat = new THREE.MeshStandardMaterial({{ color: 0xe3a008, roughness: 0.35, metalness: 0.6 }});
    const qrhHookMat = new THREE.MeshStandardMaterial({{ color: 0xd9383a, roughness: 0.3, metalness: 0.75 }});
    const capstanMat = new THREE.MeshStandardMaterial({{ color: 0x2f3640, roughness: 0.4, metalness: 0.85 }});

    function createQuickReleaseHookUnit(deckY, hookCount = 3) {{
      const qrhGroup = new THREE.Group();
      // Heavy steel base plate bolted to concrete dolphin deck
      const basePlate = new THREE.Mesh(new THREE.BoxGeometry(3.6, 0.45, 3.8), steelMat);
      basePlate.position.set(0, deckY + 0.22, 0);
      basePlate.castShadow = true;
      qrhGroup.add(basePlate);

      // Yellow QRH structural turret pedestal
      const pedestal = new THREE.Mesh(new THREE.BoxGeometry(2.4, 1.8, 3.0), qrhBaseMat);
      pedestal.position.set(0.2, deckY + 1.3, 0);
      pedestal.castShadow = true;
      qrhGroup.add(pedestal);

      // Articulated Quick Release Hooks facing the ship (-x direction)
      for (let h = 0; h < hookCount; h++) {{
        const hz = (h - (hookCount - 1) / 2.0) * 0.9;
        // Swivel clevis arm
        const clevis = new THREE.Mesh(new THREE.BoxGeometry(1.3, 0.55, 0.45), qrhBaseMat);
        clevis.position.set(-0.9, deckY + 1.55, hz);
        qrhGroup.add(clevis);
        // Counterweighted release hook head (high-visibility red/orange)
        const hookCurved = new THREE.Mesh(new THREE.TorusGeometry(0.45, 0.16, 10, 18, Math.PI * 1.35), qrhHookMat);
        hookCurved.rotation.x = Math.PI / 2;
        hookCurved.position.set(-1.65, deckY + 1.55, hz);
        hookCurved.castShadow = true;
        qrhGroup.add(hookCurved);
        // Manual trip / release lever bar
        const lever = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.07, 1.4, 8), qrhHookMat);
        lever.position.set(-0.4, deckY + 2.35, hz);
        lever.rotation.z = -0.35;
        qrhGroup.add(lever);
      }}

      // Integrated electric vertical capstan winch (messenger line drum) on rear of QRH unit
      const capstanBase = new THREE.Mesh(new THREE.CylinderGeometry(0.65, 0.75, 0.9, 16), qrhBaseMat);
      capstanBase.position.set(1.1, deckY + 0.85, 1.15);
      qrhGroup.add(capstanBase);
      const capstanDrum = new THREE.Mesh(new THREE.CylinderGeometry(0.45, 0.38, 1.2, 16), capstanMat);
      capstanDrum.position.set(1.1, deckY + 1.85, 1.15);
      capstanDrum.castShadow = true;
      qrhGroup.add(capstanDrum);

      return qrhGroup;
    }}

    // Helper: Elevated Steel Catwalk Bridge (Kedi Yolu) between dolphins on jetty side
    const catwalkBridgeMat = new THREE.MeshStandardMaterial({{ color: 0x4b5563, roughness: 0.6, metalness: 0.5 }});
    function createCatwalkBridge(x1, z1, x2, z2, yLevel = 11.2) {{
      const dx = x2 - x1, dz = z2 - z1;
      const len = Math.hypot(dx, dz);
      const angle = Math.atan2(dx, dz);
      const bridgeGrp = new THREE.Group();
      const walkway = new THREE.Mesh(new THREE.BoxGeometry(2.2, 0.3, len), catwalkBridgeMat);
      walkway.position.set(0, yLevel, 0);
      walkway.castShadow = true;
      bridgeGrp.add(walkway);
      [-1.0, 1.0].forEach(rx => {{
        const topRail = new THREE.Mesh(new THREE.BoxGeometry(0.1, 1.15, len), railingMat);
        topRail.position.set(rx, yLevel + 0.65, 0);
        bridgeGrp.add(topRail);
      }});
      bridgeGrp.position.set((x1 + x2) / 2.0, 0, (z1 + z2) / 2.0);
      bridgeGrp.rotation.y = angle;
      terminalGroup.add(bridgeGrp);
    }}

    // Berthing / Breasting Dolphins (BD-1..BD-4) on the JETTY SIDE (İskele Tarafı) of the ship!
    // Ship center is x = -172 (beam = 46m -> jetty-side hull is at x = -149).
    // Breasting dolphins sit at x = -139 with cone fenders + frontal panels contacting the hull at x = -148.5.
    const fenderRubberMat = new THREE.MeshStandardMaterial({{ color: 0x1c2127, roughness: 0.88 }});
    const fenderPadMat = new THREE.MeshStandardMaterial({{ color: 0xe6edf3, roughness: 0.4, metalness: 0.2 }});
    const breastingDolphinPositions = [
      {{ x: -139, z: -64, name: "BD-1 Yanaşma Dolfeni (Baş İç)" }},
      {{ x: -139, z: -32, name: "BD-2 Yanaşma Dolfeni (LUP Kuzey)" }},
      {{ x: -139, z:  32, name: "BD-3 Yanaşma Dolfeni (LUP Güney)" }},
      {{ x: -139, z:  64, name: "BD-4 Yanaşma Dolfeni (Kıç İç)" }}
    ];
    breastingDolphinPositions.forEach((bdPos) => {{
      const bd = createDolphin(bdPos.x, bdPos.z, 14, 16, 10.5, 4, bdPos.name);
      // Dual elastomeric cone fenders facing ship (-x)
      [-3.5, 3.5].forEach(fz => {{
        const coneFender = new THREE.Mesh(new THREE.CylinderGeometry(1.6, 2.2, 2.4, 16), fenderRubberMat);
        coneFender.rotation.z = Math.PI / 2;
        coneFender.position.set(-8.0, 9.8, fz);
        bd.add(coneFender);
      }});
      // Frontal fender panel (UHMW-PE face pad) pressing against ship's jetty-side hull (x = -148.5)
      const panel = new THREE.Mesh(new THREE.BoxGeometry(0.9, 6.2, 10.5), fenderPadMat);
      panel.position.set(-9.2, 9.8, 0);
      panel.castShadow = true;
      bd.add(panel);

      // Dual Quick Release Hook (QRH) unit on each Breasting Dolphin for Spring Lines (Açmaz Halatları)
      const qrhSpring = createQuickReleaseHookUnit(12.0, 2);
      bd.add(qrhSpring);
    }});

    // Mooring Dolphins (MD-1..MD-6) on the JETTY SIDE (İskele Tarafı), set back behind the berthing line
    // for optimal OCIMF MEG4 breast, head, and stern line angles!
    const mooringDolphinPositions = [
      {{ x: -108, z: -182, name: "MD-1 Bağlama Dolfeni (Baş Halatları)" }},
      {{ x: -114, z: -142, name: "MD-2 Bağlama Dolfeni (Baş/Koltuk)" }},
      {{ x: -118, z: -102, name: "MD-3 Bağlama Dolfeni (Baş Koltuk)" }},
      {{ x: -118, z:  102, name: "MD-4 Bağlama Dolfeni (Kıç Koltuk)" }},
      {{ x: -114, z:  142, name: "MD-5 Bağlama Dolfeni (Kıç/Koltuk)" }},
      {{ x: -108, z:  182, name: "MD-6 Bağlama Dolfeni (Kıç Halatları)" }}
    ];
    mooringDolphinPositions.forEach((pos) => {{
      const md = createDolphin(pos.x, pos.z, 15, 18, 10.5, 4, pos.name);
      // Triple Quick Release Hook (QRH) assembly + Capstan on each Mooring Dolphin
      const qrhUnit = createQuickReleaseHookUnit(12.0, 3);
      md.add(qrhUnit);
    }});

    // Connect LUP, Breasting Dolphins (BD-1..4), and Mooring Dolphins (MD-1..6) via Jetty Catwalk Bridges
    createCatwalkBridge(-120, -22, -139, -32, 12.2);
    createCatwalkBridge(-139, -32, -139, -64, 12.2);
    createCatwalkBridge(-139, -64, -118, -102, 12.2);
    createCatwalkBridge(-118, -102, -114, -142, 12.2);
    createCatwalkBridge(-114, -142, -108, -182, 12.2);

    createCatwalkBridge(-120,  22, -139,  32, 12.2);
    createCatwalkBridge(-139,  32, -139,  64, 12.2);
    createCatwalkBridge(-139,  64, -118,  102, 12.2);
    createCatwalkBridge(-118,  102, -114,  142, 12.2);
    createCatwalkBridge(-114,  142, -108,  182, 12.2);

    // 16 Properly Scaled Catenary Mooring Lines (Gemi Bağlama Halatları) from Jetty QRHs to Ship Fairleads
    const hawserMat = new THREE.MeshStandardMaterial({{
      color: 0xf0e6d2,
      roughness: 0.55,
      metalness: 0.1,
      emissive: 0x2a2418,
      emissiveIntensity: 0.25
    }});
    const chafeGuardMat = new THREE.MeshStandardMaterial({{ color: 0xf59e0b, roughness: 0.4 }});

    function createMooringHawser(qrhWorldPos, shipChockPos, sag = 1.6) {{
      const mid1 = new THREE.Vector3().lerpVectors(qrhWorldPos, shipChockPos, 0.33);
      const mid2 = new THREE.Vector3().lerpVectors(qrhWorldPos, shipChockPos, 0.67);
      mid1.y -= sag;
      mid2.y -= sag * 0.85;
      const curve = new THREE.CatmullRomCurve3([qrhWorldPos, mid1, mid2, shipChockPos]);
      // Main braided HMPE / Dyneema mooring rope (properly scaled diameter ~0.52m in scene units for clear visibility)
      const ropeMesh = new THREE.Mesh(new THREE.TubeGeometry(curve, 24, 0.26, 8, false), hawserMat);
      ropeMesh.castShadow = true;
      terminalGroup.add(ropeMesh);

      // Protective yellow chafe-guard sleeve near ship fairlead chock
      const chafeStart = curve.getPoint(0.84);
      const chafeCurve = new THREE.LineCurve3(chafeStart, shipChockPos);
      const chafeMesh = new THREE.Mesh(new THREE.TubeGeometry(chafeCurve, 6, 0.34, 8, false), chafeGuardMat);
      terminalGroup.add(chafeMesh);
    }}

    // OCIMF MEG4 Symmetric 16-Line Mooring Pattern (all on Jetty / Starboard-to-Jetty Side x = -149):
    const mooringLinePairs = [
      // 3 Head Lines (MD-1 -> Ship Bow Forecastle Chocks)
      [new THREE.Vector3(-109.6, 13.5, -182.9), new THREE.Vector3(-156.0, 18.2, -154.0), 2.2],
      [new THREE.Vector3(-109.6, 13.5, -182.0), new THREE.Vector3(-153.0, 18.2, -148.0), 2.0],
      [new THREE.Vector3(-109.6, 13.5, -181.1), new THREE.Vector3(-150.5, 18.2, -142.0), 1.9],
      // 2 Forward Breast Lines from MD-2
      [new THREE.Vector3(-115.6, 13.5, -142.9), new THREE.Vector3(-149.2, 17.8, -128.0), 1.7],
      [new THREE.Vector3(-115.6, 13.5, -141.1), new THREE.Vector3(-149.2, 17.8, -118.0), 1.7],
      // 2 Forward Breast Lines from MD-3
      [new THREE.Vector3(-119.6, 13.5, -102.9), new THREE.Vector3(-149.2, 17.8, -98.0), 1.5],
      [new THREE.Vector3(-119.6, 13.5, -101.1), new THREE.Vector3(-149.2, 17.8, -88.0), 1.5],
      // 2 Forward Spring Lines (BD-1 & BD-2 -> Ship Mid-Forward Chocks)
      [new THREE.Vector3(-140.6, 13.5, -64.4),  new THREE.Vector3(-149.2, 17.8, -38.0), 1.1],
      [new THREE.Vector3(-140.6, 13.5, -32.4),  new THREE.Vector3(-149.2, 17.8, -56.0), 1.1],
      // 2 Aft Spring Lines (BD-3 & BD-4 -> Ship Mid-Aft Chocks)
      [new THREE.Vector3(-140.6, 13.5,  32.4),  new THREE.Vector3(-149.2, 17.8,  56.0), 1.1],
      [new THREE.Vector3(-140.6, 13.5,  64.4),  new THREE.Vector3(-149.2, 17.8,  38.0), 1.1],
      // 2 Aft Breast Lines from MD-4
      [new THREE.Vector3(-119.6, 13.5,  101.1), new THREE.Vector3(-149.2, 17.8,  88.0), 1.5],
      [new THREE.Vector3(-119.6, 13.5,  102.9), new THREE.Vector3(-149.2, 17.8,  98.0), 1.5],
      // 2 Aft Breast Lines from MD-5
      [new THREE.Vector3(-115.6, 13.5,  141.1), new THREE.Vector3(-149.2, 17.8,  118.0), 1.7],
      [new THREE.Vector3(-115.6, 13.5,  142.9), new THREE.Vector3(-149.2, 17.8,  128.0), 1.7],
      // 3 Stern Lines (MD-6 -> Ship Stern Poop Deck Chocks)
      [new THREE.Vector3(-109.6, 13.5,  181.1), new THREE.Vector3(-150.5, 18.2,  142.0), 1.9],
      [new THREE.Vector3(-109.6, 13.5,  182.0), new THREE.Vector3(-153.0, 18.2,  148.0), 2.0],
      [new THREE.Vector3(-109.6, 13.5,  182.9), new THREE.Vector3(-156.0, 18.2,  154.0), 2.2]
    ];
    mooringLinePairs.forEach(([qrhPos, chockPos, sag]) => {{
      createMooringHawser(qrhPos, chockPos, sag);
    }});

    // Realistic FMC Chiksan / JLA Double-Counterweighted Pantograph Cryogenic Marine Loading Arms (MLAs)
    // Connecting LUP Dolphin Riser Standposts (x = -132.2) to Ship Midship Cargo Manifold Flanges (x = -149.2)
    const mlaStructYellowMat = new THREE.MeshStandardMaterial({{ color: 0xeab308, roughness: 0.35, metalness: 0.45 }});
    const mlaCryoWhiteMat = new THREE.MeshStandardMaterial({{ color: 0xf1f5f9, roughness: 0.3, metalness: 0.25 }});
    const mlaSwivelSteelMat = new THREE.MeshStandardMaterial({{ color: 0x94a3b8, roughness: 0.28, metalness: 0.85 }});
    const mlaCounterweightMat = new THREE.MeshStandardMaterial({{ color: 0xd97706, roughness: 0.45, metalness: 0.5 }});
    const mlaVaporBandMat = new THREE.MeshStandardMaterial({{ color: 0x38bdf8, roughness: 0.3, metalness: 0.4 }});
    const mlaLiquidBandMat = new THREE.MeshStandardMaterial({{ color: 0x0284c7, roughness: 0.3, metalness: 0.4 }});

    // Helper: create cylinder or box link exactly connecting point A to point B
    function createMemberBetween(pA, pB, radius, mat, isBox = false) {{
      const dir = new THREE.Vector3().subVectors(pB, pA);
      const len = dir.length();
      const mid = new THREE.Vector3().addVectors(pA, pB).multiplyScalar(0.5);
      const geo = isBox
        ? new THREE.BoxGeometry(radius * 1.9, len, radius * 1.5)
        : new THREE.CylinderGeometry(radius, radius, len, 14);
      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.copy(mid);
      mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.clone().normalize());
      mesh.castShadow = true;
      return mesh;
    }}

    const mlaSpecs = [
      {{ code: "MLA-1 (Sıvı LNG)", z: -13.5, isVapor: false }},
      {{ code: "MLA-2 (Sıvı LNG)", z:  -4.5, isVapor: false }},
      {{ code: "MLA-3 (BOG Buhar Dönüş)", z:   4.5, isVapor: true  }},
      {{ code: "MLA-4 (Hibrit / Sirkülasyon)", z:  13.5, isVapor: false }}
    ];

    function createFMCLoadingArm(spec) {{
      const armGroup = new THREE.Group();
      const z = spec.z;
      const serviceMat = spec.isVapor ? mlaVaporBandMat : mlaLiquidBandMat;

      // Key kinematic joint coordinates (in world space) for FMC / JLA Pantograph Arm:
      const standX = -132.2;
      const deckY = 12.0;
      const trunnionY = 21.6;
      const trunnionPos = new THREE.Vector3(standX, trunnionY, z);
      const apexPos     = new THREE.Vector3(-139.2, 28.4, z);
      const dropTopPos  = new THREE.Vector3(-148.0, 20.2, z);
      const percPos     = new THREE.Vector3(-148.0, 17.8, z);
      const qcdcPos     = new THREE.Vector3(-148.0, 16.3, z);
      const shipFlangePos = new THREE.Vector3(-149.3, 16.3, z);

      // 1. Heavy Bolted Base Flange & Gusseted Riser Standpost Column (Standpost + Internal Cryo Riser)
      const baseFlange = new THREE.Mesh(new THREE.CylinderGeometry(1.55, 1.75, 0.65, 20), steelMat);
      baseFlange.position.set(standX, deckY + 0.32, z);
      armGroup.add(baseFlange);

      // Main structural standpost column (FMC Yellow)
      const standPost = new THREE.Mesh(
        new THREE.CylinderGeometry(0.72, 0.88, trunnionY - deckY, 18),
        mlaStructYellowMat
      );
      standPost.position.set(standX, (deckY + trunnionY) / 2.0, z);
      standPost.castShadow = true;
      armGroup.add(standPost);

      // Parallel insulated Stainless 316L Cryogenic Product Riser Pipe alongside standpost
      const cryoRiser = new THREE.Mesh(
        new THREE.CylinderGeometry(0.42, 0.42, trunnionY - deckY + 0.5, 16),
        mlaCryoWhiteMat
      );
      cryoRiser.position.set(standX, (deckY + trunnionY) / 2.0, z + 0.85);
      cryoRiser.castShadow = true;
      armGroup.add(cryoRiser);

      // Service identification color band on riser (Blue = Liquid LNG, Cyan = BOG Vapor)
      const riserBand = new THREE.Mesh(new THREE.CylinderGeometry(0.75, 0.78, 1.2, 18), serviceMat);
      riserBand.position.set(standX, deckY + 4.8, z);
      armGroup.add(riserBand);

      // Upper Trunnion Service Platform & Caged Access Ladder on Standpost
      const srvPlat = new THREE.Mesh(new THREE.BoxGeometry(3.2, 0.25, 3.2), steelMat);
      srvPlat.position.set(standX, trunnionY - 1.4, z);
      armGroup.add(srvPlat);
      const srvRail = new THREE.LineSegments(
        new THREE.EdgesGeometry(new THREE.BoxGeometry(3.1, 1.1, 3.1)),
        new THREE.LineBasicMaterial({{ color: 0xeab308 }})
      );
      srvRail.position.set(standX, trunnionY - 0.75, z);
      armGroup.add(srvRail);

      // 2. Trunnion Double Swivel Joint Assembly & Pantograph Main Sheave Wheel
      const trunnionHousing = new THREE.Mesh(new THREE.CylinderGeometry(1.05, 1.05, 2.4, 20), mlaSwivelSteelMat);
      trunnionHousing.rotation.x = Math.PI / 2;
      trunnionHousing.position.copy(trunnionPos);
      armGroup.add(trunnionHousing);

      const mainSheave = new THREE.Mesh(new THREE.CylinderGeometry(1.35, 1.35, 0.38, 24), mlaStructYellowMat);
      mainSheave.rotation.x = Math.PI / 2;
      mainSheave.position.set(standX, trunnionY, z - 0.95);
      armGroup.add(mainSheave);

      // 3.FMC / JLA DOUBLE COUNTERWEIGHT SYSTEM (Primary & Secondary Pantograph Counterweights extending +x)
      const cwTailPrimary = new THREE.Vector3(standX + 5.8, trunnionY - 3.6, z);
      const cwTailSecondary = new THREE.Vector3(standX + 4.6, trunnionY + 2.2, z - 0.95);

      // Twin structural tail boom beams for Primary Counterweight (balances Inboard Arm)
      [-0.55, 0.55].forEach(dz => {{
        const beam = createMemberBetween(
          new THREE.Vector3(standX, trunnionY, z + dz),
          new THREE.Vector3(cwTailPrimary.x, cwTailPrimary.y, z + dz),
          0.22,
          mlaStructYellowMat,
          true
        );
        armGroup.add(beam);
      }});

      // Heavy Primary Counterweight Block (Orange/Yellow with dark iron plates)
      const primaryCW = new THREE.Mesh(new THREE.BoxGeometry(2.6, 2.2, 2.4), mlaCounterweightMat);
      primaryCW.position.copy(cwTailPrimary);
      primaryCW.castShadow = true;
      armGroup.add(primaryCW);
      const primaryCWCap = new THREE.Mesh(new THREE.BoxGeometry(2.7, 0.45, 2.5), redValveMat);
      primaryCWCap.position.set(cwTailPrimary.x, cwTailPrimary.y + 0.95, cwTailPrimary.z);
      armGroup.add(primaryCWCap);

      // Secondary Pantograph Counterweight Boom & Drum (balances Outboard Arm via pantograph linkage)
      const secBeam = createMemberBetween(
        new THREE.Vector3(standX, trunnionY, z - 0.95),
        cwTailSecondary,
        0.18,
        mlaStructYellowMat,
        true
      );
      armGroup.add(secBeam);
      const secondaryCW = new THREE.Mesh(new THREE.CylinderGeometry(1.05, 1.05, 1.8, 18), redValveMat);
      secondaryCW.rotation.x = Math.PI / 2;
      secondaryCW.position.copy(cwTailSecondary);
      secondaryCW.castShadow = true;
      armGroup.add(secondaryCW);

      // 4. INBOARD ARM (Insulated Cryogenic Product Pipe + Parallel Structural Support Boom & Pantograph Link)
      //    a) Cryogenic insulated product pipe (White/Silver cladding)
      const inboardProductPipe = createMemberBetween(
        new THREE.Vector3(standX, trunnionY, z + 0.55),
        new THREE.Vector3(apexPos.x, apexPos.y, z + 0.55),
        0.42,
        mlaCryoWhiteMat,
        false
      );
      armGroup.add(inboardProductPipe);

      //    b) Structural box boom carrying mechanical loads (FMC Yellow)
      const inboardStructBoom = createMemberBetween(
        new THREE.Vector3(standX, trunnionY + 0.4, z - 0.25),
        new THREE.Vector3(apexPos.x, apexPos.y + 0.4, z - 0.25),
        0.26,
        mlaStructYellowMat,
        true
      );
      armGroup.add(inboardStructBoom);

      //    c) Pantograph rigid tension link / cable rod from Secondary Sheave to Apex Sheave
      const pantoLinkInboard = createMemberBetween(
        new THREE.Vector3(standX, trunnionY + 1.15, z - 0.95),
        new THREE.Vector3(apexPos.x, apexPos.y + 1.05, z - 0.95),
        0.10,
        mlaSwivelSteelMat,
        false
      );
      armGroup.add(pantoLinkInboard);

      //    d) Hydraulic Luffing Cylinder between Standpost Head and Inboard Boom
      const luffCyl = createMemberBetween(
        new THREE.Vector3(standX - 0.8, trunnionY - 2.2, z - 0.25),
        new THREE.Vector3(standX - 3.6, trunnionY + 3.4, z - 0.25),
        0.16,
        steelMat,
        false
      );
      armGroup.add(luffCyl);

      // 5. APEX SWIVEL JOINT & PANTOGRAPH PULLEY SHEAVE (at top knuckle apexPos)
      const apexSwivel = new THREE.Mesh(new THREE.CylinderGeometry(0.85, 0.85, 2.1, 18), mlaSwivelSteelMat);
      apexSwivel.rotation.x = Math.PI / 2;
      apexSwivel.position.copy(apexPos);
      armGroup.add(apexSwivel);

      const apexSheave = new THREE.Mesh(new THREE.CylinderGeometry(1.1, 1.1, 0.35, 20), mlaStructYellowMat);
      apexSheave.rotation.x = Math.PI / 2;
      apexSheave.position.set(apexPos.x, apexPos.y, z - 0.95);
      armGroup.add(apexSheave);

      // 6. OUTBOARD ARM (Reaching from Apex Knuckle across to Ship Manifold Drop Leg)
      //    a) Main insulated cryogenic product pipe
      const outboardProductPipe = createMemberBetween(
        new THREE.Vector3(apexPos.x, apexPos.y, z + 0.35),
        new THREE.Vector3(dropTopPos.x, dropTopPos.y, z + 0.35),
        0.38,
        mlaCryoWhiteMat,
        false
      );
      armGroup.add(outboardProductPipe);

      //    b) Outboard structural support boom & pantograph stay rod (FMC Yellow)
      const outboardStructBoom = createMemberBetween(
        new THREE.Vector3(apexPos.x, apexPos.y + 0.55, z - 0.35),
        new THREE.Vector3(dropTopPos.x, dropTopPos.y + 0.35, z - 0.35),
        0.20,
        mlaStructYellowMat,
        true
      );
      armGroup.add(outboardStructBoom);

      //    c) Service color band on outboard arm
      const midOutboard = new THREE.Vector3().lerpVectors(apexPos, dropTopPos, 0.55);
      const outBand = new THREE.Mesh(new THREE.SphereGeometry(0.46, 12, 12), serviceMat);
      outBand.position.set(midOutboard.x, midOutboard.y, z + 0.35);
      armGroup.add(outBand);

      // 7. TRIPLE SWIVEL ASSEMBLY, PERC (Emergency Release Coupler) & QCDC AT SHIP MANIFOLD (x = -148.0 -> -149.3)
      //    Upper elbow swivel at dropTopPos
      const dropElbow = new THREE.Mesh(new THREE.SphereGeometry(0.62, 14, 14), mlaSwivelSteelMat);
      dropElbow.position.set(dropTopPos.x, dropTopPos.y, z + 0.15);
      armGroup.add(dropElbow);

      //    Vertical drop spool through PERC down to QCDC level
      const dropSpool = createMemberBetween(
        new THREE.Vector3(dropTopPos.x, dropTopPos.y, z + 0.15),
        new THREE.Vector3(qcdcPos.x, qcdcPos.y, z + 0.15),
        0.36,
        mlaSwivelSteelMat,
        false
      );
      armGroup.add(dropSpool);

      //    PERC (Powered Emergency Release Coupler) — Red breakaway collar + dual hydraulic release actuators
      const percCollar = new THREE.Mesh(new THREE.CylinderGeometry(0.68, 0.68, 1.15, 18), redValveMat);
      percCollar.position.set(percPos.x, percPos.y, z + 0.15);
      percCollar.castShadow = true;
      armGroup.add(percCollar);
      [-0.65, 0.65].forEach(az => {{
        const act = new THREE.Mesh(new THREE.CylinderGeometry(0.14, 0.14, 1.5, 10), mlaStructYellowMat);
        act.position.set(percPos.x, percPos.y, z + 0.15 + az);
        armGroup.add(act);
      }});

      //    Horizontal QCDC (Quick Connect/Disconnect Hydraulic Claw Coupler) mating with Ship Manifold Flange
      const qcdcSpool = createMemberBetween(
        new THREE.Vector3(qcdcPos.x, qcdcPos.y, z + 0.15),
        new THREE.Vector3(shipFlangePos.x, shipFlangePos.y, z + 0.15),
        0.42,
        mlaSwivelSteelMat,
        false
      );
      armGroup.add(qcdcSpool);

      const qcdcClaw = new THREE.Mesh(new THREE.CylinderGeometry(0.72, 0.72, 0.55, 16), mlaStructYellowMat);
      qcdcClaw.rotation.z = Math.PI / 2;
      qcdcClaw.position.set(-148.85, qcdcPos.y, z + 0.15);
      armGroup.add(qcdcClaw);

      //    Adjustable telescoping Jack Stand support leg under QCDC on ship manifold drip tray
      const jackLeg = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.15, 2.2, 10), mlaStructYellowMat);
      jackLeg.position.set(-148.9, qcdcPos.y - 1.1, z + 0.15);
      armGroup.add(jackLeg);

      terminalGroup.add(armGroup);
    }}

    mlaSpecs.forEach(spec => createFMCLoadingArm(spec));

    // Ship Midship Cargo Manifold Platform, Stainless Cryogenic Drip Tray & Ship Manifold ESDV Valves (x = -149.3..-155)
    (function buildShipManifoldAndLUPControlTower() {{
      const manifoldGrp = new THREE.Group();

      // 1. Stainless Steel Cryogenic Drip Tray & Deluge Water Curtain Frame on Ship's Jetty Side (x = -150.2)
      const dripTray = new THREE.Mesh(
        new THREE.BoxGeometry(4.2, 0.45, 34.0),
        mlaSwivelSteelMat
      );
      dripTray.position.set(-150.6, 15.0, 0.0);
      dripTray.receiveShadow = true;
      manifoldGrp.add(dripTray);

      // Elevated Manifold Access Platform Grating & Yellow Safety Handrails on Ship Midship
      const shipPlat = new THREE.Mesh(new THREE.BoxGeometry(6.5, 0.35, 36.0), steelMat);
      shipPlat.position.set(-152.2, 14.7, 0.0);
      manifoldGrp.add(shipPlat);

      // Individual Ship Manifold Presentation Spools, ESDV Gate Valves & Cross-Deck Headers into Cargo Tanks
      mlaSpecs.forEach((spec) => {{
        const z = spec.z + 0.15;
        const serviceMat = spec.isVapor ? mlaVaporBandMat : mlaLiquidBandMat;

        // Presentation flange disk at x = -149.2
        const flange = new THREE.Mesh(new THREE.CylinderGeometry(0.68, 0.68, 0.28, 18), serviceMat);
        flange.rotation.z = Math.PI / 2;
        flange.position.set(-149.2, 16.3, z);
        manifoldGrp.add(flange);

        // Horizontal ship manifold pipe running inboard (-x) from flange to ship's cargo dome header
        const shipPipe = new THREE.Mesh(new THREE.CylinderGeometry(0.38, 0.38, 12.5, 14), mlaCryoWhiteMat);
        shipPipe.rotation.z = Math.PI / 2;
        shipPipe.position.set(-155.4, 16.3, z);
        shipPipe.castShadow = true;
        manifoldGrp.add(shipPipe);

        // Ship Manifold ESDV Pneumatic Actuator Valve (Red actuator cylinder)
        const shipEsdv = new THREE.Mesh(new THREE.BoxGeometry(1.1, 1.8, 1.1), redValveMat);
        shipEsdv.position.set(-151.8, 17.2, z);
        manifoldGrp.add(shipEsdv);

        // Saddle supports on ship manifold deck
        [-150.8, -154.5].forEach(sx => {{
          const saddle = new THREE.Mesh(new THREE.BoxGeometry(0.5, 1.2, 0.9), mlaStructYellowMat);
          saddle.position.set(sx, 15.5, z);
          manifoldGrp.add(saddle);
        }});
      }});

      // 2. LUP Elevated Operator Control Cabin / Loading Master Tower (overlooking the 4 FMC/JLA arms)
      const towerX = -114.0, towerZ = -16.5;
      const towerCols = new THREE.Mesh(new THREE.BoxGeometry(4.8, 9.5, 4.8), steelMat);
      towerCols.position.set(towerX, 12.0 + 4.75, towerZ);
      manifoldGrp.add(towerCols);

      const cabinBody = new THREE.Mesh(
        new THREE.BoxGeometry(6.8, 3.8, 7.6),
        new THREE.MeshStandardMaterial({{ color: 0xe2e8f0, roughness: 0.45 }})
      );
      cabinBody.position.set(towerX, 23.2, towerZ);
      cabinBody.castShadow = true;
      manifoldGrp.add(cabinBody);

      const cabinGlass = new THREE.Mesh(new THREE.BoxGeometry(0.35, 2.2, 6.8), windowMat);
      cabinGlass.position.set(towerX - 3.3, 23.4, towerZ);
      manifoldGrp.add(cabinGlass);

      // ESDV-101 Emergency Shutdown Valve Skid & Hydraulic Power Unit (HPU) for FMC Loading Arms on LUP
      const hpuCabin = new THREE.Mesh(new THREE.BoxGeometry(4.2, 3.2, 5.5), mlaStructYellowMat);
      hpuCabin.position.set(-115.0, 13.6, 14.0);
      hpuCabin.castShadow = true;
      manifoldGrp.add(hpuCabin);

      const esdvValve = new THREE.Mesh(new THREE.BoxGeometry(2.5, 3.5, 2.5), redValveMat);
      esdvValve.position.set(-115.0, 15.0, 0.0);
      const handwheel = new THREE.Mesh(new THREE.TorusGeometry(1.2, 0.2, 8, 16), yellowMat);
      handwheel.rotation.x = Math.PI / 2;
      handwheel.position.set(-115.0, 17.5, 0.0);
      manifoldGrp.add(esdvValve);
      manifoldGrp.add(handwheel);

      terminalGroup.add(manifoldGrp);
    }})();

    // 2. LNG Carrier Vessel — berthed alongside Breasting Dolphins (ship center x = -172, jetty side x = -149)
    const shipGroup = new THREE.Group();
    shipGroup.position.set(-172, 0, 0);
    shipGroup.rotation.y = 0;

    // === HULL ===
    // Red hull (parallel midbody + tapered bow/stern)
    const hullRedMat = new THREE.MeshStandardMaterial({{ color: 0xb22222, roughness: 0.6 }});
    const hullRed = new THREE.Mesh(new THREE.BoxGeometry(46, 11, 276), hullRedMat);
    hullRed.position.set(0, 2, 0);
    hullRed.castShadow = true;
    hullRed.receiveShadow = true;
    shipGroup.add(hullRed);

    // Sculpted raked bow (-z) and tapered stern (+z)
    const bowCone = new THREE.Mesh(new THREE.CylinderGeometry(0.8, 23, 36, 4), hullRedMat);
    bowCone.rotation.x = -Math.PI / 2;
    bowCone.rotation.y = Math.PI / 4;
    bowCone.scale.set(1.0, 1.0, 0.35);
    bowCone.position.set(0, 3.5, -152);
    bowCone.castShadow = true;
    shipGroup.add(bowCone);

    // White upper hull / trunk deck
    const hullWhite = new THREE.Mesh(new THREE.BoxGeometry(44, 7, 296), new THREE.MeshStandardMaterial({{ color: 0xf0f6fc, roughness: 0.5 }}));
    hullWhite.position.set(0, 13, 0);
    hullWhite.castShadow = true;
    hullWhite.receiveShadow = true;
    shipGroup.add(hullWhite);

    // Keel / bottom
    const keel = new THREE.Mesh(new THREE.BoxGeometry(42, 4, 290), new THREE.MeshStandardMaterial({{ color: 0x2a1a1a, roughness: 0.8 }}));
    keel.position.set(0, -5, 0);
    keel.castShadow = true;
    shipGroup.add(keel);

    // === MOSS SPHERICAL CARGO TANKS ===
    const tankMat = new THREE.MeshStandardMaterial({{ color: 0xe8f0e0, roughness: 0.45, metalness: 0.15 }});
    const tankCapMat = new THREE.MeshStandardMaterial({{ color: 0x9fd3ad, roughness: 0.4, metalness: 0.3 }});
    const tankZs = [-110, -55, 0, 55, 105];
    tankZs.forEach((zPos) => {{
      const tank = new THREE.Mesh(new THREE.SphereGeometry(10, 32, 24), tankMat);
      tank.position.set(0, 16, zPos);
      tank.castShadow = true;
      tank.receiveShadow = true;
      shipGroup.add(tank);
      const cap = new THREE.Mesh(new THREE.SphereGeometry(10, 32, 16, 0, Math.PI * 2, 0, Math.PI * 0.5), tankCapMat);
      cap.position.set(0, 16, zPos);
      cap.rotation.x = -Math.PI / 2;
      shipGroup.add(cap);
    }});

    // === BRIDGE / SUPERSTRUCTURE at stern (+z) ===
    const bridge = new THREE.Mesh(new THREE.BoxGeometry(30, 15, 26), new THREE.MeshStandardMaterial({{ color: 0xf0f6fc, roughness: 0.4 }}));
    bridge.position.set(0, 24, 128);
    bridge.castShadow = true;
    bridge.receiveShadow = true;
    shipGroup.add(bridge);
    const winZ = 114.8;
    [-10, 0, 10].forEach((wx) => {{
      const win = new THREE.Mesh(new THREE.BoxGeometry(6, 4.5, 0.8), windowMat);
      win.position.set(wx, 26, winZ);
      shipGroup.add(win);
    }});
    const funnel = new THREE.Mesh(new THREE.CylinderGeometry(2.5, 2.8, 8, 16), funnelMat);
    funnel.position.set(0, 33, 134);
    funnel.castShadow = true;
    shipGroup.add(funnel);

    // === DECK RAILING ===
    const railY = 17.2;
    [22.5, -22.5].forEach((rx) => {{
      const sideRail = new THREE.Mesh(new THREE.BoxGeometry(0.25, 1.1, 286), railingMat);
      sideRail.position.set(rx, railY, 0);
      shipGroup.add(sideRail);
    }});
    [-144, 144].forEach((rz) => {{
      const endRail = new THREE.Mesh(new THREE.BoxGeometry(44, 1.1, 0.25), railingMat);
      endRail.position.set(0, railY, rz);
      shipGroup.add(endRail);
    }});

    // === SHIP FAIRLEAD CHOCKS & TWIN BOLLARDS ON JETTY SIDE (+x local = +22.5 -> world x = -149.5) ===
    const chockZs = [-154, -148, -142, -128, -118, -98, -88, -56, -38, 38, 56, 88, 98, 118, 128, 142, 148, 154];
    chockZs.forEach((cz) => {{
      const localX = Math.abs(cz) > 140 ? (22.5 - (Math.abs(cz) - 140) * 0.45) : 22.6;
      const bitt = new THREE.Mesh(new THREE.CylinderGeometry(0.65, 0.65, 1.8, 12), bollardMat);
      bitt.position.set(localX - 1.2, 17.6, cz);
      shipGroup.add(bitt);
      const chock = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.9, 1.4), steelMat);
      chock.position.set(localX, 17.5, cz);
      shipGroup.add(chock);
    }});

    terminalGroup.add(shipGroup);

    // 3. APD Dolphins & Trestle Piles along route (distributed over the dynamic span)
    const apdPositions = [];
    for (let k = 1; k <= 5; k++) {{
      apdPositions.push(ROUTE_START + (ROUTE_END - ROUTE_START) * k / 6);
    }}
    apdPositions.forEach((x, idx) => {{
      createDolphin(x, 0, 12, 14, 11, 4, `APD-${{idx + 1}}`);
    }});

    // 4. Omega Dolphins with 3D Expansion Loops (count and size follow line length)
    const omegaPlatformDepth = LOOP_EXT - parallelOffset + 24.0;
    const omegaPlatformZ = MAIN_Z + (LOOP_EXT + parallelOffset) / 2.0;
    omegaCenters.forEach((cx, k) => {{
      createDolphin(cx, omegaPlatformZ, OMEGA_W + 26.0, omegaPlatformDepth, 11, 6, `Omega Dolfeni ${{k + 1}}`);
    }});

    // 5. Onshore 4x Full-Containment LNG Storage Tank Farm (1x4 Coastal-Parallel Row: T-101..T-104),
    //    Spherical Dome Roofs, Roof-Top Valve & Pump Platforms, Impounding Basins, LNG Spill Pit & Control Building
    const tankFarmGroup = new THREE.Group();
    const R_TANK = 40.0;        // Outer prestressed concrete wall radius (D = 80m)
    const H_WALL = 46.0;        // Outer cylinder height from ground y=5.0 to top ring y=51.0
    const WALL_BASE_Y = 5.0;
    const WALL_TOP_Y = WALL_BASE_Y + H_WALL; // 51.0
    const H_DOME = 10.5;        // True spherical dome rise above compression ring
    const DOME_APEX_Y = WALL_TOP_Y + 1.2 + H_DOME; // 62.7
    const TANK_HEADER_X = TANK_X - 56.0;

    // 1x4 North-to-South parallel tank row; T-101 has semi-transparent cutaway showing 9% Ni inner tank & liquid LNG
    const TANK_SPECS = [
      {{ code: "T-101", z: -195.0, cutaway: true,  fillRatio: 0.85 }},
      {{ code: "T-102", z:  -65.0, cutaway: false, fillRatio: 0.82 }},
      {{ code: "T-103", z:   65.0, cutaway: false, fillRatio: 0.78 }},
      {{ code: "T-104", z:  195.0, cutaway: false, fillRatio: 0.88 }}
    ];

    // Helper: Canvas texture for tank corporate blue band & nameplate (T-101..T-104 LNG)
    function createTankBandTexture(tankCode) {{
      const canvas = document.createElement('canvas');
      canvas.width = 1024;
      canvas.height = 128;
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = '#005a9e';
      ctx.fillRect(0, 0, 1024, 128);
      ctx.fillStyle = '#00a8e8';
      ctx.fillRect(0, 0, 1024, 16);
      ctx.fillRect(0, 112, 1024, 16);
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 54px -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      // Repeat label around circumference so visible from seaward, landward, north, and south
      [128, 384, 640, 896].forEach(cx => {{
        ctx.fillText(tankCode + '  •  LNG', cx, 64);
      }});
      const tex = new THREE.CanvasTexture(canvas);
      tex.wrapS = THREE.RepeatWrapping;
      tex.wrapT = THREE.ClampToEdgeWrapping;
      tex.needsUpdate = true;
      return tex;
    }}

    const tankConcreteSolidMat = new THREE.MeshStandardMaterial({{
      color: isNight ? 0xcbd5e1 : 0xf1f5f9,
      roughness: 0.72,
      metalness: 0.08
    }});
    const tankConcreteCutawayMat = new THREE.MeshStandardMaterial({{
      color: 0xe2e8f0,
      roughness: 0.55,
      metalness: 0.1,
      transparent: true,
      opacity: 0.34,
      depthWrite: false
    }});
    const tankDomeMat = new THREE.MeshStandardMaterial({{
      color: isNight ? 0xb8c4d0 : 0xdbe4ee,
      roughness: 0.42,
      metalness: 0.28
    }});
    const compressionRingMat = new THREE.MeshStandardMaterial({{ color: 0x64748b, roughness: 0.65, metalness: 0.2 }});
    const innerNiSteelMat = new THREE.MeshStandardMaterial({{ color: 0x334155, roughness: 0.38, metalness: 0.82 }});
    const lngLiquidMat = new THREE.MeshStandardMaterial({{
      color: 0x0ea5e9,
      emissive: 0x0369a1,
      emissiveIntensity: 0.35,
      roughness: 0.2,
      transparent: true,
      opacity: 0.68
    }});
    const lngSurfaceRingMat = new THREE.MeshStandardMaterial({{ color: 0x38bdf8, roughness: 0.15, metalness: 0.9 }});
    const blueValveMat = new THREE.MeshStandardMaterial({{ color: 0x0284c7, roughness: 0.3, metalness: 0.5 }});
    const greenValveMat = new THREE.MeshStandardMaterial({{ color: 0x16a34a, roughness: 0.3, metalness: 0.5 }});
    const bogPipeMat = new THREE.MeshStandardMaterial({{ color: 0x38bdf8, roughness: 0.3, metalness: 0.65 }});
    const gratingDeckMat = new THREE.MeshStandardMaterial({{ color: 0x334155, roughness: 0.65, metalness: 0.55 }});

    // Exact spherical dome geometry: base radius R_DOME = 40.4m, rise H_DOME = 10.5m
    const R_DOME = R_TANK + 0.4;
    const domeSphereR = (R_DOME * R_DOME + H_DOME * H_DOME) / (2.0 * H_DOME);
    const domeThetaMax = Math.asin(R_DOME / domeSphereR);
    const domeGeo = new THREE.SphereGeometry(domeSphereR, 64, 24, 0, Math.PI * 2, 0, domeThetaMax);

    function createFullContainmentLNGTank(spec) {{
      const tGrp = new THREE.Group();
      const tz = spec.z;

      // 5.1 Reinforced concrete foundation plinth & thermal corner protection ring
      const plinth = new THREE.Mesh(
        new THREE.CylinderGeometry(R_TANK + 1.8, R_TANK + 2.6, 2.2, 64),
        compressionRingMat
      );
      plinth.position.set(TANK_X, WALL_BASE_Y + 1.1, tz);
      plinth.castShadow = true;
      plinth.receiveShadow = true;
      tGrp.add(plinth);

      // 5.2 Outer prestressed concrete containment wall (Cryogenic White / Cream)
      const outerWall = new THREE.Mesh(
        new THREE.CylinderGeometry(R_TANK, R_TANK, H_WALL, 64),
        spec.cutaway ? tankConcreteCutawayMat : tankConcreteSolidMat
      );
      outerWall.position.set(TANK_X, WALL_BASE_Y + H_WALL / 2.0, tz);
      outerWall.castShadow = true;
      outerWall.receiveShadow = true;
      tGrp.add(outerWall);

      // Horizontal post-tensioning concrete ribs
      [14.0, 24.0, 34.0].forEach(ry => {{
        const rib = new THREE.Mesh(new THREE.TorusGeometry(R_TANK + 0.18, 0.22, 8, 64), compressionRingMat);
        rib.rotation.x = Math.PI / 2;
        rib.position.set(TANK_X, ry, tz);
        tGrp.add(rib);
      }});

      // Corporate LNG Blue Band & Tank Code Nameplate (T-101..T-104) near top of cylinder
      const bandTex = createTankBandTexture(spec.code);
      const bandMat = new THREE.MeshStandardMaterial({{ map: bandTex, roughness: 0.4, metalness: 0.15 }});
      const bandCyl = new THREE.Mesh(
        new THREE.CylinderGeometry(R_TANK + 0.15, R_TANK + 0.15, 5.2, 64, 1, true),
        bandMat
      );
      bandCyl.position.set(TANK_X, WALL_TOP_Y - 5.5, tz);
      tGrp.add(bandCyl);

      // 5.3 Upper concrete compression ring beam + perimeter safety yellow handrail
      const compRing = new THREE.Mesh(
        new THREE.CylinderGeometry(R_TANK + 1.1, R_TANK + 0.5, 2.2, 64),
        compressionRingMat
      );
      compRing.position.set(TANK_X, WALL_TOP_Y + 0.8, tz);
      compRing.castShadow = true;
      tGrp.add(compRing);

      const perimeterRail = new THREE.Mesh(
        new THREE.TorusGeometry(R_TANK + 0.7, 0.16, 8, 64),
        railingMat
      );
      perimeterRail.rotation.x = Math.PI / 2;
      perimeterRail.position.set(TANK_X, WALL_TOP_Y + 2.4, tz);
      tGrp.add(perimeterRail);

      // 5.4 FIXED True Spherical Dome Roof (SphereGeometry cap instead of inverted cone)
      const domeMesh = new THREE.Mesh(domeGeo, tankDomeMat);
      domeMesh.position.set(TANK_X, (WALL_TOP_Y + 1.2) - (domeSphereR - H_DOME), tz);
      domeMesh.castShadow = true;
      domeMesh.receiveShadow = true;
      tGrp.add(domeMesh);

      // Concentric structural dome stiffening rings
      [14.0, 27.0].forEach(rr => {{
        const dy = Math.sqrt(Math.max(0, domeSphereR * domeSphereR - rr * rr)) - (domeSphereR - H_DOME);
        const dRing = new THREE.Mesh(new THREE.TorusGeometry(rr, 0.14, 8, 48), compressionRingMat);
        dRing.rotation.x = Math.PI / 2;
        dRing.position.set(TANK_X, WALL_TOP_Y + 1.25 + dy, tz);
        tGrp.add(dRing);
      }});

      // 5.5 Cutaway Inner 9% Ni Steel Tank & Cryogenic LNG Liquid Level (shown on T-101)
      if (spec.cutaway) {{
        const innerH = 41.0;
        const innerTank = new THREE.Mesh(
          new THREE.CylinderGeometry(R_TANK - 4.5, R_TANK - 4.5, innerH, 56, 1, true),
          innerNiSteelMat
        );
        innerTank.position.set(TANK_X, WALL_BASE_Y + 2.0 + innerH / 2.0, tz);
        tGrp.add(innerTank);

        const fillH = innerH * spec.fillRatio;
        const liquid = new THREE.Mesh(
          new THREE.CylinderGeometry(R_TANK - 5.2, R_TANK - 5.2, fillH, 56),
          lngLiquidMat
        );
        liquid.position.set(TANK_X, WALL_BASE_Y + 2.2 + fillH / 2.0, tz);
        tGrp.add(liquid);

        const surface = new THREE.Mesh(
          new THREE.CylinderGeometry(R_TANK - 5.1, R_TANK - 5.1, 0.55, 56),
          lngSurfaceRingMat
        );
        surface.position.set(TANK_X, WALL_BASE_Y + 2.2 + fillH + 0.25, tz);
        tGrp.add(surface);
      }}

      // 5.6 External Spiral/Caged Stairway & Elevator Tower on NE quadrant of tank
      const stairX = TANK_X + (R_TANK + 2.2) * 0.707;
      const stairZ = tz - (R_TANK + 2.2) * 0.707;
      const stairTower = new THREE.Mesh(
        new THREE.BoxGeometry(3.4, H_WALL + 2.5, 3.4),
        gratingDeckMat
      );
      stairTower.position.set(stairX, WALL_BASE_Y + (H_WALL + 2.5) / 2.0, stairZ);
      stairTower.castShadow = true;
      tGrp.add(stairTower);
      for (let sy = 10.0; sy <= WALL_TOP_Y; sy += 8.0) {{
        const landing = new THREE.Mesh(new THREE.BoxGeometry(4.2, 0.35, 4.2), railingMat);
        landing.position.set(stairX, sy, stairZ);
        tGrp.add(landing);
      }}

      // Inclined catwalk walkway climbing across the spherical dome from stair tower to roof valve platform
      const domeWalk = new THREE.Mesh(new THREE.BoxGeometry(2.0, 0.25, R_TANK * 0.85), gratingDeckMat);
      domeWalk.position.set(TANK_X + R_TANK * 0.28, WALL_TOP_Y + 6.8, tz - R_TANK * 0.28);
      domeWalk.rotation.y = Math.PI / 4;
      domeWalk.rotation.x = 0.24;
      tGrp.add(domeWalk);

      // 5.7 ROOF-TOP PIPING, PENTHOUSE & VALVE PLATFORM (Tank Çatı Üstü Borulama ve Vana Platformu)
      const platY = DOME_APEX_Y + 0.6; // ~63.3m
      // Support legs on dome crown
      [[-7.5, -5.5], [7.5, -5.5], [-7.5, 5.5], [7.5, 5.5], [0, -5.5], [0, 5.5]].forEach(([lx, lz]) => {{
        const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.32, 0.32, 3.8, 10), steelMat);
        leg.position.set(TANK_X + lx, platY - 1.8, tz + lz);
        tGrp.add(leg);
      }});
      // Main structural steel grating platform deck (17m x 13m)
      const roofDeck = new THREE.Mesh(new THREE.BoxGeometry(17.0, 0.45, 13.0), gratingDeckMat);
      roofDeck.position.set(TANK_X, platY, tz);
      roofDeck.castShadow = true;
      tGrp.add(roofDeck);
      // Yellow safety handrails around roof valve platform
      const roofRailEdges = new THREE.EdgesGeometry(new THREE.BoxGeometry(16.8, 1.25, 12.8));
      const roofRail = new THREE.LineSegments(roofRailEdges, new THREE.LineBasicMaterial({{ color: 0xeab308 }}));
      roofRail.position.set(TANK_X, platY + 0.85, tz);
      tGrp.add(roofRail);

      // 3x Submerged In-Tank Cryogenic Pump Columns (P-101A/B/C) with green explosion-proof motors
      [-4.2, 0.0, 4.2].forEach((pz) => {{
        const colBarrel = new THREE.Mesh(new THREE.CylinderGeometry(0.75, 0.85, 3.6, 16), compressionRingMat);
        colBarrel.position.set(TANK_X + 2.8, platY + 1.8, tz + pz);
        colBarrel.castShadow = true;
        tGrp.add(colBarrel);

        const pumpMotor = new THREE.Mesh(new THREE.CylinderGeometry(0.62, 0.62, 1.9, 16), greenValveMat);
        pumpMotor.position.set(TANK_X + 2.8, platY + 4.4, tz + pz);
        tGrp.add(pumpMotor);

        // Discharge spool + green isolation valve + red ESDV on each pump column
        const spool = new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.28, 2.6, 10), steelMat);
        spool.rotation.z = Math.PI / 2;
        spool.position.set(TANK_X + 1.2, platY + 2.2, tz + pz);
        tGrp.add(spool);

        const esdvBody = new THREE.Mesh(new THREE.BoxGeometry(0.85, 1.1, 0.85), redValveMat);
        esdvBody.position.set(TANK_X + 0.4, platY + 2.4, tz + pz);
        tGrp.add(esdvBody);
        const wheel = new THREE.Mesh(new THREE.TorusGeometry(0.42, 0.08, 8, 14), yellowMat);
        wheel.rotation.x = Math.PI / 2;
        wheel.position.set(TANK_X + 0.4, platY + 3.2, tz + pz);
        tGrp.add(wheel);
      }});

      // Roof-top Liquid Fill Header (Blue/Cyan) & Top/Bottom Fill Nozzles with Red/Blue Valves
      const roofFillHeader = new THREE.Mesh(new THREE.CylinderGeometry(0.45, 0.45, 9.6, 14), blueValveMat);
      roofFillHeader.rotation.x = Math.PI / 2;
      roofFillHeader.position.set(TANK_X - 3.2, platY + 1.4, tz);
      tGrp.add(roofFillHeader);

      [-3.2, 3.2].forEach((fz) => {{
        const fillNozzle = new THREE.Mesh(new THREE.CylinderGeometry(0.55, 0.65, 2.2, 14), blueValveMat);
        fillNozzle.position.set(TANK_X - 5.2, platY + 1.1, tz + fz);
        tGrp.add(fillNozzle);
        const ctrlValve = new THREE.Mesh(new THREE.BoxGeometry(0.9, 1.2, 0.9), redValveMat);
        ctrlValve.position.set(TANK_X - 4.2, platY + 2.0, tz + fz);
        tGrp.add(ctrlValve);
        const hw = new THREE.Mesh(new THREE.TorusGeometry(0.45, 0.08, 8, 14), yellowMat);
        hw.rotation.x = Math.PI / 2;
        hw.position.set(TANK_X - 4.2, platY + 2.85, tz + fz);
        tGrp.add(hw);
      }});

      // Roof-top Pump Discharge / Recirculation Collector Header (Green)
      const roofRetHeader = new THREE.Mesh(new THREE.CylinderGeometry(0.40, 0.40, 9.6, 14), greenValveMat);
      roofRetHeader.rotation.x = Math.PI / 2;
      roofRetHeader.position.set(TANK_X - 0.6, platY + 2.2, tz);
      tGrp.add(roofRetHeader);

      // Roof-top Pressure / Vacuum Relief Breather Vents (PRV Goose-Necks) & BOG Dome Header
      [-4.8, 4.8].forEach((vz) => {{
        const ventStack = new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.35, 3.8, 12), bogPipeMat);
        ventStack.position.set(TANK_X + 6.2, platY + 1.9, tz + vz);
        tGrp.add(ventStack);
        const ventHood = new THREE.Mesh(new THREE.TorusGeometry(0.55, 0.22, 8, 14, Math.PI), bogPipeMat);
        ventHood.position.set(TANK_X + 6.75, platY + 3.8, tz + vz);
        tGrp.add(ventHood);
      }});

      // Cantilevered Roof Pipe Bridge from center Valve Platform out to Western Tank Rim (x = TANK_X - R_TANK)
      const bridgeLen = R_TANK - 4.0;
      const pipeBridge = new THREE.Mesh(new THREE.BoxGeometry(bridgeLen, 0.35, 5.2), gratingDeckMat);
      pipeBridge.position.set(TANK_X - 4.0 - bridgeLen / 2.0, WALL_TOP_Y + 2.2, tz);
      tGrp.add(pipeBridge);
      [-2.5, 2.5].forEach(bz => {{
        const brRail = new THREE.Mesh(new THREE.BoxGeometry(bridgeLen, 1.0, 0.12), railingMat);
        brRail.position.set(TANK_X - 4.0 - bridgeLen / 2.0, WALL_TOP_Y + 2.85, tz + bz);
        tGrp.add(brRail);
      }});

      tankFarmGroup.add(tGrp);
    }}

    TANK_SPECS.forEach(spec => createFullContainmentLNGTank(spec));

    // 5.8 NFPA 59A / EN 1473 Secondary Impounding Basins (Dikes), Concrete Spill Trenches & Common Deep LNG Pit
    (function buildImpoundingAndLNGPit() {{
      const dikeWallMat = new THREE.MeshStandardMaterial({{ color: 0x64748b, roughness: 0.85 }});
      const basinFloorMat = new THREE.MeshStandardMaterial({{ color: isNight ? 0x262f3d : 0x475569, roughness: 0.9 }});
      const trenchWallMat = new THREE.MeshStandardMaterial({{ color: 0x94a3b8, roughness: 0.75 }});
      const trenchFloorMat = new THREE.MeshStandardMaterial({{ color: 0x0f172a, roughness: 0.6 }});
      const foamGenMat = new THREE.MeshStandardMaterial({{ color: 0xeab308, roughness: 0.35, metalness: 0.4 }});

      const dikeSpan = 104.0;
      const dikeH = 6.2;
      const dikeThick = 1.8;

      // Secondary containment basin (dike) around each of the 4 tanks
      TANK_SPECS.forEach((spec) => {{
        const tz = spec.z;
        // Concrete impounding basin floor slab
        const bFloor = new THREE.Mesh(new THREE.BoxGeometry(dikeSpan, 0.28, dikeSpan), basinFloorMat);
        bFloor.position.set(TANK_X, 5.05, tz);
        bFloor.receiveShadow = true;
        tankFarmGroup.add(bFloor);

        // 4 perimeter dike walls (North, South, West, East)
        [-dikeSpan / 2.0, dikeSpan / 2.0].forEach(dz => {{
          const nsWall = new THREE.Mesh(new THREE.BoxGeometry(dikeSpan + dikeThick, dikeH, dikeThick), dikeWallMat);
          nsWall.position.set(TANK_X, 5.0 + dikeH / 2.0, tz + dz);
          nsWall.castShadow = true;
          nsWall.receiveShadow = true;
          tankFarmGroup.add(nsWall);
        }});
        [-dikeSpan / 2.0, dikeSpan / 2.0].forEach(dx => {{
          const ewWall = new THREE.Mesh(new THREE.BoxGeometry(dikeThick, dikeH, dikeSpan), dikeWallMat);
          ewWall.position.set(TANK_X + dx, 5.0 + dikeH / 2.0, tz);
          ewWall.castShadow = true;
          ewWall.receiveShadow = true;
          tankFarmGroup.add(ewWall);
        }});

        // Corner drainage sump inside each tank dike connected to the main LNG spill trench
        const cornerSump = new THREE.Mesh(new THREE.BoxGeometry(6.5, 0.35, 6.5), trenchFloorMat);
        cornerSump.position.set(TANK_X - dikeSpan / 2.0 + 4.5, 5.12, tz + dikeSpan / 2.0 - 4.5);
        tankFarmGroup.add(cornerSump);

        // Lateral concrete spill channel from tank basin sump to main collector trench
        const branchTrench = new THREE.Mesh(new THREE.BoxGeometry(10.0, 0.45, 3.2), trenchFloorMat);
        branchTrench.position.set(TANK_X - dikeSpan / 2.0 - 3.5, 5.14, tz + dikeSpan / 2.0 - 4.5);
        tankFarmGroup.add(branchTrench);
      }});

      // Main North-South Open Concrete LNG Spill Collector Trench (from T-101 z=-195 south to Common LNG Pit z=295)
      const trenchX = TANK_X - 59.5;
      const trenchZStart = -200.0;
      const trenchZEnd = 295.0;
      const trenchLen = trenchZEnd - trenchZStart;
      const trenchCenterZ = (trenchZStart + trenchZEnd) / 2.0;

      const mainTrenchFloor = new THREE.Mesh(new THREE.BoxGeometry(3.6, 0.35, trenchLen), trenchFloorMat);
      mainTrenchFloor.position.set(trenchX, 5.12, trenchCenterZ);
      tankFarmGroup.add(mainTrenchFloor);
      [-1.95, 1.95].forEach(tx => {{
        const curb = new THREE.Mesh(new THREE.BoxGeometry(0.45, 1.1, trenchLen), trenchWallMat);
        curb.position.set(trenchX + tx, 5.55, trenchCenterZ);
        tankFarmGroup.add(curb);
      }});

      // COMMON DEEP LNG IMPOUNDING PIT / SUMP BASIN (Ortak Derin LNG Toplanma Çukuru - LNG Pit) at South end (z = 302)
      const pitX = TANK_X - 18.0;
      const pitZ = 302.0;
      const pitW = 54.0, pitD = 38.0, pitWallH = 7.5;

      // Pit floor & cryogenic blue liquid sump indicator
      const pitFloor = new THREE.Mesh(new THREE.BoxGeometry(pitW, 0.4, pitD), trenchFloorMat);
      pitFloor.position.set(pitX, 5.15, pitZ);
      tankFarmGroup.add(pitFloor);

      const pitCryoPool = new THREE.Mesh(
        new THREE.BoxGeometry(pitW - 6.0, 0.45, pitD - 6.0),
        lngLiquidMat
      );
      pitCryoPool.position.set(pitX, 5.35, pitZ);
      tankFarmGroup.add(pitCryoPool);

      // Concrete pit retaining walls + safety yellow handrails
      [-pitD / 2.0, pitD / 2.0].forEach(pz => {{
        const w = new THREE.Mesh(new THREE.BoxGeometry(pitW + 2.0, pitWallH, 2.0), dikeWallMat);
        w.position.set(pitX, 5.0 + pitWallH / 2.0, pitZ + pz);
        w.castShadow = true;
        tankFarmGroup.add(w);
      }});
      [-pitW / 2.0, pitW / 2.0].forEach(px => {{
        const w = new THREE.Mesh(new THREE.BoxGeometry(2.0, pitWallH, pitD), dikeWallMat);
        w.position.set(pitX + px, 5.0 + pitWallH / 2.0, pitZ);
        w.castShadow = true;
        tankFarmGroup.add(w);
      }});

      // 6x High-Expansion Foam Generators (Yüksek Genleşmeli Köpük Jeneratörleri) mounted along LNG Pit walls
      [-18.0, 0.0, 18.0].forEach(fx => {{
        [-pitD / 2.0, pitD / 2.0].forEach(fz => {{
          const foamBox = new THREE.Mesh(new THREE.BoxGeometry(2.8, 2.2, 2.4), foamGenMat);
          foamBox.position.set(pitX + fx, 5.0 + pitWallH + 1.1, pitZ + fz);
          foamBox.castShadow = true;
          tankFarmGroup.add(foamBox);
          const nozzle = new THREE.Mesh(new THREE.CylinderGeometry(0.55, 0.75, 1.6, 12), redValveMat);
          nozzle.rotation.x = fz < 0 ? Math.PI / 3 : -Math.PI / 3;
          nozzle.position.set(pitX + fx, 5.0 + pitWallH + 1.0, pitZ + fz + (fz < 0 ? 1.4 : -1.4));
          tankFarmGroup.add(nozzle);
        }});
      }});
    }})();

    // 5.9 Automation, SCADA & Central Control Building (Otomasyon ve Kontrol Binası) behind the tanks
    (function buildAutomationAndControlBuilding() {{
      const ctrlX = TANK_X + 114.0;
      const ctrlZ = 0.0;
      const bldgGroup = new THREE.Group();

      const facadeMat = new THREE.MeshStandardMaterial({{ color: isNight ? 0xcbd5e1 : 0xe2e8f0, roughness: 0.55, metalness: 0.15 }});
      const slateTrimMat = new THREE.MeshStandardMaterial({{ color: 0x1e293b, roughness: 0.6, metalness: 0.3 }});
      const fasciaBlueMat = new THREE.MeshStandardMaterial({{ color: 0x0284c7, roughness: 0.35, metalness: 0.25 }});
      const ctrlGlassMat = new THREE.MeshStandardMaterial({{
        color: isNight ? 0x38bdf8 : 0x0f172a,
        emissive: isNight ? 0x0284c7 : 0x075985,
        emissiveIntensity: isNight ? 0.85 : 0.25,
        roughness: 0.15,
        metalness: 0.8
      }});

      // Main 2-Story SCADA & Central Control Room (CCR) Building (56m x 14m x 26m)
      const mainBody = new THREE.Mesh(new THREE.BoxGeometry(26.0, 14.0, 56.0), facadeMat);
      mainBody.position.set(ctrlX, 5.0 + 7.0, ctrlZ);
      mainBody.castShadow = true;
      mainBody.receiveShadow = true;
      bldgGroup.add(mainBody);

      // Corporate Blue Fascia Crown & Dark Slate Base Plinth
      const crownBand = new THREE.Mesh(new THREE.BoxGeometry(26.6, 2.0, 56.6), fasciaBlueMat);
      crownBand.position.set(ctrlX, 5.0 + 13.2, ctrlZ);
      bldgGroup.add(crownBand);

      const baseTrim = new THREE.Mesh(new THREE.BoxGeometry(26.4, 1.8, 56.4), slateTrimMat);
      baseTrim.position.set(ctrlX, 5.0 + 0.9, ctrlZ);
      bldgGroup.add(baseTrim);

      // Panoramic Control Room Windows facing the 4 LNG Tanks (-x face)
      const glassStrip = new THREE.Mesh(new THREE.BoxGeometry(0.4, 3.8, 46.0), ctrlGlassMat);
      glassStrip.position.set(ctrlX - 13.05, 5.0 + 9.2, ctrlZ);
      bldgGroup.add(glassStrip);

      // Ground floor entrance canopy & glass lobby
      const canopy = new THREE.Mesh(new THREE.BoxGeometry(6.5, 0.6, 16.0), fasciaBlueMat);
      canopy.position.set(ctrlX - 15.5, 5.0 + 4.8, ctrlZ);
      canopy.castShadow = true;
      bldgGroup.add(canopy);

      // Rooftop HVAC Chiller Skids & 32m SCADA / Radar Telecom Lattice Tower
      [-14.0, 14.0].forEach(hz => {{
        const hvac = new THREE.Mesh(new THREE.BoxGeometry(6.0, 2.6, 8.0), compressionRingMat);
        hvac.position.set(ctrlX + 2.0, 5.0 + 15.3, ctrlZ + hz);
        bldgGroup.add(hvac);
      }});
      const towerMast = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 1.2, 26.0, 8), steelMat);
      towerMast.position.set(ctrlX + 4.0, 5.0 + 14.0 + 13.0, ctrlZ);
      bldgGroup.add(towerMast);
      const beacon = new THREE.Mesh(
        new THREE.SphereGeometry(0.65, 12, 12),
        new THREE.MeshBasicMaterial({{ color: 0xff2222 }})
      );
      beacon.position.set(ctrlX + 4.0, 5.0 + 14.0 + 26.5, ctrlZ);
      bldgGroup.add(beacon);

      // Adjacent Electrical Substation / MCC Switchgear Building (North wing, z = -48) + 3 HV Transformers
      const mccBldg = new THREE.Mesh(new THREE.BoxGeometry(20.0, 9.5, 28.0), facadeMat);
      mccBldg.position.set(ctrlX, 5.0 + 4.75, ctrlZ - 48.0);
      mccBldg.castShadow = true;
      bldgGroup.add(mccBldg);
      [-56.0, -48.0, -40.0].forEach(tz => {{
        const xfmr = new THREE.Mesh(new THREE.BoxGeometry(4.2, 4.5, 4.2), compressionRingMat);
        xfmr.position.set(ctrlX - 14.0, 5.0 + 2.25, tz);
        bldgGroup.add(xfmr);
      }});

      // Adjacent BOG Compressor & Analyzer Building (South wing, z = +48)
      const bogBldg = new THREE.Mesh(new THREE.BoxGeometry(22.0, 10.5, 30.0), facadeMat);
      bogBldg.position.set(ctrlX, 5.0 + 5.25, ctrlZ + 48.0);
      bogBldg.castShadow = true;
      bldgGroup.add(bogBldg);

      tankFarmGroup.add(bldgGroup);
    }})();

    // 5.10 Cryogenic Recirculation & Booster Pump Station Skid (P-201A/B/C)
    const pumpSkidBase = new THREE.Mesh(new THREE.BoxGeometry(12.0, 1.2, 20.0), compressionRingMat);
    pumpSkidBase.position.set(PUMP_X, 5.6, -18.0);
    tankFarmGroup.add(pumpSkidBase);
    [-24.0, -18.0, -12.0].forEach((pz) => {{
      const pumpCan = new THREE.Mesh(new THREE.CylinderGeometry(1.4, 1.7, 4.2, 16), greenValveMat);
      pumpCan.position.set(PUMP_X, 7.8, pz);
      pumpCan.castShadow = true;
      tankFarmGroup.add(pumpCan);
      const motor = new THREE.Mesh(new THREE.CylinderGeometry(1.05, 1.05, 3.0, 16), steelMat);
      motor.position.set(PUMP_X, 11.2, pz);
      motor.castShadow = true;
      tankFarmGroup.add(motor);
    }});

    terminalGroup.add(tankFarmGroup);

    // 6. PIPELINES: supply route, parallel-offset return route, and 4-Tank Inter-Tank Supply/Return/BOG Network

    // Temperature-driven 1D gradient texture (TubeGeometry uv.x runs along length).
    function buildTempGradient(stationData, reverse) {{
      const canvas = document.createElement('canvas');
      canvas.width = 256; canvas.height = 1;
      const ctx = canvas.getContext('2d');
      const temps = stationData.temp_c;
      const tMin = Math.min.apply(null, temps);
      const tMax = Math.max.apply(null, temps);
      const cold = new THREE.Color(0x1f6feb);
      const mid = new THREE.Color(0x3fb950);
      const hot = new THREE.Color(0xf85149);
      for (let i = 0; i < 256; i++) {{
        const fPos = i / 255.0;
        const si = Math.min(temps.length - 1, Math.round(fPos * (temps.length - 1)));
        const siRev = reverse ? (temps.length - 1 - si) : si;
        const f = (temps[siRev] - tMin) / Math.max(tMax - tMin, 1e-6);
        const col = f < 0.5 ? cold.clone().lerp(mid, f * 2.0) : mid.clone().lerp(hot, (f - 0.5) * 2.0);
        ctx.fillStyle = '#' + col.getHexString();
        ctx.fillRect(i, 0, 1, 1);
      }}
      const tex = new THREE.CanvasTexture(canvas);
      tex.wrapS = THREE.ClampToEdgeWrapping;
      tex.wrapT = THREE.ClampToEdgeWrapping;
      tex.needsUpdate = true;
      return tex;
    }}
    const tempTex = buildTempGradient(telemetry.stations, false);
    const tempTexRet = buildTempGradient(telemetry.return_stations || telemetry.stations, true);

    function pipeControlPoints(zOffset, loopExtZ) {{
      const pts = [new THREE.Vector3(ROUTE_START, 14, zOffset)];
      omegaStarts.forEach(x0 => {{
        pts.push(new THREE.Vector3(x0, 14, zOffset));
        pts.push(new THREE.Vector3(x0, 14, zOffset + loopExtZ));
        pts.push(new THREE.Vector3(x0 + OMEGA_W, 14, zOffset + loopExtZ));
        pts.push(new THREE.Vector3(x0 + OMEGA_W, 14, zOffset));
      }});
      if (pts[pts.length - 1].x < ROUTE_END - 20.0) {{
        pts.push(new THREE.Vector3(ROUTE_END - 20, 14, zOffset));
      }}
      pts.push(new THREE.Vector3(ROUTE_END, 14, zOffset));
      return pts;
    }}

    // Continuous pipe path: straight runs + rounded (long-radius) elbows.
    function buildRoundedPath(points, bendR) {{
      const path = new THREE.CurvePath();
      const n = points.length;
      let segStart = points[0].clone();
      for (let i = 1; i < n - 1; i++) {{
        const p = points[i], prevP = points[i - 1], nextP = points[i + 1];
        const dIn = new THREE.Vector3().subVectors(p, prevP).normalize();
        const dOut = new THREE.Vector3().subVectors(nextP, p).normalize();
        const angle = Math.acos(THREE.MathUtils.clamp(dIn.dot(dOut), -1, 1));
        const t = Math.min(bendR * Math.tan(angle / 2), prevP.distanceTo(p) * 0.45, nextP.distanceTo(p) * 0.45);
        const start = p.clone().addScaledVector(dIn, -t);
        const end = p.clone().addScaledVector(dOut, t);
        if (segStart.distanceTo(start) > 1e-6) path.add(new THREE.LineCurve3(segStart, start));
        path.add(new THREE.QuadraticBezierCurve3(start, p, end));
        segStart = end;
      }}
      path.add(new THREE.LineCurve3(segStart, points[n - 1]));
      return path;
    }}

    // True horizontal parallel offset of a polyline (mitered corners), so the
    // return line stays parallel through straight runs and omega loops alike.
    function offsetPolyline(points, offset) {{
      const segs = [];
      for (let i = 0; i < points.length - 1; i++) {{
        const a = points[i], b = points[i + 1];
        const dx = b.x - a.x, dz = b.z - a.z;
        const len = Math.hypot(dx, dz) || 1;
        const nx = -dz / len, nz = dx / len;
        segs.push({{
          a: new THREE.Vector3(a.x + nx * offset, a.y, a.z + nz * offset),
          b: new THREE.Vector3(b.x + nx * offset, b.y, b.z + nz * offset)
        }});
      }}
      const out = [segs[0].a];
      for (let i = 0; i < segs.length - 1; i++) {{
        const A = segs[i], B = segs[i + 1];
        const d1x = A.b.x - A.a.x, d1z = A.b.z - A.a.z;
        const d2x = B.b.x - B.a.x, d2z = B.b.z - B.a.z;
        const den = d1x * d2z - d1z * d2x;
        if (Math.abs(den) < 1e-9) {{
          out.push(A.b);
        }} else {{
          const t = ((B.a.x - A.a.x) * d2z - (B.a.z - A.a.z) * d2x) / den;
          out.push(new THREE.Vector3(A.a.x + t * d1x, A.a.y, A.a.z + t * d1z));
        }}
      }}
      out.push(segs[segs.length - 1].b);
      return out;
    }}

    const mainPts = pipeControlPoints(MAIN_Z, LOOP_EXT);
    const mainCurve = buildRoundedPath(mainPts, Math.max(2.5, mainRadius * 2.5));
    const mainPipeGeo = new THREE.TubeGeometry(mainCurve, 240, mainRadius, 18, false);
    const mainPipeMat = new THREE.MeshStandardMaterial({{
      map: tempTex, color: 0xffffff, roughness: 0.25, metalness: 0.65,
      emissive: 0x001122, emissiveIntensity: 0.25
    }});
    const mainPipe = new THREE.Mesh(mainPipeGeo, mainPipeMat);
    mainPipe.castShadow = true;
    mainPipe.userData.lineType = "main";
    terminalGroup.add(mainPipe);

    // Return / recirculation line: true parallel offset of the supply route.
    const returnPts = offsetPolyline(mainPts, parallelOffset);
    const recircCurve = buildRoundedPath(returnPts, Math.max(2.0, retRadius * 2.5));
    const recircPipeGeo = new THREE.TubeGeometry(recircCurve, 240, retRadius, 14, false);
    const recircPipeMat = new THREE.MeshStandardMaterial({{
      map: tempTexRet, color: 0x9be9a8, roughness: 0.3, metalness: 0.6,
      emissive: 0x002200, emissiveIntensity: 0.25
    }});
    const recircPipe = new THREE.Mesh(recircPipeGeo, recircPipeMat);
    recircPipe.castShadow = true;
    recircPipe.userData.lineType = "return";
    terminalGroup.add(recircPipe);

    const returnEndZ = returnPts[returnPts.length - 1].z;
    const flarePipeMat = new THREE.MeshStandardMaterial({{
      color: 0xf97316,
      roughness: 0.32,
      metalness: 0.55,
      emissive: 0x3b1100,
      emissiveIntensity: 0.28
    }});
    const FLARE_X = TANK_X + 148.0;
    const FLARE_Z = -312.0;
    const H_FLARE = 84.0;
    let bogParticleCurve = null;
    let flareParticleCurve = null;
    const flareFlameGroup = new THREE.Group();
    let flareLight = null;

    // 6.2 INTER-TANK PIPING NETWORK (4 Tank Arası Gidiş, Dönüş, BOG ve Flare Kolektörleri + Tank Çatı İniş Boruları)
    (function buildInterTankPiping() {{
      const rackMat = new THREE.MeshStandardMaterial({{ color: 0x475569, roughness: 0.6, metalness: 0.5 }});
      const supplyHeaderX = TANK_HEADER_X;
      const returnHeaderX = TANK_HEADER_X - 3.8;
      const bogHeaderX = TANK_HEADER_X + 3.2;
      const flareReliefHeaderX = TANK_X + 56.0;
      const zMinH = TANK_SPECS[0].z;
      const zMaxH = TANK_SPECS[TANK_SPECS.length - 1].z;

      // Elevated Steel Pipe Rack Portals along the front of all 4 tanks (z = -195..+195)
      for (let z = zMinH; z <= zMaxH; z += 26.0) {{
        [-4.5, 4.0].forEach(dx => {{
          const col = new THREE.Mesh(new THREE.BoxGeometry(0.65, 13.5, 0.65), rackMat);
          col.position.set(supplyHeaderX + dx, 5.0 + 6.75, z);
          terminalGroup.add(col);
        }});
        const beam1 = new THREE.Mesh(new THREE.BoxGeometry(9.6, 0.55, 0.65), rackMat);
        beam1.position.set(supplyHeaderX - 0.25, 11.8, z);
        terminalGroup.add(beam1);
        const beam2 = new THREE.Mesh(new THREE.BoxGeometry(9.6, 0.55, 0.65), rackMat);
        beam2.position.set(supplyHeaderX - 0.25, 14.2, z);
        terminalGroup.add(beam2);
        const beam3 = new THREE.Mesh(new THREE.BoxGeometry(9.6, 0.55, 0.65), rackMat);
        beam3.position.set(supplyHeaderX - 0.25, 17.0, z);
        terminalGroup.add(beam3);
      }}

      // A) Main Supply (Gidiş) Tie-In from Trestle End (ROUTE_END) to Inter-Tank Supply Header
      const supplyTieCurve = buildRoundedPath([
        new THREE.Vector3(ROUTE_END, 14.0, MAIN_Z),
        new THREE.Vector3(supplyHeaderX, 14.8, MAIN_Z)
      ], 2.5);
      terminalGroup.add(new THREE.Mesh(new THREE.TubeGeometry(supplyTieCurve, 24, mainRadius, 14, false), mainPipeMat));

      // North-South Main Supply Distribution Header (Gidiş Kolektörü) spanning T-101..T-104
      const supplyHeaderCurve = new THREE.LineCurve3(
        new THREE.Vector3(supplyHeaderX, 14.8, zMinH - 3.0),
        new THREE.Vector3(supplyHeaderX, 14.8, zMaxH + 3.0)
      );
      terminalGroup.add(new THREE.Mesh(new THREE.TubeGeometry(supplyHeaderCurve, 40, mainRadius * 0.92, 16, false), mainPipeMat));

      // B) Return / Recirculation (Dönüş) Collector Header spanning T-101..T-104 & connecting via P-201 Pump Skid
      const returnHeaderCurve = new THREE.LineCurve3(
        new THREE.Vector3(returnHeaderX, 12.4, zMinH + 3.0),
        new THREE.Vector3(returnHeaderX, 12.4, zMaxH + 3.0)
      );
      terminalGroup.add(new THREE.Mesh(new THREE.TubeGeometry(returnHeaderCurve, 40, retRadius * 0.95, 14, false), recircPipeMat));

      // Connect Return Header -> P-201 Pump Station Suction & P-201 Discharge -> Marine Return Line (recircPipe)
      const pumpSuctionCurve = buildRoundedPath([
        new THREE.Vector3(returnHeaderX, 12.4, -12.0),
        new THREE.Vector3(PUMP_X + 2.5, 12.4, -12.0),
        new THREE.Vector3(PUMP_X + 2.5, 7.8, -18.0)
      ], 2.0);
      terminalGroup.add(new THREE.Mesh(new THREE.TubeGeometry(pumpSuctionCurve, 20, retRadius, 12, false), recircPipeMat));

      const pumpDischargeCurve = buildRoundedPath([
        new THREE.Vector3(PUMP_X - 1.5, 7.8, -18.0),
        new THREE.Vector3(PUMP_X - 1.5, 14.0, returnEndZ),
        new THREE.Vector3(ROUTE_END, 14.0, returnEndZ)
      ], 2.0);
      terminalGroup.add(new THREE.Mesh(new THREE.TubeGeometry(pumpDischargeCurve, 20, retRadius, 12, false), recircPipeMat));

      // C) COMPLETE BOG (BOIL-OFF GAS) VAPOR LINE NETWORK (BOG Hattı):
      //    1. Marine Vapor Return & BOG Line from LUP Dolphin along Trestle to Onshore BOG Collector Header
      const marineBogCurve = buildRoundedPath([
        new THREE.Vector3(ROUTE_START, 16.2, 0.0),
        new THREE.Vector3(ROUTE_END, 16.2, 0.0),
        new THREE.Vector3(bogHeaderX, 17.6, 0.0)
      ], 2.5);
      terminalGroup.add(new THREE.Mesh(new THREE.TubeGeometry(marineBogCurve, 48, retRadius * 0.78, 12, false), bogPipeMat));

      //    2. North-South Overhead BOG Vapor Collector Header connecting all 4 tanks (T-101..T-104)
      const bogHeaderCurve = new THREE.LineCurve3(
        new THREE.Vector3(bogHeaderX, 17.6, zMinH),
        new THREE.Vector3(bogHeaderX, 17.6, zMaxH)
      );
      terminalGroup.add(new THREE.Mesh(new THREE.TubeGeometry(bogHeaderCurve, 36, retRadius * 0.88, 12, false), bogPipeMat));

      //    3. BOG Transfer Header from Tank Farm to BOG Compressor & Recondenser Station (V-301 & K-301)
      const bogToCompressorCurve = buildRoundedPath([
        new THREE.Vector3(bogHeaderX, 17.6, zMinH),
        new THREE.Vector3(bogHeaderX, 17.6, 125.0),
        new THREE.Vector3(TANK_X + 102.0, 17.6, 125.0),
        new THREE.Vector3(TANK_X + 102.0, 13.5, 52.0)
      ], 3.0);
      terminalGroup.add(new THREE.Mesh(new THREE.TubeGeometry(bogToCompressorCurve, 36, retRadius * 0.85, 12, false), bogPipeMat));
      bogParticleCurve = bogToCompressorCurve;

      //    4. Vertical Cryogenic BOG Recondenser Column (V-301) & Suction Knock-Out Drum outside BOG Compressor Building
      const recondenser = new THREE.Mesh(new THREE.CylinderGeometry(2.2, 2.2, 13.5, 20), bogPipeMat);
      recondenser.position.set(TANK_X + 100.0, 5.0 + 6.75, 58.0);
      recondenser.castShadow = true;
      terminalGroup.add(recondenser);
      const recondDome = new THREE.Mesh(new THREE.SphereGeometry(2.2, 20, 12, 0, Math.PI * 2, 0, Math.PI / 2), bogPipeMat);
      recondDome.position.set(TANK_X + 100.0, 5.0 + 13.5, 58.0);
      terminalGroup.add(recondDome);

      // D) Per-Tank Branch Risers (Gidiş, Dönüş, BOG & Emergency Flare Relief) climbing up each tank wall
      const riserX = TANK_X - R_TANK - 1.4;
      const eastRiserX = TANK_X + R_TANK + 1.4;
      const roofTopY = DOME_APEX_Y + 2.0;

      TANK_SPECS.forEach((spec) => {{
        const tz = spec.z;
        const zSup = tz - 1.8;
        const zRet = tz + 1.8;
        const zBog = tz;

        // 1. Supply (Gidiş) Riser: Header -> ESDV Valve -> Vertical Riser up Tank Wall -> Roof Bridge -> Roof Fill Header
        const supRiser = buildRoundedPath([
          new THREE.Vector3(supplyHeaderX, 14.8, zSup),
          new THREE.Vector3(riserX, 14.8, zSup),
          new THREE.Vector3(riserX, WALL_TOP_Y + 2.8, zSup),
          new THREE.Vector3(TANK_X - 3.2, roofTopY, zSup)
        ], 2.2);
        terminalGroup.add(new THREE.Mesh(new THREE.TubeGeometry(supRiser, 36, mainRadius * 0.72, 14, false), mainPipeMat));

        // 2. Return (Dönüş) Riser: Roof Pump Discharge Header -> Roof Bridge -> Vertical Riser down Tank Wall -> Return Header
        const retRiser = buildRoundedPath([
          new THREE.Vector3(TANK_X - 0.6, roofTopY + 0.6, zRet),
          new THREE.Vector3(riserX - 1.1, WALL_TOP_Y + 2.8, zRet),
          new THREE.Vector3(riserX - 1.1, 12.4, zRet),
          new THREE.Vector3(returnHeaderX, 12.4, zRet)
        ], 2.0);
        terminalGroup.add(new THREE.Mesh(new THREE.TubeGeometry(retRiser, 36, retRadius * 0.82, 12, false), recircPipeMat));

        // 3. BOG Vapor Riser: Roof Dome -> Vertical Riser -> Overhead BOG Collector Header
        const bogRiser = buildRoundedPath([
          new THREE.Vector3(TANK_X + 2.0, roofTopY + 1.0, zBog),
          new THREE.Vector3(riserX + 0.6, WALL_TOP_Y + 3.4, zBog),
          new THREE.Vector3(riserX + 0.6, 17.6, zBog),
          new THREE.Vector3(bogHeaderX, 17.6, zBog)
        ], 2.0);
        terminalGroup.add(new THREE.Mesh(new THREE.TubeGeometry(bogRiser, 32, retRadius * 0.68, 10, false), bogPipeMat));

        // 4. Tank Roof Overpressure / Emergency Flare Relief Riser (East face of each tank -> East Flare Relief Header)
        const tankFlareRiser = buildRoundedPath([
          new THREE.Vector3(TANK_X + 6.2, roofTopY + 1.2, tz + 4.8),
          new THREE.Vector3(eastRiserX, WALL_TOP_Y + 2.8, tz + 4.8),
          new THREE.Vector3(eastRiserX, 16.2, tz + 4.8),
          new THREE.Vector3(flareReliefHeaderX, 16.2, tz + 4.8)
        ], 2.0);
        terminalGroup.add(new THREE.Mesh(new THREE.TubeGeometry(tankFlareRiser, 32, retRadius * 0.62, 10, false), flarePipeMat));

        // Ground-level Tank Inlet/Outlet ESDV Manifold Valve Skid at each tank branch
        const esdvSup = new THREE.Mesh(new THREE.BoxGeometry(1.5, 2.2, 1.5), redValveMat);
        esdvSup.position.set((supplyHeaderX + riserX) / 2.0, 15.2, zSup);
        terminalGroup.add(esdvSup);
        const esdvRet = new THREE.Mesh(new THREE.BoxGeometry(1.3, 1.9, 1.3), greenValveMat);
        esdvRet.position.set((returnHeaderX + riserX) / 2.0, 12.8, zRet);
        terminalGroup.add(esdvRet);
      }});

      // E) COMPLETE FLARE LINE (Flare Hattı), KNOCK-OUT DRUM (V-401) & ELEVATED FLARE STACK (F-401 Flare Bacası)
      //    1. East Flare Relief Collector Header running behind all 4 tanks (z = +200 -> -260) into KO Drum V-401
      const koDrumX = FLARE_X - 28.0;
      const koDrumZ = FLARE_Z + 22.0;

      // Pipe rack supports along the East Flare Relief Header
      for (let z = -260.0; z <= 200.0; z += 32.0) {{
        const fCol = new THREE.Mesh(new THREE.BoxGeometry(0.6, 11.5, 0.6), rackMat);
        fCol.position.set(flareReliefHeaderX, 5.0 + 5.75, z);
        terminalGroup.add(fCol);
        const fCap = new THREE.Mesh(new THREE.BoxGeometry(2.6, 0.5, 0.6), rackMat);
        fCap.position.set(flareReliefHeaderX, 15.6, z);
        terminalGroup.add(fCap);
      }}

      // BOG Compressor Excess / Blowdown Branch into Main Flare Header
      const bogToFlareCurve = buildRoundedPath([
        new THREE.Vector3(TANK_X + 114.0, 13.5, 36.0),
        new THREE.Vector3(TANK_X + 92.0, 16.2, 36.0),
        new THREE.Vector3(flareReliefHeaderX, 16.2, 36.0)
      ], 2.5);
      terminalGroup.add(new THREE.Mesh(new THREE.TubeGeometry(bogToFlareCurve, 24, retRadius * 0.75, 12, false), flarePipeMat));

      // Main Flare Header from South Tank T-104 (z = +200) northwards to Flare KO Drum V-401 & up the F-401 Flare Stack
      const flareHeaderCurve = buildRoundedPath([
        new THREE.Vector3(flareReliefHeaderX, 16.2, zMaxH + 4.8),
        new THREE.Vector3(flareReliefHeaderX, 16.2, koDrumZ),
        new THREE.Vector3(koDrumX - 8.0, 16.2, koDrumZ),
        new THREE.Vector3(koDrumX - 8.0, 9.8, koDrumZ),
        new THREE.Vector3(FLARE_X, 9.8, FLARE_Z),
        new THREE.Vector3(FLARE_X, 5.0 + H_FLARE + 4.5, FLARE_Z)
      ], 2.8);
      terminalGroup.add(new THREE.Mesh(new THREE.TubeGeometry(flareHeaderCurve, 80, retRadius * 0.92, 14, false), flarePipeMat));
      flareParticleCurve = flareHeaderCurve;

      //    2. Flare Knock-Out (KO) Drum V-401 (Horizontal Liquid Separator) & Water Seal Drum V-402
      const koDrumGroup = new THREE.Group();
      const koVesselMat = new THREE.MeshStandardMaterial({{ color: 0x94a3b8, roughness: 0.4, metalness: 0.65 }});
      const koCyl = new THREE.Mesh(new THREE.CylinderGeometry(3.2, 3.2, 18.0, 24), koVesselMat);
      koCyl.rotation.z = Math.PI / 2;
      koCyl.position.set(koDrumX, 9.8, koDrumZ);
      koCyl.castShadow = true;
      koDrumGroup.add(koCyl);
      [-9.0, 9.0].forEach(dx => {{
        const cap = new THREE.Mesh(new THREE.SphereGeometry(3.2, 20, 12), koVesselMat);
        cap.scale.set(0.55, 1.0, 1.0);
        cap.position.set(koDrumX + dx, 9.8, koDrumZ);
        koDrumGroup.add(cap);
      }});
      // Orange Flare Identification Band on KO Drum V-401
      const koBand = new THREE.Mesh(new THREE.CylinderGeometry(3.26, 3.26, 2.2, 24), flarePipeMat);
      koBand.rotation.z = Math.PI / 2;
      koBand.position.set(koDrumX, 9.8, koDrumZ);
      koDrumGroup.add(koBand);
      // Concrete saddles under KO Drum V-401
      [-5.5, 5.5].forEach(dx => {{
        const saddle = new THREE.Mesh(new THREE.BoxGeometry(1.6, 4.2, 5.8), compressionRingMat);
        saddle.position.set(koDrumX + dx, 5.0 + 2.1, koDrumZ);
        koDrumGroup.add(saddle);
      }});

      // Vertical Liquid Seal Drum V-402 at base of Flare Stack
      const sealDrum = new THREE.Mesh(new THREE.CylinderGeometry(2.6, 2.6, 8.5, 20), koVesselMat);
      sealDrum.position.set(FLARE_X - 7.5, 5.0 + 4.25, FLARE_Z + 6.5);
      sealDrum.castShadow = true;
      koDrumGroup.add(sealDrum);
      terminalGroup.add(koDrumGroup);

      //    3. ELEVATED DERRICK-SUPPORTED FLARE STACK (F-401 Flare Bacası, Height = 84m)
      const flareStackGroup = new THREE.Group();

      // Sterile thermal radiation exclusion zone gravel pad + safety perimeter rail
      const flareZonePad = new THREE.Mesh(
        new THREE.CylinderGeometry(28.0, 30.0, 0.4, 36),
        new THREE.MeshStandardMaterial({{ color: isNight ? 0x2d2620 : 0x7c6f64, roughness: 0.92 }})
      );
      flareZonePad.position.set(FLARE_X, 5.05, FLARE_Z);
      flareZonePad.receiveShadow = true;
      flareStackGroup.add(flareZonePad);

      const zoneFence = new THREE.Mesh(new THREE.TorusGeometry(27.5, 0.18, 8, 48), railingMat);
      zoneFence.rotation.x = Math.PI / 2;
      zoneFence.position.set(FLARE_X, 6.2, FLARE_Z);
      flareStackGroup.add(zoneFence);

      // Heavy concrete octagonal foundation pedestal
      const flarePedestal = new THREE.Mesh(new THREE.CylinderGeometry(8.5, 10.0, 3.2, 8), compressionRingMat);
      flarePedestal.position.set(FLARE_X, 5.0 + 1.6, FLARE_Z);
      flarePedestal.castShadow = true;
      flareStackGroup.add(flarePedestal);

      // Central Stainless Steel Flare Riser Stack (84m tall)
      const riserMat = new THREE.MeshStandardMaterial({{ color: 0xcbd5e1, roughness: 0.3, metalness: 0.85 }});
      const flareRiserPipe = new THREE.Mesh(new THREE.CylinderGeometry(1.15, 1.45, H_FLARE, 20), riserMat);
      flareRiserPipe.position.set(FLARE_X, 5.0 + H_FLARE / 2.0, FLARE_Z);
      flareRiserPipe.castShadow = true;
      flareStackGroup.add(flareRiserPipe);

      // 4-Legged Structural Steel Derrick Lattice Tower supporting the 84m Flare Riser
      const baseSpread = 5.4;
      const topSpread = 2.6;
      const derrickRedMat = new THREE.MeshStandardMaterial({{ color: 0xdc2626, roughness: 0.45, metalness: 0.4 }});
      const derrickWhiteMat = new THREE.MeshStandardMaterial({{ color: 0xf8fafc, roughness: 0.45, metalness: 0.3 }});

      const nBays = 8;
      const bayH = H_FLARE / nBays;
      for (let b = 0; b < nBays; b++) {{
        const f0 = b / nBays;
        const f1 = (b + 1) / nBays;
        const y0 = 5.0 + f0 * H_FLARE;
        const y1 = 5.0 + f1 * H_FLARE;
        const ym = (y0 + y1) / 2.0;
        const s0 = baseSpread + (topSpread - baseSpread) * f0;
        const s1 = baseSpread + (topSpread - baseSpread) * f1;
        const sm = (s0 + s1) / 2.0;
        // Upper 3 bays painted in Red/White aviation obstruction warning bands
        const bayMat = b >= 5 ? (b % 2 === 1 ? derrickRedMat : derrickWhiteMat) : steelMat;

        [[-1, -1], [1, -1], [-1, 1], [1, 1]].forEach(([sx, sz]) => {{
          const legSeg = new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.32, bayH + 0.3, 8), bayMat);
          legSeg.position.set(FLARE_X + sx * sm, ym, FLARE_Z + sz * sm);
          legSeg.castShadow = true;
          flareStackGroup.add(legSeg);
        }});

        // Horizontal ring struts & diagonal X-bracing on all 4 faces of each bay
        const hBraceLen = s1 * 2.0;
        [-s1, s1].forEach(offset => {{
          const strutX = new THREE.Mesh(new THREE.BoxGeometry(hBraceLen, 0.28, 0.28), bayMat);
          strutX.position.set(FLARE_X, y1, FLARE_Z + offset);
          flareStackGroup.add(strutX);
          const strutZ = new THREE.Mesh(new THREE.BoxGeometry(0.28, 0.28, hBraceLen), bayMat);
          strutZ.position.set(FLARE_X + offset, y1, FLARE_Z);
          flareStackGroup.add(strutZ);
        }});

        const diagLen = Math.hypot(sm * 2.0, bayH);
        const diagAngle = Math.atan2(sm * 2.0, bayH);
        [-sm, sm].forEach(faceOff => {{
          [diagAngle, -diagAngle].forEach(ang => {{
            const diag = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.12, diagLen, 6), bayMat);
            diag.position.set(FLARE_X, ym, FLARE_Z + faceOff);
            diag.rotation.z = ang;
            flareStackGroup.add(diag);
          }});
        }});
      }}

      // 3 Circular Service & Pilot Inspection Platforms along Flare Stack (y = 33m, 58m, 84m)
      [33.0, 58.0, 84.0].forEach((py, idx) => {{
        const platR = 5.2 - idx * 0.7;
        const plat = new THREE.Mesh(new THREE.CylinderGeometry(platR, platR, 0.35, 24), gratingDeckMat);
        plat.position.set(FLARE_X, py, FLARE_Z);
        flareStackGroup.add(plat);
        const pRail = new THREE.Mesh(new THREE.TorusGeometry(platR - 0.1, 0.14, 8, 24), railingMat);
        pRail.rotation.x = Math.PI / 2;
        pRail.position.set(FLARE_X, py + 1.0, FLARE_Z);
        flareStackGroup.add(pRail);
      }});

      // High-Temp Stainless Sonic Flare Tip, Windshield Shroud & 3 Pilot Burners at Top (y = 89m..94.5m)
      const tipBaseY = 5.0 + H_FLARE;
      const flareTipShroud = new THREE.Mesh(
        new THREE.CylinderGeometry(1.75, 1.25, 5.2, 20),
        new THREE.MeshStandardMaterial({{ color: 0x334155, roughness: 0.35, metalness: 0.85 }})
      );
      flareTipShroud.position.set(FLARE_X, tipBaseY + 2.6, FLARE_Z);
      flareStackGroup.add(flareTipShroud);

      // 3 Pilot Gas Ignition Nozzles around the Flare Tip
      [0, (Math.PI * 2) / 3, (Math.PI * 4) / 3].forEach(ang => {{
        const pilot = new THREE.Mesh(new THREE.CylinderGeometry(0.14, 0.14, 3.2, 8), flarePipeMat);
        pilot.position.set(FLARE_X + Math.cos(ang) * 1.65, tipBaseY + 3.8, FLARE_Z + Math.sin(ang) * 1.65);
        pilot.rotation.z = -Math.cos(ang) * 0.25;
        pilot.rotation.x = Math.sin(ang) * 0.25;
        flareStackGroup.add(pilot);
      }});

      //    4. ANIMATED 3-LAYER 3D FLARE FLAME (Alev & Pilot Ateşi) + Dynamic PointLight
      const flameBaseY = tipBaseY + 5.0; // y = 94.0m
      flareFlameGroup.position.set(FLARE_X, flameBaseY, FLARE_Z);

      // Outer crimson-orange translucent flame envelope
      const outerFlameGeo = new THREE.ConeGeometry(3.4, 15.5, 20);
      outerFlameGeo.translate(0, 7.75, 0);
      const outerFlameMat = new THREE.MeshBasicMaterial({{
        color: 0xea580c,
        transparent: true,
        opacity: 0.58
      }});
      const outerFlame = new THREE.Mesh(outerFlameGeo, outerFlameMat);
      flareFlameGroup.add(outerFlame);

      // Middle bright amber-orange turbulent flame cone
      const midFlameGeo = new THREE.ConeGeometry(2.3, 11.5, 18);
      midFlameGeo.translate(0, 5.75, 0);
      const midFlameMat = new THREE.MeshBasicMaterial({{
        color: 0xf97316,
        transparent: true,
        opacity: 0.85
      }});
      const midFlame = new THREE.Mesh(midFlameGeo, midFlameMat);
      flareFlameGroup.add(midFlame);

      // Inner white-yellow incandescent flame core
      const coreFlameGeo = new THREE.ConeGeometry(1.25, 6.8, 16);
      coreFlameGeo.translate(0, 3.4, 0);
      const coreFlameMat = new THREE.MeshBasicMaterial({{ color: 0xfef08a }});
      const coreFlame = new THREE.Mesh(coreFlameGeo, coreFlameMat);
      flareFlameGroup.add(coreFlame);

      // Warm flare illumination light source
      flareLight = new THREE.PointLight(0xff7b00, isNight ? 2.6 : 1.3, 280);
      flareLight.position.set(0, 8.0, 0);
      flareFlameGroup.add(flareLight);

      flareStackGroup.add(flareFlameGroup);
      terminalGroup.add(flareStackGroup);
    }})();

    // Integrity self-check: supply and return centerlines must not interpenetrate.
    (function checkNonOverlap() {{
      const n = 60;
      let minDist = Infinity;
      for (let i = 0; i <= n; i++) {{
        const p = mainCurve.getPoint(i / n);
        for (let j = 0; j <= n; j++) {{
          minDist = Math.min(minDist, p.distanceTo(recircCurve.getPoint(j / n)));
        }}
      }}
      if (minDist < mainRadius + retRadius) {{
        console.warn('Pipe overlap risk: min centerline distance', minDist.toFixed(2));
      }}
      telemetry.min_centerline_clearance = Number(minDist.toFixed(2));
    }})();

    // Click-to-inspect fluid state at any point on the supply/return pipe
    const raycaster = new THREE.Raycaster();
    const pointer = new THREE.Vector2();
    const mainStations = telemetry.stations;
    const retStations = telemetry.return_stations || telemetry.stations;
    renderer.domElement.addEventListener('click', (event) => {{
      const rect = renderer.domElement.getBoundingClientRect();
      pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
      raycaster.setFromCamera(pointer, camera);
      const hits = raycaster.intersectObjects([mainPipe, recircPipe], false);
      if (hits.length === 0) return;
      const hit = hits[0];
      const isReturn = hit.object.userData.lineType === "return";
      const st = isReturn ? retStations : mainStations;
      const frac = hit.uv ? Math.min(1, Math.max(0, hit.uv.x)) : 0.5;
      const effFrac = isReturn ? (1.0 - frac) : frac;
      const idx = Math.round(effFrac * (st.distance_m.length - 1));
      const lineLabel = isReturn ? "Dönüş Hattı" : "Ana LNG Hattı";
      document.getElementById('pick-body').innerHTML =
        '<div class="hud-row"><span>Hat:</span><span class="hud-val">' + lineLabel + '</span></div>' +
        '<div class="hud-row"><span>Mesafe:</span><span class="hud-val">' + st.distance_m[idx].toFixed(1) + ' m</span></div>' +
        '<div class="hud-row"><span>Sıcaklık:</span><span class="hud-val">' + st.temp_c[idx].toFixed(2) + ' °C</span></div>' +
        '<div class="hud-row"><span>Basınç:</span><span class="hud-val">' + st.pressure_bar[idx].toFixed(3) + ' bar</span></div>' +
        '<div class="hud-row"><span>Psat:</span><span class="hud-val">' + st.vapor_bar[idx].toFixed(3) + ' bar</span></div>' +
        '<div class="hud-row"><span>Marj:</span><span class="hud-val">' + st.margin_bar[idx].toFixed(3) + ' bar</span></div>';
      document.getElementById('pick-panel').style.display = 'block';
    }});

    // Thermal Relief Valves (TRV) skids on Omega Dolphins
    function createTRVSkid(x, z) {{
      const skid = new THREE.Group();
      const b1 = new THREE.Mesh(new THREE.BoxGeometry(0.8, 1.8, 0.8), redValveMat);
      b1.position.set(0, 15.5, 0);
      skid.add(b1);
      const vent = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.2, 4, 8), steelMat);
      vent.position.set(0, 18, 0);
      skid.add(vent);
      skid.position.set(x, 0, z);
      terminalGroup.add(skid);
    }}
    omegaCenters.forEach(cx => createTRVSkid(cx, MAIN_Z + LOOP_EXT + 2));

    // 7. Animated Flow Particles (Main LNG, Recirculation, BOG Vapor & Flare Gas)
    const PARTICLE_COUNT = 80;
    const particleGeo = new THREE.SphereGeometry(0.4, 8, 8);
    const particleMatMain = new THREE.MeshBasicMaterial({{ color: 0xffffff }});
    const particleMatRecirc = new THREE.MeshBasicMaterial({{ color: 0x7ee787 }});
    const particleMatBog = new THREE.MeshBasicMaterial({{ color: 0x38bdf8 }});
    const particleMatFlare = new THREE.MeshBasicMaterial({{ color: 0xfb923c }});

    const mainParticles = [];
    for (let i = 0; i < PARTICLE_COUNT; i++) {{
      const p = new THREE.Mesh(particleGeo, particleMatMain);
      p.userData.t = i / PARTICLE_COUNT;
      mainParticles.push(p);
      scene.add(p);
    }}

    const recircParticles = [];
    for (let i = 0; i < 40; i++) {{
      const p = new THREE.Mesh(particleGeo, particleMatRecirc);
      p.userData.t = i / 40;
      recircParticles.push(p);
      scene.add(p);
    }}

    const bogParticles = [];
    for (let i = 0; i < 28; i++) {{
      const p = new THREE.Mesh(particleGeo, particleMatBog);
      p.userData.t = i / 28;
      bogParticles.push(p);
      scene.add(p);
    }}

    const flareParticles = [];
    for (let i = 0; i < 32; i++) {{
      const p = new THREE.Mesh(particleGeo, particleMatFlare);
      p.userData.t = i / 32;
      flareParticles.push(p);
      scene.add(p);
    }}

    // Camera preset positions
    const views = {{
      overview: {{ cam: new THREE.Vector3(SCENE_CX, OVERVIEW_DIST * 0.35, OVERVIEW_DIST * 0.75), tgt: new THREE.Vector3(SCENE_CX, 10, 0) }},
      lup: {{ cam: new THREE.Vector3(-150, 40, 70), tgt: new THREE.Vector3(-120, 15, 0) }},
      omega: {{ cam: new THREE.Vector3(ROUTE_END * 0.5, 160, 140), tgt: new THREE.Vector3(ROUTE_END * 0.5, 12, 11) }},
      tank: {{ cam: new THREE.Vector3(TANK_X - 180, 140, 310), tgt: new THREE.Vector3(TANK_X + 20, 32, 0) }},
      roof: {{ cam: new THREE.Vector3(TANK_X - 65, 92, 140), tgt: new THREE.Vector3(TANK_X, 58, 65) }},
      flare: {{ cam: new THREE.Vector3(FLARE_X - 115, 95, FLARE_Z + 145), tgt: new THREE.Vector3(FLARE_X - 10, 52, FLARE_Z + 10) }}
    }};

    let targetCamPos = camera.position.clone();
    let targetLookAt = controls.target.clone();
    let isTransitioning = false;

    window.setCameraView = function(viewName, btn) {{
      const v = views[viewName];
      if (!v) return;
      targetCamPos.copy(v.cam);
      targetLookAt.copy(v.tgt);
      isTransitioning = true;
      document.querySelectorAll('.cam-btn').forEach(b => b.classList.remove('active'));
      if (btn) btn.classList.add('active');
    }};

    window.resetControls = function() {{
      setCameraView('overview', document.querySelector('.cam-btn'));
    }};

    // Responsive resize handler
    window.addEventListener('resize', () => {{
      const h = Math.max(1, container.clientHeight);
      camera.aspect = container.clientWidth / h;
      camera.updateProjectionMatrix();
      renderer.setSize(container.clientWidth, h);
    }});

    // Animation Loop
    let clock = new THREE.Clock();

    function animate() {{
      requestAnimationFrame(animate);
      const delta = Math.min(clock.getDelta(), 0.1);
      const time = clock.getElapsedTime();

      // Animate calm sea waves via shader uniform
      waterMat.uniforms.uTime.value = time;

      // Update flow particles along main curve (Forward flow: Ship -> Tank)
      mainParticles.forEach(p => {{
        p.userData.t = ((p.userData.t + delta * 0.12) % 1.0 + 1.0) % 1.0;
        const pos = mainCurve.getPoint(p.userData.t);
        p.position.copy(pos);
      }});

      // Update recirc particles along recirc curve (Reverse flow: Tank -> Jetty)
      recircParticles.forEach(p => {{
        p.userData.t = ((p.userData.t - delta * 0.10) % 1.0 + 1.0) % 1.0;
        const pos = recircCurve.getPoint(p.userData.t);
        p.position.copy(pos);
      }});

      // Update BOG vapor particles flowing to BOG Compressor & Recondenser Station
      if (bogParticleCurve) {{
        bogParticles.forEach(p => {{
          p.userData.t = ((p.userData.t + delta * 0.14) % 1.0 + 1.0) % 1.0;
          p.position.copy(bogParticleCurve.getPoint(p.userData.t));
        }});
      }}

      // Update Flare gas particles flowing through KO Drum V-401 and up the 84m Flare Stack F-401
      if (flareParticleCurve) {{
        flareParticles.forEach(p => {{
          p.userData.t = ((p.userData.t + delta * 0.16) % 1.0 + 1.0) % 1.0;
          p.position.copy(flareParticleCurve.getPoint(p.userData.t));
        }});
      }}

      // Animate 3D Flare Stack Flame & Flickering Illumination
      const flickerY = 1.0 + 0.14 * Math.sin(time * 13.0) + 0.08 * Math.cos(time * 23.0);
      const flickerXZ = 1.0 + 0.08 * Math.cos(time * 17.0);
      flareFlameGroup.scale.set(flickerXZ, flickerY, flickerXZ);
      flareFlameGroup.rotation.z = 0.07 * Math.sin(time * 4.5);
      flareFlameGroup.rotation.x = 0.05 * Math.cos(time * 3.7);
      if (flareLight) {{
        flareLight.intensity = (isNight ? 2.6 : 1.3) + 0.45 * Math.sin(time * 19.0);
      }}

      // Smooth camera interpolation
      if (isTransitioning) {{
        camera.position.lerp(targetCamPos, 0.06);
        controls.target.lerp(targetLookAt, 0.06);
        if (camera.position.distanceTo(targetCamPos) < 0.5) {{
          isTransitioning = false;
        }}
      }}

      controls.update();
      renderer.render(scene, camera);
    }}

    animate();
  </script>
</body>
</html>
"""
    return html

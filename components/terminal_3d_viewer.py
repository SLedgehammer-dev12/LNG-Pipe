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
        ("BOG Gaz Geri Dönüş", "#f0883e"),
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
      <button class="cam-btn" onclick="setCameraView('tank', this)">🏢 Kara Tankı & Pompa</button>
      <button class="cam-btn" onclick="resetControls()">⟲ Sıfırla</button>
    </div>
  </div>

  <script>
    const telemetry = {json.dumps(telemetry)};

    const container = document.getElementById('canvas-container');
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0f18);
    scene.fog = new THREE.FogExp2(0x0a0f18, 0.0007);

    const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.5, 3000);
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
    const theme = "{theme}";
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
            // Keep terminal pad around LNG tank & road level (|z| < 135), natural rolling hills outside
            const padFlatten = Math.min(1.0, Math.max(0.0, (Math.abs(z) - 115.0) / 90.0));
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

      // Compact graded gravel pad under the LNG storage tank & pump station
      const padGeo = new THREE.CylinderGeometry(84, 88, 1.0, 48);
      const padMat = new THREE.MeshStandardMaterial({{
        color: isNight ? 0x3a352f : 0x9a8b78,
        roughness: 0.9
      }});
      const tankPad = new THREE.Mesh(padGeo, padMat);
      tankPad.position.set(TANK_X, 4.7, 0);
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

    // Onshore vehicle access road from the land to the seawall
    (function buildAccessRoad() {{
      const roadMat = new THREE.MeshStandardMaterial({{ color: 0x262b31, roughness: 0.95 }});
      const roadY = 5.2;
      const roadZ = 80.0;
      const roadWidth = 12.0;
      const roadStart = SEAWALL_X;
      const roadEnd = LAND_X + 180.0;
      const roadLen = roadEnd - roadStart;
      const road = new THREE.Mesh(new THREE.BoxGeometry(roadLen, 0.2, roadWidth), roadMat);
      road.position.set((roadStart + roadEnd) / 2, roadY, roadZ);
      road.receiveShadow = true;
      terminalGroup.add(road);
      const dashMat = new THREE.MeshBasicMaterial({{ color: 0xd0d7de }});
      for (let x = roadStart + 6; x < roadEnd; x += 12) {{
        const dash = new THREE.Mesh(new THREE.BoxGeometry(5, 0.05, 0.25), dashMat);
        dash.position.set(x, roadY + 0.12, roadZ);
        terminalGroup.add(dash);
      }}
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

    // Marine Loading Arms (MLAs): LUP dolphin outer edge (-133) -> vessel manifold (-149)
    for (let i = 0; i < 4; i++) {{
      const armGroup = new THREE.Group();
      const zOffset = -15 + i * 10;

      // Base pedestal on LUP deck outer edge (toward vessel)
      const ped = new THREE.Mesh(new THREE.CylinderGeometry(1.2, 1.5, 5, 16), steelMat);
      ped.position.set(-133, 14.5, zOffset);
      armGroup.add(ped);

      // Inboard arm (rises from pedestal)
      const inArm = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.5, 11, 12), yellowMat);
      inArm.position.set(-133, 20, zOffset);
      inArm.rotation.z = 0.35;
      armGroup.add(inArm);

      // Outboard arm reaching across to vessel manifold on jetty side
      const outArm = new THREE.Mesh(new THREE.CylinderGeometry(0.4, 0.4, 17, 12), yellowMat);
      outArm.position.set(-141, 21, zOffset);
      outArm.rotation.z = -0.52;
      armGroup.add(outArm);

      // Connecting nozzle at vessel manifold (ship jetty-facing side x = -149)
      const nozzle = new THREE.Mesh(new THREE.CylinderGeometry(0.45, 0.45, 5, 12), steelMat);
      nozzle.position.set(-149, 15, zOffset);
      nozzle.rotation.z = Math.PI / 2;
      armGroup.add(nozzle);

      terminalGroup.add(armGroup);
    }}

    // ESDV-101 Emergency Shutdown Station on LUP
    const esdvStation = new THREE.Group();
    const esdvValve = new THREE.Mesh(new THREE.BoxGeometry(2.5, 3.5, 2.5), redValveMat);
    esdvValve.position.set(-115, 15, 0);
    const handwheel = new THREE.Mesh(new THREE.TorusGeometry(1.2, 0.2, 8, 16), yellowMat);
    handwheel.rotation.x = Math.PI / 2;
    handwheel.position.set(-115, 17.5, 0);
    esdvStation.add(esdvValve);
    esdvStation.add(handwheel);
    terminalGroup.add(esdvStation);

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

    // 5. Onshore LNG Storage Tank (Full Containment)
    const tankGroup = new THREE.Group();
    // Concrete outer containment wall
    const outerWall = new THREE.Mesh(
      new THREE.CylinderGeometry(60, 60, 56, 64),
      new THREE.MeshStandardMaterial({{ color: 0x8c959f, roughness: 0.85 }})
    );
    outerWall.position.set(TANK_X, 28, 0);
    outerWall.castShadow = true;
    outerWall.receiveShadow = true;
    tankGroup.add(outerWall);

    // Domed (low-profile prestressed-concrete) roof on the outer wall
    const roof = new THREE.Mesh(
      new THREE.CylinderGeometry(62, 50, 10, 64),
      new THREE.MeshStandardMaterial({{ color: 0x9ca3af, roughness: 0.7 }})
    );
    roof.position.set(TANK_X, 63, 0);
    roof.castShadow = true;
    roof.receiveShadow = true;
    tankGroup.add(roof);

    // Bund wall around tank
    const bundGeo = new THREE.CylinderGeometry(76, 76, 9, 48, 1, true);
    const bundMat = new THREE.MeshStandardMaterial({{ color: 0x4a5560, roughness: 0.9, side: THREE.DoubleSide }});
    const bund = new THREE.Mesh(bundGeo, bundMat);
    bund.position.set(TANK_X, 4.5, 0);
    bund.castShadow = true;
    tankGroup.add(bund);

    // Inner 9% Ni steel tank (slightly smaller, inside outer wall)
    const innerTank = new THREE.Mesh(
      new THREE.CylinderGeometry(53, 53, 50, 64),
      new THREE.MeshStandardMaterial({{ color: 0x374151, roughness: 0.4, metalness: 0.85 }})
    );
    innerTank.position.set(TANK_X, 25, 0);
    innerTank.castShadow = true;
    innerTank.receiveShadow = true;
    tankGroup.add(innerTank);

    // LNG liquid level (~85 % of inner tank height)
    const fillH = 50 * 0.85;
    const liquid = new THREE.Mesh(
      new THREE.CylinderGeometry(52, 52, fillH, 64),
      new THREE.MeshStandardMaterial({{ color: 0x1f6feb, roughness: 0.3, transparent: true, opacity: 0.45 }})
    );
    liquid.position.set(TANK_X, fillH / 2, 0);
    tankGroup.add(liquid);
    // Liquid surface ring
    const surface = new THREE.Mesh(
      new THREE.CylinderGeometry(52.1, 52.1, 0.6, 64),
      new THREE.MeshStandardMaterial({{ color: 0x3fb950, roughness: 0.2, metalness: 0.9 }})
    );
    surface.position.set(TANK_X, fillH + 0.3, 0);
    tankGroup.add(surface);

    // Recirculation Pump P-201 Station
    const pumpGeo = new THREE.CylinderGeometry(2, 2.5, 4, 16);
    const pumpMesh = new THREE.Mesh(pumpGeo, new THREE.MeshStandardMaterial({{ color: 0x2ea043, roughness: 0.3 }}));
    pumpMesh.position.set(PUMP_X, 4, -18);
    pumpMesh.castShadow = true;
    tankGroup.add(pumpMesh);

    // Pump motor
    const motorGeo = new THREE.CylinderGeometry(1.5, 1.5, 3.5, 16);
    const motorMesh = new THREE.Mesh(motorGeo, steelMat);
    motorMesh.position.set(PUMP_X, 7.5, -18);
    motorMesh.castShadow = true;
    tankGroup.add(motorMesh);

    terminalGroup.add(tankGroup);

    // 6. PIPELINES: supply route plus a true parallel-offset return route.

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
      pts.push(new THREE.Vector3(ROUTE_END - 20, 14, zOffset));
      pts.push(new THREE.Vector3(ROUTE_END, 8, zOffset));
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

    // Tank inlet extension (follows supply line z)
    const tankLeadInCurve = buildRoundedPath([
      new THREE.Vector3(ROUTE_END, 8, MAIN_Z),
      new THREE.Vector3(ROUTE_END + (TANK_X - ROUTE_END) * 0.4, 18, MAIN_Z),
      new THREE.Vector3(ROUTE_END + (TANK_X - ROUTE_END) * 0.8, 48, MAIN_Z),
      new THREE.Vector3(TANK_X, 52, MAIN_Z)
    ], 3.0);
    const tankLeadIn = new THREE.Mesh(new THREE.TubeGeometry(tankLeadInCurve, 30, mainRadius, 16, false), mainPipeMat);
    tankLeadIn.castShadow = true;
    terminalGroup.add(tankLeadIn);

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

    // Connect pump P-201 to the actual return-route end (parallel offset).
    const returnEndZ = returnPts[returnPts.length - 1].z;
    const pumpConnectCurve = buildRoundedPath([
      new THREE.Vector3(PUMP_X, 4, -18),
      new THREE.Vector3(PUMP_X, 8, returnEndZ - 4),
      new THREE.Vector3(ROUTE_END, 8, returnEndZ)
    ], 2.0);
    const pumpConnect = new THREE.Mesh(new THREE.TubeGeometry(pumpConnectCurve, 16, retRadius, 12, false), recircPipeMat);
    terminalGroup.add(pumpConnect);

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
      const idx = Math.round(frac * (st.distance_m.length - 1));
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

    // 7. Animated Flow Particles
    const PARTICLE_COUNT = 80;
    const particleGeo = new THREE.SphereGeometry(0.4, 8, 8);
    const particleMatMain = new THREE.MeshBasicMaterial({{ color: 0xffffff }});
    const particleMatRecirc = new THREE.MeshBasicMaterial({{ color: 0x7ee787 }});

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

    // Camera preset positions
    const views = {{
      overview: {{ cam: new THREE.Vector3(SCENE_CX, OVERVIEW_DIST * 0.35, OVERVIEW_DIST * 0.75), tgt: new THREE.Vector3(SCENE_CX, 10, 0) }},
      lup: {{ cam: new THREE.Vector3(-150, 40, 70), tgt: new THREE.Vector3(-120, 15, 0) }},
      omega: {{ cam: new THREE.Vector3(ROUTE_END * 0.5, 160, 140), tgt: new THREE.Vector3(ROUTE_END * 0.5, 12, 11) }},
      tank: {{ cam: new THREE.Vector3(TANK_X - 70, 90, 180), tgt: new THREE.Vector3(TANK_X, 30, 0) }}
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
      camera.aspect = container.clientWidth / container.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(container.clientWidth, container.clientHeight);
    }});

    // Animation Loop
    let clock = new THREE.Clock();

    function animate() {{
      requestAnimationFrame(animate);
      const delta = clock.getDelta();
      const time = clock.getElapsedTime();

      // Animate calm sea waves via shader uniform
      waterMat.uniforms.uTime.value = time;

      // Update flow particles along main curve (Forward flow: Ship -> Tank)
      mainParticles.forEach(p => {{
        p.userData.t += delta * 0.12;
        if (p.userData.t > 1.0) p.userData.t = 0.0;
        const pos = mainCurve.getPoint(p.userData.t);
        p.position.copy(pos);
      }});

      // Update recirc particles along recirc curve (Reverse flow: Tank -> Jetty)
      recircParticles.forEach(p => {{
        p.userData.t -= delta * 0.10;
        if (p.userData.t < 0.0) p.userData.t = 1.0;
        const pos = recircCurve.getPoint(p.userData.t);
        p.position.copy(pos);
      }});

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

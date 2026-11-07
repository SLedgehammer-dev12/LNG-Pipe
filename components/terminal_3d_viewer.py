"""Interactive Three.js 3D Marine Terminal Digital Twin for LNG Transfer System."""

import json
from core.solver import PipelineSimulationResults
from core.solver_3d import Simulation3DResults


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
) -> str:
    """Generates a self-contained responsive Three.js 3D WebGL Digital Twin of the LNG Terminal.

    Visualizes:
    - LNG Carrier berthed offshore
    - LUP Dolphin (Loading / Unloading Platform) with Marine Loading Arms (MLAs) & ESDVs
    - APD Dolphins (Approach Trestle Piles)
    - Omega Dolphins with 3D thermal expansion loops & TRVs
    - Onshore Cryogenic LNG Full-Containment Tank
    - P-201 Recirculation Pump and continuous cooldown return line
    - Pipe rack, long-radius elbows, manifold and temperature-gradient pipes
    - Click-to-inspect fluid state along the pipe
    - Camera presets and interactive inspector
    """

    if isinstance(results, Simulation3DResults):
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
        if isinstance(return_results, Simulation3DResults):
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

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xdde8f5, 0.55);
    scene.add(ambientLight);

    const sunLight = new THREE.DirectionalLight(0xfff6e6, 1.1);
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

    const blueFill = new THREE.DirectionalLight(0x388bfd, 0.35);
    blueFill.position.set(150, 80, -100);
    scene.add(blueFill);

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

    // Sea Surface
    const waterGeo = new THREE.PlaneGeometry(4200, 1600, 64, 64);
    const waterMat = new THREE.MeshStandardMaterial({{
      color: 0x061e38,
      roughness: 0.15,
      metalness: 0.85,
      transparent: true,
      opacity: 0.92,
      flatShading: true
    }});
    const waterMesh = new THREE.Mesh(waterGeo, waterMat);
    waterMesh.rotation.x = -Math.PI / 2;
    waterMesh.position.set(ROUTE_END * 0.5, 0, 0);
    waterMesh.receiveShadow = true;
    scene.add(waterMesh);

    // Onshore Ground Terrain
    const landGeo = new THREE.BoxGeometry(450, 30, 800);
    const landMat = new THREE.MeshStandardMaterial({{
      color: 0x1f242d,
      roughness: 0.9,
      metalness: 0.1
    }});
    const landMesh = new THREE.Mesh(landGeo, landMat);
    landMesh.position.set(LAND_X, -10, 0);
    landMesh.receiveShadow = true;
    scene.add(landMesh);

    // Shoreline concrete seawall
    const seawallGeo = new THREE.BoxGeometry(10, 12, 800);
    const seawallMat = new THREE.MeshStandardMaterial({{ color: 0x484f58, roughness: 0.7 }});
    const seawall = new THREE.Mesh(seawallGeo, seawallMat);
    seawall.position.set(SEAWALL_X, 4, 0);
    seawall.castShadow = true;
    seawall.receiveShadow = true;
    scene.add(seawall);

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

    // 1. LUP Dolphin (Loading / Unloading Platform)
    const lupPlatform = createDolphin(-120, 0, 36, 48, 12, 6, "LUP Dolphin");

    // Berthing dolphin (kevale/dofen) right next to the vessel for mooring & manifolds
    const berthDolphin = createDolphin(-162, 0, 24, 34, 10, 4, "Gemi Yanı Dofeni");

    // Marine Loading Arms (MLAs): LUP dolphin outer edge -> vessel manifold
    for (let i = 0; i < 4; i++) {{
      const armGroup = new THREE.Group();
      const zOffset = -15 + i * 10;

      // Base pedestal on LUP deck outer edge (toward vessel)
      const ped = new THREE.Mesh(new THREE.CylinderGeometry(1.2, 1.5, 5, 16), steelMat);
      ped.position.set(-132, 14.5, zOffset);
      armGroup.add(ped);

      // Inboard arm (rises from pedestal)
      const inArm = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.5, 11, 12), yellowMat);
      inArm.position.set(-132, 20, zOffset);
      inArm.rotation.z = 0.35;
      armGroup.add(inArm);

      // Outboard arm reaching across to vessel manifold
      const outArm = new THREE.Mesh(new THREE.CylinderGeometry(0.4, 0.4, 16, 12), yellowMat);
      outArm.position.set(-139, 21, zOffset);
      outArm.rotation.z = -0.5;
      armGroup.add(outArm);

      // Connecting nozzle at vessel manifold (ship side)
      const nozzle = new THREE.Mesh(new THREE.CylinderGeometry(0.45, 0.45, 5, 12), steelMat);
      nozzle.position.set(-148, 13, zOffset);
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

    // 2. LNG Carrier Vessel
    const shipGroup = new THREE.Group();
    // Hull
    const hullGeo = new THREE.BoxGeometry(42, 16, 210);
    const hullMat = new THREE.MeshStandardMaterial({{ color: 0x161b22, roughness: 0.6 }});
    const hull = new THREE.Mesh(hullGeo, hullMat);
    hull.position.set(-150, 4, 0);
    hull.castShadow = true;
    shipGroup.add(hull);

    // Keel / Red Waterline
    const keelGeo = new THREE.BoxGeometry(40, 6, 205);
    const keelMat = new THREE.MeshStandardMaterial({{ color: 0x8b1a1a, roughness: 0.7 }});
    const keel = new THREE.Mesh(keelGeo, keelMat);
    keel.position.set(-150, 0, 0);
    shipGroup.add(keel);

    // Moss Spherical Tanks (4 spherical tanks)
    const tankMat = new THREE.MeshStandardMaterial({{ color: 0x00d2ff, roughness: 0.3, metalness: 0.2 }});
    const tankCovers = new THREE.MeshStandardMaterial({{ color: 0xe6edf3, roughness: 0.5 }});
    for (let k = 0; k < 4; k++) {{
      const zPos = -70 + k * 46;
      const dome = new THREE.Mesh(new THREE.SphereGeometry(14, 32, 24, 0, Math.PI * 2, 0, Math.PI * 0.55), tankCovers);
      dome.position.set(-150, 12, zPos);
      dome.castShadow = true;
      shipGroup.add(dome);
    }}

    // Bridge / Superstructure
    const bridge = new THREE.Mesh(new THREE.BoxGeometry(32, 24, 25), new THREE.MeshStandardMaterial({{ color: 0xf0f6fc }}));
    bridge.position.set(-150, 20, 85);
    bridge.castShadow = true;
    shipGroup.add(bridge);

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
    // Concrete Outer Tank Wall
    const tankWall = new THREE.Mesh(
      new THREE.CylinderGeometry(48, 48, 54, 48),
      new THREE.MeshStandardMaterial({{ color: 0x8c959f, roughness: 0.85 }})
    );
    tankWall.position.set(TANK_X, 27, 0);
    tankWall.castShadow = true;
    tankWall.receiveShadow = true;
    tankGroup.add(tankWall);

    // Spherical Dome Roof
    const roof = new THREE.Mesh(
      new THREE.SphereGeometry(50, 48, 24, 0, Math.PI * 2, 0, Math.PI * 0.28),
      new THREE.MeshStandardMaterial({{ color: 0xd0d7de, roughness: 0.5 }})
    );
    roof.position.set(TANK_X, 36, 0);
    roof.castShadow = true;
    tankGroup.add(roof);

    // Bund wall around tank
    const bundGeo = new THREE.CylinderGeometry(68, 68, 8, 36, 1, true);
    const bundMat = new THREE.MeshStandardMaterial({{ color: 0x57606a, side: THREE.DoubleSide }});
    const bund = new THREE.Mesh(bundGeo, bundMat);
    bund.position.set(TANK_X, 4, 0);
    bund.castShadow = true;
    tankGroup.add(bund);

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

      // Subtle water ripple oscillation
      waterMesh.position.y = Math.sin(time * 0.8) * 0.25;

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

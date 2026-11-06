"""Interactive Three.js 3D Marine Terminal Digital Twin for LNG Transfer System."""

import json
from core.solver import PipelineSimulationResults
from core.solver_3d import Simulation3DResults


def generate_terminal_3d_html(results, height_px: int = 650) -> str:
    """Generates a self-contained responsive Three.js 3D WebGL Digital Twin of the LNG Terminal.

    Visualizes:
    - LNG Carrier berthed offshore
    - LUP Dolphin (Loading / Unloading Platform) with Marine Loading Arms (MLAs) & ESDVs
    - APD Dolphins (Approach Trestle Piles)
    - Omega Dolphins with 3D thermal expansion loops & TRVs
    - Onshore Cryogenic LNG Full-Containment Tank
    - P-201 Recirculation Pump and continuous cooldown return line
    - Animated two-way cryogenic flow particles
    - Camera presets and interactive inspector
    """

    if isinstance(results, Simulation3DResults):
        cfg = results.config.pipeline_config
        t_out = results.bulk_temperature_k[-1] - 273.15
        p_out = results.pressure_pa[-1] / 1e5
        psat_out = results.wall_vapor_pressure_pa[-1] / 1e5
        flashed = results.has_wall_flashed or results.has_bulk_flashed
        flash_m = results.wall_flashing_point_m or results.bulk_flashing_point_m or 0.0
    else:
        cfg = results.config
        t_out = results.outlet_temperature_k - 273.15
        p_out = results.outlet_pressure_pa / 1e5
        psat_out = results.outlet_vapor_pressure_pa / 1e5
        flashed = results.has_flashed
        flash_m = results.flashing_point_m or 0.0

    t_in = cfg.inlet_temperature_k - 273.15
    p_in = cfg.inlet_pressure_pa / 1e5
    m_flow = cfg.mass_flow_rate_kg_s
    margin_min = results.min_flashing_margin_pa / 1e5

    telemetry = {
        "length_m": cfg.length_m,
        "diameter_mm": cfg.inner_diameter_m * 1000.0,
        "mass_flow": m_flow,
        "inlet_t_c": round(t_in, 2),
        "outlet_t_c": round(t_out, 2),
        "inlet_p_bar": round(p_in, 3),
        "outlet_p_bar": round(p_out, 3),
        "outlet_psat_bar": round(psat_out, 3),
        "min_margin_bar": round(margin_min, 3),
        "has_flashed": flashed,
        "flash_point_m": round(flash_m, 1),
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
      <div class="hud-row" style="margin-top:6px; padding-top:6px; border-top:1px dashed rgba(255,255,255,0.1);">
        <span>Parlama Durumu:</span>
        <span class="status-badge {'status-warn' if flashed else 'status-ok'}">
          {'⚠️ PARLAMA' if flashed else '✅ HOMOJEN SIVI'}
        </span>
      </div>
    </div>

    <div class="legend-panel">
      <div style="font-weight:700; color:#8b949e; margin-bottom:6px; text-transform:uppercase; font-size:10px;">Hat Lejantı</div>
      <div class="legend-item">
        <div class="legend-swatch" style="background:#00d2ff; box-shadow:0 0 6px #00d2ff;"></div>
        <span>Ana LNG Boşaltma (24")</span>
      </div>
      <div class="legend-item">
        <div class="legend-swatch" style="background:#39d353; box-shadow:0 0 6px #39d353;"></div>
        <span>Sirkülasyon Soğutma (8")</span>
      </div>
      <div class="legend-item">
        <div class="legend-swatch" style="background:#f0883e;"></div>
        <span>BOG Gaz Geri Dönüş</span>
      </div>
      <div class="legend-item">
        <div class="legend-swatch" style="background:#d2a8ff;"></div>
        <span>Omega Dolfeni & TRV</span>
      </div>
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
    scene.fog = new THREE.FogExp2(0x0a0f18, 0.0018);

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
    const d = 250;
    sunLight.shadow.camera.left = -d;
    sunLight.shadow.camera.right = d;
    sunLight.shadow.camera.top = d;
    sunLight.shadow.camera.bottom = -d;
    scene.add(sunLight);

    const blueFill = new THREE.DirectionalLight(0x388bfd, 0.35);
    blueFill.position.set(150, 80, -100);
    scene.add(blueFill);

    // Sea Surface
    const waterGeo = new THREE.PlaneGeometry(1600, 1600, 64, 64);
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
    waterMesh.position.y = 0;
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
    landMesh.position.set(380, -10, 0);
    landMesh.receiveShadow = true;
    scene.add(landMesh);

    // Shoreline concrete seawall
    const seawallGeo = new THREE.BoxGeometry(10, 12, 800);
    const seawallMat = new THREE.MeshStandardMaterial({{ color: 0x484f58, roughness: 0.7 }});
    const seawall = new THREE.Mesh(seawallGeo, seawallMat);
    seawall.position.set(155, 4, 0);
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

    // Marine Loading Arms (MLAs) on LUP
    for (let i = 0; i < 4; i++) {{
      const armGroup = new THREE.Group();
      const zOffset = -15 + i * 10;
      
      // Base pedestal
      const ped = new THREE.Mesh(new THREE.CylinderGeometry(1.2, 1.5, 5, 16), steelMat);
      ped.position.set(-10, 14.5, zOffset);
      armGroup.add(ped);

      // Inboard arm
      const inArm = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.5, 12, 12), yellowMat);
      inArm.position.set(-10, 21, zOffset);
      inArm.rotation.z = 0.4;
      armGroup.add(inArm);

      // Outboard arm leaning to vessel
      const outArm = new THREE.Mesh(new THREE.CylinderGeometry(0.4, 0.4, 14, 12), yellowMat);
      outArm.position.set(-15, 22, zOffset);
      outArm.rotation.z = -0.7;
      armGroup.add(outArm);

      // Connecting nozzle
      const nozzle = new THREE.Mesh(new THREE.CylinderGeometry(0.45, 0.45, 4, 12), steelMat);
      nozzle.position.set(-20, 17, zOffset);
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

    // 3. APD Dolphins & Trestle Piles along route
    const apdPositions = [-75, -30, 20, 70, 115];
    apdPositions.forEach((x, idx) => {{
      createDolphin(x, 0, 12, 14, 11, 4, `APD-${{idx + 1}}`);
    }});

    // 4. Omega Dolphins with 3D Expansion Loops (Thermal Contraction Absorption)
    // Omega Dolphin 1
    const omegaDolphin1 = createDolphin(-5, 26, 28, 42, 11, 6, "Omega Dolfeni 1");
    // Omega Dolphin 2
    const omegaDolphin2 = createDolphin(95, 26, 28, 42, 11, 6, "Omega Dolfeni 2");

    // 5. Onshore LNG Storage Tank (Full Containment)
    const tankGroup = new THREE.Group();
    // Concrete Outer Tank Wall
    const tankWall = new THREE.Mesh(
      new THREE.CylinderGeometry(48, 48, 54, 48),
      new THREE.MeshStandardMaterial({{ color: 0x8c959f, roughness: 0.85 }})
    );
    tankWall.position.set(300, 27, 0);
    tankWall.castShadow = true;
    tankWall.receiveShadow = true;
    tankGroup.add(tankWall);

    // Spherical Dome Roof
    const roof = new THREE.Mesh(
      new THREE.SphereGeometry(50, 48, 24, 0, Math.PI * 2, 0, Math.PI * 0.28),
      new THREE.MeshStandardMaterial({{ color: 0xd0d7de, roughness: 0.5 }})
    );
    roof.position.set(300, 36, 0);
    roof.castShadow = true;
    tankGroup.add(roof);

    // Bund wall around tank
    const bundGeo = new THREE.CylinderGeometry(68, 68, 8, 36, 1, true);
    const bundMat = new THREE.MeshStandardMaterial({{ color: 0x57606a, side: THREE.DoubleSide }});
    const bund = new THREE.Mesh(bundGeo, bundMat);
    bund.position.set(300, 4, 0);
    bund.castShadow = true;
    tankGroup.add(bund);

    // Recirculation Pump P-201 Station
    const pumpGeo = new THREE.CylinderGeometry(2, 2.5, 4, 16);
    const pumpMesh = new THREE.Mesh(pumpGeo, new THREE.MeshStandardMaterial({{ color: 0x2ea043, roughness: 0.3 }}));
    pumpMesh.position.set(230, 4, -18);
    pumpMesh.castShadow = true;
    tankGroup.add(pumpMesh);

    // Pump motor
    const motorGeo = new THREE.CylinderGeometry(1.5, 1.5, 3.5, 16);
    const motorMesh = new THREE.Mesh(motorGeo, steelMat);
    motorMesh.position.set(230, 7.5, -18);
    motorMesh.castShadow = true;
    tankGroup.add(motorMesh);

    terminalGroup.add(tankGroup);

    // 6. PIPELINES: Main LNG Line (Blue) and Recirculation Line (Green)
    // Construction of 3D Path through Omega Loops
    function buildPipeCurve(zOffset, loopExtZ) {{
      const pts = [
        new THREE.Vector3(-115, 14, zOffset),
        new THREE.Vector3(-20, 14, zOffset),
        // Omega Loop 1
        new THREE.Vector3(-12, 14, zOffset),
        new THREE.Vector3(-10, 14, zOffset + loopExtZ),
        new THREE.Vector3(0, 14, zOffset + loopExtZ + 8),
        new THREE.Vector3(10, 14, zOffset + loopExtZ),
        new THREE.Vector3(12, 14, zOffset),
        new THREE.Vector3(80, 14, zOffset),
        // Omega Loop 2
        new THREE.Vector3(88, 14, zOffset),
        new THREE.Vector3(90, 14, zOffset + loopExtZ),
        new THREE.Vector3(100, 14, zOffset + loopExtZ + 8),
        new THREE.Vector3(110, 14, zOffset + loopExtZ),
        new THREE.Vector3(112, 14, zOffset),
        // Onshore run to tank / pump
        new THREE.Vector3(160, 12, zOffset),
        new THREE.Vector3(220, 8, zOffset)
      ];
      return new THREE.CatmullRomCurve3(pts, false, 'catmullrom', 0.15);
    }}

    const mainCurve = buildPipeCurve(0, 22);
    const mainPipeGeo = new THREE.TubeGeometry(mainCurve, 120, 1.1, 16, false);
    const mainPipe = new THREE.Mesh(mainPipeGeo, pipeMatMain);
    mainPipe.castShadow = true;
    terminalGroup.add(mainPipe);

    // Tank inlet pipe extension
    const tankLeadInCurve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(220, 8, 0),
      new THREE.Vector3(260, 18, 0),
      new THREE.Vector3(285, 48, 0),
      new THREE.Vector3(300, 52, 0)
    ]);
    const tankLeadIn = new THREE.Mesh(new THREE.TubeGeometry(tankLeadInCurve, 30, 1.1, 16, false), pipeMatMain);
    tankLeadIn.castShadow = true;
    terminalGroup.add(tankLeadIn);

    // Recirculation Line (Green - 8" dia)
    const recircCurve = buildPipeCurve(-4, 18);
    const recircPipeGeo = new THREE.TubeGeometry(recircCurve, 120, 0.65, 12, false);
    const recircPipe = new THREE.Mesh(recircPipeGeo, pipeMatRecirc);
    recircPipe.castShadow = true;
    terminalGroup.add(recircPipe);

    // Connect pump P-201 to recirc line
    const pumpConnectCurve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(230, 4, -18),
      new THREE.Vector3(230, 8, -4),
      new THREE.Vector3(220, 8, -4)
    ]);
    const pumpConnect = new THREE.Mesh(new THREE.TubeGeometry(pumpConnectCurve, 16, 0.65, 12, false), pipeMatRecirc);
    terminalGroup.add(pumpConnect);

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
    createTRVSkid(0, 32);
    createTRVSkid(100, 32);

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
      overview: {{ cam: new THREE.Vector3(-180, 110, 240), tgt: new THREE.Vector3(60, 10, 0) }},
      lup: {{ cam: new THREE.Vector3(-150, 40, 70), tgt: new THREE.Vector3(-120, 15, 0) }},
      omega: {{ cam: new THREE.Vector3(0, 50, 100), tgt: new THREE.Vector3(0, 15, 25) }},
      tank: {{ cam: new THREE.Vector3(240, 70, 160), tgt: new THREE.Vector3(300, 30, 0) }}
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

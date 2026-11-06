"""Interactive Three.js WebGL 3D Pipe Cutaway Component for LNG Pipeline Flow."""

import json
from core.solver import PipelineSimulationResults
from core.solver_3d import Simulation3DResults


def generate_3d_pipe_html(results, height_px: int = 560) -> str:
    """Generates a self-contained responsive Three.js 3D WebGL pipeline cutaway visualizer."""

    if isinstance(results, Simulation3DResults):
        cfg = results.config.pipeline_config
        outlet_t_k = results.bulk_temperature_k[-1]
        outlet_psat_pa = results.wall_vapor_pressure_pa[-1]
        flashed = results.has_wall_flashed or results.has_bulk_flashed
        flash_point = results.wall_flashing_point_m or results.bulk_flashing_point_m or 0.0
    else:
        cfg = results.config
        outlet_t_k = results.outlet_temperature_k
        outlet_psat_pa = results.outlet_vapor_pressure_pa
        flashed = results.has_flashed
        flash_point = results.flashing_point_m or 0.0

    inlet_t_c = cfg.inlet_temperature_k - 273.15
    outlet_t_c = outlet_t_k - 273.15
    inlet_p_bar = cfg.inlet_pressure_pa / 1e5
    outlet_p_bar = results.pressure_pa[-1] / 1e5
    outlet_psat_bar = outlet_psat_pa / 1e5
    min_margin_bar = results.min_flashing_margin_pa / 1e5
    flash_ratio = (flash_point / cfg.length_m) if cfg.length_m > 0 else 0.0

    # Build telemetry data payload for client-side JS
    telemetry = {
        "length_m": cfg.length_m,
        "diameter_mm": cfg.inner_diameter_m * 1000.0,
        "mass_flow": cfg.mass_flow_rate_kg_s,
        "inlet_t_c": round(inlet_t_c, 2),
        "outlet_t_c": round(outlet_t_c, 2),
        "inlet_p_bar": round(inlet_p_bar, 3),
        "outlet_p_bar": round(outlet_p_bar, 3),
        "outlet_psat_bar": round(outlet_psat_bar, 3),
        "min_margin_bar": round(min_margin_bar, 3),
        "has_flashed": flashed,
        "flash_point_m": round(flash_point, 1),
        "flash_ratio": round(flash_ratio, 3),
        "heat_ingress_kw": round(results.total_heat_ingress_w / 1000.0, 2),
    }

    html = f"""
<!DOCTYPE html>
<html lang="en">
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
      top: 12px;
      left: 14px;
      background: rgba(14, 17, 23, 0.85);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 8px;
      padding: 12px 16px;
      font-size: 12px;
      pointer-events: auto;
      backdrop-filter: blur(6px);
      box-shadow: 0 4px 16px rgba(0,0,0,0.4);
      max-width: 280px;
    }}
    .hud-title {{
      font-weight: 700;
      font-size: 13px;
      color: #58a6ff;
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .hud-row {{
      display: flex;
      justify-content: space-between;
      margin-bottom: 4px;
      gap: 12px;
      color: #8b949e;
    }}
    .hud-val {{
      color: #f0f6fc;
      font-weight: 600;
      font-family: monospace;
    }}
    .status-badge {{
      display: inline-block;
      padding: 3px 8px;
      border-radius: 4px;
      font-weight: 700;
      font-size: 11px;
      margin-top: 6px;
      text-align: center;
      width: 100%;
    }}
    .status-safe {{
      background: rgba(35, 134, 54, 0.25);
      color: #3fb950;
      border: 1px solid #238636;
    }}
    .status-alert {{
      background: rgba(218, 54, 51, 0.25);
      color: #f85149;
      border: 1px solid #da3633;
    }}
    .controls-panel {{
      position: absolute;
      bottom: 14px;
      left: 14px;
      background: rgba(14, 17, 23, 0.85);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 8px;
      padding: 8px 12px;
      display: flex;
      gap: 8px;
      backdrop-filter: blur(6px);
    }}
    .ctrl-btn {{
      background: #21262d;
      color: #c9d1d9;
      border: 1px solid rgba(255,255,255,0.15);
      border-radius: 4px;
      padding: 5px 10px;
      font-size: 11px;
      cursor: pointer;
      transition: all 0.2s ease;
    }}
    .ctrl-btn:hover {{
      background: #30363d;
      color: #58a6ff;
    }}
    .ctrl-btn.active {{
      background: #1f6feb;
      color: #ffffff;
      border-color: #58a6ff;
    }}
    .legend-panel {{
      position: absolute;
      top: 12px;
      right: 14px;
      background: rgba(14, 17, 23, 0.85);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 8px;
      padding: 10px 14px;
      font-size: 11px;
      backdrop-filter: blur(6px);
    }}
    .legend-item {{
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 4px;
      color: #c9d1d9;
    }}
    .legend-color {{
      width: 12px;
      height: 12px;
      border-radius: 2px;
    }}
  </style>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
</head>
<body>
  <div id="canvas-container">
    <div class="hud-panel">
      <div class="hud-title">⚡ LNG Boru Akış Telemetrisi</div>
      <div class="hud-row"><span>Giriş Sıcaklığı:</span><span class="hud-val">{inlet_t_c:.1f} °C</span></div>
      <div class="hud-row"><span>Çıkış Sıcaklığı:</span><span class="hud-val">{outlet_t_c:.1f} °C</span></div>
      <div class="hud-row"><span>Toplam Basınç:</span><span class="hud-val">{outlet_p_bar:.2f} bar</span></div>
      <div class="hud-row"><span>Doyma Buhar Basıncı:</span><span class="hud-val">{outlet_psat_bar:.2f} bar</span></div>
      <div class="hud-row"><span>Güvenlik Marjı:</span><span class="hud-val">{min_margin_bar:.2f} bar</span></div>
      <div class="hud-row"><span>Toplam Isı Girişi:</span><span class="hud-val">{telemetry['heat_ingress_kw']} kW</span></div>
      {"<div class='status-badge status-safe'>✓ TEK FAZ SIVI AKIŞ (GÜVENLİ)</div>" if not flashed else f"<div class='status-badge status-alert'>⚠️ FLAŞ / KAYNAMA UYARISI ({flash_point:.1f} m)</div>"}
    </div>

    <div class="legend-panel">
      <div style="font-weight:700; color:#8b949e; margin-bottom:6px;">KATMANLAR</div>
      <div class="legend-item"><div class="legend-color" style="background:#1f6feb;"></div>Kriyojenik LNG Akışı</div>
      <div class="legend-item"><div class="legend-color" style="background:#8b949e;"></div>Metal Boru Çeperi (SS304L)</div>
      <div class="legend-item"><div class="legend-color" style="background:#e3b341;"></div>Kriyojenik İzolasyon</div>
      <div class="legend-item"><div class="legend-color" style="background:#f85149;"></div>Flaş / Kavitasyon Noktası</div>
    </div>

    <div class="controls-panel">
      <button class="ctrl-btn active" id="btn-cutaway" onclick="toggleCutaway()">180° Kesit</button>
      <button class="ctrl-btn" id="btn-particles" onclick="toggleParticles()">Akış Parçacıkları</button>
      <button class="ctrl-btn" onclick="resetView()">Bakışı Sıfırla</button>
    </div>
  </div>

  <script>
    const data = {json.dumps(telemetry)};
    let scene, camera, renderer, controls;
    let pipeGroup, fluidMesh, wallMesh, insMesh, flashMarker;
    let particles, particleGeo, particleMat;
    let isCutaway = true;
    let showParticles = true;

    function init() {{
      const container = document.getElementById('canvas-container');
      const width = container.clientWidth;
      const height = container.clientHeight;

      scene = new THREE.Scene();
      scene.background = new THREE.Color(0x0e1117);

      camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
      camera.position.set(0, 18, 38);

      renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
      renderer.setSize(width, height);
      renderer.setPixelRatio(window.devicePixelRatio);
      renderer.shadowMap.enabled = true;
      container.appendChild(renderer.domElement);

      controls = new THREE.OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;
      controls.dampingFactor = 0.08;
      controls.maxPolarAngle = Math.PI / 2 + 0.1;

      // Lights
      const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
      scene.add(ambientLight);

      const dirLight1 = new THREE.DirectionalLight(0xffffff, 0.8);
      dirLight1.position.set(20, 40, 20);
      scene.add(dirLight1);

      const dirLight2 = new THREE.DirectionalLight(0x58a6ff, 0.5);
      dirLight2.position.set(-20, -10, -20);
      scene.add(dirLight2);

      // Grid helper
      const grid = new THREE.GridHelper(50, 50, 0x30363d, 0x161b22);
      grid.position.y = -6;
      scene.add(grid);

      buildPipeline();
      initParticles();

      window.addEventListener('resize', onWindowResize);
      animate();
    }}

    function buildPipeline() {{
      pipeGroup = new THREE.Group();
      scene.add(pipeGroup);

      const length = 32.0;
      const rFluid = 2.4;
      const rWall = 2.7;
      const rIns = 3.6;

      const thetaLength = isCutaway ? Math.PI : Math.PI * 2;

      // 1. Fluid core
      const fluidGeo = new THREE.CylinderGeometry(rFluid, rFluid, length, 32, 32, false, 0, Math.PI * 2);
      // Vertex coloring for thermal gradient along cylinder height (Y-axis)
      const count = fluidGeo.attributes.position.count;
      const colors = [];
      const colCold = new THREE.Color(0x1f6feb); // Cryogenic blue at inlet
      const colWarm = data.has_flashed ? new THREE.Color(0xf85149) : new THREE.Color(0x3fb950); // Warning/Warming

      for (let i = 0; i < count; i++) {{
        const y = fluidGeo.attributes.position.getY(i);
        const norm = (y + length / 2) / length; // 0 (inlet) to 1 (outlet)
        const col = colCold.clone().lerp(colWarm, norm);
        colors.push(col.r, col.g, col.b);
      }}
      fluidGeo.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));

      const fluidMat = new THREE.MeshPhysicalMaterial({{
        vertexColors: true,
        roughness: 0.2,
        transmission: 0.35,
        transparent: true,
        opacity: 0.88,
        reflectivity: 0.9
      }});
      fluidMesh = new THREE.Mesh(fluidGeo, fluidMat);
      fluidMesh.rotation.z = Math.PI / 2;
      pipeGroup.add(fluidMesh);

      // 2. Metal Pipe Wall (semi-transparent cutaway)
      const wallGeo = new THREE.CylinderGeometry(rWall, rWall, length, 32, 1, true, 0, thetaLength);
      const wallMat = new THREE.MeshStandardMaterial({{
        color: 0x8b949e,
        metalness: 0.85,
        roughness: 0.35,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.55
      }});
      wallMesh = new THREE.Mesh(wallGeo, wallMat);
      wallMesh.rotation.z = Math.PI / 2;
      pipeGroup.add(wallMesh);

      // 3. Insulation layer (cutaway shell)
      const insGeo = new THREE.CylinderGeometry(rIns, rIns, length, 32, 1, true, 0, thetaLength);
      const insMat = new THREE.MeshStandardMaterial({{
        color: 0xd29922,
        roughness: 0.8,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.65
      }});
      insMesh = new THREE.Mesh(insGeo, insMat);
      insMesh.rotation.z = Math.PI / 2;
      pipeGroup.add(insMesh);

      // 4. Flashing beacon if flashing occurred
      if (data.has_flashed) {{
        const posX = -length / 2 + (data.flash_ratio * length);
        const ringGeo = new THREE.TorusGeometry(rIns + 0.3, 0.2, 16, 64);
        const ringMat = new THREE.MeshBasicMaterial({{ color: 0xff0000 }});
        flashMarker = new THREE.Mesh(ringGeo, ringMat);
        flashMarker.rotation.y = Math.PI / 2;
        flashMarker.position.x = posX;
        pipeGroup.add(flashMarker);
      }}
    }}

    function initParticles() {{
      const pCount = 200;
      particleGeo = new THREE.BufferGeometry();
      const pos = [];
      const speed = [];

      for (let i = 0; i < pCount; i++) {{
        const x = (Math.random() - 0.5) * 30.0;
        const radius = Math.random() * 2.0;
        const angle = Math.random() * Math.PI * 2;
        const y = Math.cos(angle) * radius;
        const z = Math.sin(angle) * radius;
        pos.push(x, y, z);
        speed.push(0.08 + Math.random() * 0.08);
      }}

      particleGeo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
      particleGeo.userData.speed = speed;

      particleMat = new THREE.PointsMaterial({{
        color: 0xffffff,
        size: 0.35,
        transparent: true,
        opacity: 0.8
      }});

      particles = new THREE.Points(particleGeo, particleMat);
      pipeGroup.add(particles);
    }}

    function toggleCutaway() {{
      isCutaway = !isCutaway;
      const btn = document.getElementById('btn-cutaway');
      btn.innerText = isCutaway ? "180° Kesit" : "Tam Kapalı Boru";
      btn.classList.toggle('active', isCutaway);
      scene.remove(pipeGroup);
      buildPipeline();
      initParticles();
    }}

    function toggleParticles() {{
      showParticles = !showParticles;
      particles.visible = showParticles;
      document.getElementById('btn-particles').classList.toggle('active', showParticles);
    }}

    function resetView() {{
      camera.position.set(0, 18, 38);
      controls.target.set(0, 0, 0);
      controls.update();
    }}

    function onWindowResize() {{
      const container = document.getElementById('canvas-container');
      camera.aspect = container.clientWidth / container.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(container.clientWidth, container.clientHeight);
    }}

    function animate() {{
      requestAnimationFrame(animate);

      // Animate flow particles moving along flow direction (X axis)
      if (particles && showParticles) {{
        const positions = particleGeo.attributes.position.array;
        const speeds = particleGeo.userData.speed;
        for (let i = 0; i < positions.length; i += 3) {{
          positions[i] += speeds[i / 3];
          if (positions[i] > 16.0) {{
            positions[i] = -16.0;
          }}
        }}
        particleGeo.attributes.position.needsUpdate = true;
      }}

      // Pulsate flashing marker if present
      if (flashMarker) {{
        const scale = 1.0 + 0.15 * Math.sin(Date.now() * 0.008);
        flashMarker.scale.set(scale, scale, scale);
      }}

      controls.update();
      renderer.render(scene, camera);
    }}

    window.onload = init;
  </script>
</body>
</html>
"""
    return html

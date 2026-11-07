# Spec: ASME Pipe Schedule, Return Line, and 3D Terminal Upgrades

## Goal
1. Replace free-form pipe diameter/thickness with ASME B36.10 (carbon steel) and
   ASME B36.19 (stainless steel) tables, with manual override.
2. Add user inputs for the recirculation/return line.
3. Upgrade the 3D terminal twin: pipe rack, elbows, manifold, no supply/return
   interpenetration, temperature-gradient coloring, click-to-inspect fluid state,
   dynamic legend.

## Impacted areas
- `core/pipe_schedule.py` (new): ASME dimension data + ID helper.
- `app.py`: sidebar geometry UI, return-line inputs, pass geometry/legend to viewer.
- `components/terminal_3d_viewer.py`: rack, elbows, manifold, mirrored loops,
  gradient texture, raycast inspector, dynamic legend, station telemetry.
- `tests/`: new schedule test; update app smoke test selectors; terminal viewer
  assertions.

## Decisions
- Canonical simulation input stays `diameter_mm` = inner diameter, `wall_thickness_mm`.
  ASME table selection computes `ID = OD - 2*t`.
- Geometry mode radio: "ASME Tablosu" (default) / "Manuel Giriş" (presets default here).
- Return line: manual ID, wall, mass flow; passed to 3D viewer only (no second solve).
- Supply pipe at z=+3, return at z=-3; omega loops mirror (+z vs -z) so they never cross.
- Pipe radius in 3D scales with actual ID so user selection is visible.
- Temperature gradient: 1D CanvasTexture sampled from the simulated station temperatures,
  applied to TubeGeometry (uv.x runs along length).
- Click inspector: Raycaster on tube meshes, uv.x -> nearest station, HUD shows
  T, P, Psat, margin, position. Return line reuses the station profile (labelled).
- Legend built in Python from user inputs (material, DN, schedules, insulation, lines).

## Tests
- `tests/test_pipe_schedule.py`: table sanity, OD>ID, schedules sorted, ID formula.
- `tests/test_app.py`: find widgets by label (not fixed index) to survive new widgets.
- `tests/test_schematic.py` / `test_pipe_3d_viewer.py`: keep working signatures.
- New assertions: terminal HTML contains "pipe rack", "manifold", "gradient",
  raycast/click handler, dynamic legend entries.
- JS syntax check with `node --check` on extracted inline script.

## Out of scope
- A second hydraulic solve for the return line.
- Real ASME B31.3 stress re-check of elbows (geometry only).
- Full ASME schedule rows beyond DN15-DN600.

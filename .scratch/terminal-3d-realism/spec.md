# Spec: 3D Terminal Realism + Thermo/Fluid Cyclic Improvements

## Part A — 3D Visual Realism (`components/terminal_3d_viewer.py`)

### A1. Detailed LNG carrier ship model
- Replace box hull + 4 spheres with a proportional LNG carrier:
  - Hull: long box, red below waterline, grey/white above; keel line; bow/stern taper hint
  - Moss-type spherical cargo tanks: 4–5 spheres on deck, spaced along length
  - Bridge/superstructure at stern (box + windows), mast
  - Deck railing & bollards near manifolds
  - Manifold connection points where MLAs dock
- Position ship berthed at LUP; keep seabed keel clearance.

### A2. Realistic sea surface
- Replace flat plane with animated calm-water shader:
  - Vertex shader: gentle sine/cosine wave displacement (x,z,time), low amplitude, long wavelength
  - Fragment shader: depth gradient (dark deep blue → lighter near shore) + subtle foam at shore/ship hull contact
- Keep OrbitControls and fog consistent.

### A3. Realistic full-containment LNG tank
- Replace single cylinder+dome with:
  - Outer concrete full-containment wall (tall cylinder)
  - Inner 9% Ni steel inner tank (slightly smaller, inside outer)
  - Domed roof (prestressed concrete) + dome insulation hint
  - Liquid level line inside inner tank (animated blue fill at ~85%)
  - Bund wall (dyke) around tank at ground level
  - Tank sits on land behind seawall

### A4. Sync with line length
- Keep `length_scale` / dynamic span; ship, tank, seawall, catwalk, road all scale together.

## Part B — Thermodynamics & Fluid Mechanics cyclic improvements (≥10)

Each is a small, testable cycle (Red → Green → Refactor) in `core/` and `app.py`:

1. **B1** Remove unphysical property floors in `core/fluids.py` (`max(rho,300)`, `max(cp,2000)`, `max(P,50kPa)`). Replace with phase detection + small epsilon clamp; flag sub-triple-point states.
2. **B2** Post-flash two-phase marching in `core/solver.py`: on flashing compute quality from enthalpy, pin T to Tsat(P), use homogeneous two-phase density, stop at methane triple point instead of 1000 Pa floor.
3. **B3** Real-fluid EOS validation guard in `core/fluids.py`: verify CoolProp phase/property validity, surface NaN before marching.
4. **B4** ASME B31.3 displacement stress `S_A` with sustained stress & stress-range factor in `core/mechanics.py` (Eq. 1a/1b), not `1.25*(Sc+Sh)`.
5. **B5** Material properties per selected pipe material in `core/mechanics.py` + `app.py` (Invar α, Al E, 9%Ni S) instead of hard-coded 304L defaults.
6. **B6** Wall-thickness acceptance vs mill undertolerance in `app.py`: compare `0.875*t_nominal >= t_required` or use `t_nominal_recommended`.
7. **B7** Surge acceptance vs design pressure in `app.py`: `peak_line_pressure <= design_pressure` (or 1.33×MAWP), not hard-coded 5 bar.
8. **B8** Two-phase momentum/acceleration pressure-drop term in `core/solver.py` two-phase region.
9. **B9** Heat-ingress radial consistency check between 1D radial_temperatures and 3D wall temperature at shared stations.
10. **B10** Mixture normalization guard + cavitation/NPSH margin linkage in `app.py`/`core/fluids.py`.

## Tests
- `tests/test_terminal_3d_realism.py`: ship parts present, sea shader/waves present, tank inner+outer+bund present.
- Existing `test_schematic.py`, `test_pipe_3d_viewer.py`, `test_app.py` must stay green.
- JS syntax via `node --check`; Streamlit `AppTest` smoke.

## Out of scope
- Real CFD/FIV (handled by senior-mechanical skill separately).
- PDF visual layout changes.

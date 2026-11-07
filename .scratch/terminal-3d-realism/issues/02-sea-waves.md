# Ticket A2 — Realistic sea surface (gradient + calm waves)
Status: ready-for-agent
Scope: components/terminal_3d_viewer.py waterMesh section
Acceptance:
- Water plane replaced by ShaderMaterial with vertex wave displacement (sine/cosine, low amplitude, long wavelength, animated by time)
- Fragment shader depth gradient: dark deep blue → lighter near shore + subtle foam near ship/seawall
- Wave amplitude small (calm sea), wavelength long
- node --check on extracted JS passes
- AppTest smoke: 0 exceptions

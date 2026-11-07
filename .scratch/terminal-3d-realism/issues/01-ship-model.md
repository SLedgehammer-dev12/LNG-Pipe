# Ticket A1 — Detailed LNG carrier ship model
Status: ready-for-agent
Scope: components/terminal_3d_viewer.py shipGroup section (replace box hull + 4 spheres)
Acceptance:
- Hull is a long proportional box with red below waterline, grey/white above, keel line
- 4-5 Moss spherical cargo tanks on deck, spaced along length
- Bridge/superstructure at stern with windows
- Deck railing & bollards near manifolds
- Ship berthed at LUP with keel clearance above seabed
- node --check on extracted JS passes
- tests/test_terminal_3d_realism.py asserts ship parts present

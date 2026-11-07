"""Smoke tests for the Streamlit app entry point (app.py).

Guards against NameError / attribute-mismatch regressions across 1D and 3D
simulation branches. See app.py:426 fix (t_in_c -> inlet_t_c).
"""

from streamlit.testing.v1 import AppTest


def _run_app():
    return AppTest.from_file("app.py", default_timeout=180).run()


def test_default_3d_runs_without_exception():
    at = _run_app()
    assert not at.exception, at.exception[0].value if at.exception else "unknown error"


def test_1d_mode_runs_without_exception():
    at = _run_app()
    at.sidebar.radio[0].set_value("⚡ 1D Sonlu Hacimler (Hızlı Mod)")
    at.run()
    assert not at.exception, at.exception[0].value if at.exception else "unknown error"


def test_critical_low_pressure_preset_runs_without_exception():
    at = _run_app()
    at.sidebar.selectbox[0].set_value("Kritik Düşük Basınç Testi (Çeperde Kaynama Başlangıcı)")
    at.run()
    assert not at.exception, at.exception[0].value if at.exception else "unknown error"

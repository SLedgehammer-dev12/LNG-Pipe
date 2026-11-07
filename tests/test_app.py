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


def _inputs(at):
    return {n.label: n.value for n in at.sidebar.number_input}


def test_preset_applies_geometry_and_manual_mode():
    at = _run_app()
    at.sidebar.selectbox[0].set_value("Marine Jetty Yükleme Hattı (DN250, 500m, 5 bar)")
    at.run()
    assert not at.exception, at.exception[0].value if at.exception else "unknown error"
    assert at.sidebar.radio[1].value == "Manuel Giriş"
    values = _inputs(at)
    assert values["Boru Uzunluğu L"] == 500.0
    assert values["Boru İç Çapı ID"] == 250.0
    assert values["Boru Et Kalınlığı"] == 6.35
    assert values["Hat Eğim Açısı θ (°)"] == 0.0


def test_unit_switch_converts_input_and_output():
    at = _run_app()
    for s in at.sidebar.selectbox:
        if s.label == "Giriş Sıcaklığı T_in birimi":
            s.set_value("°F")
        elif s.label == "Giriş Toplam Basıncı P_in birimi":
            s.set_value("bar (g)")
        elif s.label == "Et Kalınlığı / Schedule (mm)":
            unsched = [opt for opt in s.options if "Schedule'sız" in opt]
            assert unsched, "ASME B36.19 main line must list unscheduled mm wall thicknesses"
            s.set_value(unsched[0])
        elif s.label == "Dönüş Hattı Et Kalınlığı / Schedule (mm)":
            ret_unsched = [opt for opt in s.options if "Schedule'sız" in opt]
            assert ret_unsched, "ASME B36.19 return line must list unscheduled mm wall thicknesses"
            s.set_value(ret_unsched[0])
    at.run()
    assert not at.exception, at.exception[0].value if at.exception else "unknown error"
    assert abs(_inputs(at)["Giriş Sıcaklığı T_in"] - (-258.7)) < 0.2
    # 5.0 bar (abs) -> 5.0 - 1.01325 = 3.98675 bar (g)
    assert abs(_inputs(at)["Giriş Toplam Basıncı P_in"] - 3.98675) < 0.01
    assert any("°F" in m.value for m in at.markdown if "metric-value" in m.value)
    assert any("bar (g)" in m.value for m in at.markdown if "metric-value" in m.value)

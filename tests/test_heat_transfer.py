import pytest
from core.fluids import FluidProperties
from core.heat_transfer import InsulationLayer, PipeThermalModel

def test_radial_heat_transfer_basic():
    # 8-inch Sch 40 (ID ~ 0.2027 m, OD ~ 0.2191 m)
    # 50 mm PIR insulation (k = 0.022 W/m-K)
    layers = [
        InsulationLayer(name="PIR Foam", thickness_m=0.050, thermal_conductivity=0.022)
    ]
    pipe_model = PipeThermalModel(
        inner_diameter_m=0.2027,
        wall_thickness_m=0.0082,
        pipe_conductivity=15.0,  # Stainless steel 304L
        insulation_layers=layers,
        ambient_temperature_k=300.15,  # 27 °C
        wind_speed_m_s=2.0
    )
    
    fluid_props = FluidProperties(
        temperature=112.0,
        pressure=400000.0,
        density=422.0,
        specific_heat=3480.0,
        viscosity=1.15e-4,
        thermal_conductivity=0.185,
        vapor_pressure=105000.0,
        enthalpy=0.0
    )
    
    mass_flow_rate = 25.0  # kg/s
    heat_ingress_w_m, temperatures = pipe_model.calculate_heat_ingress(fluid_props, mass_flow_rate)
    
    # Heat ingress must be positive and within realistic cryogenic range for insulated pipe (15 - 50 W/m)
    assert 10.0 < heat_ingress_w_m < 80.0
    
    # Check monotonic radial temperature profile: fluid < wall_in < wall_out < ins_out < ambient
    assert fluid_props.temperature < temperatures["pipe_inner"]
    assert temperatures["pipe_inner"] <= temperatures["pipe_outer"]
    assert temperatures["pipe_outer"] < temperatures["insulation_outer"]
    assert temperatures["insulation_outer"] < pipe_model.ambient_temperature_k

def test_vacuum_jacketed_versus_standard_insulation():
    # Vacuum jacketed insulation has much lower effective conductivity
    pir_layers = [InsulationLayer(name="PIR", thickness_m=0.08, thermal_conductivity=0.024)]
    vacuum_layers = [InsulationLayer(name="Vacuum MLI", thickness_m=0.02, thermal_conductivity=0.002)]
    
    base_kwargs = dict(
        inner_diameter_m=0.15,
        wall_thickness_m=0.005,
        pipe_conductivity=15.0,
        ambient_temperature_k=295.0,
        wind_speed_m_s=3.0
    )
    
    model_pir = PipeThermalModel(insulation_layers=pir_layers, **base_kwargs)
    model_vacuum = PipeThermalModel(insulation_layers=vacuum_layers, **base_kwargs)
    
    fluid_props = FluidProperties(
        temperature=111.5,
        pressure=300000.0,
        density=423.0,
        specific_heat=3500.0,
        viscosity=1.15e-4,
        thermal_conductivity=0.185,
        vapor_pressure=101325.0,
        enthalpy=0.0
    )
    
    q_pir, _ = model_pir.calculate_heat_ingress(fluid_props, 20.0)
    q_vacuum, _ = model_vacuum.calculate_heat_ingress(fluid_props, 20.0)
    
    # Vacuum jacketed pipe must have significantly lower heat ingress despite smaller thickness
    assert q_vacuum < q_pir
    assert q_vacuum < 15.0


def test_b9_radial_consistency_check():
    # B9: 1D vs 3D wall temperature consistency diagnostic
    from core.heat_transfer import check_radial_consistency
    # Close temperatures -> consistent
    r = check_radial_consistency(112.0, 112.4, "x=100m")
    assert r["consistent"] is True
    assert r["delta_k"] == 0.4
    # Far-apart temperatures -> not consistent
    r2 = check_radial_consistency(112.0, 118.0, "x=200m")
    assert r2["consistent"] is False
    assert r2["relative_delta"] > 0.05


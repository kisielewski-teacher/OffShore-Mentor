"""Symulacje Monte Carlo i testy property-based dla silnika planowania.

W odróżnieniu od tests/test_planner.py (testy jednostkowe konkretnych
przypadków), ten moduł uruchamia planer wielokrotnie na losowo
wygenerowanych/wyfuzzowanych danych wejściowych i sprawdza niezmienniki,
które muszą zachodzić niezależnie od konkretnych wartości.
"""

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from planner.plan import Fault, Vessel, Window, gen_faults, gen_vessels, gen_windows, plan_repairs
from tests._helpers import assert_schedule_invariants as _assert_schedule_invariants


# ------------------------------
#   Monte Carlo: dane z generatorów projektu, wiele nasion/skal
# ------------------------------


def test_monte_carlo_across_seeds_and_scales():
    seeds = range(20)
    scales = [1, 10, 30, 50, 80]
    thresholds = [(0.5, 5.0), (1.5, 15.0), (3.0, 20.0)]

    ran = 0
    for seed in seeds:
        for n in scales:
            for hs_thr, wind_thr in thresholds:
                faults = gen_faults(n=n, seed=seed)
                windows = gen_windows(horizon_days=14, seed=seed)
                vessels = gen_vessels(seed=seed)

                schedule, total_cost = plan_repairs(
                    faults, windows, vessels, hs_thr=hs_thr, wind_thr=wind_thr
                )
                _assert_schedule_invariants(faults, windows, vessels, schedule, total_cost)
                ran += 1

    assert ran == len(list(seeds)) * len(scales) * len(thresholds)


def test_monte_carlo_extreme_fleet_and_horizon_sizes():
    # Duża farma / krótki horyzont / mała flota - kombinacje brzegowe
    for seed in range(5):
        faults = gen_faults(n=80, seed=seed)
        windows = gen_windows(horizon_days=3, seed=seed)
        vessels = gen_vessels(seed=seed)[:1]  # tylko jeden statek

        schedule, total_cost = plan_repairs(faults, windows, vessels)
        _assert_schedule_invariants(faults, windows, vessels, schedule, total_cost)


# ------------------------------
#   Property-based fuzzing niezależny od generatorów projektu
# ------------------------------

_fault_strategy = st.builds(
    Fault,
    fault_id=st.uuids().map(str),
    turbine_id=st.uuids().map(str),
    reported_h=st.integers(min_value=0, max_value=200),
    repair_hours=st.integers(min_value=1, max_value=48),
    priority=st.integers(min_value=1, max_value=3),
    lat=st.floats(min_value=54.5, max_value=55.5, allow_nan=False),
    lon=st.floats(min_value=16.0, max_value=18.0, allow_nan=False),
)

_window_strategy = st.builds(
    Window,
    win_id=st.uuids().map(str),
    start=st.integers(min_value=0, max_value=300),
    end=st.integers(min_value=1, max_value=400),
    hs_m=st.floats(min_value=0.0, max_value=5.0, allow_nan=False),
    wind_ms=st.floats(min_value=0.0, max_value=30.0, allow_nan=False),
).filter(lambda w: w.start < w.end)

_vessel_strategy = st.builds(
    Vessel,
    vessel_id=st.uuids().map(str),
    name=st.text(min_size=1, max_size=10),
    teams=st.integers(min_value=1, max_value=3),
    speed_kn=st.floats(min_value=0.1, max_value=40.0, allow_nan=False),
    day_cost_pln=st.floats(min_value=0.0, max_value=200_000.0, allow_nan=False),
)


@settings(max_examples=60, suppress_health_check=[HealthCheck.too_slow])
@given(
    faults=st.lists(_fault_strategy, min_size=0, max_size=15, unique_by=lambda f: f.fault_id),
    windows=st.lists(_window_strategy, min_size=0, max_size=8, unique_by=lambda w: w.win_id),
    vessels=st.lists(_vessel_strategy, min_size=0, max_size=4, unique_by=lambda v: v.vessel_id),
)
def test_plan_repairs_invariants_hold_for_arbitrary_inputs(faults, windows, vessels):
    schedule, total_cost = plan_repairs(faults, windows, vessels)
    _assert_schedule_invariants(faults, windows, vessels, schedule, total_cost)


@settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow])
@given(
    hs_thr=st.floats(min_value=0.0, max_value=5.0, allow_nan=False),
    wind_thr=st.floats(min_value=0.0, max_value=30.0, allow_nan=False),
    n=st.integers(min_value=0, max_value=60),
    seed=st.integers(min_value=0, max_value=1000),
)
def test_plan_repairs_invariants_hold_for_random_thresholds(hs_thr, wind_thr, n, seed):
    faults = gen_faults(n=n, seed=seed)
    windows = gen_windows(horizon_days=14, seed=seed)
    vessels = gen_vessels(seed=seed)

    schedule, total_cost = plan_repairs(faults, windows, vessels, hs_thr=hs_thr, wind_thr=wind_thr)
    _assert_schedule_invariants(faults, windows, vessels, schedule, total_cost)

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from planner.optimizer import solve_optimal_schedule, unassigned_weighted_count
from planner.plan import Fault, Vessel, Window, gen_faults, gen_vessels, gen_windows, plan_repairs
from tests._helpers import assert_schedule_invariants


def test_single_fault_single_window_single_vessel_is_optimal_and_matches_formula():
    fault = Fault(
        fault_id="F001", turbine_id="T001", reported_h=0,
        repair_hours=4, priority=1, lat=55.0, lon=16.9,
    )
    window = Window(win_id="W001", start=0, end=100, hs_m=0.5, wind_ms=5.0)
    vessel = Vessel(vessel_id="V01", name="Test Vessel", teams=1, speed_kn=12.0, day_cost_pln=1000.0)

    schedule, cost, meta = solve_optimal_schedule([fault], [window], [vessel])

    assert meta["status"] == "optimal"
    assert len(schedule) == 1
    row = schedule[0]
    assert row["start"] is not None
    assert row["vessel_id"] == "V01"
    assert cost > 0
    assert row["cost_pln"] == pytest.approx(cost)


def test_optimal_picks_cheaper_vessel_where_greedy_heuristic_does_not():
    # Statek droższy jest PIERWSZY na liście - plan_repairs (first-fit) go
    # wybierze, solver optymalny powinien wybrać tańszy (ten sam efekt: obie
    # naprawy dają się wykonać w tym samym oknie, więc jedyna różnica to koszt).
    fault = Fault(
        fault_id="F001", turbine_id="T001", reported_h=0,
        repair_hours=4, priority=1, lat=55.0, lon=16.9,
    )
    window = Window(win_id="W001", start=0, end=100, hs_m=0.5, wind_ms=5.0)
    expensive = Vessel(vessel_id="V_EXP", name="Expensive", teams=1, speed_kn=12.0, day_cost_pln=100_000.0)
    cheap = Vessel(vessel_id="V_CHEAP", name="Cheap", teams=1, speed_kn=12.0, day_cost_pln=1_000.0)

    sched_h, cost_h = plan_repairs([fault], [window], [expensive, cheap])
    sched_o, cost_o, meta = solve_optimal_schedule([fault], [window], [expensive, cheap])

    assert sched_h[0]["vessel_id"] == "V_EXP"
    assert meta["status"] == "optimal"
    assert sched_o[0]["vessel_id"] == "V_CHEAP"
    assert cost_o < cost_h


def test_no_candidates_short_circuits_without_calling_solver():
    faults = gen_faults(n=5, seed=1)
    windows = gen_windows(seed=1)
    vessels = gen_vessels()

    schedule, cost, meta = solve_optimal_schedule(
        faults, windows, vessels, hs_thr=0.0, wind_thr=0.0
    )

    assert meta["status"] == "no_candidates"
    assert cost == 0.0
    assert meta["runtime_s"] < 0.5
    assert all(row["start"] is None for row in schedule)


def test_no_faults_returns_empty_schedule():
    schedule, cost, meta = solve_optimal_schedule([], gen_windows(), gen_vessels())
    assert schedule == []
    assert cost == 0.0
    assert meta["status"] == "no_candidates"


def test_no_vessels_leaves_everything_unplanned():
    faults = gen_faults(n=5, seed=1)
    windows = gen_windows(seed=1)
    schedule, cost, meta = solve_optimal_schedule(faults, windows, vessels=[])
    assert cost == 0.0
    assert meta["status"] == "no_candidates"
    assert all(row["start"] is None for row in schedule)


def test_schedule_shape_matches_plan_repairs_row_keys():
    faults = gen_faults(n=3, seed=2)
    windows = gen_windows(seed=2)
    vessels = gen_vessels()

    sched_h, _ = plan_repairs(faults, windows, vessels)
    sched_o, _, _ = solve_optimal_schedule(faults, windows, vessels)

    assert set(sched_h[0].keys()) <= set(sched_o[0].keys()) | {"note"}
    for row in sched_o:
        assert "fault_id" in row and "start" in row and "cost_pln" in row


def test_unassigned_weighted_count_sums_priority_weights():
    faults = [
        Fault(fault_id="A", turbine_id="TA", reported_h=0, repair_hours=4, priority=1, lat=55.0, lon=16.9),
        Fault(fault_id="B", turbine_id="TB", reported_h=0, repair_hours=4, priority=3, lat=55.0, lon=16.9),
    ]
    schedule = [
        {"fault_id": "A", "start": None},
        {"fault_id": "B", "start": 0},
    ]
    # priority 1 -> weight 3 (see planner.optimizer._URGENCY_WEIGHT); B is assigned so contributes 0
    assert unassigned_weighted_count(faults, schedule) == 3


# ------------------------------
#   Niezmienniki na małych, losowych scenariuszach (solver dowodzi optimum)
# ------------------------------


@settings(max_examples=15, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(seed=st.integers(min_value=0, max_value=200), n=st.integers(min_value=0, max_value=8))
def test_optimal_schedule_satisfies_generic_invariants(seed, n):
    faults = gen_faults(n=n, seed=seed)
    windows = gen_windows(horizon_days=5, seed=seed)
    vessels = gen_vessels()

    schedule, cost, meta = solve_optimal_schedule(faults, windows, vessels, time_limit_s=3.0)
    assert_schedule_invariants(faults, windows, vessels, schedule, cost)
    assert meta["status"] in ("optimal", "time_limit", "no_candidates")


@pytest.mark.parametrize("n", [3, 5, 8, 12])
def test_optimal_is_never_worse_than_heuristic_on_combined_objective(n):
    # Jedyny dowodliwy invariant porównawczy: gdy solver DOWIÓDŁ optimum,
    # połączony cel wagowy (BIG*unassigned_weighted + koszt) dla optimum musi
    # być <= niż dla heurystyki. NIE testujemy cost_opt <= cost_heurystyka w
    # izolacji - to nieprawda w ogólności (optimum może zaakceptować wyższy
    # koszt w zamian za mniej nieobsłużonych pilnych usterek).
    faults = gen_faults(n=n, seed=100 + n)
    windows = gen_windows(horizon_days=5, seed=100 + n)
    vessels = gen_vessels()

    sched_h, cost_h = plan_repairs(faults, windows, vessels)
    sched_o, cost_o, meta = solve_optimal_schedule(faults, windows, vessels, time_limit_s=5.0)

    if meta["status"] != "optimal":
        pytest.skip("solver nie dowiódł optimum w limicie czasu dla tej instancji")

    big_m = meta["big_m"]
    obj_h = big_m * unassigned_weighted_count(faults, sched_h) + cost_h
    obj_o = big_m * unassigned_weighted_count(faults, sched_o) + cost_o

    assert obj_o <= obj_h + 1e-6
    assert unassigned_weighted_count(faults, sched_o) <= unassigned_weighted_count(faults, sched_h)

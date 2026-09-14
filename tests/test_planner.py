import math

import pytest

from planner.plan import (
    Fault,
    Vessel,
    Window,
    feasible,
    gen_faults,
    gen_vessels,
    gen_windows,
    haversine,
    plan_repairs,
    transit_time_km,
)


# ------------------------------
#   haversine
# ------------------------------


def test_haversine_zero_distance_for_same_point():
    assert haversine(54.58, 16.86, 54.58, 16.86) == pytest.approx(0.0, abs=1e-9)


def test_haversine_is_symmetric():
    a = haversine(54.58, 16.86, 55.0, 17.1)
    b = haversine(55.0, 17.1, 54.58, 16.86)
    assert a == pytest.approx(b)


def test_haversine_matches_known_reference_distance():
    # Warszawa -> Gdańsk, great-circle reference ~ 283.5 km
    dist = haversine(52.2297, 21.0122, 54.3520, 18.6466)
    assert dist == pytest.approx(283.5, rel=0.02)


# ------------------------------
#   transit_time_km
# ------------------------------


def test_transit_time_km_basic():
    # 18.52 km at 10 knots (18.52 km/h) => 1h
    assert transit_time_km(18.52, 10.0) == pytest.approx(1.0, rel=1e-3)


def test_transit_time_km_zero_speed_is_infinite():
    assert transit_time_km(100.0, 0.0) == float("inf")


def test_transit_time_km_negative_speed_is_infinite():
    assert transit_time_km(100.0, -5.0) == float("inf")


def test_transit_time_km_zero_distance_is_zero():
    assert transit_time_km(0.0, 12.0) == pytest.approx(0.0)


# ------------------------------
#   feasible
# ------------------------------


def test_feasible_within_thresholds():
    w = Window(win_id="W1", start=0, end=10, hs_m=1.0, wind_ms=10.0)
    assert feasible(w, hs_thr=1.5, wind_thr=15.0) is True


def test_feasible_hs_exceeds_threshold():
    w = Window(win_id="W1", start=0, end=10, hs_m=2.0, wind_ms=10.0)
    assert feasible(w, hs_thr=1.5, wind_thr=15.0) is False


def test_feasible_wind_exceeds_threshold():
    w = Window(win_id="W1", start=0, end=10, hs_m=1.0, wind_ms=20.0)
    assert feasible(w, hs_thr=1.5, wind_thr=15.0) is False


def test_feasible_exact_threshold_is_ok():
    w = Window(win_id="W1", start=0, end=10, hs_m=1.5, wind_ms=15.0)
    assert feasible(w, hs_thr=1.5, wind_thr=15.0) is True


# ------------------------------
#   generators
# ------------------------------


def test_gen_faults_count_and_uniqueness():
    faults = gen_faults(n=25, seed=1)
    assert len(faults) == 25
    assert len({f.fault_id for f in faults}) == 25
    assert len({f.turbine_id for f in faults}) == 25


def test_gen_faults_fields_within_expected_ranges():
    faults = gen_faults(n=50, seed=7)
    for f in faults:
        assert 0 <= f.reported_h <= 48
        assert f.repair_hours in {4, 6, 8, 12, 16}
        assert f.priority in {1, 2, 3}
        assert f.lat >= 54.80  # always offshore, per module contract


def test_gen_faults_is_deterministic_for_same_seed():
    a = gen_faults(n=10, seed=42)
    b = gen_faults(n=10, seed=42)
    assert a == b


def test_gen_faults_different_seeds_diverge():
    a = gen_faults(n=10, seed=1)
    b = gen_faults(n=10, seed=2)
    assert a != b


def test_gen_faults_zero_count():
    assert gen_faults(n=0) == []


def test_gen_windows_are_sorted_and_non_overlapping():
    windows = gen_windows(horizon_days=14, seed=1)
    assert len(windows) > 0
    for prev, cur in zip(windows, windows[1:]):
        assert prev.end <= cur.start

    for w in windows:
        assert w.start < w.end
        assert w.end <= 14 * 24
        assert 0.3 <= w.hs_m <= 1.4
        assert 3.0 <= w.wind_ms <= 14.0


def test_gen_vessels_returns_three_named_vessels():
    vessels = gen_vessels()
    assert len(vessels) == 3
    ids = {v.vessel_id for v in vessels}
    assert ids == {"V01", "V02", "V03"}
    for v in vessels:
        assert v.speed_kn > 0
        assert v.day_cost_pln > 0
        assert v.teams >= 1


def test_gen_vessels_default_count_matches_explicit_count_3():
    assert gen_vessels() == gen_vessels(count=3)


def test_gen_vessels_count_1_returns_prefix():
    vessels = gen_vessels(count=1)
    assert len(vessels) == 1
    assert vessels[0].vessel_id == "V01"


def test_gen_vessels_count_above_3_generates_extra_vessels_with_unique_ids():
    vessels = gen_vessels(count=5)
    assert len(vessels) == 5
    ids = [v.vessel_id for v in vessels]
    assert len(set(ids)) == 5
    assert ids[:3] == ["V01", "V02", "V03"]
    for v in vessels:
        assert v.speed_kn > 0
        assert v.day_cost_pln > 0


def test_gen_faults_arrival_horizon_h_none_matches_default_behavior():
    assert gen_faults(n=20, seed=5) == gen_faults(n=20, seed=5, arrival_horizon_h=None)


def test_gen_faults_arrival_horizon_h_bounds_reported_h():
    faults = gen_faults(n=100, seed=9, arrival_horizon_h=72)
    assert all(f.reported_h <= 71 for f in faults)


# ------------------------------
#   plan_repairs
# ------------------------------


def test_plan_repairs_no_faults_returns_empty_schedule():
    schedule, cost = plan_repairs([], gen_windows(), gen_vessels())
    assert schedule == []
    assert cost == 0.0


def test_plan_repairs_no_vessels_leaves_everything_unplanned():
    faults = gen_faults(n=5, seed=1)
    windows = gen_windows(seed=1)
    schedule, cost = plan_repairs(faults, windows, vessels=[])
    assert len(schedule) == 5
    assert cost == 0.0
    assert all(row["start"] is None for row in schedule)


def test_plan_repairs_no_windows_leaves_everything_unplanned():
    faults = gen_faults(n=5, seed=1)
    schedule, cost = plan_repairs(faults, windows=[], vessels=gen_vessels())
    assert len(schedule) == 5
    assert cost == 0.0
    assert all(row["start"] is None for row in schedule)


def test_plan_repairs_impossible_weather_thresholds_leave_all_unplanned():
    faults = gen_faults(n=10, seed=3)
    windows = gen_windows(seed=3)
    vessels = gen_vessels()
    # thresholds below any generated hs_m/wind_ms => no window ever feasible
    schedule, cost = plan_repairs(faults, windows, vessels, hs_thr=0.0, wind_thr=0.0)
    assert cost == 0.0
    assert all(row["start"] is None for row in schedule)


def test_plan_repairs_single_fault_single_window_gets_scheduled():
    fault = Fault(
        fault_id="F001",
        turbine_id="T001",
        reported_h=0,
        repair_hours=4,
        priority=1,
        lat=55.0,
        lon=16.9,
    )
    window = Window(win_id="W001", start=0, end=100, hs_m=0.5, wind_ms=5.0)
    vessel = Vessel(vessel_id="V01", name="Test Vessel", teams=1, speed_kn=12.0, day_cost_pln=1000.0)

    schedule, cost = plan_repairs([fault], [window], [vessel])

    assert len(schedule) == 1
    row = schedule[0]
    assert row["start"] is not None
    assert row["end"] > row["start"]
    assert row["vessel_id"] == "V01"
    assert cost > 0
    assert row["cost_pln"] == pytest.approx(cost)


def test_plan_repairs_window_too_short_leaves_fault_unplanned():
    fault = Fault(
        fault_id="F001",
        turbine_id="T001",
        reported_h=0,
        repair_hours=16,
        priority=1,
        lat=55.0,
        lon=16.9,
    )
    # Window barely covers repair time but not the round-trip transit
    window = Window(win_id="W001", start=0, end=17, hs_m=0.5, wind_ms=5.0)
    vessel = Vessel(vessel_id="V01", name="Test Vessel", teams=1, speed_kn=12.0, day_cost_pln=1000.0)

    schedule, cost = plan_repairs([fault], [window], [vessel])

    assert schedule[0]["start"] is None
    assert cost == 0.0


def test_plan_repairs_higher_priority_wins_contended_slot():
    # Two faults at the same turbine location competing for the only
    # window/vessel slot big enough for just one of them.
    low_prio = Fault(
        fault_id="F_LOW", turbine_id="T1", reported_h=0, repair_hours=4,
        priority=3, lat=55.0, lon=16.9,
    )
    high_prio = Fault(
        fault_id="F_HIGH", turbine_id="T2", reported_h=0, repair_hours=4,
        priority=1, lat=55.0, lon=16.9,
    )
    window = Window(win_id="W001", start=0, end=10, hs_m=0.5, wind_ms=5.0)
    vessel = Vessel(vessel_id="V01", name="Only Vessel", teams=1, speed_kn=100.0, day_cost_pln=1000.0)

    schedule, _ = plan_repairs([low_prio, high_prio], [window], [vessel])
    by_id = {row["fault_id"]: row for row in schedule}

    assert by_id["F_HIGH"]["start"] is not None
    assert by_id["F_LOW"]["start"] is None


def test_plan_repairs_does_not_double_book_a_vessel():
    faults = gen_faults(n=40, seed=11)
    windows = gen_windows(horizon_days=14, seed=11)
    vessels = gen_vessels()

    schedule, _ = plan_repairs(faults, windows, vessels)

    by_vessel = {}
    for row in schedule:
        if row["start"] is None:
            continue
        by_vessel.setdefault(row["vessel_id"], []).append((row["start"], row["end"]))

    for vessel_id, intervals in by_vessel.items():
        intervals.sort()
        for (s1, e1), (s2, e2) in zip(intervals, intervals[1:]):
            assert e1 <= s2, f"Vessel {vessel_id} double-booked: {(s1, e1)} overlaps {(s2, e2)}"


def test_plan_repairs_total_cost_equals_sum_of_row_costs():
    faults = gen_faults(n=30, seed=5)
    windows = gen_windows(seed=5)
    vessels = gen_vessels()

    schedule, total_cost = plan_repairs(faults, windows, vessels)

    assert total_cost == pytest.approx(sum(row["cost_pln"] for row in schedule))
    assert total_cost >= 0


def test_plan_repairs_returns_one_row_per_fault():
    faults = gen_faults(n=37, seed=9)
    windows = gen_windows(seed=9)
    vessels = gen_vessels()

    schedule, _ = plan_repairs(faults, windows, vessels)

    assert len(schedule) == len(faults)
    assert {row["fault_id"] for row in schedule} == {f.fault_id for f in faults}


def test_plan_repairs_usage_none_default_matches_no_usage_arg():
    faults = gen_faults(n=20, seed=4)
    windows = gen_windows(seed=4)
    vessels = gen_vessels()

    sched_a, cost_a = plan_repairs(faults, windows, vessels)
    sched_b, cost_b = plan_repairs(faults, windows, vessels, usage=None)

    assert sched_a == sched_b
    assert cost_a == cost_b


def test_plan_repairs_carried_usage_blocks_reuse_of_reserved_hours():
    # plan_repairs próbuje tylko jednego, ustalonego slotu na okno
    # (start = max(window.start, fault.reported_h)) - nie przeszukuje okna w
    # poszukiwaniu wolnego fragmentu. Żeby zaobserwować efekt przekazanego
    # `usage`, potrzebne jest drugie okno zaczynające się już po
    # zarezerwowanych godzinach.
    vessel = Vessel(vessel_id="V01", name="Only Vessel", teams=1, speed_kn=100.0, day_cost_pln=1000.0)
    window_blocked = Window(win_id="W_BLOCKED", start=0, end=50, hs_m=0.5, wind_ms=5.0)
    window_free = Window(win_id="W_FREE", start=10, end=50, hs_m=0.5, wind_ms=5.0)
    fault = Fault(fault_id="F001", turbine_id="T001", reported_h=0, repair_hours=4, priority=1, lat=55.0, lon=16.9)

    usage = {"V01": [0] * 51}
    # pre-reserve hours 0-9, jak gdyby zostały zajęte poprzedniego dnia symulacji
    for h in range(0, 10):
        usage["V01"][h] = 1

    schedule, _ = plan_repairs([fault], [window_blocked, window_free], [vessel], usage=usage)

    row = schedule[0]
    assert row["start"] is not None
    assert row["win_id"] == "W_FREE"
    assert row["start"] >= 10, "plan_repairs powinien pominąć godziny już zarezerwowane w przekazanym `usage`"


def test_plan_repairs_carried_usage_leaves_fault_unplanned_if_only_window_is_fully_reserved():
    vessel = Vessel(vessel_id="V01", name="Only Vessel", teams=1, speed_kn=100.0, day_cost_pln=1000.0)
    window = Window(win_id="W001", start=0, end=50, hs_m=0.5, wind_ms=5.0)
    fault = Fault(fault_id="F001", turbine_id="T001", reported_h=0, repair_hours=4, priority=1, lat=55.0, lon=16.9)

    usage = {"V01": [1] * 51}  # statek zajęty przez cały horyzont

    schedule, cost = plan_repairs([fault], [window], [vessel], usage=usage)

    assert schedule[0]["start"] is None
    assert cost == 0.0


def test_plan_repairs_mutates_usage_in_place():
    vessel = Vessel(vessel_id="V01", name="Only Vessel", teams=1, speed_kn=100.0, day_cost_pln=1000.0)
    window = Window(win_id="W001", start=0, end=50, hs_m=0.5, wind_ms=5.0)
    fault = Fault(fault_id="F001", turbine_id="T001", reported_h=0, repair_hours=4, priority=1, lat=55.0, lon=16.9)

    usage = {}
    schedule, _ = plan_repairs([fault], [window], [vessel], usage=usage)

    row = schedule[0]
    assert "V01" in usage
    assert all(usage["V01"][h] == 1 for h in range(row["start"], row["end"]))


def test_plan_repairs_assigned_rows_stay_within_their_window():
    faults = gen_faults(n=30, seed=13)
    windows = gen_windows(seed=13)
    vessels = gen_vessels()
    windows_by_id = {w.win_id: w for w in windows}

    schedule, _ = plan_repairs(faults, windows, vessels)

    for row in schedule:
        if row["start"] is None:
            continue
        w = windows_by_id[row["win_id"]]
        assert w.start <= row["start"]
        assert row["end"] <= w.end
        assert not math.isnan(row["cost_pln"])

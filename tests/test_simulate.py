import pytest

from planner.plan import gen_faults, gen_vessels, gen_windows
from planner.simulate import run_rolling_simulation, snapshots_to_dataframe
from tests._helpers import assert_no_vessel_overlap


# ------------------------------
#   Regresja: gen_faults(arrival_horizon_h=...) - błąd inclusive/exclusive
# ------------------------------


def test_gen_faults_arrival_horizon_h_upper_bound_is_exclusive_of_horizon():
    horizon_h = 240  # 10 dni
    faults = gen_faults(n=200, seed=1, arrival_horizon_h=horizon_h)
    assert max(f.reported_h for f in faults) <= horizon_h - 1

    # każda usterka musi zostać "wchłonięta" przez jakiś dzień symulacji
    horizon_days = horizon_h // 24
    for f in faults:
        day = f.reported_h // 24
        assert 0 <= day < horizon_days


def test_gen_faults_arrival_horizon_h_none_keeps_old_behavior():
    a = gen_faults(n=30, seed=42)
    b = gen_faults(n=30, seed=42, arrival_horizon_h=None)
    assert a == b
    assert all(f.reported_h <= 48 for f in a)


# ------------------------------
#   run_rolling_simulation - niezmienniki
# ------------------------------


def _run(n_faults=60, horizon_days=10, seed=7, vessel_count=3):
    faults = gen_faults(n=n_faults, seed=seed, arrival_horizon_h=horizon_days * 24)
    windows = gen_windows(horizon_days=horizon_days, seed=seed)
    vessels = gen_vessels(count=vessel_count)
    return run_rolling_simulation(faults, windows, vessels, horizon_days), faults


def test_backlog_never_negative():
    (snapshots, _df), _faults = _run()
    assert all(s.backlog_after >= 0 for s in snapshots)


def test_resolved_sum_never_exceeds_total_faults_generated():
    (snapshots, _df), faults = _run()
    assert sum(s.resolved_today for s in snapshots) <= len(faults)


def test_cumulative_cost_nondecreasing_and_matches_committed_rows():
    (snapshots, df), _faults = _run()
    costs = [s.cumulative_cost for s in snapshots]
    assert all(b >= a - 1e-9 for a, b in zip(costs, costs[1:]))
    assert costs[-1] == pytest.approx(df["cost_pln"].sum())


def test_snapshot_count_equals_horizon_days():
    horizon_days = 12
    (snapshots, _df), _faults = _run(horizon_days=horizon_days)
    assert len(snapshots) == horizon_days


def test_no_vessel_double_booked_across_entire_simulation():
    (_snapshots, df), _faults = _run(n_faults=120, horizon_days=14, seed=3)

    by_vessel = {}
    for _, row in df.iterrows():
        by_vessel.setdefault(row["vessel_id"], []).append((row["start"], row["end"]))

    assert_no_vessel_overlap(by_vessel)


def test_empty_horizon_inputs_return_schema_correct_empty_dataframe():
    (snapshots, df), _faults = _run(n_faults=0, horizon_days=3, vessel_count=1)
    assert len(snapshots) == 3
    assert list(df.columns) == [
        "fault_id", "turbine_id", "start", "end", "vessel_id", "vessel_name",
        "cost_pln", "priority", "distance_km", "transit_h", "win_id", "day",
    ]
    assert df.empty


def test_on_day_complete_callback_invoked_once_per_day_in_order():
    horizon_days = 6
    faults = gen_faults(n=20, seed=4, arrival_horizon_h=horizon_days * 24)
    windows = gen_windows(horizon_days=horizon_days, seed=4)
    vessels = gen_vessels()

    calls = []
    run_rolling_simulation(
        faults, windows, vessels, horizon_days,
        on_day_complete=lambda day, total: calls.append((day, total)),
    )

    assert calls == [(d, horizon_days) for d in range(horizon_days)]


def test_on_day_complete_defaults_to_none_without_error():
    # brak callbacku (domyślne None) musi zachowywać się identycznie jak dotychczas
    (snapshots, df), _faults = _run(horizon_days=5)
    assert len(snapshots) == 5


def test_snapshots_to_dataframe_shape():
    (snapshots, _df), _faults = _run(horizon_days=5)
    df_snap = snapshots_to_dataframe(snapshots)
    assert len(df_snap) == 5
    assert set(df_snap.columns) == {
        "day", "new_faults", "resolved_today", "backlog_after", "cost_today", "cumulative_cost",
    }


# ------------------------------
#   Storytelling smoke test: mała flota -> backlog rośnie, duża -> nie
# ------------------------------


def test_small_fleet_backlog_grows_large_fleet_backlog_shrinks():
    horizon_days = 20
    faults = gen_faults(n=250, seed=11, arrival_horizon_h=horizon_days * 24)
    windows = gen_windows(horizon_days=horizon_days, seed=11)

    snaps_small, _ = run_rolling_simulation(
        faults, windows, gen_vessels(count=1), horizon_days
    )
    snaps_large, _ = run_rolling_simulation(
        faults, windows, gen_vessels(count=4), horizon_days
    )

    mid = horizon_days // 2
    small_backlog_growth = snaps_small[-1].backlog_after - snaps_small[mid].backlog_after
    large_backlog_final = snaps_large[-1].backlog_after

    assert small_backlog_growth > 0, "z 1 statkiem backlog powinien rosnąć w drugiej połowie horyzontu"
    assert large_backlog_final < snaps_small[-1].backlog_after, (
        "flota 4 statków powinna kończyć z mniejszym backlogiem niż flota 1 statku"
    )

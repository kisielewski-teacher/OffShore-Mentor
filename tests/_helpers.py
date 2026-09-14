"""Wspólne pomocnicze asercje niezmienników harmonogramu, reużywane przez
testy heurystyki (test_simulation.py), solvera optymalnego (test_optimizer.py)
i symulacji wielodniowej (test_simulate.py).
"""

import math

import pytest


def assert_schedule_invariants(faults, windows, vessels, schedule, total_cost):
    """Sprawdza niezmienniki, które muszą zachodzić dla KAŻDEGO poprawnego
    harmonogramu (niezależnie od tego, czy powstał z heurystyki czy solvera):
    jedno zadanie na usterkę, spójność kosztów, brak nakładania się rejsów
    tego samego statku, zgodność z oknem pogodowym.
    """
    windows_by_id = {w.win_id: w for w in windows}

    assert len(schedule) == len(faults)
    assert {row["fault_id"] for row in schedule} == {f.fault_id for f in faults}

    assert total_cost == pytest.approx(sum(row["cost_pln"] for row in schedule))
    assert total_cost >= 0

    by_vessel = {}
    for row in schedule:
        if row["start"] is None:
            assert row["end"] is None
            assert row["vessel_id"] is None
            assert row["cost_pln"] == 0.0
            continue

        assert row["start"] >= 0
        assert row["end"] > row["start"]
        assert not math.isnan(row["cost_pln"])
        assert row["cost_pln"] >= 0

        w = windows_by_id[row["win_id"]]
        assert w.start <= row["start"]
        assert row["end"] <= w.end

        by_vessel.setdefault(row["vessel_id"], []).append((row["start"], row["end"]))

    assert_no_vessel_overlap(by_vessel)


def assert_no_vessel_overlap(intervals_by_vessel):
    """Sprawdza, że żaden statek nie ma dwóch nakładających się przedziałów
    czasu. `intervals_by_vessel` to dict {vessel_id: [(start, end), ...]}.
    """
    for vessel_id, intervals in intervals_by_vessel.items():
        intervals = sorted(intervals)
        for (s1, e1), (s2, e2) in zip(intervals, intervals[1:]):
            assert e1 <= s2, f"vessel {vessel_id} double-booked: {(s1, e1)} vs {(s2, e2)}"

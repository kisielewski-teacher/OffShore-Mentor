"""Symulacja wielodniowa (rolling horizon) planowania napraw.

W odróżnieniu od `plan_repairs` (jednorazowy plan dla statycznego zbioru
usterek), ten moduł krok po kroku "przeżywa" symulowany horyzont dni: nowe
usterki napływają w czasie, a plan jest przeliczany codziennie na bieżąco na
podstawie wciąż nierozwiązanego backlogu. Pokazuje, czy flota "nadąża" z
naprawami (backlog się stabilizuje) czy nie (backlog rośnie).

Świadomie używa wyłącznie zachłannej heurystyki `plan_repairs` (nigdy solvera
MIP z `planner.optimizer`) - przeliczanie ILP co symulowany dzień
złamałoby wymóg płynnego działania demo na żywo.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import pandas as pd

from planner.plan import Fault, Vessel, Window, plan_repairs

_SCHEDULE_COLUMNS = [
    "fault_id", "turbine_id", "start", "end", "vessel_id", "vessel_name",
    "cost_pln", "priority", "distance_km", "transit_h", "win_id", "day",
]


@dataclass
class DaySnapshot:
    day: int
    new_faults: int
    resolved_today: int
    backlog_after: int
    cost_today: float
    cumulative_cost: float
    vessel_hours_today: Dict[str, int] = field(default_factory=dict)


def run_rolling_simulation(
    faults: List[Fault],
    windows: List[Window],
    vessels: List[Vessel],
    horizon_days: int,
    hs_thr: float = 1.5,
    wind_thr: float = 15.0,
    workday_hours: int = 8,
    port_lat: float = 54.580,
    port_lon: float = 16.860,
) -> Tuple[List[DaySnapshot], pd.DataFrame]:
    """Uruchamia symulację dzień po dniu na przekazanym zbiorze usterek/okien.

    Wywołujący jest odpowiedzialny za wygenerowanie `faults` (typowo przez
    `gen_faults(..., arrival_horizon_h=horizon_days*24)`, aby usterki napływały
    w całym horyzoncie, nie tylko w pierwszych 48h) oraz `windows`
    (`gen_windows(horizon_days, seed)`), tak jak dziś robi to wywołujący
    `plan_repairs`.
    """
    usage: Dict[str, List[int]] = {}
    backlog: List[Fault] = []
    committed_rows: List[Dict] = []
    snapshots: List[DaySnapshot] = []
    cumulative_cost = 0.0

    for day in range(horizon_days):
        now = day * 24
        day_end = now + 24

        new_today = [f for f in faults if now <= f.reported_h < day_end]
        backlog.extend(new_today)

        windows_from_now = [
            Window(w.win_id, max(w.start, now), w.end, w.hs_m, w.wind_ms)
            for w in windows
            if w.end > now
        ]
        windows_from_now = [w for w in windows_from_now if w.start < w.end]

        schedule, _ = plan_repairs(
            backlog, windows_from_now, vessels,
            hs_thr=hs_thr, wind_thr=wind_thr,
            port_lat=port_lat, port_lon=port_lon,
            workday_hours=workday_hours, usage=usage,
        )

        committed_today: List[Dict] = []
        for row in schedule:
            if row["start"] is None:
                continue
            if row["start"] < day_end:
                committed_today.append(row)
            else:
                # Spillover na przyszły dzień: usterka zostaje w backlogu i
                # będzie przeplanowana od nowa jutro (np. inne okno/statek
                # może się wtedy okazać lepsze) - cofamy tymczasową rezerwację
                # godzin, żeby nie blokowała innych usterek. Bezpieczne, bo
                # plan_repairs w ramach jednego wywołania gwarantuje brak
                # nakładania się wierszy na tym samym statku.
                for h in range(row["start"], row["end"]):
                    usage[row["vessel_id"]][h] = 0

        committed_ids = {row["fault_id"] for row in committed_today}
        backlog = [f for f in backlog if f.fault_id not in committed_ids]

        day_cost = sum(row["cost_pln"] for row in committed_today)
        cumulative_cost += day_cost

        vessel_hours_today: Dict[str, int] = {}
        for row in committed_today:
            vessel_hours_today[row["vessel_id"]] = (
                vessel_hours_today.get(row["vessel_id"], 0) + (row["end"] - row["start"])
            )
            committed_rows.append({**row, "day": day})

        snapshots.append(
            DaySnapshot(
                day=day,
                new_faults=len(new_today),
                resolved_today=len(committed_today),
                backlog_after=len(backlog),
                cost_today=day_cost,
                cumulative_cost=cumulative_cost,
                vessel_hours_today=vessel_hours_today,
            )
        )

    df = pd.DataFrame(committed_rows, columns=_SCHEDULE_COLUMNS)
    return snapshots, df


def snapshots_to_dataframe(snapshots: List[DaySnapshot]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "day": s.day,
                "new_faults": s.new_faults,
                "resolved_today": s.resolved_today,
                "backlog_after": s.backlog_after,
                "cost_today": s.cost_today,
                "cumulative_cost": s.cumulative_cost,
            }
            for s in snapshots
        ]
    )

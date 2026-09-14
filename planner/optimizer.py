"""Optymalny (dowiedziony/near-optimal) planer napraw - alternatywa dla
zachłannej heurystyki `plan_repairs`.

Modeluje ten sam problem jako MIP (PuLP + CBC) i pozwala porównać, ile
heurystyka "traci" względem prawdziwego optimum - w kosztach oraz w liczbie
nieobsłużonych (ważonych priorytetem) usterek.
"""

import logging
import math
import tempfile
import time
import warnings
from pathlib import Path
from typing import Dict, List, Tuple

import pulp

from planner.plan import Fault, Vessel, Window, feasible, haversine, transit_time_km

# PULP_CBC_CMD is deprecated in favor of COIN_CMD + the `pulp[cbc]` extra, but
# that extra pulls in a ~150MB separate "cbcbox" package. PULP_CBC_CMD already
# ships a small bundled CBC binary inside pulp itself (pulp/solverdir/cbc/...),
# which is what we want for a lightweight, easily-packaged dependency - so we
# deliberately keep using it and just silence the cosmetic deprecation notice.
warnings.filterwarnings(
    "ignore", message="PULP_CBC_CMD is deprecated", category=DeprecationWarning
)

logger = logging.getLogger("offshore_app")

# Limity bezpieczne dla demo na żywo - solver MIP nie może zawiesić UI.
SOLVER_MAX_FAULTS = 40
SOLVER_TIME_LIMIT_S = 8.0

_URGENCY_WEIGHT = {1: 3, 2: 2, 3: 1}


def _urgency_weight(priority: int) -> float:
    return _URGENCY_WEIGHT.get(priority, 1)


def unassigned_weighted_count(faults: List[Fault], schedule: List[Dict]) -> float:
    """Suma wag urgencji usterek, które w danym harmonogramie są niezaplanowane."""
    weight_by_id = {f.fault_id: _urgency_weight(f.priority) for f in faults}
    total = 0.0
    for row in schedule:
        if row["start"] is None:
            total += weight_by_id.get(row["fault_id"], 0)
    return total


def _build_candidates(
    faults: List[Fault],
    windows: List[Window],
    vessels: List[Vessel],
    hs_thr: float,
    wind_thr: float,
    port_lat: float,
    port_lon: float,
    workday_hours: int,
) -> List[Dict]:
    """Generuje wszystkie wykonalne trójki (usterka, okno, statek).

    Ta sama arytmetyka co wnętrze pętli `plan_repairs` (transit/repair/cost),
    ale bez early-exit - MIP potrzebuje całego zbioru kandydatów, nie tylko
    pierwszego dopasowania.
    """
    candidates: List[Dict] = []
    for f in faults:
        distance_km = haversine(port_lat, port_lon, f.lat, f.lon)
        for w in windows:
            if not feasible(w, hs_thr, wind_thr):
                continue
            for v in vessels:
                transit_h = transit_time_km(distance_km, v.speed_kn)
                transit_h_int = math.ceil(transit_h)
                repair_h_int = int(f.repair_hours)
                operation_h = transit_h_int + repair_h_int + transit_h_int

                start = max(w.start, f.reported_h)
                end = start + operation_h
                if end > w.end:
                    continue

                days = math.ceil(operation_h / max(workday_hours, 1))
                cost = days * v.day_cost_pln

                candidates.append(
                    {
                        "fault_id": f.fault_id,
                        "turbine_id": f.turbine_id,
                        "priority": f.priority,
                        "start": start,
                        "end": end,
                        "vessel_id": v.vessel_id,
                        "vessel_name": v.name,
                        "cost_pln": cost,
                        "distance_km": round(distance_km, 2),
                        "transit_h": round(transit_h, 2),
                        "win_id": w.win_id,
                    }
                )
    return candidates


def solve_optimal_schedule(
    faults: List[Fault],
    windows: List[Window],
    vessels: List[Vessel],
    hs_thr: float = 1.5,
    wind_thr: float = 15.0,
    port_lat: float = 54.580,
    port_lon: float = 16.860,
    workday_hours: int = 8,
    time_limit_s: float = SOLVER_TIME_LIMIT_S,
) -> Tuple[List[Dict], float, Dict]:
    """Liczy (near-)optymalny harmonogram tego samego problemu co `plan_repairs`.

    Zwraca (schedule, total_cost, meta) - `schedule` ma identyczny format
    wierszy co `plan_repairs`, więc `viz/gantt.py::gantt_chart` i istniejące
    renderowanie tabeli działają na nim bez zmian.

    `meta["status"]` to jedno z: "optimal" (dowiedzione optimum),
    "time_limit" (najlepsze znalezione w limicie czasu, optimum niedowiedzione),
    "infeasible", "no_candidates".
    """
    t0 = time.perf_counter()
    candidates = _build_candidates(
        faults, windows, vessels, hs_thr, wind_thr, port_lat, port_lon, workday_hours
    )

    def _unassigned_rows(assigned_ids: set) -> List[Dict]:
        rows = []
        for f in faults:
            if f.fault_id in assigned_ids:
                continue
            distance_km = haversine(port_lat, port_lon, f.lat, f.lon)
            rows.append(
                {
                    "fault_id": f.fault_id,
                    "turbine_id": f.turbine_id,
                    "start": None,
                    "end": None,
                    "vessel_id": None,
                    "vessel_name": None,
                    "cost_pln": 0.0,
                    "priority": f.priority,
                    "distance_km": round(distance_km, 2),
                    "transit_h": None,
                    "win_id": None,
                    "note": "niezaplanowane (brak okna/zasobu)",
                }
            )
        return rows

    if not candidates:
        schedule = _unassigned_rows(assigned_ids=set())
        meta = {
            "status": "no_candidates",
            "runtime_s": time.perf_counter() - t0,
            "objective_value": None,
            "unassigned_weighted": unassigned_weighted_count(faults, schedule),
            "num_candidates": 0,
            "num_faults": len(faults),
            "num_vessels": len(vessels),
            "time_limit_s": time_limit_s,
            "big_m": 0.0,
        }
        return schedule, 0.0, meta

    big_m = sum(c["cost_pln"] for c in candidates) + 1

    prob = pulp.LpProblem("offshore_repair_scheduling", pulp.LpMinimize)
    x = {i: prob.add_variable(f"x_{i}", cat="Binary") for i in range(len(candidates))}

    candidates_by_fault: Dict[str, List[int]] = {}
    for i, c in enumerate(candidates):
        candidates_by_fault.setdefault(c["fault_id"], []).append(i)

    for f in faults:
        idxs = candidates_by_fault.get(f.fault_id, [])
        if idxs:
            prob += pulp.lpSum(x[i] for i in idxs) <= 1

    # Ograniczenie zajętości statku: godzinowe, analogicznie do `usage` w
    # plan_repairs, żeby uniknąć O(kandydaci^2) ograniczeń parami.
    by_vessel_hour: Dict[Tuple[str, int], List[int]] = {}
    for i, c in enumerate(candidates):
        for h in range(c["start"], c["end"]):
            by_vessel_hour.setdefault((c["vessel_id"], h), []).append(i)
    for idxs in by_vessel_hour.values():
        if len(idxs) > 1:
            prob += pulp.lpSum(x[i] for i in idxs) <= 1

    cost_term = pulp.lpSum(candidates[i]["cost_pln"] * x[i] for i in range(len(candidates)))
    urgency_term = pulp.lpSum(
        big_m * _urgency_weight(candidates[i]["priority"]) * x[i]
        for i in range(len(candidates))
    )
    prob += cost_term - urgency_term

    with tempfile.TemporaryDirectory() as tmp_dir:
        log_path = str(Path(tmp_dir) / "cbc.log")
        solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=time_limit_s, logPath=log_path)
        try:
            prob.solve(solver)
        except Exception:
            logger.exception("Solver PuLP/CBC nie powiódł się")
            schedule = _unassigned_rows(assigned_ids=set())
            meta = {
                "status": "infeasible",
                "runtime_s": time.perf_counter() - t0,
                "objective_value": None,
                "unassigned_weighted": unassigned_weighted_count(faults, schedule),
                "num_candidates": len(candidates),
                "num_faults": len(faults),
                "num_vessels": len(vessels),
                "time_limit_s": time_limit_s,
                "big_m": big_m,
            }
            return schedule, 0.0, meta

        log_text = ""
        try:
            log_text = Path(log_path).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            logger.exception("Nie udało się odczytać logu solvera CBC")

    lp_status = pulp.LpStatus[prob.status]
    if lp_status in ("Infeasible", "Unbounded", "Not Solved", "Undefined"):
        schedule = _unassigned_rows(assigned_ids=set())
        meta = {
            "status": "infeasible",
            "runtime_s": time.perf_counter() - t0,
            "objective_value": None,
            "unassigned_weighted": unassigned_weighted_count(faults, schedule),
            "num_candidates": len(candidates),
            "num_faults": len(faults),
            "num_vessels": len(vessels),
            "time_limit_s": time_limit_s,
            "big_m": big_m,
        }
        return schedule, 0.0, meta

    if "Stopped on time limit" in log_text:
        status = "time_limit"
    elif "Optimal solution found" in log_text:
        status = "optimal"
    else:
        # nieznana/nierozstrzygnięta treść logu - nie okłamuj jury statusem "optimal"
        status = "time_limit"

    chosen = [i for i in range(len(candidates)) if pulp.value(x[i]) and pulp.value(x[i]) > 0.5]
    assigned_ids = {candidates[i]["fault_id"] for i in chosen}

    schedule_rows = []
    total_cost = 0.0
    for i in chosen:
        c = candidates[i]
        row = {k: v for k, v in c.items() if k != "priority"}
        row["priority"] = c["priority"]
        schedule_rows.append(row)
        total_cost += c["cost_pln"]

    schedule_rows.extend(_unassigned_rows(assigned_ids))

    meta = {
        "status": status,
        "runtime_s": time.perf_counter() - t0,
        "objective_value": pulp.value(prob.objective),
        "unassigned_weighted": unassigned_weighted_count(faults, schedule_rows),
        "num_candidates": len(candidates),
        "num_faults": len(faults),
        "num_vessels": len(vessels),
        "time_limit_s": time_limit_s,
        "big_m": big_m,
    }
    return schedule_rows, total_cost, meta

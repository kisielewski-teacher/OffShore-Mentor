from dataclasses import dataclass
from typing import List, Tuple, Dict
import math

# ------------------------------
#   DATA CLASSES
# ------------------------------


@dataclass
class Fault:
    fault_id: str
    turbine_id: str
    reported_h: int
    repair_hours: int
    priority: int
    lat: float
    lon: float


@dataclass
class Window:
    win_id: str
    start: int
    end: int
    hs_m: float
    wind_ms: float


@dataclass
class Vessel:
    vessel_id: str
    name: str
    teams: int
    speed_kn: float
    day_cost_pln: float


# ------------------------------
#   HELPERS
# ------------------------------


def feasible(w: Window, hs_thr: float, wind_thr: float) -> bool:
    """Czy okno pogodowe spełnia progi?"""
    return (w.hs_m <= hs_thr) and (w.wind_ms <= wind_thr)


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Odległość w km między dwoma punktami geograficznymi."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def transit_time_km(distance_km: float, speed_knots: float) -> float:
    """Czas tranzytu w godzinach dla odległości [km] i prędkości [węzły]."""
    speed_kmh = speed_knots * 1.852
    if speed_kmh <= 0:
        return float("inf")
    return distance_km / speed_kmh


# ------------------------------
#   PLANNING HEURISTIC
# ------------------------------


def plan_repairs(
    faults: List[Fault],
    windows: List[Window],
    vessels: List[Vessel],
    hs_thr: float = 1.5,
    wind_thr: float = 15.0,
    port_lat: float = 54.580,
    port_lon: float = 16.860,
    workday_hours: int = 8,
) -> Tuple[List[Dict], float]:
    """
    Planuje naprawy w oknach pogodowych z uwzględnieniem tranzytu (tam i z powrotem) oraz kosztów.
    Zwraca listę zadań (harmonogram) oraz łączny koszt.
    """
    # Sortuj usterki: priorytet, czas zgłoszenia
    faults_sorted = sorted(faults, key=lambda f: (f.priority, f.reported_h))

    horizon = max([w.end for w in windows]) if windows else 7 * 24
    usage: Dict[str, List[int]] = {
        v.vessel_id: [0] * (horizon + 1) for v in vessels
    }  # 0=free, 1=busy

    schedule: List[Dict] = []
    total_cost = 0.0

    for f in faults_sorted:
        assigned = False
        # Odległość port -> turbina
        distance_km = haversine(port_lat, port_lon, f.lat, f.lon)

        # Szukaj pierwszego okna i wolnego statku, aby zmieścić operację (tranzyt + naprawa + powrót)
        for w in sorted(windows, key=lambda w: w.start):
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

                # Sprawdź zajętość statku
                if end > len(usage[v.vessel_id]):
                    usage[v.vessel_id].extend([0] * (end - len(usage[v.vessel_id]) + 1))
                if all(usage[v.vessel_id][h] == 0 for h in range(start, end)):
                    # Zajmij sloty
                    for h in range(start, end):
                        usage[v.vessel_id][h] = 1

                    # Koszt proporcjonalny do liczby dni pracy
                    days = math.ceil(operation_h / max(workday_hours, 1))
                    cost = days * v.day_cost_pln
                    total_cost += cost

                    schedule.append(
                        {
                            "fault_id": f.fault_id,
                            "turbine_id": f.turbine_id,
                            "start": start,
                            "end": end,
                            "vessel_id": v.vessel_id,
                            "vessel_name": v.name,
                            "cost_pln": cost,
                            "priority": f.priority,
                            "distance_km": round(distance_km, 2),
                            "transit_h": round(transit_h, 2),
                            "win_id": w.win_id,
                        }
                    )
                    assigned = True
                    break

            if assigned:
                break

        if not assigned:
            schedule.append(
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

    return schedule, total_cost

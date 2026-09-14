from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
import math
import random

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
    *,
    usage: Optional[Dict[str, List[int]]] = None,
) -> Tuple[List[Dict], float]:
    """
    Planuje naprawy w oknach pogodowych z uwzględnieniem tranzytu (tam i z powrotem) oraz kosztów.
    Zwraca listę zadań (harmonogram) oraz łączny koszt.

    `usage` to opcjonalny słownik zajętości statków (godzina -> 0/1), mutowany
    in-place. Pozwala wywołującemu (np. symulacji wielodniowej) przenosić
    zajętość statków między kolejnymi wywołaniami. Gdy nie podany, zachowanie
    jest identyczne jak dotychczas (świeża, pusta tablica zajętości).
    """
    # Sortuj usterki: priorytet, czas zgłoszenia
    faults_sorted = sorted(faults, key=lambda f: (f.priority, f.reported_h))

    horizon = max([w.end for w in windows]) if windows else 7 * 24
    if usage is None:
        usage = {v.vessel_id: [0] * (horizon + 1) for v in vessels}  # 0=free, 1=busy
    else:
        for v in vessels:
            arr = usage.setdefault(v.vessel_id, [])
            if len(arr) < horizon + 1:
                arr.extend([0] * (horizon + 1 - len(arr)))

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


# ------------------------------
#   TEST DATA GENERATORS
# ------------------------------

# Baltic Sea wind farm ~40 km north of Ustka port (54.580, 16.860)
# Minimum lat 54.80 keeps all turbines well offshore (coast ~54.58 N)
_FARM_CENTER_LAT = 55.00
_FARM_CENTER_LON = 16.90
_FARM_RADIUS_DEG = 0.20
_FARM_MIN_LAT = 54.80


def gen_faults(
    n: int = 30, seed: int = 42, arrival_horizon_h: Optional[int] = None
) -> List[Fault]:
    """Generuje n losowych usterek turbin w farmie wiatrowej.

    `arrival_horizon_h`, gdy podany, rozciąga czas zgłoszenia usterek
    (`reported_h`) na cały ten horyzont (godziny) - używane przez symulację
    wielodniową, aby usterki napływały w czasie, a nie tylko w pierwszych 48h.
    Górna granica jest pomniejszona o 1, bo dzienne okno przyjęcia w symulacji
    to [dzień*24, dzień*24+24) - wartość równa dokładnie horyzontowi wypadłaby
    poza ostatnim dniem. Domyślnie (`None`) zachowanie jest identyczne jak
    dotychczas (0-48h).
    """
    rng = random.Random(seed)
    max_report_h = (arrival_horizon_h - 1) if arrival_horizon_h is not None else 48
    max_report_h = max(max_report_h, 0)
    faults = []
    for i in range(n):
        lat = _FARM_CENTER_LAT + rng.uniform(-_FARM_RADIUS_DEG, _FARM_RADIUS_DEG)
        lat = max(lat, _FARM_MIN_LAT)  # zawsze na morzu
        lon = _FARM_CENTER_LON + rng.uniform(-_FARM_RADIUS_DEG, _FARM_RADIUS_DEG)
        faults.append(
            Fault(
                fault_id=f"F{i+1:03d}",
                turbine_id=f"T{i+1:03d}",
                reported_h=rng.randint(0, max_report_h),
                repair_hours=rng.choice([4, 6, 8, 12, 16]),
                priority=rng.randint(1, 3),
                lat=round(lat, 5),
                lon=round(lon, 5),
            )
        )
    return faults


def gen_windows(horizon_days: int = 14, seed: int = 42) -> List[Window]:
    """Generuje okna pogodowe na zadany horyzont (domyślnie 14 dni)."""
    rng = random.Random(seed)
    windows = []
    h = 0
    horizon_h = horizon_days * 24
    win_id = 1
    while h < horizon_h:
        # okno niesprzyjające (zła pogoda)
        bad_len = rng.randint(6, 36)
        h += bad_len
        if h >= horizon_h:
            break
        # okno sprzyjające (dobra pogoda)
        good_len = rng.randint(8, 48)
        end = min(h + good_len, horizon_h)
        windows.append(
            Window(
                win_id=f"W{win_id:03d}",
                start=h,
                end=end,
                hs_m=round(rng.uniform(0.3, 1.4), 2),
                wind_ms=round(rng.uniform(3.0, 14.0), 1),
            )
        )
        win_id += 1
        h = end
    return windows


def gen_vessels(seed: int = 42, count: int = 3) -> List[Vessel]:
    """Zwraca flotę statków serwisowych.

    Domyślnie (`count=3`) zwraca dokładnie dotychczasową stałą flotę (V01-V03).
    `count` > 3 dogenerowuje dodatkowe statki (na bazie wzorców) - przydatne do
    scenariuszy "co jeśli dodamy kolejny statek" w symulacji wielodniowej.
    `count` < 3 zwraca odpowiedni prefiks floty.
    """
    _ = seed  # zachowany dla spójności API
    templates = [
        Vessel(vessel_id="V01", name="Baltic Hawk", teams=2, speed_kn=12.0, day_cost_pln=45_000),
        Vessel(vessel_id="V02", name="North Star", teams=1, speed_kn=10.0, day_cost_pln=32_000),
        Vessel(vessel_id="V03", name="Sea Falcon", teams=2, speed_kn=14.0, day_cost_pln=58_000),
    ]
    if count <= len(templates):
        return templates[:count]

    vessels = list(templates)
    for i in range(len(templates), count):
        base = templates[i % len(templates)]
        vessels.append(
            Vessel(
                vessel_id=f"V{i+1:02d}",
                name=f"{base.name} II",
                teams=base.teams,
                speed_kn=base.speed_kn,
                day_cost_pln=base.day_cost_pln,
            )
        )
    return vessels

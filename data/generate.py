import random
from planner.plan import Fault, Window, Vessel

# ---------------------------------------------------------
# GENEROWANIE USTEREK – turbiny na morzu, ~20 km na zachód od Ustki
# ---------------------------------------------------------


def gen_faults(n=30):
    faults = []
    for i in range(n):
        # Pas na morzu na zachód od Ustki
        # Ustka: ok. 54.58 N, 16.86 E
        # Tu: trochę bardziej na północ (pewnie na wodzie)
        #     i wyraźnie na zachód (~20+ km)
        lat = random.uniform(54.65, 54.75)  # tylko morze, na północ od brzegu
        lon = random.uniform(16.40, 16.70)  # na zachód od Ustki

        faults.append(
            Fault(
                fault_id=f"F-{i:03d}",
                turbine_id=f"T-{random.randint(1, 50):03d}",
                reported_h=random.randint(0, 7 * 24 - 24),
                repair_hours=random.choice([4, 6, 8, 12]),
                priority=random.choice([1, 2, 3]),
                lat=lat,
                lon=lon,
            )
        )
    return faults


# ---------------------------------------------------------
# GENEROWANIE OKIEN POGODOWYCH
# ---------------------------------------------------------


def gen_windows():
    windows = []
    t = 0
    while t < 7 * 24:
        dur = random.choice([6, 8, 12, 24])
        windows.append(
            Window(
                win_id=f"W-{len(windows):03d}",
                start=t,
                end=min(t + dur, 7 * 24),
                hs_m=round(random.uniform(0.5, 2.5), 1),
                wind_ms=round(random.uniform(4, 18), 1),
            )
        )
        t += dur
    return windows


# ---------------------------------------------------------
# GENEROWANIE STATKÓW
# ---------------------------------------------------------


def gen_vessels():
    return [
        Vessel("V-1", "CTV-Alpha", teams=2, speed_kn=20, day_cost_pln=3500.0),
        Vessel("V-2", "CTV-Beta", teams=1, speed_kn=18, day_cost_pln=3200.0),
    ]

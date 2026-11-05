"""Sprawdza, czy projekt OffShore Mentor ma wszystko, co potrzebne do uruchomienia.

Wywolywany przez uruchom.bat. Kod wyjscia: 0 = wszystko w porzadku, 1 = brakuje
zaleznosci Pythona lub solver CBC (bat sprobuje doinstalowac pakiety),
2 = problem, ktorego instalacja nie naprawi (brak plikow projektu, zly Python,
blad importu, katalog niezapisywalny).

Uzycie: python sprawdz_zaleznosci.py [--wolny-port OD DO]  (wypisuje pierwszy wolny port)
"""

from __future__ import annotations

import re
import sys
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MIN_PYTHON = (3, 10)

PLIKI_WYMAGANE = [
    "streamlit_app.py",
    "requirements.txt",
    "modules/__init__.py",
    "modules/visual.py",
    "planner/__init__.py",
    "planner/plan.py",
    "planner/optimizer.py",
    "planner/simulate.py",
    "viz/__init__.py",
    "viz/gantt.py",
    "assets/icons.png",
    "assets/port.png",
    "assets/statek.png",
    "assets/wind-turbine.png",
    ".streamlit/config.toml",
]

# modul projektu -> importowany w trakcie startu aplikacji
MODULY_PROJEKTU = ["modules.visual", "planner.plan", "planner.optimizer", "planner.simulate", "viz.gantt"]


def _norm(nazwa: str) -> str:
    return re.sub(r"[-_.]+", "-", nazwa).lower()


def wczytaj_wymagania() -> list[tuple[str, str | None]]:
    wynik: list[tuple[str, str | None]] = []
    for linia in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        linia = linia.split("#", 1)[0].strip()
        if not linia or linia.startswith("-"):
            continue
        m = re.match(r"^([A-Za-z0-9_.\-]+)\s*(?:==\s*([^\s;]+))?", linia)
        if m:
            wynik.append((m.group(1), m.group(2)))
    return wynik


def sprawdz_python() -> list[str]:
    if sys.version_info < MIN_PYTHON:
        return [f"Python {sys.version.split()[0]} jest za stary (wymagany {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+)"]
    return []


def sprawdz_pliki() -> list[str]:
    return [f"brak pliku projektu: {p}" for p in PLIKI_WYMAGANE if not (ROOT / p).is_file()]


def sprawdz_pakiety() -> list[str]:
    problemy: list[str] = []
    for nazwa, wersja in wczytaj_wymagania():
        try:
            zainstalowana = metadata.version(_norm(nazwa))
        except metadata.PackageNotFoundError:
            problemy.append(f"brak pakietu: {nazwa}" + (f"=={wersja}" if wersja else ""))
            continue
        if wersja and zainstalowana != wersja:
            problemy.append(f"zla wersja {nazwa}: jest {zainstalowana}, wymagana {wersja}")
    return problemy


def sprawdz_solver() -> list[str]:
    """Solver CBC dolaczony do PuLP musi dac sie uruchomic (porownanie z rozwiazaniem optymalnym)."""
    try:
        import pulp
    except Exception as exc:  # noqa: BLE001 - zgloszone jako brak pakietu
        return [f"nie mozna zaimportowac pulp: {exc}"]
    try:
        if not pulp.PULP_CBC_CMD(msg=False).available():
            return ["solver CBC (pulp) niedostepny - zablokowany przez antywirus lub uszkodzona instalacja pulp"]
    except Exception as exc:  # noqa: BLE001
        return [f"solver CBC (pulp) nie dziala: {exc}"]
    return []


def sprawdz_importy() -> list[str]:
    sys.path.insert(0, str(ROOT))
    problemy: list[str] = []
    for mod in MODULY_PROJEKTU:
        try:
            __import__(mod)
        except Exception as exc:  # noqa: BLE001
            problemy.append(f"modul {mod} nie importuje sie: {type(exc).__name__}: {exc}")
    return problemy


def sprawdz_zapis() -> list[str]:
    """Aplikacja zapisuje logi i generuje static/icons.png - katalogi musza byc zapisywalne."""
    problemy: list[str] = []
    for katalog in ("static", "logs"):
        sciezka = ROOT / katalog
        try:
            sciezka.mkdir(exist_ok=True)
            probny = sciezka / ".zapis_test"
            probny.write_text("ok", encoding="utf-8")
            probny.unlink()
        except OSError as exc:
            problemy.append(f"katalog {katalog}/ nie jest zapisywalny: {exc}")
    return problemy


def port_wolny(port: int) -> bool:
    """Prawdziwa proba zajecia portu (IPv4 i IPv6), tak jak robi to Streamlit.

    Parsowanie `netstat` nie wystarcza: porty trzymane przez konczace sie procesy
    (stan FIN_WAIT/CLOSED) nie sa LISTENING, a mimo to nie da sie ich zajac.
    """
    import socket

    adresy = [(socket.AF_INET, "0.0.0.0")]
    if socket.has_ipv6:
        adresy.append((socket.AF_INET6, "::"))
    for rodzina, adres in adresy:
        try:
            with socket.socket(rodzina, socket.SOCK_STREAM) as s:
                s.bind((adres, port))
        except OSError:
            return False
    return True


def znajdz_wolny_port(od: int, do: int) -> int | None:
    return next((p for p in range(od, do + 1) if port_wolny(p)), None)


def main() -> int:
    if len(sys.argv) == 4 and sys.argv[1] == "--wolny-port":
        port = znajdz_wolny_port(int(sys.argv[2]), int(sys.argv[3]))
        if port is None:
            return 2
        print(port)
        return 0

    twarde: list[str] = []  # nienaprawialne instalacja
    miekkie: list[str] = []  # naprawialne przez pip install

    twarde += sprawdz_python()
    twarde += sprawdz_pliki()
    if twarde:
        return _raport(twarde, miekkie)

    miekkie += sprawdz_pakiety()
    if not miekkie:
        # Solver i importy maja sens dopiero, gdy pakiety sa na miejscu.
        miekkie += sprawdz_solver()
        twarde += sprawdz_importy()
        twarde += sprawdz_zapis()
    return _raport(twarde, miekkie)


def _raport(twarde: list[str], miekkie: list[str]) -> int:
    for p in twarde:
        print(f"  [BLAD] {p}")
    for p in miekkie:
        print(f"  [BRAK] {p}")
    if twarde:
        return 2
    if miekkie:
        return 1
    print("  [OK] Python, pliki projektu, pakiety, solver CBC, importy i zapis katalogow")
    return 0


if __name__ == "__main__":
    sys.exit(main())

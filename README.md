# Offshore Mentor

Interaktywny symulator logistyki serwisowania morskich farm wiatrowych offshore

Aplikacja odwzorowuje realne wyzwania operacyjne: planowanie napraw turbin z uwzględnieniem prognoz pogody, dostępności statków serwisowych (CTV), czasu tranzytu i kosztów operacji. Kontekst – polska energetyka wiatrowa na Bałtyku (cel 18+ GW do 2040 r.).

---

## Funkcje

- Generowanie losowych usterek turbin w wybranej lokalizacji na Bałtyku
- Generowanie okien pogodowych (Hs, prędkość wiatru) i planowanie napraw algorytmem zachłannym
- **Porównanie z rozwiązaniem optymalnym** – solver MIP (PuLP/CBC) liczy (near-)optymalny harmonogram tego samego problemu i pokazuje liczbowo, ile heurystyka "traci" w koszcie/liczbie nieobsłużonych usterek
- **Symulacja wielodniowa (rolling horizon)** – usterki napływają w czasie, plan jest przeliczany codziennie na bieżąco; wykresy backlogu i kosztu skumulowanego pokazują, czy flota "nadąża" z naprawami
- Interaktywna mapa pydeck z ikonami turbin i portu bazowego (Ustka)
- Animacja ruchu statku serwisowego: port → turbina → port
- Wykres Gantta z harmonogramem zaplanowanych operacji
- KPI: zaplanowane/niezaplanowane naprawy, szacowany koszt [PLN]
- Obsługa trybu wysokiego kontrastu
- Wersja desktopowa `.exe` (PyInstaller + Inno Setup)

---

## Wymagania

| Pakiet | Rola |
| --- | --- |
| `streamlit` | Framework interfejsu webowego |
| `pandas` | Przetwarzanie danych tabelarycznych |
| `altair` | Wykresy (Gantt) |
| `pydeck` | Mapa interaktywna (deck.gl) |
| `pillow` | Generowanie atlasu ikon (wymagane) |
| `pulp` | Solver MIP (CBC) dla rozwiązania optymalnego |
| `ruff` | Formatowanie kodu (dla deweloperów) |

Python **3.10+**, Windows 10/11 / Linux / macOS.

---

## Szybki start

### Najprościej (Windows): `uruchom.bat`

Dwuklik na `uruchom.bat` sprawdza Pythona 3.10+, tworzy `.venv`, kontroluje pliki
projektu, wersje pakietów z `requirements.txt` i solver CBC, w razie braków
doinstalowuje pakiety, a potem uruchamia aplikację (na wolnym porcie od 8501).
Warianty: `uruchom.bat sprawdz` (tylko kontrola) i `uruchom.bat test` (ruff + pytest).

### Ręcznie

#### 1. Zainstaluj zależności

```powershell
python -m pip install -r requirements.txt
```

#### 2. Uruchom aplikację

```powershell
python -m streamlit run streamlit_app.py
```

Przeglądarka otworzy się automatycznie pod adresem `http://localhost:8501`.

> **Windows:** jeśli `streamlit` nie jest rozpoznawany, używaj zawsze `python -m streamlit run ...`

#### Wirtualne środowisko (zalecane)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

---

## Testy i symulacje

Projekt ma zestaw testów `pytest` (testy jednostkowe, symulacje Monte Carlo,
testy property-based `hypothesis` oraz smoke test całej aplikacji Streamlit).

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Zakres testów (katalog `tests/`):

| Plik | Zakres |
| --- | --- |
| `test_planner.py` | Jednostkowe testy algorytmu planowania (`planner/plan.py`): odległości, tranzyt, progi pogodowe, generatory danych, harmonogramowanie |
| `test_simulation.py` | Symulacje Monte Carlo (wiele skal/nasion/progów) + fuzzing `hypothesis` sprawdzający niezmienniki harmonogramu (brak nakładania się rejsów statku, spójność kosztów, zgodność z oknami pogodowymi) |
| `test_optimizer.py` | Solver optymalny (`planner/optimizer.py`): przypadki z policzalnym optimum, brak kandydatów, przewaga nad heurystyką, niezmienniki |
| `test_simulate.py` | Symulacja wielodniowa (`planner/simulate.py`): backlog, koszt skumulowany, brak nakładania się statków w całej symulacji, storytelling (mała vs. duża flota) |
| `test_gantt.py` | Budowa wykresu Gantta (`viz/gantt.py`) |
| `test_visual.py` | Atlas ikon i logika mapowania ikon (`modules/visual.py`) |
| `test_app_smoke.py` | Uruchomienie całej aplikacji (`streamlit.testing.v1.AppTest`) przed i po kliknięciu „Start symulacji” |
| `_helpers.py` | Wspólne asercje niezmienników harmonogramu, reużywane przez powyższe pliki |

---

## Uruchomienie jako plik .exe (Windows)

Jeśli korzystasz z wersji spakowanej (`dist/OffShoreMentor/`):

```powershell
OffShoreMentor.exe
```

Aplikacja uruchamia wbudowany serwer Streamlit i otwiera przeglądarkę automatycznie.
Instrukcja budowania pliku wykonywalnego: [packaging/README_BUILD.md](packaging/README_BUILD.md).

---

## Struktura projektu

```text
OffShore/
├── streamlit_app.py        # Punkt wejścia aplikacji
├── launcher.py             # Uruchamiacz dla wersji .exe (PyInstaller)
├── requirements.txt        # Zależności
├── OffShoreMentor.spec     # Konfiguracja PyInstaller
│
├── planner/
│   ├── __init__.py
│   ├── plan.py             # Algorytm planowania (heurystyka) + generatory danych
│   ├── optimizer.py        # Solver optymalny (PuLP/CBC) - porównanie z heurystyką
│   └── simulate.py         # Symulacja wielodniowa (rolling horizon)
│
├── modules/
│   ├── __init__.py
│   └── visual.py           # Silnik animacji statku (pydeck)
│
├── viz/
│   ├── __init__.py
│   └── gantt.py            # Funkcje pomocnicze wykresów Gantta
│
├── tests/
│   ├── test_planner.py     # Testy jednostkowe algorytmu planowania
│   ├── test_simulation.py  # Symulacje Monte Carlo + testy property-based
│   ├── test_optimizer.py   # Testy solvera optymalnego
│   ├── test_simulate.py    # Testy symulacji wielodniowej
│   ├── test_gantt.py       # Testy wykresu Gantta
│   ├── test_visual.py      # Testy atlasu ikon / mapy
│   ├── test_app_smoke.py   # Smoke test całej aplikacji Streamlit
│   └── _helpers.py         # Wspólne asercje niezmienników harmonogramu
│
├── assets/
│   ├── wind-turbine.png    # Ikona turbiny
│   ├── port.png            # Ikona portu
│   ├── statek.png          # Ikona statku
│   └── icons.png           # Atlas ikon (generowany automatycznie przez Pillow)
│
├── logs/
│   └── animation.log       # Logi aplikacji (rotating, maks. 3 × 2 MB)
│
└── packaging/
    ├── build_exe.bat        # Skrypt budowania .exe (cmd)
    ├── build_exe.ps1        # Skrypt budowania .exe (PowerShell)
    ├── installer.iss        # Konfiguracja instalatora Inno Setup
    └── README_BUILD.md      # Instrukcja budowania dystrybucji
```

---

## Pełna dokumentacja

Szczegółowa instrukcja obsługi (interfejs, algorytm planowania, pojęcia, rozwiązywanie problemów):
[INSTRUKCJA.md](INSTRUKCJA.md)

Historia zmian i numeracja wersji: [CHANGELOG.md](CHANGELOG.md)
Licencja i informacje o bibliotekach zewnętrznych: [LICENSE.txt](LICENSE.txt), [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md)

---

*Projekt zgodny z celami SDG 7 (czysta energia), SDG 9 (innowacje), SDG 13 (działania klimatyczne).*

# Offshore Mentor

**Interaktywny symulator logistyki serwisowania morskich farm wiatrowych offshore**

Aplikacja odwzorowuje realne wyzwania operacyjne: planowanie napraw turbin z uwzględnieniem prognoz pogody, dostępności statków serwisowych (CTV), czasu tranzytu i kosztów operacji. Kontekst – polska energetyka wiatrowa na Bałtyku (cel 18+ GW do 2040 r.).

---

## Funkcje

- Generowanie losowych usterek turbin w wybranej lokalizacji na Bałtyku
- Generowanie okien pogodowych (Hs, prędkość wiatru) i planowanie napraw algorytmem zachłannym
- Interaktywna mapa pydeck z ikonami turbin i portu bazowego (Ustka)
- Animacja ruchu statku serwisowego: port → turbina → port
- Wykres Gantta z harmonogramem zaplanowanych operacji
- KPI: zaplanowane/niezaplanowane naprawy, szacowany koszt [PLN]
- Obsługa trybu wysokiego kontrastu
- Wersja desktopowa `.exe` (PyInstaller + Inno Setup)

---

## Wymagania

| Pakiet | Rola |
|--------|------|
| `streamlit` | Framework interfejsu webowego |
| `pandas` | Przetwarzanie danych tabelarycznych |
| `altair` | Wykresy (Gantt) |
| `pydeck` | Mapa interaktywna (deck.gl) |
| `pillow` | Generowanie atlasu ikon (wymagane) |
| `ruff` | Formatowanie kodu (dla deweloperów) |

Python **3.10+**, Windows 10/11 / Linux / macOS.

---

## Szybki start

### 1. Zainstaluj zależności

```powershell
python -m pip install -r requirements.txt
```

### 2. Uruchom aplikację

```powershell
python -m streamlit run streamlit_app.py
```

Przeglądarka otworzy się automatycznie pod adresem `http://localhost:8501`.

> **Windows:** jeśli `streamlit` nie jest rozpoznawany, używaj zawsze `python -m streamlit run ...`

### Wirtualne środowisko (zalecane)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

---

## Uruchomienie jako plik .exe (Windows)

Jeśli korzystasz z wersji spakowanej (`dist/OffShoreMentor/`):

```
OffShoreMentor.exe
```

Aplikacja uruchamia wbudowany serwer Streamlit i otwiera przeglądarkę automatycznie.
Instrukcja budowania pliku wykonywalnego: [packaging/README_BUILD.md](packaging/README_BUILD.md).

---

## Struktura projektu

```
OffShore/
├── streamlit_app.py        # Punkt wejścia aplikacji
├── launcher.py             # Uruchamiacz dla wersji .exe (PyInstaller)
├── requirements.txt        # Zależności
├── OffShoreMentor.spec     # Konfiguracja PyInstaller
│
├── planner/
│   ├── __init__.py
│   └── plan.py             # Algorytm planowania + generatory danych
│
├── modules/
│   ├── __init__.py
│   └── visual.py           # Silnik animacji statku (pydeck)
│
├── viz/
│   ├── __init__.py
│   └── gantt.py            # Funkcje pomocnicze wykresów Gantta
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

---

*Projekt zgodny z celami SDG 7 (czysta energia), SDG 9 (innowacje), SDG 13 (działania klimatyczne).*

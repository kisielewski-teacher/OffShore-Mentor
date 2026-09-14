# Instrukcja obsługi – Offshore Mentor

**Symulator planowania serwisowania farm wiatrowych offshore**

---

## Spis treści

1. [Opis aplikacji](#1-opis-aplikacji)
2. [Wymagania systemowe](#2-wymagania-systemowe)
3. [Instalacja](#3-instalacja)
4. [Uruchomienie](#4-uruchomienie)
5. [Interfejs użytkownika](#5-interfejs-użytkownika)
6. [Kluczowe pojęcia](#6-kluczowe-pojęcia)
7. [Algorytm planowania](#7-algorytm-planowania)
8. [Struktura projektu](#8-struktura-projektu)
9. [Rozwiązywanie problemów](#9-rozwiązywanie-problemów)

---

## 1. Opis aplikacji

**Offshore Mentor** to interaktywny symulator logistyki serwisowania morskich farm wiatrowych. Aplikacja odwzorowuje realne wyzwania operacyjne: planowanie napraw turbin z uwzględnieniem prognoz pogody, dostępności statków serwisowych, czasu tranzytu i kosztów operacji.

### Co robi aplikacja

- Generuje losowe usterki turbin w wybranej lokalizacji na Bałtyku
- Generuje okna pogodowe (okresy, gdy warunki morskie pozwalają na pracę)
- Planuje naprawy – przydziela statki do usterek zgodnie z priorytetami i dostępnymi oknami
- Wyświetla wyniki na mapie interaktywnej, wykresie Gantta i w tabeli
- Animuje ruch statku serwisowego na trasie port → turbina → port

### Kontekst

Polska planuje rozbudowę morskiej energetyki wiatrowej do **18+ GW do 2040 r.** Porty Ustka, Łeba i Gdynia będą bazami serwisowymi dla tych instalacji. Aplikacja uczy planowania operacji w warunkach realnych ograniczeń: zmiennej pogody, kosztów dobowych statków i priorytetów awarii.

---

## 2. Wymagania systemowe

| Wymaganie | Minimalna wersja |
|-----------|-----------------|
| Python | 3.10 lub nowszy |
| System operacyjny | Windows 10/11, Linux, macOS |
| RAM | 512 MB |
| Połączenie internetowe | Wymagane tylko przy pierwszym uruchomieniu (pobieranie kafelków mapy) |

---

## 3. Instalacja

### Krok 1 – Pobierz Python

Jeśli Python nie jest zainstalowany, pobierz go ze strony [python.org](https://www.python.org/downloads/).
Podczas instalacji zaznacz opcję **"Add Python to PATH"**.

### Krok 2 – Utwórz wirtualne środowisko (zalecane)

```powershell
python -m venv .venv
.venv\Scripts\activate
```

Na Linux/macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Krok 3 – Zainstaluj zależności

```powershell
pip install -r requirements.txt
```

Zainstalowane pakiety:
| Pakiet | Rola |
|--------|------|
| `streamlit` | Framework interfejsu webowego |
| `pandas` | Przetwarzanie danych tabelarycznych |
| `altair` | Wykresy (Gantt) |
| `pydeck` | Mapa interaktywna (deck.gl) |
| `ruff` | Formatowanie kodu (tylko dla deweloperów) |

Opcjonalnie (lepsza jakość ikon na mapie):
```powershell
pip install pillow
```

---

## 4. Uruchomienie

```powershell
python -m streamlit run streamlit_app.py
```

Jeśli środowisko wirtualne jest aktywne (`.venv\Scripts\activate`), działa też krótsza forma:

```powershell
streamlit run streamlit_app.py
```

> **Uwaga dla Windows:** Jeśli pojawia się błąd `'streamlit' is not recognized`, użyj zawsze `python -m streamlit run streamlit_app.py`.

Po chwili przeglądarka otworzy się automatycznie pod adresem:

```
http://localhost:8501
```

Jeśli przeglądarka nie otworzy się sama, skopiuj adres z terminala i wklej go ręcznie.

### Uruchomienie jako plik wykonywalny (Windows)

Jeśli korzystasz z wersji spakowanej przez PyInstaller (`dist/OffShoreMentor/`), uruchom:

```
OffShoreMentor.exe
```

Aplikacja uruchomi wbudowany serwer Streamlit i otworzy przeglądarkę automatycznie.

---

## 5. Interfejs użytkownika

### Panel parametrów (górna sekcja)

Po uruchomieniu aplikacji widoczne są suwaki i przełączniki konfiguracji symulacji.

#### Lewa kolumna

| Parametr | Zakres | Opis |
|----------|--------|------|
| **Liczba usterek** | 10–80 | Ile turbin ma losowe awarie do zaplanowania |
| **Próg Hs [m]** | 0,5–3,0 m | Maksymalna dopuszczalna wysokość fali znaczącej (Hs); im niższy próg, tym mniej dostępnych okien |

#### Środkowa kolumna

| Parametr | Zakres | Opis |
|----------|--------|------|
| **Próg wiatru [m/s]** | 5–20 m/s | Maksymalna dopuszczalna prędkość wiatru; im niższy próg, tym trudniej o okno |
| **Dzień pracy = 8h** | Tak/Nie | Jeśli zaznaczone, koszty liczone są na podstawie 8-godzinnych dni roboczych; odznaczone = 24 h |

#### Prawa kolumna

| Parametr | Opis |
|----------|------|
| **Tryb wysoki kontrast** | Jaśniejsze kolory i grubsze linie – przydatne przy prezentacji lub słabym oświetleniu |
| **Szybkość animacji [kl/s]** | Ile klatek na sekundę renderuje animacja statku (1–20) |
| **Start symulacji** | Uruchamia planowanie i generuje wszystkie wyniki |

> **Wskazówka:** Zacznij od domyślnych ustawień (30 usterek, Hs ≤ 1,5 m, wiatr ≤ 15 m/s) i kliknij **Start symulacji**.

---

### Sekcja KPI – Kluczowe wskaźniki

Po uruchomieniu symulacji pojawiają się trzy metryki:

| Metryka | Znaczenie |
|---------|-----------|
| **Zaplanowane naprawy** | Liczba usterek, do których udało się przydzielić statek i okno pogodowe |
| **Niezaplanowane** | Usterki, które nie mieszczą się w żadnym dostępnym oknie (np. zbyt surowe progi) |
| **Szac. koszt [PLN]** | Łączny koszt operacji serwisowych obliczony na podstawie dobowych stawek statków |

---

### Mapa turbin i portu bazowego

Interaktywna mapa (otwarta na Morzu Bałtyckim) pokazuje:

- **Niebieskie punkty** – turbiny z usterkami
- **Żółty punkt** – port bazowy (Ustka, 54.580°N, 16.860°E)
- **Czerwony punkt** – aktualnie wybrana turbina (wyróżnienie)

#### Wybór turbiny do trasy

Lista rozwijana **„Wybierz turbinę do trasy port → turbina"** pozwala wskazać konkretną usterkę. Aplikacja obliczy:

- Odległość port–turbina [km]
- Czas tranzytu [h] przy prędkości pierwszego statku z floty
- Status pogodowy: czy istnieje okno, w którym operacja jest wykonalna

---

### Animacja ruchu statku

Poniżej mapy statycznej widoczna jest sekcja animacji:

1. Kliknij **▶️ Start animacji** – statek (zielony punkt) rusza z portu w kierunku wybranej turbiny.
2. Kliknij **⏹️ Stop animacji** – zatrzymuje ruch.
3. Animacja wykonuje pełny rejs tam i z powrotem, a następnie zatrzymuje się automatycznie.

Szybkość animacji reguluje suwak **Szybkość animacji** w panelu parametrów.

---

### Harmonogram napraw – wykres Gantta

Wykres Gantta pokazuje zaplanowane operacje w funkcji czasu:

- **Oś X** – czas w godzinach od startu horyzontu planowania
- **Oś Y** – identyfikator usterki (F001, F002 …)
- **Kolor belki** – przydzielony statek serwisowy
- **Długość belki** – czas trwania operacji (tranzyt + naprawa + powrót)

Najeżdżając kursorem na belkę, zobaczysz szczegółowy tooltip:

| Pole | Opis |
|------|------|
| `fault_id` | Identyfikator usterki |
| `turbine_id` | Turbina |
| `vessel_name` | Przydzielony statek |
| `start` / `end` | Godzina startu i zakończenia [h] |
| `cost_pln` | Koszt tej operacji [PLN] |
| `distance_km` | Odległość od portu |
| `transit_h` | Czas tranzytu (1 kierunek) |

---

### Tabela harmonogramu

Pełna tabela wszystkich usterek z wynikami planowania. Usterki bez przydzielonego statku mają puste pola `start`, `end`, `vessel_name` i notatkę `niezaplanowane (brak okna/zasobu)`.

---

## 6. Kluczowe pojęcia

### Usterka (Fault)

Zdarzenie serwisowe na turbinie. Parametry:

| Pole | Opis |
|------|------|
| `fault_id` | Unikalny identyfikator (np. F001) |
| `turbine_id` | Identyfikator turbiny (np. T001) |
| `reported_h` | Godzina zgłoszenia usterki od startu horyzontu |
| `repair_hours` | Szacowany czas naprawy na miejscu [h] |
| `priority` | Priorytet 1 (najwyższy) – 3 (najniższy) |
| `lat`, `lon` | Współrzędne geograficzne turbiny |

### Okno pogodowe (Weather Window)

Przedział czasu, w którym warunki morskie są bezpieczne dla operacji serwisowych.

| Pole | Opis |
|------|------|
| `win_id` | Identyfikator okna (np. W001) |
| `start` / `end` | Początek i koniec okna [h] |
| `hs_m` | Wysokość fali znaczącej [m] |
| `wind_ms` | Prędkość wiatru [m/s] |

Okno jest **sprzyjające**, gdy `hs_m ≤ Próg Hs` i `wind_ms ≤ Próg wiatru`.

### Statek serwisowy (CTV – Crew Transfer Vessel)

Flota zawiera 3 statki o różnych parametrach:

| Statek | Prędkość | Zesp. | Koszt dobowy |
|--------|----------|-------|--------------|
| Baltic Hawk | 12 kn | 2 | 45 000 PLN |
| North Star | 10 kn | 1 | 32 000 PLN |
| Sea Falcon | 14 kn | 2 | 58 000 PLN |

### Tranzyt

Czas przejazdu portu do turbiny obliczany wzorem haversine (odległość sferyczna) podzielony przez prędkość statku. Pełna operacja = tranzyt + naprawa + powrót.

### Wysokość fali znaczącej (Hs)

Statystyczna miara stanu morza: średnia z jednej trzeciej najwyższych fal. Standardowy próg dla operacji CTV to **Hs ≤ 1,5 m**.

---

## 7. Algorytm planowania

Planowanie odbywa się metodą zachłanną (greedy heuristic):

1. **Sortowanie usterek** według priorytetu (1 → 3), a następnie czasu zgłoszenia.
2. Dla każdej usterki – iteracja po oknach pogodowych (od najwcześniejszego).
3. Dla każdego okna – iteracja po statkach.
4. Sprawdzenie **warunków feasibility**:
   - Okno spełnia progi Hs i wiatru
   - Operacja (tranzyt + naprawa + powrót) mieści się w oknie
   - Statek jest wolny (żaden jego slot nie jest zajęty)
5. Jeśli wszystkie warunki spełnione → przydziel statek i zajmij sloty.
6. Usterki bez możliwości przydziału → oznaczone jako niezaplanowane.

**Koszt operacji** = `ceil(czas_operacji / godziny_dnia_pracy) × koszt_dobowy_statku`

---

## 8. Struktura projektu

```
OffShore/
├── streamlit_app.py        # Główna aplikacja – punkt wejścia
├── requirements.txt        # Lista zależności
├── INSTRUKCJA.md           # Ten plik
├── README.md               # Skrócona instrukcja startowa
├── launcher.py             # Uruchamiacz dla wersji .exe (PyInstaller)
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
│   └── gantt.py            # Pomocnicze funkcje wykresów Gantta
│
├── assets/
│   ├── wind-turbine.png    # Ikona turbiny
│   ├── port.png            # Ikona portu
│   ├── statek.png          # Ikona statku
│   └── icons.png           # Atlas ikon (generowany automatycznie)
│
├── logs/
│   └── animation.log       # Logi aplikacji (rotating, maks. 3 × 2 MB)
│
└── packaging/
    └── README_BUILD.md     # Instrukcja budowania .exe i instalatora
```

---

## 9. Rozwiązywanie problemów

### `ModuleNotFoundError: No module named 'streamlit'`

Nie zainstalowano zależności lub nie aktywowano środowiska wirtualnego.

```powershell
.venv\Scripts\activate
pip install -r requirements.txt
```

### Mapa nie wyświetla się / jest biała

Pydeck wymaga połączenia internetowego do pobrania kafelków tła mapy. Sprawdź połączenie i odśwież stronę (F5).

### Punkty turbiny niewidoczne na mapie

Zdarza się przy pierwszym uruchomieniu gdy atlas ikon jest generowany. Odśwież stronę po zakończeniu symulacji. Jeśli problem utrzymuje się, zainstaluj `Pillow`:

```powershell
pip install pillow
```

### Animacja się nie uruchamia

Kliknij **Start symulacji** i poczekaj aż wyniki się załadują, a dopiero potem kliknij **▶️ Start animacji**.

### Błąd przy uruchomieniu z PyInstaller (wersja .exe)

Upewnij się, że uruchamiasz `OffShoreMentor.exe` z katalogu `dist/OffShoreMentor/` (nie przenosisz samego pliku .exe bez pozostałych plików).

### Wykres Gantta pusty – „Brak zaplanowanych napraw"

Progi pogodowe są za restrykcyjne. Spróbuj:
- Zwiększyć **Próg Hs** (np. do 2,5 m)
- Zwiększyć **Próg wiatru** (np. do 18 m/s)
- Zmniejszyć **Liczbę usterek**

### Logi diagnostyczne

Szczegółowe logi aplikacji zapisywane są w pliku `logs/animation.log`. Przy problemach z mapą lub animacją zajrzyj tam po informacje diagnostyczne.

---

*Projekt zgodny z celami SDG 7 (czysta energia), SDG 9 (innowacje), SDG 13 (działania klimatyczne).*

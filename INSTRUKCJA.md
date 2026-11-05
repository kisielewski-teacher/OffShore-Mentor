# Instrukcja obsługi – Offshore Mentor

Symulator planowania serwisowania farm wiatrowych offshore

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
9. [Testy](#9-testy)
10. [Rozwiązywanie problemów](#10-rozwiązywanie-problemów)

---

## 1. Opis aplikacji

**Offshore Mentor** to interaktywny symulator logistyki serwisowania morskich farm wiatrowych. Aplikacja odwzorowuje realne wyzwania operacyjne: planowanie napraw turbin z uwzględnieniem prognoz pogody, dostępności statków serwisowych, czasu tranzytu i kosztów operacji.

### Co robi aplikacja

Aplikacja ma dwa tryby, dostępne jako zakładki: **Symulacja jednorazowa** i **Symulacja wielodniowa**.

W zakładce **Symulacja jednorazowa**:

- Generuje losowe usterki turbin w wybranej lokalizacji na Bałtyku
- Generuje okna pogodowe (okresy, gdy warunki morskie pozwalają na pracę)
- Planuje naprawy – przydziela statki do usterek zgodnie z priorytetami i dostępnymi oknami (algorytm zachłanny)
- Wyświetla wyniki na mapie interaktywnej, wykresie Gantta i w tabeli
- Animuje ruch statku serwisowego na trasie port → turbina → port
- Na żądanie liczy **rozwiązanie optymalne** (solver MIP PuLP/CBC) i porównuje je z heurystyką pod względem kosztu i liczby niezaplanowanych usterek

W zakładce **Symulacja wielodniowa**:

- Symuluje napływ usterek dzień po dniu na zadanym horyzoncie (rolling horizon)
- Codziennie przelicza plan na podstawie nierozwiązanego backlogu
- Pokazuje, czy flota „nadąża" z naprawami (backlog się stabilizuje) czy nie (backlog rośnie bez końca)
- Wyświetla wykresy backlogu w czasie, nowych vs. rozwiązanych usterek, kosztu skumulowanego oraz harmonogram zrealizowanych napraw

### Kontekst

Polska planuje rozbudowę morskiej energetyki wiatrowej do **18+ GW do 2040 r.** Porty Ustka, Łeba i Gdynia będą bazami serwisowymi dla tych instalacji. Aplikacja uczy planowania operacji w warunkach realnych ograniczeń: zmiennej pogody, kosztów dobowych statków i priorytetów awarii.

---

## 2. Wymagania systemowe

| Wymaganie | Minimalna wersja |
| --- | --- |
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
| --- | --- |
| `streamlit` | Framework interfejsu webowego |
| `pandas` | Przetwarzanie danych tabelarycznych |
| `altair` | Wykresy (Gantt, backlog, koszt skumulowany) |
| `pydeck` | Mapa interaktywna (deck.gl) |
| `pillow` | Generowanie atlasu ikon na mapie (ma fallback, jeśli brak) |
| `pulp` | Solver MIP (CBC) dla rozwiązania optymalnego |
| `ruff` | Formatowanie kodu (tylko dla deweloperów) |

> Do uruchamiania testów (patrz [9. Testy](#9-testy)) doinstaluj dodatkowo `requirements-dev.txt`:
>
> ```powershell
> pip install -r requirements-dev.txt
> ```

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

```text
http://localhost:8501
```

Jeśli przeglądarka nie otworzy się sama, skopiuj adres z terminala i wklej go ręcznie.

### Uruchomienie jako plik wykonywalny (Windows)

Jeśli korzystasz z wersji spakowanej przez PyInstaller (`dist/OffShoreMentor/`), uruchom:

```powershell
OffShoreMentor.exe
```

Aplikacja uruchomi wbudowany serwer Streamlit i otworzy przeglądarkę automatycznie.

---

## 5. Interfejs użytkownika

### Panel parametrów (górna sekcja)

Po uruchomieniu aplikacji widoczne są suwaki i przełączniki konfiguracji symulacji.

#### Lewa kolumna

| Parametr | Zakres | Opis |
| --- | --- | --- |
| **Liczba usterek** | 10–80 | Ile turbin ma losowe awarie do zaplanowania |
| **Próg Hs [m]** | 0,5–3,0 m | Maksymalna dopuszczalna wysokość fali znaczącej (Hs); im niższy próg, tym mniej dostępnych okien |

#### Środkowa kolumna

| Parametr | Zakres | Opis |
| --- | --- | --- |
| **Próg wiatru [m/s]** | 5–20 m/s | Maksymalna dopuszczalna prędkość wiatru; im niższy próg, tym trudniej o okno |
| **Dzień pracy = 8h** | Tak/Nie | Jeśli zaznaczone, koszty liczone są na podstawie 8-godzinnych dni roboczych; odznaczone = 24 h |

#### Prawa kolumna

| Parametr | Opis |
| --- | --- |
| **Tryb wysoki kontrast** | Jaśniejsze kolory i grubsze linie – przydatne przy prezentacji lub słabym oświetleniu |
| **Szybkość animacji [kl/s]** | Ile klatek na sekundę renderuje animacja statku (1–20) |
| **Start symulacji** | Uruchamia planowanie i generuje wszystkie wyniki |

> **Wskazówka:** Zacznij od domyślnych ustawień (30 usterek, Hs ≤ 1,5 m, wiatr ≤ 15 m/s) i kliknij **Start symulacji**.

Progi Hs i wiatru oraz przełącznik dnia pracy są współdzielone przez obie zakładki opisane niżej.

---

### Zakładki

Poniżej panelu parametrów aplikacja dzieli się na dwie zakładki:

| Zakładka | Zawartość |
| --- | --- |
| **Symulacja jednorazowa** | KPI, mapa, animacja statku, wykres Gantta, tabela harmonogramu, porównanie z rozwiązaniem optymalnym – opisane w podrozdziałach poniżej |
| **Symulacja wielodniowa** | Symulacja rolling horizon – nowe usterki napływają dzień po dniu, plan jest przeliczany na bieżąco – opisana w [Zakładka: Symulacja wielodniowa](#zakładka-symulacja-wielodniowa) |

---

### Zakładka: Symulacja jednorazowa – Sekcja KPI

Po uruchomieniu symulacji pojawiają się trzy metryki:

| Metryka | Znaczenie |
| --- | --- |
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
| --- | --- |
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

### Porównanie z rozwiązaniem optymalnym

Pod tabelą harmonogramu znajduje się przycisk **„Porównaj z rozwiązaniem optymalnym (PuLP)"**. Uruchamia on solver MIP (PuLP/CBC), który liczy (near-)optymalny harmonogram tego samego problemu (te same usterki, okna i statki) i pokazuje, ile heurystyka „traci” względem prawdziwego optimum.

- Przycisk jest **wyłączony**, gdy liczba usterek przekracza limit solvera (40) – ILP na dużej liczbie usterek mógłby zawiesić UI na dłuższy czas. Zmniejsz **Liczbę usterek** i uruchom symulację ponownie, aby porównanie było dostępne.
- Solver ma limit czasu obliczeń (8 s); jeśli go nie zmieści, zwraca najlepsze dotąd znalezione rozwiązanie (nie zawsze dowiedzione optimum).

Po obliczeniu wyniku pojawiają się metryki:

| Metryka | Znaczenie |
| --- | --- |
| **Koszt (heurystyka)** | Koszt z algorytmu zachłannego (ten sam co w sekcji KPI) |
| **Koszt (optymalny)** | Koszt z rozwiązania solvera; delta pokazuje różnicę względem heurystyki |
| **Niezaplanowane (optymalny)** | Liczba usterek bez przydziału w rozwiązaniu solvera; delta względem heurystyki |

Znaczek pod metrykami pokazuje status solvera:

| Status | Znaczenie |
| --- | --- |
| ✅ optimum dowiedzione | Solver znalazł i udowodnił optimum przed upływem limitu czasu |
| ⏱️ najlepsze znalezione (limit czasu) | Solver nie zdążył dowieść optimum – zwrócił najlepsze znalezione rozwiązanie |
| ⛔ brak rozwiązania | Problem jest niewykonalny dla podanych ograniczeń |
| ⛔ brak wykonalnych kombinacji | Żadna trójka (usterka, okno, statek) nie spełnia progów pogodowych/harmonogramu |

Obok statusu wyświetlany jest czas obliczeń solvera i liczba rozważonych kandydatów.

---

### Zakładka: Symulacja wielodniowa

Druga zakładka symuluje harmonogram dzień po dniu (rolling horizon): usterki napływają w czasie na cały horyzont, a plan jest przeliczany codziennie na podstawie nierozwiązanego backlogu. Pokazuje, czy flota „nadąża” z naprawami, czy backlog rośnie bez końca.

#### Parametry symulacji wielodniowej

| Parametr | Zakres | Opis |
| --- | --- | --- |
| **Liczba dni symulacji** | 7–30 | Długość symulowanego horyzontu |
| **Liczba usterek (cały horyzont)** | 20–300 | Łączna liczba usterek napływających w trakcie całej symulacji |
| **Liczba statków w flocie** | 1–6 | Rozmiar floty CTV użytej w symulacji (rozszerza domyślną flotę 3 statków) |

Progi Hs, wiatru i tryb dnia pracy z górnego panelu parametrów obowiązują także tutaj. Przycisk **„Uruchom symulację wielodniową”** startuje symulację; pasek postępu pokazuje aktualnie przetwarzany dzień.

#### Wyniki

| Element | Opis |
| --- | --- |
| **KPI** | Rozwiązane naprawy (suma), backlog na koniec horyzontu, łączny koszt [PLN] |
| **Wykres: Backlog w czasie** | Liczba usterek czekających w kolejce na koniec każdego dnia |
| **Wykres: Nowe vs. rozwiązane usterki per dzień** | Porównanie napływu i tempa realizacji napraw dzień po dniu |
| **Wykres: Koszt skumulowany** | Narastający koszt operacji w czasie |
| **Harmonogram zrealizowanych napraw (Gantt)** | Wykres Gantta analogiczny do zakładki jednorazowej, ale tylko dla napraw faktycznie zrealizowanych w symulacji |
| **Dziennik symulacji** | Tabela dzień po dniu: nowe usterki, rozwiązane, backlog, koszt dnia, koszt skumulowany |

> **Uwaga:** Symulacja wielodniowa używa wyłącznie heurystyki zachłannej (nie solvera MIP) – przeliczanie rozwiązania optymalnego co symulowany dzień byłoby zbyt wolne dla płynnego demo.

---

## 6. Kluczowe pojęcia

### Usterka (Fault)

Zdarzenie serwisowe na turbinie. Parametry:

| Pole | Opis |
| --- | --- |
| `fault_id` | Unikalny identyfikator (np. F001) |
| `turbine_id` | Identyfikator turbiny (np. T001) |
| `reported_h` | Godzina zgłoszenia usterki od startu horyzontu |
| `repair_hours` | Szacowany czas naprawy na miejscu [h] |
| `priority` | Priorytet 1 (najwyższy) – 3 (najniższy) |
| `lat`, `lon` | Współrzędne geograficzne turbiny |

### Okno pogodowe (Weather Window)

Przedział czasu, w którym warunki morskie są bezpieczne dla operacji serwisowych.

| Pole | Opis |
| --- | --- |
| `win_id` | Identyfikator okna (np. W001) |
| `start` / `end` | Początek i koniec okna [h] |
| `hs_m` | Wysokość fali znaczącej [m] |
| `wind_ms` | Prędkość wiatru [m/s] |

Okno jest **sprzyjające**, gdy `hs_m ≤ Próg Hs` i `wind_ms ≤ Próg wiatru`.

### Statek serwisowy (CTV – Crew Transfer Vessel)

Domyślna flota zawiera 3 statki o różnych parametrach:

| Statek | Prędkość | Zesp. | Koszt dobowy |
| --- | --- | --- | --- |
| Baltic Hawk | 12 kn | 2 | 45 000 PLN |
| North Star | 10 kn | 1 | 32 000 PLN |
| Sea Falcon | 14 kn | 2 | 58 000 PLN |

W zakładce **Symulacja wielodniowa** flotę można powiększyć do 6 statków – dodatkowe jednostki (np. „Baltic Hawk II") powielają parametry powyższych trzech wzorców.

### Tranzyt

Czas przejazdu portu do turbiny obliczany wzorem haversine (odległość sferyczna) podzielony przez prędkość statku. Pełna operacja = tranzyt + naprawa + powrót.

### Wysokość fali znaczącej (Hs)

Statystyczna miara stanu morza: średnia z jednej trzeciej najwyższych fal. Standardowy próg dla operacji CTV to **Hs ≤ 1,5 m**.

### Backlog

Zbiór usterek jeszcze nieprzydzielonych do żadnego statku/okna. W symulacji jednorazowej to po prostu usterki z pustym `start` w tabeli harmonogramu. W symulacji wielodniowej backlog kumuluje się i jest przeliczany na nowo każdego dnia – jego wielkość na koniec horyzontu pokazuje, czy flota nadąża z naprawami.

### Rozwiązanie optymalne (solver MIP)

Alternatywa dla heurystyki zachłannej: ten sam problem (usterki, okna, statki) zamodelowany jako zadanie programowania całkowitoliczbowego (MIP) i rozwiązany solverem PuLP/CBC. W przeciwieństwie do heurystyki, która przydziela pierwsze pasujące okno/statek, solver przeszukuje wszystkie wykonalne kombinacje i minimalizuje łączny koszt oraz ważoną priorytetem liczbę niezaplanowanych usterek jednocześnie.

---

## 7. Algorytm planowania

### 7.1 Heurystyka zachłanna (`planner/plan.py`)

Domyślne planowanie (obie zakładki) odbywa się metodą zachłanną (greedy heuristic):

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

### 7.2 Solver optymalny (`planner/optimizer.py`)

Używany po kliknięciu **„Porównaj z rozwiązaniem optymalnym”** w zakładce jednorazowej:

1. Zbudowanie zbioru wszystkich wykonalnych trójek (usterka, okno, statek) – ta sama arytmetyka tranzytu/kosztu co w heurystyce, ale bez zatrzymania na pierwszym dopasowaniu.
2. Sformułowanie zadania MIP: zmienne binarne wyboru każdej trójki, ograniczenia braku nakładania się slotów statku oraz przydziału co najwyżej jednej trójki na usterkę.
3. Minimalizacja funkcji celu: koszt operacji + kara za niezaplanowane usterki ważona priorytetem (priorytet 1 = waga 3, priorytet 2 = waga 2, priorytet 3 = waga 1).
4. Rozwiązanie solverem CBC z limitem czasu 8 s i limitem liczby usterek 40 (patrz [Porównanie z rozwiązaniem optymalnym](#porównanie-z-rozwiązaniem-optymalnym)).

### 7.3 Symulacja wielodniowa – rolling horizon (`planner/simulate.py`)

Używana w zakładce **Symulacja wielodniowa**:

1. Symulacja przechodzi dzień po dniu (0…liczba dni − 1).
2. Każdego dnia do backlogu dodawane są usterki zgłoszone w tym dniu (`reported_h` w przedziale doby).
3. Backlog jest przeliczany heurystyką zachłanną (7.1) na oknach pogodowych liczonych od bieżącego momentu, z zajętością statków przenoszoną między dniami.
4. Naprawy zaplanowane na dziś są „zatwierdzane" (committed); te zaplanowane na przyszłość wracają do backlogu i mogą zostać przeplanowane innego dnia/statkiem.
5. Po każdym dniu zapisywany jest snapshot: nowe usterki, rozwiązane dziś, backlog po dniu, koszt dnia i skumulowany.

Symulacja wielodniowa celowo używa wyłącznie heurystyki (nigdy solvera MIP) – przeliczanie ILP co dzień symulacji byłoby zbyt wolne dla płynnego demo.

---

## 8. Struktura projektu

```text
OffShore/
├── streamlit_app.py        # Główna aplikacja – punkt wejścia
├── requirements.txt        # Zależności runtime
├── requirements-dev.txt    # Dodatkowe zależności do testów (pytest, hypothesis)
├── INSTRUKCJA.md           # Ten plik
├── README.md               # Skrócona instrukcja startowa
├── launcher.py             # Uruchamiacz dla wersji .exe (PyInstaller)
├── OffShoreMentor.spec     # Konfiguracja PyInstaller
│
├── planner/
│   ├── __init__.py
│   ├── plan.py             # Algorytm planowania (heurystyka) + generatory danych
│   ├── optimizer.py        # Solver optymalny (PuLP/CBC) – porównanie z heurystyką
│   └── simulate.py         # Symulacja wielodniowa (rolling horizon)
│
├── modules/
│   ├── __init__.py
│   └── visual.py           # Silnik animacji statku (pydeck)
│
├── viz/
│   ├── __init__.py
│   └── gantt.py            # Pomocnicze funkcje wykresów Gantta
│
├── tests/
│   ├── test_planner.py     # Testy jednostkowe algorytmu planowania
│   ├── test_simulation.py  # Symulacje Monte Carlo + testy property-based (hypothesis)
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
│   └── icons.png           # Atlas ikon (generowany automatycznie)
│
├── logs/
│   └── animation.log       # Logi aplikacji (rotating, maks. 3 × 2 MB)
│
└── packaging/
    ├── build_exe.bat       # Skrypt budowania .exe (cmd)
    ├── build_exe.ps1       # Skrypt budowania .exe (PowerShell)
    ├── installer.iss       # Konfiguracja instalatora Inno Setup
    └── README_BUILD.md     # Instrukcja budowania .exe i instalatora
```

---

## 9. Testy

Projekt ma zestaw testów `pytest`: testy jednostkowe algorytmu planowania, symulacje Monte Carlo, testy property-based (`hypothesis`), testy solvera optymalnego i symulacji wielodniowej oraz smoke test całej aplikacji Streamlit.

```powershell
pip install -r requirements-dev.txt
python -m pytest -q
```

| Plik | Zakres |
| --- | --- |
| `test_planner.py` | Odległości, tranzyt, progi pogodowe, generatory danych, harmonogramowanie (`planner/plan.py`) |
| `test_simulation.py` | Symulacje Monte Carlo (wiele skal/nasion/progów) + fuzzing `hypothesis` sprawdzający niezmienniki harmonogramu (brak nakładania się rejsów statku, spójność kosztów, zgodność z oknami pogodowymi) |
| `test_optimizer.py` | Solver optymalny (`planner/optimizer.py`): przypadki z policzalnym optimum, brak kandydatów, przewaga nad heurystyką, niezmienniki |
| `test_simulate.py` | Symulacja wielodniowa (`planner/simulate.py`): backlog, koszt skumulowany, brak nakładania się statków w całej symulacji, mała vs. duża flota |
| `test_gantt.py` | Budowa wykresu Gantta (`viz/gantt.py`) |
| `test_visual.py` | Atlas ikon i logika mapowania ikon (`modules/visual.py`) |
| `test_app_smoke.py` | Uruchomienie całej aplikacji (`streamlit.testing.v1.AppTest`) przed i po kliknięciu „Start symulacji" |
| `_helpers.py` | Wspólne asercje niezmienników harmonogramu, reużywane przez powyższe pliki |

---

## 10. Rozwiązywanie problemów

### `ModuleNotFoundError: No module named 'streamlit'`

Nie zainstalowano zależności lub nie aktywowano środowiska wirtualnego.

```powershell
.venv\Scripts\activate
pip install -r requirements.txt
```

### Mapa nie wyświetla się / jest biała

Pydeck wymaga połączenia internetowego do pobrania kafelków tła mapy. Sprawdź połączenie i odśwież stronę (F5).

### Punkty turbiny niewidoczne na mapie

Zdarza się przy pierwszym uruchomieniu gdy atlas ikon jest generowany. Odśwież stronę po zakończeniu symulacji. `Pillow` jest już w `requirements.txt`, więc jeśli problem utrzymuje się, sprawdź czy jest zainstalowany:

```powershell
pip install -r requirements.txt
```

Aplikacja działa też bez Pillow (fallback na prostsze kształty ikon), więc mapa nie powinna być pusta nawet bez tej biblioteki.

### Animacja się nie uruchamia

Kliknij **Start symulacji** i poczekaj aż wyniki się załadują, a dopiero potem kliknij **▶️ Start animacji**.

### Błąd przy uruchomieniu z PyInstaller (wersja .exe)

Upewnij się, że uruchamiasz `OffShoreMentor.exe` z katalogu `dist/OffShoreMentor/` (nie przenosisz samego pliku .exe bez pozostałych plików).

### Wykres Gantta pusty – „Brak zaplanowanych napraw"

Progi pogodowe są za restrykcyjne. Spróbuj:

- Zwiększyć **Próg Hs** (np. do 2,5 m)
- Zwiększyć **Próg wiatru** (np. do 18 m/s)
- Zmniejszyć **Liczbę usterek**

### Przycisk „Porównaj z rozwiązaniem optymalnym” jest nieaktywny

Liczba usterek przekracza limit solvera (40). Zmniejsz **Liczbę usterek** w panelu parametrów, uruchom symulację ponownie i spróbuj jeszcze raz.

### Błąd `ModuleNotFoundError: No module named 'pulp'` lub problem z solverem CBC

Doinstaluj zależności (`pulp` jest już w `requirements.txt`):

```powershell
pip install -r requirements.txt
```

Jeśli solver zwraca status „⏱️ najlepsze znalezione (limit czasu)” zamiast „✅ optimum dowiedzione”, to nie błąd – oznacza, że nie zmieścił się w limicie 8 s i zwrócił najlepsze dotąd znalezione rozwiązanie.

### Logi diagnostyczne

Szczegółowe logi aplikacji zapisywane są w pliku `logs/animation.log`. Przy problemach z mapą lub animacją zajrzyj tam po informacje diagnostyczne.

---

*Projekt zgodny z celami SDG 7 (czysta energia), SDG 9 (innowacje), SDG 13 (działania klimatyczne).*

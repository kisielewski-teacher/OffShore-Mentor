# Changelog

Wszystkie znaczące zmiany w projekcie Offshore Mentor są dokumentowane w tym
pliku.

Format oparty na [Keep a Changelog](https://keepachangelog.com/pl/1.0.0/),
a numeracja wersji zgodna z [Semantic Versioning](https://semver.org/lang/pl/)
(`MAJOR.MINOR.PATCH`):

- **MAJOR** — niekompatybilne zmiany (np. inny format zapisanych danych/scenariuszy).
- **MINOR** — nowe funkcje zachowujące kompatybilność wsteczną.
- **PATCH** — poprawki błędów, drobne usprawnienia, bez nowych funkcji.

Numer wersji w tym pliku musi być zsynchronizowany z:
`AppVersion` w [packaging/installer.iss](packaging/installer.iss) oraz
`filevers`/`prodvers`/`FileVersion`/`ProductVersion` w
[packaging/version_info.txt](packaging/version_info.txt).

## [Unreleased]

### Zmienione
- Przygotowanie projektu do sprzedaży: usunięto z repozytorium archiwalne
  materiały konkursowe (`Readme/`, `Readme_texts/`, prezentację), dodano
  `LICENSE.txt` (licencja własnościowa) i `THIRD_PARTY_LICENSES.md` (audyt
  licencji zależności pod kątem dystrybucji closed-source).
- Dodano ikonę aplikacji (`assets/icon.ico`) oraz osadzone metadane wersji
  Windows w pliku .exe (`packaging/version_info.txt`).
- Przypięto dokładne wersje zależności w `requirements.txt` /
  `requirements-dev.txt` dla powtarzalnych buildów; przeniesiono `ruff` do
  zależności deweloperskich.
- Wyłączono domyślną telemetrię Streamlit (`gatherUsageStats = false`).

## [1.0.0] — pierwsze wydanie

### Dodane
- Generowanie losowych usterek turbin w wybranej lokalizacji na Bałtyku.
- Generowanie okien pogodowych (Hs, prędkość wiatru) i planowanie napraw
  algorytmem zachłannym.
- Solver MIP (PuLP/CBC) liczący (near-)optymalny harmonogram do porównania
  z heurystyką zachłanną.
- Symulacja wielodniowa (rolling horizon) z wykresami backlogu i kosztu
  skumulowanego.
- Interaktywna mapa pydeck (ikony turbin, port bazowy Ustka) i animacja
  ruchu statku serwisowego.
- Wykres Gantta harmonogramu operacji, KPI (zaplanowane/niezaplanowane
  naprawy, szacowany koszt PLN), tryb wysokiego kontrastu.
- Wersja desktopowa `.exe` (PyInstaller + Inno Setup).
- Zestaw testów `pytest` (jednostkowe, Monte Carlo, property-based
  `hypothesis`, smoke test aplikacji Streamlit).

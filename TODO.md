# TODO – przygotowanie Offshore Mentor do sprzedaży

Ten plik śledzi zadania związane z czyszczeniem projektu, weryfikacją licencji
i przygotowaniem programu do sprzedaży. Ukończone punkty są usuwane z listy;
nowe wynikłe potrzeby są dopisywane.

Ostatnia aktualizacja: 2026-09-27 (wersja release bez okna konsoli + logowanie/dialog błędów)

## Do zrobienia — prawne / licencyjne

- [ ] `LICENSE.txt` to szablon — przed faktyczną sprzedażą uzupełnić dane autora/firmy, jurysdykcję, warunki wsparcia/zwrotów i **skonsultować z prawnikiem**.
- [ ] Przy każdej aktualizacji `requirements.txt` ponownie zweryfikować licencje nowych/zmienionych zależności (`pip show <pakiet>` lub `pip-licenses`).
- [ ] Zdecydować i spisać model sprzedaży (jednorazowa licencja / subskrypcja / liczba stanowisk) i odzwierciedlić to w `LICENSE.txt` oraz w materiałach sprzedażowych.

## Do zrobienia — pakowanie / dystrybucja (.exe, instalator)

- [ ] **Wymaga zakupu przez Ciebie:** certyfikat code-signing (OV/EV) od CA (np. DigiCert, Sectigo, SSL.com) — to jedyny krok, którego nie da się zautomatyzować (wymaga weryfikacji tożsamości firmy/autora przez CA i płatności). Skrypty budowania (`packaging/build_exe.ps1` — parametry `-CertPath`/`-CertPassword`, oraz `packaging/installer.iss` — sekcja `SignTool`) są już przygotowane do podpisywania .exe/instalatora, wystarczy podać certyfikat (instrukcja: `packaging/README_BUILD.md`, sekcja "Code signing"). Bez tego Windows SmartScreen będzie ostrzegał kupujących przy pierwszym uruchomieniu.
- [ ] `packaging/version_info.txt` (metadane wersji .exe) ma placeholder `CompanyName`/`LegalCopyright` = "Offshore Mentor" — uzupełnić realną nazwą firmy/autora (spójnie z `LICENSE.txt`) i synchronizować numer wersji przy każdym wydaniu z `AppVersion` w `installer.iss`.

## Do zrobienia — jakość / utrzymanie

- [ ] Brak CI (np. GitHub Actions) uruchamiającego `pytest` + `ruff` automatycznie przy każdym push/PR — zalecane przed sprzedażą, aby wyłapywać regresje.

## Do zrobienia — materiały sprzedażowe

- [ ] Przygotować krótki opis produktu / landing page / cennik (obecny `README.md` i `INSTRUKCJA.md` są dokumentacją techniczną, nie materiałem marketingowym).
- [ ] Przygotować zrzuty ekranu / demo wideo aplikacji do materiałów sprzedażowych.

## Do zrobienia — instalator / dystrybucja

- [ ] Repozytorium `kisielewski-teacher/OffShore-Mentor` jest **prywatne** — link z `instaluj.bat` zadziała u odbiorców dopiero po zmianie na publiczne (albo użyć wydania/hostingu pliku ZIP). Przed upublicznieniem sprawdzić, czy w historii nie ma danych poufnych.
- [ ] `instaluj.bat` pobiera gałąź `master`; po ustabilizowaniu przejść na tagowane wydania (GitHub Releases), żeby odbiorcy nie dostawali niedokończonych zmian.
- [ ] Przetestować `uruchom.bat` na komputerach uczniów z różnymi wersjami Pythona (3.10–3.14, 32-bit, Microsoft Store); gdy `requirements.txt` zostanie zaktualizowany, sprawdzić, czy nowe wersje mają gotowe pakiety (wheels) dla wszystkich obsługiwanych wersji Pythona.
- [ ] Zaktualizować dokumentację (`PODRECZNIK_UCZNIA.pdf` rozdz. 10–11, `INSTRUKCJA.md` rozdz. 3–4, `README.md`): instalacja przez `instaluj.bat` (link do wydania), skrót "OffShore Mentor" na pulpicie, automatyczna instalacja Pythona 3.12 i wymóg 64-bitowego Pythona 3.10–3.14. Po aktualizacji wysłać uczniom nową wersję podręcznika.

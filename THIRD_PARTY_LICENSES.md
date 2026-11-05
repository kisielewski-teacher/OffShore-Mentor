# Licencje bibliotek zewnętrznych (Third-Party Licenses)

Offshore Mentor jest oprogramowaniem własnościowym (zob. [LICENSE.txt](LICENSE.txt)),
ale korzysta z poniższych bibliotek open-source. Wszystkie wymienione licencje
są permisywne lub słabo copyleftowe (plikowo) i **pozwalają na dystrybucję
w produkcie zamkniętoźródłowym (closed-source)**, pod warunkiem zachowania
wymaganych informacji o prawach autorskich/licencji (co niniejszy plik
realizuje).

## Zależności uruchomieniowe (dystrybuowane razem z aplikacją / .exe)

| Biblioteka | Wersja (sprawdzona) | Licencja | Uwagi dot. komercyjnego użycia |
| --- | --- | --- | --- |
| [Streamlit](https://streamlit.io) | 1.54.0 | Apache-2.0 | Permisywna, wymaga zachowania noty copyright; brak wymogu ujawnienia kodu własnego |
| [pandas](https://pandas.pydata.org) | 2.3.3 | BSD-3-Clause | Permisywna |
| [Vega-Altair](https://altair-viz.github.io) | 6.0.0 | BSD-3-Clause | Permisywna |
| [pydeck](https://github.com/visgl/deck.gl) | 0.9.1 | Apache-2.0 | Permisywna |
| [Pillow](https://python-pillow.github.io) | 12.1.0 | MIT-CMU (HPND-style) | Permisywna, wywodzi się z libImaging/PIL |
| [PuLP](https://github.com/coin-or/pulp) | 3.3.2 | MIT | Permisywna |
| CBC (Coin-OR Branch and Cut) — solver MIP dołączany przez PuLP jako binarka | wg dystrybucji PuLP | EPL-2.0 (Eclipse Public License 2.0) | Słaby copyleft **plikowy** — dotyczy tylko plików źródłowych CBC. Aplikacja wywołuje CBC jako osobny proces (subprocess), nie linkuje ani nie modyfikuje jego kodu, więc dystrybucja niezmodyfikowanej binarki w produkcie closed-source jest dozwolona. Kod źródłowy CBC pozostaje publicznie dostępny na https://github.com/coin-or/Cbc |

## Zależności deweloperskie (NIE są dystrybuowane w produkcie/.exe)

| Biblioteka | Wersja | Licencja | Uwagi |
| --- | --- | --- | --- |
| [ruff](https://docs.astral.sh/ruff) | 0.15.0 | MIT | Tylko lint/format podczas developmentu |
| [pytest](https://pytest.org) | 9.1.1 | MIT | Tylko testy |
| [hypothesis](https://hypothesis.works) | 6.168.0 | MPL-2.0 | Tylko testy property-based. MPL-2.0 jest copyleftem plikowym — dotyczyłby tylko modyfikacji plików samej biblioteki hypothesis, których projekt nie modyfikuje. Ponieważ narzędzie to nie trafia do dystrybuowanego produktu, nie nakłada żadnych zobowiązań na kod aplikacji |

## Wniosek prawny (stan na dzień sprawdzenia)

Żadna z bibliotek wykorzystywanych w ścieżce uruchomieniowej (runtime) nie
wymaga: (a) ujawnienia kodu źródłowego aplikacji, (b) licencjonowania
aplikacji na tych samych warunkach (brak "strong copyleft" typu GPL/AGPL),
ani (c) opłat licencyjnych za redystrybucję. Wymagane jest jedynie zachowanie
niniejszych informacji o licencjach i prawach autorskich w dystrybuowanym
pakiecie (np. w folderze `dist/` obok pliku .exe) oraz w dokumentacji.

**Zalecenie:** przy każdej aktualizacji `requirements.txt` należy ponownie
zweryfikować licencje nowych/zaktualizowanych zależności (np. `pip-licenses`
lub ręcznie `pip show <pakiet>`), ponieważ niektóre pakiety zmieniają licencję
między wersjami.

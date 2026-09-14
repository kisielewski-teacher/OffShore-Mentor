"""Testy dymne (smoke tests) całej aplikacji Streamlit.

Uruchamiają streamlit_app.py w symulowanym środowisku Streamlit
(streamlit.testing.v1.AppTest) i sprawdzają, że skrypt wykonuje się
bez wyjątków - zarówno przed, jak i po uruchomieniu symulacji.
"""

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = str(Path(__file__).resolve().parents[1] / "streamlit_app.py")


def test_app_loads_without_exceptions_before_simulation():
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)
    assert not at.exception


def test_app_runs_simulation_without_exceptions():
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)
    assert not at.exception

    start_buttons = [b for b in at.button if b.label == "Start symulacji"]
    assert len(start_buttons) == 1

    start_buttons[0].click().run(timeout=30)
    assert not at.exception

    # KPI metrics should now be present with a schedule computed
    metric_labels = {m.label for m in at.metric}
    assert "Zaplanowane naprawy" in metric_labels
    assert "Niezaplanowane" in metric_labels
    assert "Szac. koszt [PLN]" in metric_labels


def test_app_simulation_survives_a_second_rerun():
    # Re-running the script (e.g. via a widget interaction) should keep
    # using the cached sim_data in session_state without re-raising.
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)
    at.button[0].click().run(timeout=30)
    assert not at.exception

    at.run(timeout=30)
    assert not at.exception

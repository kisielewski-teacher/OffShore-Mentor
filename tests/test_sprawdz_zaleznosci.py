"""Testy skryptu sprawdz_zaleznosci.py (uzywanego przez uruchom.bat)."""

import socket

import sprawdz_zaleznosci as sz


def _zajmij_port() -> tuple[socket.socket, int]:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("0.0.0.0", 0))
    s.listen()
    return s, s.getsockname()[1]


def test_port_wolny_wykrywa_zajety_port():
    s, port = _zajmij_port()
    try:
        assert sz.port_wolny(port) is False
    finally:
        s.close()


def test_znajdz_wolny_port_pomija_zajety():
    s, port = _zajmij_port()
    try:
        znaleziony = sz.znajdz_wolny_port(port, port + 20)
        assert znaleziony is not None
        assert znaleziony != port
        assert port < znaleziony <= port + 20
    finally:
        s.close()


def test_znajdz_wolny_port_none_gdy_wszystkie_zajete():
    s, port = _zajmij_port()
    try:
        assert sz.znajdz_wolny_port(port, port) is None
    finally:
        s.close()


def test_wymagania_sa_wczytywane_z_requirements():
    nazwy = {n for n, _ in sz.wczytaj_wymagania()}
    assert {"streamlit", "pandas", "pulp"} <= nazwy


def test_pliki_projektu_sa_komplet():
    assert sz.sprawdz_pliki() == []

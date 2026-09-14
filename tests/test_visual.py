from pathlib import Path

from modules import visual


def test_get_icon_mapping_three_slot_atlas(monkeypatch):
    monkeypatch.setattr(visual, "_ICON_ATLAS_WIDTH", 192)
    mapping = visual._get_icon_mapping()
    assert set(mapping.keys()) == {"wind", "port", "ship"}
    assert mapping["wind"]["x"] == 0
    assert mapping["port"]["x"] == 64
    assert mapping["ship"]["x"] == 128


def test_get_icon_mapping_two_slot_atlas(monkeypatch):
    monkeypatch.setattr(visual, "_ICON_ATLAS_WIDTH", 128)
    mapping = visual._get_icon_mapping()
    assert set(mapping.keys()) == {"wind", "ship"}
    assert mapping["wind"]["x"] == 0
    assert mapping["ship"]["x"] == 64


def test_get_icon_mapping_single_slot_atlas_maps_both_to_same_slot(monkeypatch):
    monkeypatch.setattr(visual, "_ICON_ATLAS_WIDTH", 64)
    mapping = visual._get_icon_mapping()
    assert mapping["wind"] == mapping["ship"]


def test_get_icon_mapping_none_width_falls_back_to_single_slot(monkeypatch):
    monkeypatch.setattr(visual, "_ICON_ATLAS_WIDTH", None)
    mapping = visual._get_icon_mapping()
    assert mapping["wind"] == mapping["ship"]


def test_ensure_icon_atlas_builds_atlas_from_asset_files(tmp_path, monkeypatch):
    static_dir = tmp_path / "static"
    monkeypatch.setattr(visual, "_STATIC_DIR", static_dir)
    # _ASSETS_DIR points at the real project assets, which contain the
    # three source PNGs (wind-turbine.png, port.png, statek.png).
    assert visual._ASSETS_DIR.exists()

    ok = visual._ensure_icon_atlas()

    assert ok is True
    atlas_path = static_dir / "icons.png"
    assert atlas_path.exists()
    assert atlas_path.stat().st_size > 0


def test_ensure_icon_atlas_is_idempotent_when_file_exists(tmp_path, monkeypatch):
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    atlas_path = static_dir / "icons.png"
    atlas_path.write_bytes(b"not-a-real-png-but-present")
    monkeypatch.setattr(visual, "_STATIC_DIR", static_dir)

    ok = visual._ensure_icon_atlas()

    assert ok is True
    # file untouched, no rebuild attempted
    assert atlas_path.read_bytes() == b"not-a-real-png-but-present"


def test_get_icon_atlas_url_returns_none_when_not_ready(tmp_path, monkeypatch):
    static_dir = tmp_path / "static"
    monkeypatch.setattr(visual, "_STATIC_DIR", static_dir)
    monkeypatch.setattr(visual, "_ICON_ATLAS_READY", False)
    assert visual._get_icon_atlas_url() is None


def test_get_icon_atlas_url_returns_path_when_ready(tmp_path, monkeypatch):
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "icons.png").write_bytes(b"fake")
    monkeypatch.setattr(visual, "_STATIC_DIR", static_dir)
    monkeypatch.setattr(visual, "_ICON_ATLAS_READY", True)

    url = visual._get_icon_atlas_url()

    assert url == str(static_dir / "icons.png")
    assert Path(url).exists()

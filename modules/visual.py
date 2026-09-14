import time
import streamlit as st
import pydeck as pdk
import pandas as pd
import logging
from pathlib import Path

_APP_ROOT = Path(__file__).resolve().parents[1]
_ASSETS_DIR = _APP_ROOT / "assets"
_STATIC_DIR = _APP_ROOT / "static"

_ICON_ATLAS_WIDTH: int | None = None
_ICON_ATLAS_MAPPING: dict | None = None


def _ensure_icon_atlas() -> bool:
    """Buduje atlas ikon PNG w static/icons.png z plików w assets/.

    Kolejność: wind-turbine.png, port.png, statek.png (każdy slot 64×64).
    Jeśli Pillow niedostępny – tworzy fallback z prostymi kształtami.
    Zwraca True gdy atlas jest gotowy.
    """
    _STATIC_DIR.mkdir(parents=True, exist_ok=True)
    atlas_path = _STATIC_DIR / "icons.png"

    if atlas_path.exists():
        try:
            from PIL import Image
            globals()["_ICON_ATLAS_WIDTH"] = Image.open(atlas_path).size[0]
        except Exception:
            globals()["_ICON_ATLAS_WIDTH"] = None
        return True

    try:
        from PIL import Image, ImageDraw

        custom_files = [
            ("wind", _ASSETS_DIR / "wind-turbine.png"),
            ("port", _ASSETS_DIR / "port.png"),
            ("ship", _ASSETS_DIR / "statek.png"),
        ]
        found = [(key, p) for key, p in custom_files if p.exists()]

        if found:
            slots = len(found)
            atlas_img = Image.new("RGBA", (64 * slots, 64), (0, 0, 0, 0))
            mapping = {}
            for idx, (key, path) in enumerate(found):
                src = Image.open(path).convert("RGBA").resize((64, 64))
                atlas_img.paste(src, (idx * 64, 0), src)
                mapping[key] = {"x": idx * 64, "y": 0, "width": 64, "height": 64, "anchorY": 64}
            atlas_img.save(atlas_path)
            globals()["_ICON_ATLAS_WIDTH"] = 64 * slots
            globals()["_ICON_ATLAS_MAPPING"] = mapping
            logging.getLogger("offshore_app").info(
                "Atlas ikon zapisany: %s | mapping: %s", atlas_path, mapping
            )
            return True

        # fallback – proste kształty gdy brak plików PNG
        img = Image.new("RGBA", (128, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse((4, 4, 60, 60), fill=(0, 180, 255, 255))   # turbina (koło)
        draw.polygon(((72, 56), (120, 56), (96, 8)), fill=(0, 200, 0, 255))  # statek (trójkąt)
        img.save(atlas_path)
        globals()["_ICON_ATLAS_WIDTH"] = 128
        globals()["_ICON_ATLAS_MAPPING"] = {
            "wind": {"x": 0, "y": 0, "width": 64, "height": 64, "anchorY": 64},
            "ship": {"x": 64, "y": 0, "width": 64, "height": 64, "anchorY": 64},
        }
        logging.getLogger("offshore_app").info("Fallback atlas zapisany: %s", atlas_path)
        return True

    except Exception:
        logging.getLogger("offshore_app").exception("Nie udało się zbudować atlasu ikon")
        return False


_ICON_ATLAS_READY = _ensure_icon_atlas()


def _get_icon_atlas_url() -> str | None:
    """Zwraca absolutną ścieżkę atlasu ikon – pydeck czyta plik i sam robi base64."""
    atlas_path = _STATIC_DIR / "icons.png"
    return str(atlas_path) if (_ICON_ATLAS_READY and atlas_path.exists()) else None


def _get_icon_mapping():
    # Return mapping depending on atlas width. If atlas has only one
    # 64px slot, map both 'wind' and 'ship' to that slot; otherwise use
    # two-slot mapping.
    width = globals().get("_ICON_ATLAS_WIDTH")
    if width and width >= 192:
        # three-slot atlas (wind, port, ship)
        return {
            "wind": {"x": 0, "y": 0, "width": 64, "height": 64, "anchorY": 64},
            "port": {"x": 64, "y": 0, "width": 64, "height": 64, "anchorY": 64},
            "ship": {"x": 128, "y": 0, "width": 64, "height": 64, "anchorY": 64},
        }
    if width and width >= 128:
        # two-slot atlas (wind, ship)
        return {
            "wind": {"x": 0, "y": 0, "width": 64, "height": 64, "anchorY": 64},
            "ship": {"x": 64, "y": 0, "width": 64, "height": 64, "anchorY": 64},
        }
    # single-slot: map both to same slot
    return {
        "wind": {"x": 0, "y": 0, "width": 64, "height": 64, "anchorY": 64},
        "ship": {"x": 0, "y": 0, "width": 64, "height": 64, "anchorY": 64},
    }


def render_animation(
    t_lat,
    t_lon,
    port_lat,
    port_lon,
    hi_contrast: bool,
    speed: int = 8,
    df_map: pd.DataFrame | None = None,
    df_port: pd.DataFrame | None = None,
    route_data: pd.DataFrame | None = None,
    map_style: str = "light",
    turbine_color: list | None = None,
    port_color: list | None = None,
    turbine_radius: int | None = None,
    port_radius: int | None = None,
    line_width: int | None = None,
    round_trip: bool = True,
    pause_s: float = 0.6,
):
    if "anim" not in st.session_state:
        st.session_state.anim = {"running": False, "frame": 0}

    start_btn = st.button("▶️ Start animacji", key="visual_start")
    stop_btn = st.button("⏹️ Stop animacji", key="visual_stop")
    logger = logging.getLogger("offshore_app")

    if start_btn:
        st.session_state.anim = {"running": True, "frame": 0}
        logger.info("Start button pressed - animation requested")
    if stop_btn:
        st.session_state.anim["running"] = False
        logger.info("Stop button pressed - animation requested stop")

    FRAMES = max(int(60 * (1 + 10 / max(speed, 1))), 10)
    placeholder = st.empty()

    # sensible defaults
    if turbine_color is None:
        turbine_color = [0, 200, 255] if hi_contrast else [0, 120, 255]
    if port_color is None:
        port_color = [255, 200, 0] if hi_contrast else [255, 160, 0]
    if turbine_radius is None:
        turbine_radius = 160 if hi_contrast else 120
    if port_radius is None:
        port_radius = 200 if hi_contrast else 160
    if line_width is None:
        line_width = 6 if hi_contrast else 4

    # map style: allow simple 'light'/'dark' names
    map_style_full = map_style

    def make_deck(lat, lon):
        logger = logging.getLogger("offshore_app")
        layers: list = []
        # Absolutna ścieżka do atlasu – pydeck czyta plik lokalnie i koduje do base64
        atlas_for_layer = _get_icon_atlas_url()
        use_icon_layer = atlas_for_layer is not None

        # turbines: prefer IconLayer if atlas available, otherwise ScatterplotLayer
        if df_map is not None and not df_map.empty:
            if atlas_for_layer and use_icon_layer:
                df_map_icons = df_map.copy()
                df_map_icons["icon"] = "wind"
                icon_mapping = _get_icon_mapping()

                # Use conservative icon sizing: avoid huge icons by keeping
                # size_scale near 1 and deriving a modest get_size from
                # the configured turbine radius. Also compute scaled
                # pixel radii for ScatterplotLayer fallbacks.
                turbine_get_size = 20
                turbine_radius_px = max(4, int(turbine_radius * 0.08))
                try:
                    turbine_layer = pdk.Layer(
                        "IconLayer",
                        data=df_map_icons,
                        get_icon="icon",
                        get_position="[lon, lat]",
                        icon_atlas=atlas_for_layer,
                        icon_mapping=icon_mapping,
                        size_scale=1,
                        get_size=turbine_get_size,
                        pickable=True,
                    )
                    logger.debug("Turbine IconLayer params: icon_atlas=%s get_size=%s size_scale=%s", atlas_for_layer, turbine_get_size, 1)
                except Exception:
                    logger.exception("Failed to create turbine IconLayer, falling back to ScatterplotLayer")
                    turbine_layer = pdk.Layer(
                        "ScatterplotLayer",
                        data=df_map,
                        get_position="[lon, lat]",
                        get_color=turbine_color,
                        get_radius=turbine_radius,
                        radius_units="pixels",
                        radius_min_pixels=2,
                        pickable=True,
                    )
            else:
                turbine_layer = pdk.Layer(
                    "ScatterplotLayer",
                    data=df_map,
                    get_position="[lon, lat]",
                    get_color=turbine_color,
                    get_radius=turbine_radius,
                    radius_units="pixels",
                    radius_min_pixels=2,
                    pickable=True,
                )
            layers.append(turbine_layer)

        # port
        if df_port is not None and not df_port.empty:
            if atlas_for_layer and use_icon_layer:
                df_port_icons = df_port.copy()
                icon_mapping = _get_icon_mapping()
                if "port" in icon_mapping:
                    df_port_icons["icon"] = "port"
                elif "ship" in icon_mapping:
                    df_port_icons["icon"] = "ship"
                else:
                    df_port_icons["icon"] = "wind"
                port_get_size = 24
                try:
                    port_layer = pdk.Layer(
                        "IconLayer",
                        data=df_port_icons,
                        get_icon="icon",
                        get_position="[lon, lat]",
                        icon_atlas=atlas_for_layer,
                        icon_mapping=icon_mapping,
                        size_scale=1,
                        get_size=port_get_size,
                        pickable=True,
                    )
                except Exception:
                    logger.exception("Port IconLayer failed, fallback to ScatterplotLayer")
                    port_layer = pdk.Layer(
                        "ScatterplotLayer",
                        data=df_port,
                        get_position="[lon, lat]",
                        get_color=port_color,
                        get_radius=max(4, int(port_radius * 0.08)),
                        radius_units="pixels",
                        radius_min_pixels=2,
                        pickable=True,
                    )
            else:
                port_layer = pdk.Layer(
                    "ScatterplotLayer",
                    data=df_port,
                    get_position="[lon, lat]",
                    get_color=port_color,
                    get_radius=max(4, int(port_radius * 0.08)),
                    radius_units="pixels",
                    radius_min_pixels=2,
                    pickable=True,
                )
            layers.append(port_layer)

        # route
        if route_data is not None and not route_data.empty:
            route_color = [0, 0, 0] if (isinstance(map_style, str) and "light" in map_style) else [255, 255, 255]
            route_layer = pdk.Layer(
                "LineLayer",
                data=route_data,
                get_source_position="[lon, lat]",
                get_target_position="[lon, lat]",
                get_color=route_color,
                get_width=line_width,
                pickable=False,
            )
            layers.append(route_layer)

        # vessel (animated)
        v_df = pd.DataFrame([{"lat": lat, "lon": lon}])
        if atlas_for_layer and use_icon_layer:
            icon_mapping = _get_icon_mapping()
            if "ship" in icon_mapping:
                v_df["icon"] = "ship"
            elif "port" in icon_mapping:
                v_df["icon"] = "port"
            else:
                v_df["icon"] = "wind"
            # Derive vessel icon size conservatively from map radii
            vessel_radius = 10 if hi_contrast else 8
            vessel_get_size = 22
            try:
                vessel_layer = pdk.Layer(
                    "IconLayer",
                    data=v_df,
                    get_icon="icon",
                    get_position="[lon, lat]",
                    icon_atlas=atlas_for_layer,
                    icon_mapping=icon_mapping,
                    size_scale=1,
                    get_size=vessel_get_size,
                    pickable=True,
                )
                logger.debug("Vessel IconLayer params: icon_atlas=%s get_size=%s", atlas_for_layer, vessel_get_size)
            except Exception:
                logger.exception("Failed to create vessel IconLayer, falling back to ScatterplotLayer")
                vessel_layer = pdk.Layer(
                    "ScatterplotLayer",
                    data=v_df,
                    get_position="[lon, lat]",
                    get_color=[0, 200, 0],
                    get_radius=vessel_radius,
                    radius_units="pixels",
                    radius_min_pixels=2,
                    pickable=True,
                )
        else:
            vessel_radius = 10 if hi_contrast else 8
            vessel_layer = pdk.Layer(
                "ScatterplotLayer",
                data=v_df,
                get_position="[lon, lat]",
                get_color=[0, 200, 0],
                get_radius=vessel_radius,
                radius_units="pixels",
                radius_min_pixels=2,
                pickable=True,
            )
        layers.append(vessel_layer)

        # choose view: center on turbines if present otherwise on vessel
        if df_map is not None and not df_map.empty:
            center_lat = float(df_map["lat"].mean())
            center_lon = float(df_map["lon"].mean())
            zoom = 9.2
        else:
            center_lat = lat
            center_lon = lon
            zoom = 8

        view = pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=zoom, pitch=0)
        deck = pdk.Deck(layers=layers, initial_view_state=view, map_style=map_style_full)
        # Try serializing the deck to detect IconLayer/image issues early.
        try:
            _ = deck.to_json()
            return deck
        except Exception:
            logger.exception("IconLayer serialization failed, falling back to ScatterplotLayer for visibility")
            fallback_layers: list = []
            # Convert any icon-based dataframes to scatterplots for reliable rendering
            try:
                # scale down radii for fallback scatterplots so markers
                # remain visible but not huge
                try:
                    turb_px = turbine_radius_px if 'turbine_radius_px' in locals() else max(4, int(turbine_radius * 0.08))
                except Exception:
                    turb_px = max(4, int(turbine_radius * 0.08))
                try:
                    port_px = max(4, int(port_radius * 0.08))
                except Exception:
                    port_px = max(4, int(port_radius * 0.08))

                if df_map is not None and not df_map.empty:
                    fallback_layers.append(
                        pdk.Layer(
                            "ScatterplotLayer",
                            data=df_map,
                            get_position="[lon, lat]",
                            get_color=turbine_color,
                            get_radius=turb_px,
                            radius_units="pixels",
                            radius_min_pixels=2,
                            pickable=True,
                        )
                    )
                if df_port is not None and not df_port.empty:
                    fallback_layers.append(
                        pdk.Layer(
                            "ScatterplotLayer",
                            data=df_port,
                            get_position="[lon, lat]",
                            get_color=port_color,
                            get_radius=port_px,
                            radius_units="pixels",
                            radius_min_pixels=2,
                            pickable=True,
                        )
                    )
                # vessel
                v_df = pd.DataFrame([{"lat": lat, "lon": lon}])
                fallback_layers.append(
                    pdk.Layer(
                        "ScatterplotLayer",
                        data=v_df,
                        get_position="[lon, lat]",
                        get_color=[0, 200, 0],
                        get_radius=10 if hi_contrast else 8,
                        radius_units="pixels",
                        radius_min_pixels=2,
                        pickable=True,
                    )
                )
            except Exception:
                logger.exception("Failed to create fallback ScatterplotLayer(s)")
            return pdk.Deck(layers=fallback_layers, initial_view_state=view, map_style=map_style_full)

    # tune radii for light maps (make turbines larger/visible)
    if isinstance(map_style, str) and "light" in map_style:
        turbine_radius = int(turbine_radius * 1.8)
        port_radius = int(port_radius * 1.6)

    def _animate_forward():
        logger = logging.getLogger("offshore_app")
        logger.info("Animation loop (_animate_forward) started, FRAMES=%s", FRAMES)
        while st.session_state.anim["running"]:
            frame = st.session_state.anim["frame"]
            t = frame / FRAMES
            if t > 1:
                break
            lat = port_lat + (t_lat - port_lat) * t
            lon = port_lon + (t_lon - port_lon) * t
            deck = make_deck(lat, lon)
            try:
                placeholder.pydeck_chart(deck)
            except Exception:
                logger.exception("Failed to render deck in forward animation")
            st.session_state.anim["frame"] += 1
            if frame % max(1, FRAMES // 10) == 0:
                logger.debug("Animating forward frame=%s t=%s", frame, t)
            time.sleep(1.0 / max(speed, 1))

    def _animate_backward():
        # animate back from t=1 to t=0
        logger = logging.getLogger("offshore_app")
        logger.info("Animation loop (_animate_backward) started")
        for back_frame in range(FRAMES, -1, -1):
            if not st.session_state.anim["running"]:
                break
            t = back_frame / FRAMES
            lat = port_lat + (t_lat - port_lat) * t
            lon = port_lon + (t_lon - port_lon) * t
            deck = make_deck(lat, lon)
            try:
                placeholder.pydeck_chart(deck)
            except Exception:
                logger.exception("Failed to render deck in backward animation")
            if back_frame % max(1, FRAMES // 10) == 0:
                logger.debug("Animating backward frame=%s t=%s", back_frame, t)
            time.sleep(1.0 / max(speed, 1))

    # Run forward animation; optionally pause and return
    while st.session_state.anim["running"]:
        st.session_state.anim["frame"] = 0
        _animate_forward()
        if not st.session_state.anim["running"]:
            break
        # reached target
        time.sleep(pause_s)
        if round_trip and st.session_state.anim["running"]:
            _animate_backward()
            # small pause at port
            time.sleep(0.2)
        # stop after one round-trip
        st.session_state.anim["running"] = False

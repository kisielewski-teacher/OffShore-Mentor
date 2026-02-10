# streamlit_app.py (light map style + high contrast + vessel animation)
import math
import time
import pandas as pd
import streamlit as st
import altair as alt
import pydeck as pdk

from data.generate import gen_faults, gen_windows, gen_vessels
from planner.plan import plan_repairs, haversine, transit_time_km

st.set_page_config(page_title="Offshore Mentor", layout="wide")
st.title("Offshore Mentor – Symulator serwisowania farm wiatrowych offshore")
st.markdown(
    "Aplikacja symuluje planowanie napraw turbin offshore z uwzględnieniem okien pogodowych, priorytetów usterek, czasu tranzytu statków oraz kosztów operacji."
)

# --- Init session state for animation ---
if "anim_running" not in st.session_state:
    st.session_state.anim_running = False
if "anim_frame" not in st.session_state:
    st.session_state.anim_frame = 0

# --- Panel parametrów ---
col1, col2, col3 = st.columns(3)
with col1:
    n_faults = st.slider("Liczba usterek", 10, 80, 30)
    hs_thr = st.slider("Próg Hs [m]", 0.5, 3.0, 1.5, 0.1)
with col2:
    wind_thr = st.slider("Próg wiatru [m/s]", 5.0, 20.0, 15.0, 0.5)
    workday_8h = st.checkbox("Dzień pracy = 8h (szacunek kosztów)", value=True)
with col3:
    hi_contrast = st.checkbox("Tryb wysoki kontrast", value=True)
    anim_speed = st.slider("Szybkość animacji [kl/s]", 1, 20, 8)
    run_sim = st.button("Start symulacji")

st.markdown("---")

# --- Symulacja ---
if run_sim:
    faults = gen_faults(n_faults)
    windows = gen_windows()
    vessels = gen_vessels()

    schedule, tot_cost = plan_repairs(
        faults,
        windows,
        vessels,
        hs_thr=hs_thr,
        wind_thr=wind_thr,
        workday_hours=(8 if workday_8h else 24),
    )
    df = pd.DataFrame(schedule)

    # KPI
    st.subheader("KPI – Kluczowe wskaźniki")
    planned = int(df["start"].notna().sum())
    unplanned = int(df["start"].isna().sum())
    col_k1, col_k2, col_k3 = st.columns(3)
    col_k1.metric("Zaplanowane naprawy", planned)
    col_k2.metric("Niezaplanowane", unplanned)
    col_k3.metric("Szac. koszt [PLN]", f"{tot_cost:,.0f}")

    st.markdown("---")

    # Mapa turbin i portu
    st.subheader("Mapa turbin i portu bazowego")
    port_lat = 54.580
    port_lon = 16.860

    df_map = pd.DataFrame(
        [
            {
                "lat": f.lat,
                "lon": f.lon,
                "fault_id": f.fault_id,
                "turbine_id": f.turbine_id,
                "priority": f.priority,
                "type": "turbina",
            }
            for f in faults
        ]
    )
    df_port = pd.DataFrame(
        [
            {
                "lat": port_lat,
                "lon": port_lon,
                "fault_id": "PORT",
                "turbine_id": "Port Ustka",
                "priority": 0,
                "type": "port",
            }
        ]
    )

    # Styl mapy i kolory (jasne tło)
    map_style_value = "light"
    turbine_color = [0, 200, 255] if hi_contrast else [0, 120, 255]
    port_color = [255, 200, 0] if hi_contrast else [255, 160, 0]
    line_width = 6 if hi_contrast else 4
    turbine_radius = 120 if hi_contrast else 90
    port_radius = 160 if hi_contrast else 130

    # Warstwy pydeck
    turbine_layer = pdk.Layer(
        "ScatterplotLayer",
        data=df_map,
        get_position="[lon, lat]",
        get_color=turbine_color,
        get_radius=turbine_radius,
        pickable=True,
    )
    port_layer = pdk.Layer(
        "ScatterplotLayer",
        data=df_port,
        get_position="[lon, lat]",
        get_color=port_color,
        get_radius=port_radius,
        pickable=True,
    )

    view_state = pdk.ViewState(
        latitude=df_map["lat"].mean(),
        longitude=df_map["lon"].mean(),
        zoom=9.2,
        pitch=0,
    )
    deck = pdk.Deck(
        layers=[turbine_layer, port_layer],
        initial_view_state=view_state,
        tooltip={"text": "{turbine_id}"},
        map_style=map_style_value,
    )
    st.pydeck_chart(deck)

    # Wybór turbiny → trasa port → turbina
    selected_fault = st.selectbox(
        "Wybierz turbinę do trasy port → turbina:", df_map["fault_id"].tolist()
    )
    info = df_map[df_map["fault_id"] == selected_fault].iloc[0]

    st.subheader("Trasa port → turbina")
    ref_vessel_speed = vessels[0].speed_kn if vessels else 20.0
    distance_km = haversine(port_lat, port_lon, info["lat"], info["lon"])
    transit_h = transit_time_km(distance_km, ref_vessel_speed)

    # Status pogodowy (czy jakiekolwiek okno spełnia progi i mieści operację 2*tranzyt + 8h)
    duration_h = math.ceil(transit_h) * 2 + 8

    def find_feasible_window(windows, hs_thr, wind_thr, reported_h, duration_h):
        for w in sorted(windows, key=lambda w: w.start):
            if (w.hs_m <= hs_thr) and (w.wind_ms <= wind_thr):
                start = max(w.start, reported_h)
                if start + duration_h <= w.end:
                    return w
        return None

    w = find_feasible_window(
        windows, hs_thr, wind_thr, reported_h=0, duration_h=duration_h
    )

    color = [0, 200, 0] if w is not None else [220, 0, 0]
    status = (
        "Warunki OK – operacja możliwa w najbliższym oknie"
        if w is not None
        else "Warunki przekroczone – brak okna dla operacji"
    )

    st.write(f"**Odległość:** {distance_km:.2f} km")
    st.write(f"**Czas tranzytu (1 strona):** {transit_h:.2f} h")
    st.write(f"**Status pogodowy:** {status}")

    # --- ROUTE (static) ---
    route_data = pd.DataFrame(
        [
            {"lat": port_lat, "lon": port_lon},
            {"lat": info["lat"], "lon": info["lon"]},
        ]
    )
    route_layer = pdk.Layer(
        "LineLayer",
        data=route_data,
        get_source_position="[lon, lat]",
        get_target_position="[lon, lat]",
        get_color=color,
        get_width=line_width,
        pickable=True,
    )

    # --- VESSEL ANIMATION ---
    st.markdown("### Animacja ruchu statku")
    col_a1, col_a2 = st.columns(2)
    start_anim = col_a1.button("▶️ Start animacji")
    stop_anim = col_a2.button("⏹️ Stop animacji")

    if start_anim:
        st.session_state.anim_running = True
        st.session_state.anim_frame = 0
    if stop_anim:
        st.session_state.anim_running = False

    # Parametry animacji
    FRAMES = 120  # liczba klatek na odcinek port→turbina
    sleep_dt = 1.0 / max(anim_speed, 1)

    # Funkcja interpolacji pozycji (lon,lat)
    def interpolate(lon1, lat1, lon2, lat2, t):
        # t in [0,1]
        lon = lon1 + (lon2 - lon1) * t
        lat = lat1 + (lat2 - lat1) * t
        return lon, lat

    # Placeholder na animowaną mapę
    anim_placeholder = st.empty()

    # Render statycznej trasy (gdy animacja nie działa)
    if not st.session_state.anim_running:
        vessel_lon, vessel_lat = port_lon, port_lat
        vessel_layer = pdk.Layer(
            "ScatterplotLayer",
            data=pd.DataFrame([{"lon": vessel_lon, "lat": vessel_lat}]),
            get_position="[lon, lat]",
            get_color=[0, 255, 0],
            get_radius=160 if hi_contrast else 120,
        )
        deck_route = pdk.Deck(
            layers=[turbine_layer, port_layer, route_layer, vessel_layer],
            initial_view_state=pdk.ViewState(
                latitude=info["lat"], longitude=info["lon"], zoom=9.3, pitch=0
            ),
            tooltip={"text": "Trasa statku port → turbina"},
            map_style=map_style_value,
        )
        anim_placeholder.pydeck_chart(deck_route)

    # Animacja: render jednej klatki na przebieg skryptu i ponowne uruchomienie
    if st.session_state.anim_running:
        frame = st.session_state.anim_frame
        t = min(frame / FRAMES, 1.0)
        vessel_lon, vessel_lat = interpolate(
            port_lon, port_lat, float(info["lon"]), float(info["lat"]), t
        )

        vessel_layer = pdk.Layer(
            "ScatterplotLayer",
            data=pd.DataFrame([{"lon": vessel_lon, "lat": vessel_lat}]),
            get_position="[lon, lat]",
            get_color=[0, 255, 0],
            get_radius=160 if hi_contrast else 120,
            pickable=True,
        )

        deck_route = pdk.Deck(
            layers=[turbine_layer, port_layer, route_layer, vessel_layer],
            initial_view_state=pdk.ViewState(
                latitude=info["lat"], longitude=info["lon"], zoom=9.3, pitch=0
            ),
            tooltip={"text": "Statek (animacja)"},
            map_style=map_style_value,
        )
        anim_placeholder.pydeck_chart(deck_route)

        # Update klatki i zaplanuj kolejny rerun (nie blokujemy serwera pętlą)
        st.session_state.anim_frame = frame + 1
        if st.session_state.anim_frame > FRAMES:
            st.session_state.anim_running = False
        else:
            time.sleep(sleep_dt)
            st.experimental_rerun()

    st.markdown("---")

    # Gantt – harmonogram
    st.subheader("Harmonogram napraw (Gantt)")
    df_gantt = df[df["start"].notna()].copy()
    if len(df_gantt) > 0:
        chart = (
            alt.Chart(df_gantt)
            .mark_bar()
            .encode(
                x=alt.X("start:Q", title="Godzina startu"),
                x2=alt.X2("end:Q", title="Godzina zakończenia"),
                y=alt.Y("fault_id:N", title="Usterka", sort=None),
                color=alt.Color("vessel_name:N", title="Statek"),
                tooltip=[
                    "fault_id",
                    "turbine_id",
                    "vessel_name",
                    "start",
                    "end",
                    "cost_pln",
                    "priority",
                    "distance_km",
                    "transit_h",
                ],
            )
            .properties(height=450)
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Brak zaplanowanych napraw dla zadanych parametrów.")

    st.markdown("---")

    # Tabela harmonogramu
    st.subheader("Tabela harmonogramu")
    st.dataframe(df)
else:
    st.info(
        "Ustaw parametry po lewej i kliknij Start symulacji, aby wygenerować harmonogram."
    )

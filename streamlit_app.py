import math
import time
import pandas as pd
import streamlit as st
import altair as alt
import pydeck as pdk
import logging
import os
from logging.handlers import RotatingFileHandler

from planner.plan import plan_repairs, haversine, transit_time_km, gen_faults, gen_windows, gen_vessels
from planner.optimizer import solve_optimal_schedule, SOLVER_MAX_FAULTS
from planner.simulate import run_rolling_simulation, snapshots_to_dataframe
from modules import visual
from viz.gantt import gantt_chart

# --- logging setup --------------------------------------------------
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, "animation.log")
logger = logging.getLogger("offshore_app")
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    fh = RotatingFileHandler(log_file, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setLevel(logging.INFO)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
logger.debug("Logger initialized, log_file=%s", log_file)
try:
    assets_icon = os.path.join(os.path.dirname(__file__), "assets", "icons.png")
    assets_exists = os.path.exists(assets_icon)
    assets_size = os.path.getsize(assets_icon) if assets_exists else None
    logger.info("Asset icon path: %s exists=%s size=%s", assets_icon, assets_exists, assets_size)
    logger.info("Expected public icon path served by Streamlit: %s", "/assets/icons.png")
except Exception:
    logger.exception("Failed to stat assets/icons.png")

# --------------------------------------------------------------------

# Optional autorefresh support (third-party). Graceful fallback if missing.
try:
    from streamlit_autorefresh import st_autorefresh  # type: ignore
    _HAS_ST_AUTOREFRESH = True
except Exception:
    st_autorefresh = None
    _HAS_ST_AUTOREFRESH = False


def trigger_client_rerun(delay_ms: int = 1000) -> None:
    js = f"""
    <script>
    setTimeout(function(){{
        try {{
            const p = new URLSearchParams(window.location.search);
            p.set('_r', '{int(time.time()*1000)}');
            const newUrl = window.location.pathname + '?' + p.toString();
            try {{ if (window.top && window.top !== window) {{ window.top.location.href = newUrl; return; }} }} catch(e){{}}
            try {{ if (window.parent && window.parent !== window) {{ window.parent.location.href = newUrl; return; }} }} catch(e){{}}
            window.location.href = newUrl;
        }} catch (e) {{ /* ignore */ }}
    }},{delay_ms});
    </script>
    """
    try:
        st.components.v1.html(js, height=1)
        st.session_state._client_rerun_injected = True
        st.session_state._client_rerun_injected_ts = int(time.time() * 1000)
        logger.info("Injected client rerun HTML (delay_ms=%s)", delay_ms)
    except Exception:
        logger.exception("Client rerun injection failed, falling back to do_rerun")
        do_rerun()


def do_rerun():
    if hasattr(st, "experimental_rerun"):
        try:
            st.experimental_rerun()
            return
        except Exception:
            pass

    for mod in (
        "streamlit.script_runner",
        "streamlit.runtime.scriptrunner",
        "streamlit.scriptrunner",
    ):
        try:
            m = __import__(mod, fromlist=["RerunException"])  # type: ignore
            RerunException = getattr(m, "RerunException", None)
            if RerunException is not None:
                raise RerunException()
        except Exception:
            pass

    try:
        try:
            st.query_params = {"_rerun": int(time.time())}
        except Exception:
            params = dict(st.query_params) if hasattr(st, "query_params") else {}
            params["_rerun"] = int(time.time())
            try:
                st.query_params = params
            except Exception:
                pass
    except Exception:
        return


st.set_page_config(page_title="Offshore Mentor", page_icon="⚓", layout="wide")

st.markdown(
    """
    <style>
    @keyframes omFadeInUp {
        from { opacity: 0; transform: translateY(8px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes omGradientShift {
        0%, 100% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
    }

    .om-hero {
        background: linear-gradient(120deg, #ECFDF9, #EAF4FE, #ECFDF9);
        background-size: 200% 200%;
        border: 1px solid #BFE9E1;
        border-radius: 16px;
        padding: 1.6rem 2rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 4px 16px rgba(15, 23, 42, 0.06);
        animation: omFadeInUp 0.5s ease-out, omGradientShift 10s ease-in-out infinite;
    }
    .om-hero h1 {
        margin: 0 0 0.4rem 0;
        font-size: 1.9rem;
        font-weight: 700;
        letter-spacing: 0.2px;
        color: #0F2A3D;
    }
    .om-hero p {
        margin: 0;
        color: #52667A;
        font-size: 0.98rem;
        max-width: 900px;
    }
    .om-badge-row { margin-top: 0.8rem; display: flex; gap: 0.5rem; flex-wrap: wrap; }
    .om-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.22rem 0.7rem;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.2px;
    }
    .om-badge-teal { background: #E6FFFB; color: #0D9488; border: 1px solid #99E6DA; }
    .om-badge-amber { background: #FFF7E6; color: #B45309; border: 1px solid #FCD9A0; }
    .om-badge-coral { background: #FEF2F2; color: #B91C1C; border: 1px solid #FBC5C5; }

    h3 { position: relative; padding-left: 0.7rem; border-left: 3px solid #0D9488; }

    div[data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 0.9rem 1.1rem 0.7rem 1.1rem;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06);
        transition: transform 0.18s ease, box-shadow 0.18s ease;
        animation: omFadeInUp 0.4s ease-out backwards;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(13, 148, 136, 0.15);
    }
    div[data-testid="stMetricLabel"] { color: #64748B !important; }
    div[data-testid="stMetricValue"] { color: #0F2A3D !important; }

    /* Rozłożone w czasie pojawianie się kart KPI ułożonych w st.columns(3) */
    div[data-testid="column"]:nth-of-type(1) div[data-testid="stMetric"] { animation-delay: 0s; }
    div[data-testid="column"]:nth-of-type(2) div[data-testid="stMetric"] { animation-delay: 0.08s; }
    div[data-testid="column"]:nth-of-type(3) div[data-testid="stMetric"] { animation-delay: 0.16s; }

    /* Płynne pojawianie się zawartości przy przełączaniu zakładek */
    [data-baseweb="tab-panel"] { animation: omFadeInUp 0.35s ease-out; }

    div.stButton > button {
        background: linear-gradient(135deg, #14B8A6 0%, #0D9488 100%);
        color: #FFFFFF;
        font-weight: 700;
        border: none;
        border-radius: 999px;
        padding: 0.5rem 1.4rem;
        transition: transform 0.15s ease, box-shadow 0.15s ease, filter 0.15s ease;
        box-shadow: 0 4px 14px rgba(13, 148, 136, 0.25);
    }
    div.stButton > button:hover {
        transform: translateY(-1px);
        filter: brightness(1.06);
        box-shadow: 0 6px 18px rgba(13, 148, 136, 0.35);
    }
    div.stButton > button:disabled {
        background: #E2E8F0;
        color: #94A3B8;
        box-shadow: none;
    }

    .stTabs [data-baseweb="tab-list"] { gap: 0.4rem; border-bottom: 1px solid #E2E8F0; }
    .stTabs [data-baseweb="tab"] {
        font-weight: 600;
        font-size: 0.95rem;
        color: #64748B;
        padding: 0.6rem 1.1rem;
    }
    .stTabs [aria-selected="true"] {
        color: #0D9488 !important;
        border-bottom: 2px solid #0D9488 !important;
    }

    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, rgba(13, 148, 136, 0) 0%, rgba(13, 148, 136, 0.35) 50%, rgba(13, 148, 136, 0) 100%);
        margin: 1.1rem 0;
    }
    </style>

    <div class="om-hero">
      <h1>⚓ Offshore Mentor</h1>
      <p>Symulator planowania serwisowania morskich farm wiatrowych offshore – okna pogodowe, priorytety usterek,
      czas tranzytu statków i koszty operacji, z porównaniem do rozwiązania optymalnego oraz symulacją wielodniową.</p>
      <div class="om-badge-row">
        <span class="om-badge om-badge-teal">🌊 Bałtyk</span>
        <span class="om-badge om-badge-teal">🚢 Flota CTV</span>
        <span class="om-badge om-badge-amber">⚙️ Solver optymalny (PuLP)</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- Init session state for animation ---
if "anim_running" not in st.session_state:
    st.session_state.anim_running = False
if "anim_frame" not in st.session_state:
    st.session_state.anim_frame = 0
if "sim_data" not in st.session_state:
    st.session_state.sim_data = None

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

tab1, tab2 = st.tabs(["Symulacja jednorazowa", "Symulacja wielodniowa"])

with tab1:
    # --- Symulacja ---
    if run_sim:
        with st.spinner("🌊 Generuję usterki, okna pogodowe i harmonogram..."):
            faults = gen_faults(n_faults)
            windows = gen_windows()
            vessels = gen_vessels()
            logger.info("Simulation started: n_faults=%s, hs_thr=%s, wind_thr=%s", n_faults, hs_thr, wind_thr)

            schedule, tot_cost = plan_repairs(
                faults,
                windows,
                vessels,
                hs_thr=hs_thr,
                wind_thr=wind_thr,
                workday_hours=(8 if workday_8h else 24),
            )
            df = pd.DataFrame(schedule)
        st.session_state.sim_data = (faults, windows, vessels, df, tot_cost)

    # If simulation already stored in session state, use it so animation survives reruns
    if st.session_state.sim_data is not None:
        faults, windows, vessels, df, tot_cost = st.session_state.sim_data
        logger.info("Loaded simulation from session_state: faults=%s, windows=%s, vessels=%s", len(faults), len(windows), len(vessels))

        # KPI
        st.subheader("📊 KPI – Kluczowe wskaźniki")
        planned = int(df["start"].notna().sum())
        unplanned = int(df["start"].isna().sum())
        col_k1, col_k2, col_k3 = st.columns(3)
        col_k1.metric("Zaplanowane naprawy", planned)
        col_k2.metric("Niezaplanowane", unplanned)
        col_k3.metric("Szac. koszt [PLN]", f"{tot_cost:,.0f}")

        st.markdown("---")

        # Mapa turbin i portu
        st.subheader("🗺️ Mapa turbin i portu bazowego")
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

        # Wybór turbiny → zaznaczenie na mapie (highlight)
        selected_fault = st.selectbox(
            "Wybierz turbinę do trasy port → turbina:", df_map["fault_id"].tolist()
        )

        try:
            selected_df = df_map[df_map["fault_id"] == selected_fault]
        except Exception:
            selected_df = pd.DataFrame(columns=df_map.columns)


        # Styl mapy i kolory (jasne tło)
        map_style_value = "light"
        turbine_color = [0, 200, 255] if hi_contrast else [0, 120, 255]
        port_color = [255, 200, 0] if hi_contrast else [255, 160, 0]
        line_width = 6 if hi_contrast else 4
        # Use pixel units for scatterplot radii so points remain visible at map zooms
        turbine_radius = 8 if hi_contrast else 6
        port_radius = 10 if hi_contrast else 8

        # Coerce lat/lon to floats and log diagnostics to help visibility issues
        try:
            df_map["lat"] = df_map["lat"].astype(float)
            df_map["lon"] = df_map["lon"].astype(float)
            df_port["lat"] = df_port["lat"].astype(float)
            df_port["lon"] = df_port["lon"].astype(float)
            logger.info("df_map dtypes: %s", df_map.dtypes.to_dict())
            logger.info(
                "df_map lat range: %s - %s, lon range: %s - %s, count=%s",
                df_map["lat"].min(),
                df_map["lat"].max(),
                df_map["lon"].min(),
                df_map["lon"].max(),
                len(df_map),
            )
        except Exception:
            logger.exception("Failed to coerce df_map/df_port lat/lon to float")

        # Warstwy pydeck
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
        port_layer = pdk.Layer(
            "ScatterplotLayer",
            data=df_port,
            get_position="[lon, lat]",
            get_color=port_color,
            get_radius=port_radius,
            radius_units="pixels",
            radius_min_pixels=2,
            pickable=True,
        )

        # Ikony: pydeck czyta plik lokalnie i koduje do base64 przed wysłaniem do przeglądarki.
        atlas_uri = visual._get_icon_atlas_url()
        if atlas_uri:
            try:
                icon_mapping = visual._get_icon_mapping()
                df_map_icons = df_map.copy()
                df_map_icons["icon"] = "wind"
                df_port_icons = df_port.copy()
                df_port_icons["icon"] = "port" if "port" in icon_mapping else "wind"
                turbine_layer = pdk.Layer(
                    "IconLayer",
                    data=df_map_icons,
                    get_icon="icon",
                    get_position="[lon, lat]",
                    icon_atlas=atlas_uri,
                    icon_mapping=icon_mapping,
                    size_scale=1,
                    get_size=24,
                    pickable=True,
                )
                port_layer = pdk.Layer(
                    "IconLayer",
                    data=df_port_icons,
                    get_icon="icon",
                    get_position="[lon, lat]",
                    icon_atlas=atlas_uri,
                    icon_mapping=icon_mapping,
                    size_scale=1,
                    get_size=28,
                    pickable=True,
                )
            except Exception:
                logger.exception("IconLayer dla mapy statycznej nie powiódł się – fallback do ScatterplotLayer")


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
        # Dodajemy warstwę podświetlenia wybranej turbiny (nakładka)
        try:
            highlight_color = [255, 80, 80] if hi_contrast else [255, 60, 60]
            highlight_radius = max(turbine_radius * 2, turbine_radius + 4)
            selected_layer = pdk.Layer(
                "ScatterplotLayer",
                data=selected_df,
                get_position="[lon, lat]",
                get_color=highlight_color,
                get_radius=highlight_radius,
                radius_units="pixels",
                pickable=False,
            )
            # Umieszczamy warstwę zaznaczenia jako ostatnią (na wierzchu)
            deck.layers.append(selected_layer)
        except Exception:
            logger.exception("Failed to create selected highlight layer")

        st.pydeck_chart(deck)

        # (DEBUG) removed fallback `st.map` to avoid duplicate maps in UI

        # Wybór turbiny już wykonany wyżej; odwołaj się do `selected_fault`
        info = df_map[df_map["fault_id"] == selected_fault].iloc[0]

        st.subheader("🧭 Trasa port → turbina")
        ref_vessel_speed = vessels[0].speed_kn if (vessels and len(vessels) > 0) else 20.0
        distance_km = haversine(port_lat, port_lon, info["lat"], info["lon"])
        transit_h = transit_time_km(distance_km, ref_vessel_speed)

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
        st.markdown("### 🚢 Animacja ruchu statku")
        # Use modular animation renderer (handles start/stop and session_state internally)
        visual.render_animation(
            float(info["lat"]),
            float(info["lon"]),
            port_lat,
            port_lon,
            hi_contrast,
            anim_speed,
            df_map=df_map,
            df_port=df_port,
            route_data=route_data,
            map_style=map_style_value,
            turbine_color=turbine_color,
            port_color=port_color,
            turbine_radius=turbine_radius,
            port_radius=port_radius,
            line_width=line_width,
        )

        st.markdown("---")

        # Gantt – harmonogram
        st.subheader("📅 Harmonogram napraw (Gantt)")
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
            st.altair_chart(chart, width="stretch")
        else:
            st.info("Brak zaplanowanych napraw dla zadanych parametrów.")

        st.markdown("---")

        # Tabela harmonogramu
        st.subheader("📋 Tabela harmonogramu")
        st.dataframe(df)

        st.markdown("---")

        # --- Solver optymalny (PuLP) vs. heurystyka ---
        st.subheader("⚖️ Porównanie z rozwiązaniem optymalnym")
        solver_disabled = len(faults) > SOLVER_MAX_FAULTS
        if solver_disabled:
            st.caption(
                f"Porównanie z rozwiązaniem optymalnym dostępne dla ≤{SOLVER_MAX_FAULTS} usterek "
                f"(limit czasu obliczeń solvera). Zmniejsz „Liczbę usterek” i uruchom symulację ponownie."
            )
        if st.button(
            "Porównaj z rozwiązaniem optymalnym (PuLP)",
            disabled=solver_disabled,
            key="solve_optimal_btn",
        ):
            with st.spinner("Solver liczy (near-)optymalny harmonogram..."):
                sched_opt, cost_opt, meta = solve_optimal_schedule(
                    faults,
                    windows,
                    vessels,
                    hs_thr=hs_thr,
                    wind_thr=wind_thr,
                    workday_hours=(8 if workday_8h else 24),
                )
            st.session_state.optimal_data = (sched_opt, cost_opt, meta)
            logger.info(
                "Optimal solver run: status=%s runtime_s=%.2f num_candidates=%s",
                meta["status"], meta["runtime_s"], meta["num_candidates"],
            )

        if st.session_state.get("optimal_data") is not None:
            sched_opt, cost_opt, meta = st.session_state.optimal_data
            planned_opt = sum(1 for r in sched_opt if r["start"] is not None)
            unplanned_opt = len(sched_opt) - planned_opt

            c1, c2, c3 = st.columns(3)
            c1.metric("Koszt (heurystyka)", f"{tot_cost:,.0f} PLN")
            c2.metric(
                "Koszt (optymalny)",
                f"{cost_opt:,.0f} PLN",
                delta=f"{cost_opt - tot_cost:,.0f} PLN",
                delta_color="inverse",
            )
            c3.metric(
                "Niezaplanowane (optymalny)",
                unplanned_opt,
                delta=unplanned_opt - unplanned,
                delta_color="inverse",
            )

            status_labels = {
                "optimal": ("✅ optimum dowiedzione", "teal"),
                "time_limit": ("⏱️ najlepsze znalezione (limit czasu)", "amber"),
                "infeasible": ("⛔ brak rozwiązania", "coral"),
                "no_candidates": ("⛔ brak wykonalnych kombinacji", "coral"),
            }
            label, tone = status_labels.get(meta["status"], (meta["status"], "amber"))
            st.markdown(
                f"""
                <div style="margin-top: 0.4rem;">
                    <span class="om-badge om-badge-{tone}">{label}</span>
                    <span style="color: #64748B; font-size: 0.85rem; margin-left: 0.6rem;">
                        czas: {meta['runtime_s']:.1f}s · kandydatów: {meta['num_candidates']}
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info(
            "Ustaw parametry po lewej i kliknij Start symulacji, aby wygenerować harmonogram."
        )

with tab2:
    st.markdown(
        "Symulacja dzień po dniu: nowe usterki napływają w czasie, a plan jest "
        "przeliczany na bieżąco na podstawie nierozwiązanego backlogu. Pokazuje, "
        "czy flota „nadąża” z naprawami, czy backlog rośnie bez końca."
    )

    rc1, rc2, rc3 = st.columns(3)
    with rc1:
        roll_horizon_days = st.slider(
            "Liczba dni symulacji", 7, 30, 14, key="roll_horizon_days"
        )
    with rc2:
        roll_total_faults = st.slider(
            "Liczba usterek (cały horyzont)", 20, 300, 100, key="roll_total_faults"
        )
    with rc3:
        roll_fleet_size = st.slider(
            "Liczba statków w flocie", 1, 6, 3, key="roll_fleet_size"
        )

    roll_run = st.button("Uruchom symulację wielodniową", key="roll_run_btn")

    st.markdown("---")

    if roll_run:
        f2 = gen_faults(n=roll_total_faults, seed=42, arrival_horizon_h=roll_horizon_days * 24)
        w2 = gen_windows(horizon_days=roll_horizon_days, seed=42)
        v2 = gen_vessels(count=roll_fleet_size)

        roll_progress = st.progress(0.0, text=f"🌊 Dzień 0/{roll_horizon_days}...")

        def _on_day_complete(day: int, total: int) -> None:
            roll_progress.progress(
                (day + 1) / total, text=f"🌊 Dzień {day + 1}/{total}..."
            )

        snapshots, df_committed = run_rolling_simulation(
            f2, w2, v2, roll_horizon_days,
            hs_thr=hs_thr, wind_thr=wind_thr,
            workday_hours=(8 if workday_8h else 24),
            on_day_complete=_on_day_complete,
        )
        roll_progress.empty()
        st.session_state.rolling_data = (snapshots, df_committed)
        logger.info(
            "Rolling simulation run: horizon_days=%s total_faults=%s fleet_size=%s",
            roll_horizon_days, roll_total_faults, roll_fleet_size,
        )

    if st.session_state.get("rolling_data") is not None:
        snapshots, df_committed = st.session_state.rolling_data
        df_snap = snapshots_to_dataframe(snapshots)

        st.subheader("📊 KPI – Symulacja wielodniowa")
        k1, k2, k3 = st.columns(3)
        k1.metric("Rozwiązane naprawy", int(df_snap["resolved_today"].sum()))
        k2.metric("Backlog na koniec horyzontu", int(df_snap["backlog_after"].iloc[-1]))
        k3.metric("Łączny koszt [PLN]", f"{df_snap['cumulative_cost'].iloc[-1]:,.0f}")

        st.markdown("---")

        st.subheader("📈 Backlog w czasie")
        st.altair_chart(
            alt.Chart(df_snap)
            .mark_line(point=True)
            .encode(
                x=alt.X("day:Q", title="Dzień symulacji"),
                y=alt.Y("backlog_after:Q", title="Usterki w backlogu"),
                tooltip=["day", "backlog_after", "new_faults", "resolved_today"],
            )
            .properties(height=300),
            width="stretch",
        )

        st.subheader("📊 Nowe vs. rozwiązane usterki per dzień")
        long_df = df_snap.melt(
            id_vars="day",
            value_vars=["new_faults", "resolved_today"],
            var_name="seria",
            value_name="liczba",
        )
        st.altair_chart(
            alt.Chart(long_df)
            .mark_bar()
            .encode(
                x=alt.X("day:O", title="Dzień symulacji"),
                y=alt.Y("liczba:Q", title="Liczba usterek"),
                color=alt.Color("seria:N", title="Seria"),
                xOffset="seria:N",
                tooltip=["day", "seria", "liczba"],
            )
            .properties(height=300),
            width="stretch",
        )

        st.subheader("💰 Koszt skumulowany")
        st.altair_chart(
            alt.Chart(df_snap)
            .mark_line(point=True)
            .encode(
                x=alt.X("day:Q", title="Dzień symulacji"),
                y=alt.Y("cumulative_cost:Q", title="Koszt skumulowany [PLN]"),
                tooltip=["day", "cumulative_cost", "cost_today"],
            )
            .properties(height=300),
            width="stretch",
        )

        st.subheader("📅 Harmonogram zrealizowanych napraw (Gantt)")
        chart = gantt_chart(df_committed)
        if chart is not None:
            st.altair_chart(chart, width="stretch")
        else:
            st.info("Brak zrealizowanych napraw dla zadanych parametrów.")

        st.subheader("🗒️ Dziennik symulacji")
        st.dataframe(df_snap)
    else:
        st.info(
            "Ustaw parametry powyżej i kliknij „Uruchom symulację wielodniową”, "
            "aby zobaczyć jak backlog usterek zmienia się w czasie."
        )

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

PLOTLY_THEME = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(20,25,32,0.8)",
    font=dict(family="Exo 2, sans-serif", color="#8892a4", size=11),
    title_font=dict(family="Rajdhani, sans-serif", color="#e8eaf0", size=16),
    colorway=["#ff6b2b", "#00d4ff", "#39ff14", "#ff2b4e", "#ffcc00", "#c084fc"],
    xaxis=dict(gridcolor="#1e2d40", zerolinecolor="#1e2d40"),
    yaxis=dict(gridcolor="#1e2d40", zerolinecolor="#1e2d40"),
)

def metric_card(label, value, color="#ff6b2b"):
    return f"""
    <div class="metric-card">
        <div class="metric-val" style="color:{color}">{value}</div>
        <div class="metric-label">{label}</div>
    </div>"""

def render(data: dict):
    meta     = data["meta"]
    dmg      = data["dmg"]
    kills    = data["kills"]
    grenades = data["grenades"]

    if meta.empty:
        st.warning("Keine Daten für aktuelle Filter.")
        return

    # ── KPI Row ───────────────────────────────────────────────────────────────
    st.markdown('<p class="section-header">Key Metrics</p>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns(5)
    total_rounds  = len(meta)
    total_kills   = len(kills)
    total_dmg     = int(dmg["hp_dmg"].sum()) if "hp_dmg" in dmg.columns else 0
    total_grenades= len(grenades)
    maps_count    = meta["map"].nunique() if "map" in meta.columns else 0

    c1.markdown(metric_card("Runden", f"{total_rounds:,}"), unsafe_allow_html=True)
    c2.markdown(metric_card("Kills", f"{total_kills:,}", "#00d4ff"), unsafe_allow_html=True)
    c3.markdown(metric_card("HP Schaden", f"{total_dmg:,}", "#ff2b4e"), unsafe_allow_html=True)
    c4.markdown(metric_card("Granaten", f"{total_grenades:,}", "#39ff14"), unsafe_allow_html=True)
    c5.markdown(metric_card("Karten", f"{maps_count}", "#ffcc00"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Row 1: Rundentypen + CT vs T Gewinnrate ────────────────────────────────
    st.markdown('<p class="section-header">Rundenanalyse</p>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    with col1:
        if "round_type" in meta.columns:
            rt = meta["round_type"].value_counts().reset_index()
            rt.columns = ["Rundentyp", "Anzahl"]
            fig = px.pie(rt, names="Rundentyp", values="Anzahl", hole=0.55,
                         title="Rundentypen-Verteilung",
                         color_discrete_sequence=["#ff6b2b","#00d4ff","#39ff14","#ff2b4e","#ffcc00"])
            fig.update_layout(**PLOTLY_THEME, showlegend=True,
                              legend=dict(bgcolor="rgba(0,0,0,0)"))
            fig.update_traces(textfont_color="#e8eaf0")
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        if "winner_side" in meta.columns:
            ws = meta["winner_side"].value_counts().reset_index()
            ws.columns = ["Seite", "Siege"]
            color_map = {"CounterTerrorist": "#00d4ff", "Terrorist": "#ff6b2b"}
            fig = px.bar(ws, x="Seite", y="Siege", title="CT vs T Siege",
                         color="Seite", color_discrete_map=color_map)
            fig.update_layout(**PLOTLY_THEME, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    # ── Row 2: Siege pro Map + Rundenverteilung ────────────────────────────────
    col3, col4 = st.columns(2)

    with col3:
        if "map" in meta.columns and "winner_side" in meta.columns:
            map_side = meta.groupby(["map", "winner_side"]).size().reset_index(name="Siege")
            fig = px.bar(map_side, x="map", y="Siege", color="winner_side",
                         title="Siege pro Karte & Seite", barmode="group",
                         color_discrete_map={"CounterTerrorist":"#00d4ff","Terrorist":"#ff6b2b"})
            fig.update_layout(**PLOTLY_THEME, xaxis_tickangle=-30,
                              legend=dict(bgcolor="rgba(0,0,0,0)", title=""))
            st.plotly_chart(fig, use_container_width=True)

    with col4:
        if "end_seconds" in meta.columns and "start_seconds" in meta.columns:
            meta2 = meta.copy()
            meta2["duration"] = meta2["end_seconds"] - meta2["start_seconds"]
            meta2 = meta2[meta2["duration"] > 0]
            fig = px.histogram(meta2, x="duration", nbins=50,
                               title="Rundenddauer (Sekunden)",
                               color_discrete_sequence=["#ff6b2b"])
            fig.update_layout(**PLOTLY_THEME)
            st.plotly_chart(fig, use_container_width=True)

    # ── Row 3: Kills pro Waffentyp + Schaden pro Hitbox ───────────────────────
    st.markdown('<p class="section-header">Kampf-Übersicht</p>', unsafe_allow_html=True)
    col5, col6 = st.columns(2)

    with col5:
        if "wp_type" in kills.columns:
            wt = kills["wp_type"].value_counts().head(10).reset_index()
            wt.columns = ["Waffentyp", "Kills"]
            fig = px.bar(wt, x="Kills", y="Waffentyp", orientation="h",
                         title="Kills nach Waffentyp",
                         color="Kills", color_continuous_scale=["#1e2d40","#ff6b2b"])
            fig.update_layout(**PLOTLY_THEME, coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)

    with col6:
        if "hitbox" in dmg.columns:
            hb = dmg["hitbox"].value_counts().reset_index()
            hb.columns = ["Hitbox", "Treffer"]
            fig = px.pie(hb.head(8), names="Hitbox", values="Treffer", hole=0.45,
                         title="Schaden nach Hitbox",
                         color_discrete_sequence=["#ff6b2b","#00d4ff","#39ff14",
                                                  "#ff2b4e","#ffcc00","#c084fc","#38bdf8","#fb7185"])
            fig.update_layout(**PLOTLY_THEME, legend=dict(bgcolor="rgba(0,0,0,0)"))
            fig.update_traces(textfont_color="#e8eaf0")
            st.plotly_chart(fig, use_container_width=True)

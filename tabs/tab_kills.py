import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

PLOTLY_THEME = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(20,25,32,0.8)",
    font=dict(family="Exo 2, sans-serif", color="#8892a4", size=11),
    title_font=dict(family="Rajdhani, sans-serif", color="#e8eaf0", size=16),
    colorway=["#ff6b2b", "#00d4ff", "#39ff14", "#ff2b4e", "#ffcc00", "#c084fc"],
    xaxis=dict(gridcolor="#1e2d40", zerolinecolor="#1e2d40"),
    yaxis=dict(gridcolor="#1e2d40", zerolinecolor="#1e2d40"),
)

def render(data: dict):
    kills = data["kills"]
    meta  = data["meta"]

    st.markdown('<p class="section-header">💀 Kill-Analyse</p>', unsafe_allow_html=True)

    if kills.empty:
        st.warning("Keine Kill-Daten verfügbar.")
        return

    # ── Row 1: Top Waffen + Kills pro Runde ───────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        if "wp" in kills.columns:
            top_n = st.slider("Top N Waffen", 5, 25, 15, key="kills_topn")
            wk = kills["wp"].value_counts().head(top_n).reset_index()
            wk.columns = ["Waffe", "Kills"]
            fig = px.bar(wk, x="Kills", y="Waffe", orientation="h",
                         title=f"Top {top_n} Waffen nach Kills",
                         color="Kills", color_continuous_scale=["#1e2d40","#ff2b4e"])
            fig.update_layout(**PLOTLY_THEME, coloraxis_showscale=False, height=420)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        if "round" in kills.columns:
            kills_per_round = kills.groupby("round").size().reset_index(name="Kills")
            fig = px.line(kills_per_round, x="round", y="Kills",
                          title="Kills pro Runde",
                          color_discrete_sequence=["#00d4ff"])
            fig.update_traces(line=dict(width=2))
            fig.add_scatter(x=kills_per_round["round"], y=kills_per_round["Kills"],
                            mode="markers", marker=dict(size=4, color="#ff6b2b"), showlegend=False)
            fig.update_layout(**PLOTLY_THEME, height=420)
            st.plotly_chart(fig, use_container_width=True)

    # ── Row 2: CT vs T Kills + Überlebende ────────────────────────────────────
    col3, col4 = st.columns(2)

    with col3:
        if "att_side" in kills.columns and "wp_type" in kills.columns:
            side_kills = kills.groupby(["att_side","wp_type"]).size().reset_index(name="Kills")
            fig = px.bar(side_kills, x="wp_type", y="Kills", color="att_side",
                         title="Kills nach Seite & Waffentyp", barmode="stack",
                         color_discrete_map={"CounterTerrorist":"#00d4ff","Terrorist":"#ff6b2b"})
            fig.update_layout(**PLOTLY_THEME, xaxis_tickangle=-30,
                              legend=dict(bgcolor="rgba(0,0,0,0)", title=""))
            st.plotly_chart(fig, use_container_width=True)

    with col4:
        if "ct_alive" in kills.columns and "t_alive" in kills.columns and "seconds" in kills.columns:
            sample_kills = kills.sample(min(3000, len(kills)), random_state=1)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=sample_kills["seconds"], y=sample_kills["ct_alive"],
                                     mode="markers", name="CT alive",
                                     marker=dict(color="#00d4ff", size=3, opacity=0.4)))
            fig.add_trace(go.Scatter(x=sample_kills["seconds"], y=sample_kills["t_alive"],
                                     mode="markers", name="T alive",
                                     marker=dict(color="#ff6b2b", size=3, opacity=0.4)))
            fig.update_layout(**PLOTLY_THEME, title="Überlebende CT & T über Rundenzeit",
                              xaxis_title="Sekunden", yaxis_title="Überlebende",
                              legend=dict(bgcolor="rgba(0,0,0,0)"))
            st.plotly_chart(fig, use_container_width=True)

    # ── Row 3: Bombe + Zeitpunkt-Histogramm ───────────────────────────────────
    col5, col6 = st.columns(2)

    with col5:
        if "is_bomb_planted" in kills.columns:
            bp = kills["is_bomb_planted"].value_counts().reset_index()
            bp.columns = ["Bombe", "Kills"]
            bp["Bombe"] = bp["Bombe"].map({True:"Gepflanzt", False:"Nicht gepflanzt"})
            fig = px.pie(bp, names="Bombe", values="Kills", hole=0.5,
                         title="Kills: Bombe gepflanzt?",
                         color_discrete_sequence=["#ff2b4e","#00d4ff"])
            fig.update_layout(**PLOTLY_THEME, legend=dict(bgcolor="rgba(0,0,0,0)"))
            fig.update_traces(textfont_color="#e8eaf0")
            st.plotly_chart(fig, use_container_width=True)

    with col6:
        if "seconds" in kills.columns:
            fig = px.histogram(kills, x="seconds", nbins=60,
                               title="Kill-Zeitpunkte (Sekunden in Runde)",
                               color_discrete_sequence=["#ff6b2b"])
            fig.update_layout(**PLOTLY_THEME)
            st.plotly_chart(fig, use_container_width=True)

    # ── Row 4: Momentum Chart (Rundenergebnis über Zeit) ─────────────────────
    if "winner_side" in meta.columns and "round" in meta.columns:
        st.markdown('<p class="section-header">Momentum Chart</p>', unsafe_allow_html=True)
        meta2 = meta.copy()
        meta2["CT_win"] = (meta2["winner_side"] == "CounterTerrorist").astype(int)
        meta2["T_win"]  = (meta2["winner_side"] == "Terrorist").astype(int)
        momentum = meta2.groupby("round").agg(CT=("CT_win","sum"), T=("T_win","sum")).reset_index()
        momentum["CT_pct"] = momentum["CT"] / (momentum["CT"] + momentum["T"]) * 100

        fig = go.Figure()
        fig.add_trace(go.Bar(x=momentum["round"], y=momentum["CT"],
                             name="CT Siege", marker_color="#00d4ff"))
        fig.add_trace(go.Bar(x=momentum["round"], y=-momentum["T"],
                             name="T Siege", marker_color="#ff6b2b"))
        fig.update_layout(**{k:v for k,v in PLOTLY_THEME.items() if k != "yaxis"},
                          title="CT vs T Siege pro Runde",
                          barmode="relative", xaxis_title="Runde",
                          legend=dict(bgcolor="rgba(0,0,0,0)"),
                          yaxis=dict(gridcolor="#1e2d40", zerolinecolor="#8892a4",
                                     title="← T Siege  |  CT Siege →"))
        st.plotly_chart(fig, use_container_width=True)

    # ── Row 5: Waffe × Seite Heatmap ─────────────────────────────────────────
    if "wp" in kills.columns and "att_side" in kills.columns:
        st.markdown('<p class="section-header">Waffe × Seite Matrix</p>', unsafe_allow_html=True)
        top_wps = kills["wp"].value_counts().head(20).index
        tmp = kills[kills["wp"].isin(top_wps)].copy()
        tmp["count"] = 1
        pivot = tmp.pivot_table(
            index="wp", columns="att_side", values="count", aggfunc="sum", fill_value=0
        )
        fig = px.imshow(pivot, title="Kill-Häufigkeit: Waffe × Seite",
                        color_continuous_scale=["#0a0c0f","#ff6b2b"],
                        aspect="auto", text_auto=True)
        fig.update_layout(**{k:v for k,v in PLOTLY_THEME.items() if k not in ["xaxis","yaxis"]})
        fig.update_traces(textfont_color="#e8eaf0")
        st.plotly_chart(fig, use_container_width=True)
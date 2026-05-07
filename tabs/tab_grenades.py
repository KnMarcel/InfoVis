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

NADE_COLORS = {
    "Smoke":   "#8892a4",
    "HE":      "#39ff14",
    "Molotov": "#ff6b2b",
    "Flashbang":"#00d4ff",
    "Decoy":   "#ffcc00",
    "Incendiary":"#ff2b4e",
}

def render(data: dict):
    grenades = data["grenades"]
    meta     = data["meta"]

    st.markdown('<p class="section-header">💣 Granaten-Analyse</p>', unsafe_allow_html=True)

    if grenades.empty:
        st.warning("Keine Granaten-Daten verfügbar.")
        return

    # ── Row 1: Granatentypen + Nutzung pro Seite ──────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        if "nade" in grenades.columns:
            nd = grenades["nade"].value_counts().reset_index()
            nd.columns = ["Typ", "Anzahl"]
            colors = [NADE_COLORS.get(t, "#c084fc") for t in nd["Typ"]]
            fig = px.pie(nd, names="Typ", values="Anzahl", hole=0.55,
                         title="Granatentypen-Verteilung",
                         color_discrete_sequence=colors)
            fig.update_layout(**PLOTLY_THEME, legend=dict(bgcolor="rgba(0,0,0,0)"))
            fig.update_traces(textfont_color="#e8eaf0")
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        if "nade" in grenades.columns and "att_side" in grenades.columns:
            side_nade = grenades.groupby(["att_side","nade"]).size().reset_index(name="Anzahl")
            fig = px.bar(side_nade, x="nade", y="Anzahl", color="att_side",
                         title="Granadeusage based on Team", barmode="group",
                         color_discrete_map={"CounterTerrorist":"#00d4ff","Terrorist":"#ff6b2b"})
            fig.update_layout(**PLOTLY_THEME, xaxis_tickangle=-20,
                              legend=dict(bgcolor="rgba(0,0,0,0)", title=""))
            st.plotly_chart(fig, use_container_width=True)

    # ── Row 2: Schaden + Wurfweite ────────────────────────────────────────────
    col3, col4 = st.columns(2)

    with col3:
        if "nade" in grenades.columns and "hp_dmg" in grenades.columns:
            dmg_by_nade = grenades[grenades["hp_dmg"] > 0].groupby("nade").agg(
                Gesamtschaden=("hp_dmg","sum"),
                Treffer=("hp_dmg","count"),
                Durchschnitt=("hp_dmg","mean"),
            ).reset_index().sort_values("Gesamtschaden", ascending=False)
            fig = px.bar(dmg_by_nade, x="nade", y="Gesamtschaden",
                         title="Totaldamage by Granadetyp",
                         color="Durchschnitt",
                         color_continuous_scale=["#1e2d40","#ff6b2b","#ff2b4e"],
                         hover_data=["Treffer","Durchschnitt"])
            fig.update_layout(**PLOTLY_THEME)
            st.plotly_chart(fig, use_container_width=True)

    with col4:
        if all(c in grenades.columns for c in ["att_pos_x","att_pos_y","nade_land_x","nade_land_y"]):
            sample = grenades.dropna(subset=["att_pos_x","att_pos_y","nade_land_x","nade_land_y"]).copy()
            sample["wurfweite"] = np.sqrt(
                (sample["att_pos_x"] - sample["nade_land_x"])**2 +
                (sample["att_pos_y"] - sample["nade_land_y"])**2
            )
            sample = sample[(sample["wurfweite"] > 10) & (sample["wurfweite"] < 5000)]
            if "nade" in sample.columns:
                fig = px.box(sample, x="nade", y="wurfweite",
                             title="Throwingrange by Granadetype",
                             color="nade",
                             color_discrete_map=NADE_COLORS)
                fig.update_layout(**PLOTLY_THEME, showlegend=False)
            else:
                fig = px.histogram(sample, x="wurfweite", nbins=50,
                                   title="Wurfweiten-Verteilung",
                                   color_discrete_sequence=["#ff6b2b"])
                fig.update_layout(**PLOTLY_THEME)
            st.plotly_chart(fig, use_container_width=True)

    # ── Row 3: Zeitverlauf Granaten pro Runde ─────────────────────────────────
    st.markdown('<p class="section-header">Granaten-Zeitverlauf</p>', unsafe_allow_html=True)

    if "round" in grenades.columns and "nade" in grenades.columns:
        col5, col6 = st.columns(2)

        with col5:
            nades_per_round = grenades.groupby(["round","nade"]).size().reset_index(name="Anzahl")
            fig = px.line(nades_per_round, x="round", y="Anzahl", color="nade",
                          title="Granadeusage per Round",
                          color_discrete_map=NADE_COLORS)
            fig.update_layout(**PLOTLY_THEME, legend=dict(bgcolor="rgba(0,0,0,0)", title=""))
            st.plotly_chart(fig, use_container_width=True)

        with col6:
            if "seconds" in grenades.columns:
                fig = px.histogram(grenades, x="seconds", color="nade", nbins=50,
                                   title="Granaten-Zeitpunkte (Sekunden)",
                                   color_discrete_map=NADE_COLORS, barmode="stack")
                fig.update_layout(**PLOTLY_THEME, legend=dict(bgcolor="rgba(0,0,0,0)", title=""))
                st.plotly_chart(fig, use_container_width=True)

    # ── Row 4: Bombeneinfluss + Bombsite ─────────────────────────────────────
    col7, col8 = st.columns(2)

    with col7:
        if "is_bomb_planted" in grenades.columns and "nade" in grenades.columns:
            bp_nade = grenades.groupby(["is_bomb_planted","nade"]).size().reset_index(name="Anzahl")
            bp_nade["is_bomb_planted"] = bp_nade["is_bomb_planted"].map({True:"Gepflanzt", False:"Nicht gepflanzt"})
            fig = px.bar(bp_nade, x="nade", y="Anzahl", color="is_bomb_planted",
                         title="Granaten vor/nach Bombenpflanzung", barmode="group",
                         color_discrete_map={"Gepflanzt":"#ff2b4e","Nicht gepflanzt":"#00d4ff"})
            fig.update_layout(**PLOTLY_THEME, xaxis_tickangle=-20,
                              legend=dict(bgcolor="rgba(0,0,0,0)", title=""))
            st.plotly_chart(fig, use_container_width=True)

    with col8:
        if "bomb_site" in grenades.columns and "nade" in grenades.columns:
            bs_nade = grenades[grenades["bomb_site"].notna() & (grenades["bomb_site"] != "")].groupby(
                ["bomb_site","nade"]).size().reset_index(name="Anzahl")
            if not bs_nade.empty:
                fig = px.bar(bs_nade, x="bomb_site", y="Anzahl", color="nade",
                             title="Granaten nach Bombsite",
                             color_discrete_map=NADE_COLORS)
                fig.update_layout(**PLOTLY_THEME, legend=dict(bgcolor="rgba(0,0,0,0)", title=""))
                st.plotly_chart(fig, use_container_width=True)

    # ── Row 5: Scatter Wurfweite vs Schaden ──────────────────────────────────
    if all(c in grenades.columns for c in ["att_pos_x","att_pos_y","nade_land_x","nade_land_y","hp_dmg"]):
        st.markdown('<p class="section-header">Wurfweite vs. Schaden</p>', unsafe_allow_html=True)
        sample = grenades[grenades["hp_dmg"] > 0].dropna(
            subset=["att_pos_x","att_pos_y","nade_land_x","nade_land_y"]
        ).sample(min(3000, len(grenades[grenades["hp_dmg"]>0])), random_state=42).copy()
        sample["wurfweite"] = np.sqrt(
            (sample["att_pos_x"] - sample["nade_land_x"])**2 +
            (sample["att_pos_y"] - sample["nade_land_y"])**2
        )
        fig = px.scatter(sample, x="wurfweite", y="hp_dmg",
                         color="nade" if "nade" in sample.columns else None,
                         title="Wurfweite vs. Schaden (Sample)",
                         opacity=0.5,
                         color_discrete_map=NADE_COLORS)
        fig.update_layout(**PLOTLY_THEME, legend=dict(bgcolor="rgba(0,0,0,0)", title=""))
        fig.update_traces(marker=dict(size=5))
        st.plotly_chart(fig, use_container_width=True)

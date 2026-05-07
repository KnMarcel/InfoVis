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
    dmg = data["dmg"]

    st.markdown('<p class="section-header">💥 Schadensanalyse</p>', unsafe_allow_html=True)

    if dmg.empty:
        st.warning("Keine Schadensdaten verfügbar.")
        return

    # ── Row 1: Schaden pro Waffe + Schadensverteilung ─────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        if "wp" in dmg.columns and "hp_dmg" in dmg.columns:
            top_n = st.slider("Top N Waffen", 5, 30, 15, key="dmg_topn")
            wp_dmg = dmg.groupby("wp")["hp_dmg"].sum().sort_values(ascending=False).head(top_n).reset_index()
            wp_dmg.columns = ["Waffe", "Gesamtschaden"]
            fig = px.bar(wp_dmg, x="Gesamtschaden", y="Waffe", orientation="h",
                         title=f"Top {top_n} Waffen nach Gesamtschaden",
                         color="Gesamtschaden", color_continuous_scale=["#1e2d40","#ff2b4e"])
            fig.update_layout(**PLOTLY_THEME, coloraxis_showscale=False, height=450)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        if "hp_dmg" in dmg.columns:
            fig = px.histogram(dmg[dmg["hp_dmg"] > 0], x="hp_dmg", nbins=60,
                               title="HP-Schadensverteilung",
                               color_discrete_sequence=["#ff6b2b"])
            fig.update_layout(**PLOTLY_THEME, height=450)
            fig.add_vline(x=100, line_dash="dash", line_color="#39ff14",
                          annotation_text="100 HP (One-Shot)", annotation_font_color="#39ff14")
            st.plotly_chart(fig, use_container_width=True)

    # ── Row 2: Hitbox-Verteilung + Schaden nach Seite ─────────────────────────
    col3, col4 = st.columns(2)

    with col3:
        if "hitbox" in dmg.columns and "hp_dmg" in dmg.columns:
            hb = dmg.groupby("hitbox")["hp_dmg"].agg(["sum", "count", "mean"]).reset_index()
            hb.columns = ["Hitbox", "Gesamtschaden", "Treffer", "Durchschnitt"]
            hb = hb.sort_values("Gesamtschaden", ascending=False)
            fig = px.bar(hb, x="Hitbox", y="Gesamtschaden",
                         title="Schaden nach Hitbox",
                         color="Durchschnitt",
                         color_continuous_scale=["#1e2d40","#ffcc00","#ff2b4e"],
                         hover_data=["Treffer", "Durchschnitt"])
            fig.update_layout(**PLOTLY_THEME, xaxis_tickangle=-30)
            st.plotly_chart(fig, use_container_width=True)

    with col4:
        if "att_side" in dmg.columns and "hp_dmg" in dmg.columns and "wp_type" in dmg.columns:
            side_wp = dmg.groupby(["att_side", "wp_type"])["hp_dmg"].sum().reset_index()
            side_wp.columns = ["Seite", "Waffentyp", "Schaden"]
            fig = px.bar(side_wp, x="Waffentyp", y="Schaden", color="Seite",
                         title="Schaden nach Seite & Waffentyp", barmode="group",
                         color_discrete_map={"CounterTerrorist":"#00d4ff","Terrorist":"#ff6b2b"})
            fig.update_layout(**PLOTLY_THEME, xaxis_tickangle=-30,
                              legend=dict(bgcolor="rgba(0,0,0,0)", title=""))
            st.plotly_chart(fig, use_container_width=True)

    # ── Row 3: Waffenvergleich Radar + Bombeneinfluss ─────────────────────────
    st.markdown('<p class="section-header">Waffenvergleich & Bombeneinfluss</p>', unsafe_allow_html=True)
    col5, col6 = st.columns(2)

    with col5:
        if "wp" in dmg.columns and "hp_dmg" in dmg.columns and "hitbox" in dmg.columns:
            st.markdown("**Radardiagramm: Waffenvergleich**")
            top_weapons = dmg["wp"].value_counts().head(8).index.tolist()
            sel_wps = st.multiselect("Waffen auswählen", top_weapons, default=top_weapons[:4], key="radar_wp")

            if sel_wps:
                radar_df = dmg[dmg["wp"].isin(sel_wps)]
                metrics = radar_df.groupby("wp").agg(
                    Gesamtschaden=("hp_dmg", "sum"),
                    Treffer=("hp_dmg", "count"),
                    DurchschnittsDMG=("hp_dmg", "mean"),
                    Rüstungsschaden=("arm_dmg", "mean") if "arm_dmg" in dmg.columns else ("hp_dmg", "mean"),
                ).reset_index()

                # Normalisieren auf 0–100
                for col in ["Gesamtschaden","Treffer","DurchschnittsDMG","Rüstungsschaden"]:
                    if metrics[col].max() > 0:
                        metrics[col] = metrics[col] / metrics[col].max() * 100

                categories = ["Gesamtschaden","Treffer","DurchschnittsDMG","Rüstungsschaden"]
                colors      = ["#ff6b2b","#00d4ff","#39ff14","#ff2b4e","#ffcc00","#c084fc"]
                fill_colors = ["rgba(255,107,43,0.15)","rgba(0,212,255,0.15)",
                               "rgba(57,255,20,0.15)","rgba(255,43,78,0.15)",
                               "rgba(255,204,0,0.15)","rgba(192,132,252,0.15)"]

                fig = go.Figure()
                for i, row in metrics.iterrows():
                    vals = [row[c] for c in categories]
                    vals.append(vals[0])
                    fig.add_trace(go.Scatterpolar(
                        r=vals,
                        theta=categories + [categories[0]],
                        fill="toself",
                        name=row["wp"],
                        line_color=colors[i % len(colors)],
                        fillcolor=fill_colors[i % len(fill_colors)],
                        opacity=0.85
                    ))
                fig.update_layout(
                    **{k: v for k, v in PLOTLY_THEME.items() if k != "xaxis" and k != "yaxis"},
                    polar=dict(
                        bgcolor="rgba(20,25,32,0.8)",
                        radialaxis=dict(visible=True, range=[0,100], gridcolor="#1e2d40", color="#8892a4"),
                        angularaxis=dict(gridcolor="#1e2d40", color="#8892a4"),
                    ),
                    legend=dict(bgcolor="rgba(0,0,0,0)"),
                )
                st.plotly_chart(fig, use_container_width=True)

    with col6:
        if "is_bomb_planted" in dmg.columns and "hp_dmg" in dmg.columns:
            bomb = dmg.groupby("is_bomb_planted")["hp_dmg"].agg(["mean", "sum", "count"]).reset_index()
            bomb["is_bomb_planted"] = bomb["is_bomb_planted"].map({True:"Bombe gepflanzt", False:"Bombe nicht gepflanzt"})
            bomb.columns = ["Status","Ø Schaden","Gesamtschaden","Treffer"]

            fig = go.Figure()
            fig.add_trace(go.Bar(name="Ø Schaden", x=bomb["Status"], y=bomb["Ø Schaden"],
                                 marker_color=["#ff6b2b","#00d4ff"]))
            fig.update_layout(**PLOTLY_THEME, title="Schaden: Bombe gepflanzt vs. nicht",
                              showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    # ── Row 4: Scatter Schaden vs Entfernung ──────────────────────────────────
    if all(c in dmg.columns for c in ["att_pos_x","att_pos_y","vic_pos_x","vic_pos_y","hp_dmg"]):
        st.markdown('<p class="section-header">Schaden vs. Entfernung</p>', unsafe_allow_html=True)
        sample = dmg.sample(min(5000, len(dmg)), random_state=42).copy()
        sample["distance"] = np.sqrt(
            (sample["att_pos_x"] - sample["vic_pos_x"])**2 +
            (sample["att_pos_y"] - sample["vic_pos_y"])**2
        )
        sample = sample[(sample["distance"] > 0) & (sample["distance"] < 10000)]

        color_by = st.selectbox("Farbe nach", ["wp_type","att_side","hitbox"] if "wp_type" in dmg.columns else ["att_side"], key="scatter_color")
        fig = px.scatter(sample, x="distance", y="hp_dmg",
                         color=color_by if color_by in sample.columns else None,
                         title="Schaden vs. Kampfentfernung (Sample 5.000)",
                         opacity=0.4,
                         color_discrete_sequence=["#ff6b2b","#00d4ff","#39ff14","#ff2b4e","#ffcc00","#c084fc"])
        fig.update_layout(**PLOTLY_THEME, legend=dict(bgcolor="rgba(0,0,0,0)", title=""))
        fig.update_traces(marker=dict(size=4))
        st.plotly_chart(fig, use_container_width=True)

    # ── Row 5: Hitbox Heatmap-Tabelle ─────────────────────────────────────────
    if "wp_type" in dmg.columns and "hitbox" in dmg.columns:
        st.markdown('<p class="section-header">Hitbox × Waffentyp Matrix</p>', unsafe_allow_html=True)
        pivot = dmg.pivot_table(index="hitbox", columns="wp_type", values="hp_dmg",
                                aggfunc="count", fill_value=0)
        fig = px.imshow(pivot, title="Treffer-Häufigkeit: Hitbox × Waffentyp",
                        color_continuous_scale=["#0a0c0f","#ff6b2b","#ffffff"],
                        aspect="auto")
        fig.update_layout(**{k:v for k,v in PLOTLY_THEME.items() if k not in ["xaxis","yaxis"]},
                          coloraxis_colorbar=dict(title="Treffer", tickfont=dict(color="#8892a4")))
        st.plotly_chart(fig, use_container_width=True)
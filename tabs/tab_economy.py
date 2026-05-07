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

def render(data: dict):
    meta = data["meta"]

    st.markdown('<p class="section-header">💰 Economy-Analyse</p>', unsafe_allow_html=True)

    if meta.empty or "ct_eq_val" not in meta.columns:
        st.warning("Keine Economy-Daten verfügbar (ct_eq_val / t_eq_val fehlen).")
        return

    meta2 = meta.copy()
    meta2["total_eq"] = meta2["ct_eq_val"] + meta2["t_eq_val"]
    meta2["ct_advantage"] = meta2["ct_eq_val"] - meta2["t_eq_val"]

    # ── Row 1: Budget-Verteilung + Budget vs Sieg ─────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        fig = go.Figure()
        fig.add_trace(go.Histogram(x=meta2["ct_eq_val"], name="CT Budget",
                                   marker_color="#00d4ff", opacity=0.7, nbinsx=40))
        fig.add_trace(go.Histogram(x=meta2["t_eq_val"], name="T Budget",
                                   marker_color="#ff6b2b", opacity=0.7, nbinsx=40))
        fig.update_layout(**PLOTLY_THEME, title="Budget-Verteilung CT vs T",
                          barmode="overlay", legend=dict(bgcolor="rgba(0,0,0,0)"),
                          xaxis_title="Equipment-Wert ($)")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        if "winner_side" in meta2.columns:
            fig = px.box(meta2, x="winner_side", y="ct_eq_val",
                         title="CT-Budget nach Runden-Gewinner",
                         color="winner_side",
                         color_discrete_map={"CounterTerrorist":"#00d4ff","Terrorist":"#ff6b2b"})
            fig.update_layout(**PLOTLY_THEME, showlegend=False,
                              xaxis_title="Gewinner", yaxis_title="CT Equipment ($)")
            st.plotly_chart(fig, use_container_width=True)

    # ── Row 2: Budget pro Rundentyp + Zeitverlauf ─────────────────────────────
    col3, col4 = st.columns(2)

    with col3:
        if "round_type" in meta2.columns:
            rt_eq = meta2.groupby("round_type").agg(
                CT_avg=("ct_eq_val","mean"),
                T_avg=("t_eq_val","mean"),
            ).reset_index()
            fig = go.Figure()
            fig.add_trace(go.Bar(name="CT Ø Budget", x=rt_eq["round_type"], y=rt_eq["CT_avg"],
                                 marker_color="#00d4ff"))
            fig.add_trace(go.Bar(name="T Ø Budget", x=rt_eq["round_type"], y=rt_eq["T_avg"],
                                 marker_color="#ff6b2b"))
            fig.update_layout(**PLOTLY_THEME, title="Ø Budget nach Rundentyp",
                              barmode="group", legend=dict(bgcolor="rgba(0,0,0,0)"),
                              xaxis_tickangle=-20, yaxis_title="Equipment ($)")
            st.plotly_chart(fig, use_container_width=True)

    with col4:
        if "round" in meta2.columns:
            round_eq = meta2.groupby("round").agg(
                CT=("ct_eq_val","mean"), T=("t_eq_val","mean")
            ).reset_index()
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=round_eq["round"], y=round_eq["CT"],
                                     name="CT", line=dict(color="#00d4ff", width=2)))
            fig.add_trace(go.Scatter(x=round_eq["round"], y=round_eq["T"],
                                     name="T", line=dict(color="#ff6b2b", width=2)))
            # Halbzeit-Linie
            fig.add_vline(x=15.5, line_dash="dash", line_color="#ffcc00",
                          annotation_text="Halbzeit", annotation_font_color="#ffcc00")
            fig.update_layout(**PLOTLY_THEME, title="Ø Equipment pro Runde",
                              xaxis_title="Runde", yaxis_title="Equipment ($)",
                              legend=dict(bgcolor="rgba(0,0,0,0)"))
            st.plotly_chart(fig, use_container_width=True)

    # ── Row 3: Budget-Vorteil vs Gewinner + Scatter ───────────────────────────
    col5, col6 = st.columns(2)

    with col5:
        if "winner_side" in meta2.columns:
            meta2["ct_wins"] = (meta2["winner_side"] == "CounterTerrorist").astype(int)
            bins = pd.cut(meta2["ct_advantage"], bins=10)
            win_rate = meta2.groupby(bins)["ct_wins"].mean().reset_index()
            win_rate.columns = ["Budget-Vorteil CT", "CT Gewinnrate"]
            win_rate["Budget-Vorteil CT"] = win_rate["Budget-Vorteil CT"].astype(str)
            fig = px.bar(win_rate, x="Budget-Vorteil CT", y="CT Gewinnrate",
                         title="CT-Gewinnrate nach Budget-Vorteil",
                         color="CT Gewinnrate",
                         color_continuous_scale=["#ff2b4e","#ffcc00","#39ff14"])
            fig.update_layout(**PLOTLY_THEME, xaxis_tickangle=-30,
                              yaxis_tickformat=".0%",
                              coloraxis_showscale=False)
            fig.add_hline(y=0.5, line_dash="dash", line_color="#8892a4")
            st.plotly_chart(fig, use_container_width=True)

    with col6:
        sample = meta2.sample(min(3000, len(meta2)), random_state=42)
        if "winner_side" in sample.columns:
            fig = px.scatter(sample, x="ct_eq_val", y="t_eq_val",
                             color="winner_side", title="CT-Budget vs T-Budget (Gewinner)",
                             opacity=0.5,
                             color_discrete_map={"CounterTerrorist":"#00d4ff","Terrorist":"#ff6b2b"})
            # Diagonale (Gleichstand)
            max_val = max(sample["ct_eq_val"].max(), sample["t_eq_val"].max())
            fig.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val,
                          line=dict(color="#ffcc00", dash="dash", width=1))
            fig.update_layout(**PLOTLY_THEME, legend=dict(bgcolor="rgba(0,0,0,0)", title=""))
            fig.update_traces(marker=dict(size=4))
            st.plotly_chart(fig, use_container_width=True)

    # ── Row 4: Rundentyp-Gewinnrate ──────────────────────────────────────────
    if "round_type" in meta2.columns and "winner_side" in meta2.columns:
        st.markdown('<p class="section-header">Rundentyp Gewinnrate</p>', unsafe_allow_html=True)
        rt_win = meta2.groupby(["round_type","winner_side"]).size().reset_index(name="Anzahl")
        rt_total = meta2.groupby("round_type").size().reset_index(name="Total")
        rt_win = rt_win.merge(rt_total, on="round_type")
        rt_win["Rate"] = rt_win["Anzahl"] / rt_win["Total"]
        fig = px.bar(rt_win, x="round_type", y="Rate", color="winner_side",
                     title="Gewinnrate nach Rundentyp",
                     barmode="stack",
                     color_discrete_map={"CounterTerrorist":"#00d4ff","Terrorist":"#ff6b2b"})
        fig.update_layout(**PLOTLY_THEME, yaxis_tickformat=".0%",
                          legend=dict(bgcolor="rgba(0,0,0,0)", title=""))
        fig.add_hline(y=0.5, line_dash="dash", line_color="#ffcc00")
        st.plotly_chart(fig, use_container_width=True)

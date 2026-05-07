import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import os
from PIL import Image, ImageOps

MAPS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "maps")

NADE_COLORS = {
    "Smoke": "#8892a4", "HE": "#39ff14", "Molotov": "#ff6b2b",
    "Flashbang": "#00d4ff", "Decoy": "#ffcc00", "Incendiary": "#ff2b4e",
}

MINI_THEME = dict(
    paper_bgcolor="rgba(20,25,32,0.0)",
    plot_bgcolor="rgba(20,25,32,0.0)",
    font=dict(family="Exo 2, sans-serif", color="#8892a4", size=10),
    title_font=dict(family="Rajdhani, sans-serif", color="#e8eaf0", size=13),
    margin=dict(l=8, r=8, t=32, b=8),
    xaxis=dict(gridcolor="#1e2d40", zerolinecolor="#1e2d40", tickfont=dict(size=9)),
    yaxis=dict(gridcolor="#1e2d40", zerolinecolor="#1e2d40", tickfont=dict(size=9)),
    colorway=["#ff6b2b","#00d4ff","#39ff14","#ff2b4e","#ffcc00","#c084fc"],
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=9), title_text=""),
    showlegend=True,
)

def world_to_pixel(series_x, series_y, map_row):
    sx, sy = float(map_row["StartX"]), float(map_row["StartY"])
    ex, ey = float(map_row["EndX"]),   float(map_row["EndY"])
    rx, ry = float(map_row["ResX"]),   float(map_row["ResY"])
    return (series_x - sx) / (ex - sx) * rx, (series_y - sy) / (ey - sy) * ry

@st.cache_data(show_spinner=False)
def compute_density(_px, _py, res_x, res_y, bins=200):
    h, _, _ = np.histogram2d(_px, _py, bins=bins, range=[[0,res_x],[0,res_y]])
    try:
        from scipy.ndimage import gaussian_filter
        h = gaussian_filter(h.T, sigma=3)
    except ImportError:
        h = h.T
    return h

@st.cache_data(show_spinner=False)
def load_map_image(map_name):
    path = os.path.join(MAPS_DIR, f"{map_name}.png")
    if not os.path.exists(path):
        return None
    img = Image.open(path).convert("RGBA")
    return ImageOps.flip(img)   # Y-Achse anpassen

def mini_chart(fig, height=180):
    fig.update_layout(height=height)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

def tile(label):
    st.markdown(f'<p style="font-family:Share Tech Mono,monospace;color:#ff6b2b;font-size:0.62rem;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:4px;">{label}</p>', unsafe_allow_html=True)

def kpi(label, value, color="#ff6b2b"):
    st.markdown(f"""
    <div style="background:rgba(20,25,32,0.9);border:1px solid #1e2d40;border-top:2px solid {color};
                padding:10px 12px;border-radius:3px;margin-bottom:6px;">
        <div style="font-family:Rajdhani,sans-serif;font-size:1.6rem;font-weight:700;color:{color};line-height:1">{value}</div>
        <div style="font-family:Share Tech Mono,monospace;font-size:0.6rem;color:#8892a4;letter-spacing:0.1em;text-transform:uppercase;margin-top:3px">{label}</div>
    </div>""", unsafe_allow_html=True)

def render(data: dict):
    map_data = data["map_data"]
    dmg      = data["dmg"]
    grenades = data["grenades"]
    kills    = data["kills"]
    meta     = data["meta"]

    if map_data.empty or "map" not in map_data.columns:
        st.error("❌ map_data fehlt.")
        return

    maps_with_coords = map_data["map"].tolist()
    sel_maps = data.get("selected_maps", [])
    available = [m for m in sel_maps if m in maps_with_coords] if sel_maps else maps_with_coords
    if not available:
        st.warning(f"Keine Karte mit Koordinaten gewählt. Verfügbar: {maps_with_coords}")
        return

    # ── Karten- & Heatmap-Auswahl (kompakt, eine Zeile) ──────────────────────
    st.markdown('<p class="section-header">🗺️ Kartenanalyse</p>', unsafe_allow_html=True)
    ctrl1, ctrl2, ctrl3, ctrl4 = st.columns([2,2,2,2])
    with ctrl1: chosen_map  = st.selectbox("Karte", available, key="hm_map")
    with ctrl2:
        hm_type = st.selectbox("Heatmap", [
            "Schaden – Opfer", "Schaden – Schütze",
            "Granaten – Einschlag", "Granaten – Wurf"
        ], key="hm_type")
    with ctrl3: hm_side = st.selectbox("Seite", ["Alle","CounterTerrorist","Terrorist"], key="hm_side")
    with ctrl4:
        nade_filter = "Alle"
        if "Granaten" in hm_type and "nade" in grenades.columns:
            nade_types = ["Alle"] + sorted(grenades["nade"].dropna().unique().tolist())
            nade_filter = st.selectbox("Granadentyp", nade_types, key="hm_nade")
        else:
            st.empty()

    # ── Daten für diese Karte ─────────────────────────────────────────────────
    def map_filter(df): 
        return df[df["map"] == chosen_map] if "map" in df.columns else df

    dmg_m  = map_filter(dmg)
    gren_m = map_filter(grenades)
    kill_m = map_filter(kills)
    meta_m = map_filter(meta)

    if hm_side != "Alle":
        dmg_m  = dmg_m[dmg_m.get("att_side","") == hm_side]  if "att_side" in dmg_m.columns  else dmg_m
        gren_m = gren_m[gren_m["att_side"] == hm_side]        if "att_side" in gren_m.columns else gren_m
        kill_m = kill_m[kill_m["att_side"] == hm_side]        if "att_side" in kill_m.columns else kill_m

    # ── Heatmap-Koordinaten wählen ────────────────────────────────────────────
    type_map = {
        "Schaden – Opfer":    (dmg_m,  "vic_pos_x",  "vic_pos_y"),
        "Schaden – Schütze":  (dmg_m,  "att_pos_x",  "att_pos_y"),
        "Granaten – Einschlag":(gren_m, "nade_land_x","nade_land_y"),
        "Granaten – Wurf":    (gren_m, "att_pos_x",  "att_pos_y"),
    }
    df_hm, x_col, y_col = type_map[hm_type]
    if nade_filter != "Alle" and "nade" in df_hm.columns:
        df_hm = df_hm[df_hm["nade"] == nade_filter]

    map_row = map_data[map_data["map"] == chosen_map].iloc[0]
    res_x, res_y = float(map_row["ResX"]), float(map_row["ResY"])

    # Koordinaten umrechnen
    df_coords = df_hm[[x_col,y_col]].dropna()
    df_coords = df_coords[(df_coords[x_col]!=0)|(df_coords[y_col]!=0)]
    heatmap_trace = None
    n_points = 0

    if not df_coords.empty:
        px_c, py_c = world_to_pixel(df_coords[x_col], df_coords[y_col], map_row)
        m = (px_c>=0)&(px_c<=res_x)&(py_c>=0)&(py_c<=res_y)
        px_c, py_c = px_c[m].values, py_c[m].values
        n_points = len(px_c)

        if n_points > 0:
            density = compute_density(px_c, py_c, res_x, res_y, bins=200)
            density_m = np.where(density > density.max()*0.01, density, np.nan)

            if "Granaten" in hm_type and nade_filter != "Alle":
                bc = NADE_COLORS.get(nade_filter, "#ff6b2b")
                r,g,b = int(bc[1:3],16),int(bc[3:5],16),int(bc[5:7],16)
                cs = [[0,f"rgba({r},{g},{b},0)"],[0.3,f"rgba({r},{g},{b},0.4)"],
                      [0.7,f"rgba({r},{g},{b},0.85)"],[1.0,f"rgba({r},{g},{b},1.0)"]]
            else:
                cs = [[0,"rgba(0,0,0,0)"],[0.2,"rgba(0,212,255,0.35)"],
                      [0.55,"rgba(255,107,43,0.75)"],[0.85,"rgba(255,43,78,0.9)"],
                      [1.0,"rgba(255,255,255,1.0)"]]

            heatmap_trace = go.Heatmap(
                z=density_m,
                x=np.linspace(0, res_x, density_m.shape[1]),
                y=np.linspace(0, res_y, density_m.shape[0]),
                colorscale=cs, showscale=False,
                hoverinfo="skip", opacity=0.88, zsmooth="best",
            )

    # ── Layout: Links | Mitte (Karte) | Rechts ───────────────────────────────
    left, mid, right = st.columns([1, 2.2, 1], gap="small")

    # ════ LINKE KACHELN ══════════════════════════════════════════════════════
    with left:
        # KPI: Runden
        n_rounds = len(meta_m)
        n_kills  = len(kill_m)
        n_dmg    = int(dmg_m["hp_dmg"].sum()) if "hp_dmg" in dmg_m.columns else 0
        kpi("Runden", f"{n_rounds:,}")
        kpi("Kills", f"{n_kills:,}", "#00d4ff")
        kpi("HP Schaden", f"{n_dmg:,}", "#ff2b4e")

        # Mini: CT vs T Siege
        if "winner_side" in meta_m.columns and not meta_m.empty:
            tile("Siege CT vs T")
            ws = meta_m["winner_side"].value_counts().reset_index()
            ws.columns = ["Seite","n"]
            fig = px.pie(ws, names="Seite", values="n", hole=0.6,
                         color_discrete_map={"CounterTerrorist":"#00d4ff","Terrorist":"#ff6b2b"})
            fig.update_layout(**{k:v for k,v in MINI_THEME.items() if k not in ["xaxis","yaxis"]},
                              showlegend=True)
            fig.update_traces(textinfo="none")
            mini_chart(fig, 160)

        # Mini: Kills pro Waffe
        if "wp" in kill_m.columns and not kill_m.empty:
            tile("Top Waffen")
            wk = kill_m["wp"].value_counts().head(6).reset_index()
            wk.columns = ["Waffe","Kills"]
            fig = px.bar(wk, x="Kills", y="Waffe", orientation="h",
                         color="Kills", color_continuous_scale=["#1e2d40","#ff2b4e"])
            fig.update_layout(**MINI_THEME, showlegend=False, coloraxis_showscale=False)
            mini_chart(fig, 190)

    # ════ MITTE: HEATMAP ══════════════════════════════════════════════════════
    with mid:
        fig_map = go.Figure()

        # Kartenbild (transparent PNG, vertikal gespiegelt)
        img = load_map_image(chosen_map)
        if img is not None:
            fig_map.add_layout_image(dict(
                source=img, xref="x", yref="y",
                x=0, y=res_y, sizex=res_x, sizey=res_y,
                xanchor="left", yanchor="top",
                sizing="stretch", opacity=1.0, layer="below"
            ))

        # Heatmap-Layer
        if heatmap_trace is not None:
            fig_map.add_trace(heatmap_trace)

        subtitle = hm_type
        if hm_side != "Alle": subtitle += f" · {hm_side}"
        if nade_filter != "Alle": subtitle += f" · {nade_filter}"

        fig_map.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            title=dict(text=f"<b>{chosen_map}</b>  <span style='font-size:11px;color:#8892a4'>{subtitle}</span>",
                       font=dict(family="Rajdhani,sans-serif", color="#e8eaf0", size=15)),
            height=520,
            xaxis=dict(range=[0,res_x], showgrid=False, zeroline=False,
                       showticklabels=False, scaleanchor="y", scaleratio=1),
            yaxis=dict(range=[0,res_y], showgrid=False, zeroline=False, showticklabels=False),
            margin=dict(l=0, r=0, t=36, b=0),
        )
        st.plotly_chart(fig_map, use_container_width=True, config={"displayModeBar": False})

        # Info-Zeile unter der Karte
        ia, ib = st.columns(2)
        ia.markdown(f'<p style="font-family:Share Tech Mono,monospace;color:#39ff14;font-size:0.65rem;">📍 {n_points:,} Datenpunkte</p>', unsafe_allow_html=True)
        ib.markdown(f'<p style="font-family:Share Tech Mono,monospace;color:#8892a4;font-size:0.65rem;text-align:right;">Karte: {chosen_map}</p>', unsafe_allow_html=True)

        # Mini: Schaden-Zeitverlauf (unter der Karte, volle Breite)
        if "round" in dmg_m.columns and "hp_dmg" in dmg_m.columns and not dmg_m.empty:
            tile("Ø Schaden pro Runde")
            rnd_dmg = dmg_m.groupby("round")["hp_dmg"].mean().reset_index()
            fig = px.area(rnd_dmg, x="round", y="hp_dmg",
                          color_discrete_sequence=["#ff6b2b"])
            fig.update_traces(fill="tozeroy", fillcolor="rgba(255,107,43,0.18)",
                              line=dict(color="#ff6b2b", width=1.5))
            fig.update_layout(**MINI_THEME)
            mini_chart(fig, 130)

    # ════ RECHTE KACHELN ══════════════════════════════════════════════════════
    with right:
        n_gren = len(gren_m)
        ct_avg = int(meta_m["ct_eq_val"].mean()) if "ct_eq_val" in meta_m.columns and not meta_m.empty else 0
        t_avg  = int(meta_m["t_eq_val"].mean())  if "t_eq_val"  in meta_m.columns and not meta_m.empty else 0
        kpi("Granaten", f"{n_gren:,}", "#39ff14")
        kpi("Ø CT Budget", f"${ct_avg:,}", "#00d4ff")
        kpi("Ø T Budget", f"${t_avg:,}", "#ffcc00")

        # Mini: Granadentypen
        if "nade" in gren_m.columns and not gren_m.empty:
            tile("Granaten-Typen")
            nd = gren_m["nade"].value_counts().reset_index()
            nd.columns = ["Typ","n"]
            fig = px.pie(nd, names="Typ", values="n", hole=0.6,
                         color_discrete_sequence=[NADE_COLORS.get(t,"#c084fc") for t in nd["Typ"]])
            fig.update_layout(**{k:v for k,v in MINI_THEME.items() if k not in ["xaxis","yaxis"]},
                              showlegend=True) 
            fig.update_traces(textinfo="none")
            mini_chart(fig, 160)

        # Mini: Hitbox-Treffer
        if "hitbox" in dmg_m.columns and not dmg_m.empty:
            tile("Hitbox-Verteilung")
            hb = dmg_m["hitbox"].value_counts().head(6).reset_index()
            hb.columns = ["Hitbox","Treffer"]
            fig = px.bar(hb, x="Treffer", y="Hitbox", orientation="h",
                         color="Treffer", color_continuous_scale=["#1e2d40","#00d4ff"])
            fig.update_layout(**MINI_THEME, showlegend=False, coloraxis_showscale=False)
            mini_chart(fig, 190)
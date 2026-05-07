import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import os
from PIL import Image, ImageOps
from constants import BASE_THEME, NADE_COLORS, get_price, kpi_card
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from heatmap_loader import load_heatmap_grid, available_nade_types, get_colorscale, is_precomputed, LAYER_MAP

MAPS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "maps")
NADE_LIST = ["Smoke","Flashbang","HE","Molotov","Incendiary","Decoy"]

AX = dict(gridcolor="#1e2d40", zerolinecolor="#1e2d40", linecolor="#1e2d40")

def pc(fig, h, key=None):
    fig.update_layout(height=h)
    kw = {"key": key} if key else {}
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, **kw)

def sec_label(text):
    st.markdown(f'<div class="section-label">{text}</div>', unsafe_allow_html=True)

def theme(**kwargs):
    base = {k: v for k, v in BASE_THEME.items() if k not in ["xaxis","yaxis","margin","colorway"]}
    base.update(kwargs)
    return base

@st.cache_data(show_spinner=False)
def load_map_img(map_name):
    p = os.path.join(MAPS_DIR, f"{map_name}.png")
    if not os.path.exists(p): return None
    return ImageOps.flip(Image.open(p).convert("RGBA"))

@st.cache_data(show_spinner=False)
def compute_density(_px, _py, res_x, res_y, bins=160):
    h, _, _ = np.histogram2d(_px, _py, bins=bins, range=[[0,res_x],[0,res_y]])
    try:
        from scipy.ndimage import gaussian_filter
        h = gaussian_filter(h.T, sigma=3)
    except ImportError:
        h = h.T
    return h

def to_px(df, xc, yc, mr):
    sx,sy,ex,ey,rx,ry = (float(mr[k]) for k in ["StartX","StartY","EndX","EndY","ResX","ResY"])
    return (df[xc]-sx)/(ex-sx)*rx, (df[yc]-sy)/(ey-sy)*ry

def clip(px, py, rx, ry):
    m=(px>=0)&(px<=rx)&(py>=0)&(py<=ry)
    return px[m].values, py[m].values

def render(data: dict, chosen_map: str):
    map_data = data["map_data"]
    dmg=data["dmg"]; grenades=data["grenades"]
    kills=data["kills"]; meta=data["meta"]

    if chosen_map not in map_data["map"].values:
        st.warning(f"Keine map_data für {chosen_map}"); return

    mr = map_data[map_data["map"]==chosen_map].iloc[0]
    rx = float(mr["ResX"]); ry = float(mr["ResY"])

    def mf(df): return df[df["map"]==chosen_map].copy() if "map" in df.columns else df.copy()
    D=mf(dmg); G=mf(grenades); K=mf(kills); M=mf(meta)

    # ── ATFF: seconds column is seconds WITHIN round, not absolute ─────────────
    # We take the minimum seconds per round (first damage event)
    # and cap at 115 (round max length)
    atff = 0.0
    if not D.empty and "seconds" in D.columns and "hp_dmg" in D.columns:
        first = D[D["hp_dmg"]>0].groupby(["file","round"])["seconds"].min()
        atff = float(np.clip(first.mean(), 0, 115))

    lethality_pct = 0.0
    if not D.empty and "hp_dmg" in D.columns and len(K)>0:
        td = D["hp_dmg"].sum()
        lethality_pct = len(K)/td*100 if td>0 else 0

    # ═══ TOP ROW ══════════════════════════════════════════════════════════════
    tl, tm, tr = st.columns([1.3, 2.4, 0.9], gap="small")

    with tl:
        # Bullet gauge
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=round(atff, 1),
            title=dict(text="Time-to-First-Frag (avg)",
                       font=dict(family="Share Tech Mono", color="#8892a4", size=9)),
            number=dict(suffix="s", font=dict(family="Rajdhani", color="#ff6b2b", size=30),
                        valueformat=".1f"),
            gauge=dict(
                shape="bullet",
                axis=dict(range=[0,115], tickcolor="#1e2d40",
                          tickfont=dict(size=7, color="#8892a4"),
                          nticks=6),
                bar=dict(color="#ff6b2b", thickness=0.35),
                bgcolor="rgba(20,25,32,0.9)",
                bordercolor="#1e2d40", borderwidth=1,
                steps=[
                    dict(range=[0,30],  color="rgba(255,43,78,0.2)"),
                    dict(range=[30,70], color="rgba(255,204,0,0.1)"),
                    dict(range=[70,115],color="rgba(57,255,20,0.07)"),
                ],
            ),
        ))
        fig.update_layout(**theme(), margin=dict(l=12,r=12,t=40,b=12), height=105)
        pc(fig, 105)

    with tm:
        sec_label("Map Momentum — CT vs T Rolling DMG Delta")
        if not D.empty and "round" in D.columns and "att_side" in D.columns:
            rd = D.groupby(["round","att_side"])["hp_dmg"].sum().unstack(fill_value=0).reset_index()
            ct="CounterTerrorist"; t="Terrorist"
            if ct in rd.columns and t in rd.columns:
                rd["delta"]   = rd[ct]-rd[t]
                rd["rolling"] = rd["delta"].rolling(5, min_periods=1).mean()
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=rd["round"], y=rd["rolling"].clip(lower=0),
                    fill="tozeroy", fillcolor="rgba(0,212,255,0.15)",
                    line=dict(color="#00d4ff", width=1.5, shape="spline"), name="CT+",
                ))
                fig.add_trace(go.Scatter(
                    x=rd["round"], y=rd["rolling"].clip(upper=0),
                    fill="tozeroy", fillcolor="rgba(255,107,43,0.15)",
                    line=dict(color="#ff6b2b", width=1.5, shape="spline"), name="T+",
                ))
                fig.add_hline(y=0, line_color="#2a3545", line_width=1)
                fig.update_layout(**theme(), margin=dict(l=6,r=6,t=8,b=6), height=105,
                                  showlegend=False,
                                  xaxis=dict(**AX, title="Round"),
                                  yaxis=dict(**AX, title="DMG Δ"))
                pc(fig, 105)

    with tr:
        st.markdown(f"""
        <div style="text-align:center;padding:10px 0 0 0">
          <div style="font-family:Share Tech Mono,monospace;font-size:0.58rem;
                      color:#8892a4;letter-spacing:0.15em;text-transform:uppercase">Lethality Index</div>
          <div style="font-family:Rajdhani,sans-serif;font-size:3.0rem;font-weight:700;
                      color:#ff2b4e;line-height:1.05">{lethality_pct:.1f}%</div>
          <div style="font-family:Share Tech Mono,monospace;font-size:0.52rem;color:#8892a4">
            kills / total dmg × 100</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<hr style='border-color:#1e2d40;margin:5px 0 7px 0'>", unsafe_allow_html=True)

    # ═══ MAIN 3-COL ═══════════════════════════════════════════════════════════
    left, mid, right = st.columns([1, 2.3, 1], gap="small")

    # ──────────────────────── LEFT ────────────────────────────────────────────
    with left:
        # Top-3 Weapons Hitbox Radar
        sec_label("Weapon Hitbox Profile — Top 3")
        if not D.empty and "hitbox" in D.columns and "wp" in D.columns:
            cats   = ["Head","Chest","Stomach","Arms","Legs","Generic"]
            colors = [
                ("rgba(255,107,43,1)",  "rgba(255,107,43,0.15)"),
                ("rgba(0,212,255,1)",   "rgba(0,212,255,0.12)"),
                ("rgba(57,255,20,1)",   "rgba(57,255,20,0.10)"),
            ]
            top3 = (D["wp"].value_counts()
                      .head(3).index.tolist())
            fig = go.Figure()
            max_pct = 1
            for i, wp_name in enumerate(top3):
                sub = D[D["wp"] == wp_name]
                hb  = sub["hitbox"].value_counts()
                tot = len(sub) or 1
                pcts = [round(hb.get(c,0)/tot*100,1) for c in cats]
                max_pct = max(max_pct, max(pcts))
                lc, fc = colors[i]
                fig.add_trace(go.Scatterpolar(
                    r=pcts+[pcts[0]],
                    theta=cats+[cats[0]],
                    fill="toself",
                    line=dict(color=lc, width=2),
                    fillcolor=fc,
                    name=wp_name,
                ))
            fig.update_layout(
                **{k:v for k,v in theme().items() if k != "legend"},
                margin=dict(l=10,r=10,t=10,b=10),
                height=240,
                polar=dict(
                    bgcolor="rgba(0,0,0,0)",
                    radialaxis=dict(visible=True, gridcolor="#1e2d40",
                                   tickfont=dict(size=7,color="#8892a4"),
                                   ticksuffix="%",
                                   range=[0, min(max_pct*1.3, 100)]),
                    angularaxis=dict(gridcolor="#1e2d40",
                                     tickfont=dict(size=10,color="#e8eaf0")),
                ),
                showlegend=True,
                legend=dict(
                    bgcolor="rgba(14,18,24,0.85)",
                    bordercolor="#1e2d40", borderwidth=1,
                    font=dict(size=9, color="#e8eaf0",
                              family="Share Tech Mono"),
                    x=0.5, xanchor="center", y=-0.08,
                    orientation="h",
                ),
            )
            pc(fig, 240)

        # Weapon Yield
        sec_label("Weapon Yield")
        if not D.empty and "wp" in D.columns and "hp_dmg" in D.columns:
            wa = D.groupby("wp").agg(
                avg_dmg=("hp_dmg","mean"),
                count=("hp_dmg","count"),
            ).reset_index()
            wa["price"] = wa["wp"].apply(get_price)
            wa = wa.dropna(subset=["price"])
            wa = wa[wa["price"]>0]
            top = wa.nlargest(16,"count")
            sizes = np.clip(np.sqrt(top["count"])/np.sqrt(top["count"].max())*30+6, 6, 36)
            fig = go.Figure(go.Scatter(
                x=top["avg_dmg"],
                y=top["price"],
                mode="markers+text",
                marker=dict(
                    size=sizes,
                    color=top["avg_dmg"],
                    colorscale=[[0,"#1e2d40"],[0.5,"#00d4ff"],[1,"#ff2b4e"]],
                    showscale=False, opacity=0.9,
                    line=dict(color="#0a0c0f",width=1),
                ),
                text=top["wp"],
                textposition="top center",
                textfont=dict(size=8, color="#8892a4"),
                hovertemplate="<b>%{text}</b><br>Avg DMG: %{x:.1f}<br>Cost: $%{y}<extra></extra>",
            ))
            fig.update_layout(**theme(),
                              margin=dict(l=6,r=6,t=10,b=6), height=210,
                              xaxis=dict(**AX, title="Avg Damage"),
                              yaxis=dict(**AX, title="Cost ($)"))
            pc(fig, 210)

    # ──────────────────────── CENTER ──────────────────────────────────────────
    with mid:
        hc1, hc2 = st.columns(2)
        with hc1:
            hm_type = st.selectbox("Engagement Layer", [
                "Schaden – Opfer","Schaden – Schütze",
                "Granaten – Einschlag","Granaten – Wurf","Att + Vic",
            ], key="hm_type")
        with hc2:
            hm_side = st.selectbox("Seite", ["Alle","CounterTerrorist","Terrorist"], key="hm_side")

        # ── Granatentyp-Filter (nur bei Granaten-Einschlag) ─────────────────
        nade_filter = "Alle"
        if hm_type == "Granaten – Einschlag":
            nade_types = available_nade_types(chosen_map)
            if nade_types:
                nade_filter = st.selectbox("Granatentyp", ["Alle"] + nade_types, key="hm_nade")

        # ── Layer-Key bestimmen ───────────────────────────────────────────────
        side_suffix = {"CounterTerrorist":"_ct","Terrorist":"_t"}.get(hm_side, "")
        if hm_type == "Schaden – Opfer" and hm_side != "Alle":
            layer_key = f"dmg_vic{side_suffix}"
        elif hm_type == "Granaten – Einschlag" and nade_filter != "Alle":
            layer_key = f"nade_land_{nade_filter}"
        else:
            layer_key = LAYER_MAP.get(hm_type, "dmg_vic")

        # ── Figure aufbauen ───────────────────────────────────────────────────
        fig_map = go.Figure()

        img = load_map_img(chosen_map)
        if img:
            fig_map.add_layout_image(dict(
                source=img, xref="x", yref="y",
                x=0, y=ry, sizex=rx, sizey=ry,
                xanchor="left", yanchor="top",
                sizing="stretch", opacity=1.0, layer="below",
            ))

        n_pts = 0

        def add_precomputed_layer(layer_name, nade_type=None):
            grid = load_heatmap_grid(chosen_map, layer_name)
            if grid is None:
                return
            dm = np.where(grid > 0.015, grid, np.nan)
            cs = get_colorscale(layer_name, nade_type)
            fig_map.add_trace(go.Heatmap(
                z=dm,
                x0=0, dx=rx/200,
                y0=0, dy=ry/200,
                colorscale=cs, showscale=False,
                hoverinfo="skip", opacity=0.85, zsmooth="best",
            ))

        if not is_precomputed(chosen_map):
            st.warning("⚠️ Heatmaps noch nicht vorberechnet. Bitte `python precompute_heatmaps.py` ausführen.")
        elif hm_type == "Att + Vic":
            add_precomputed_layer("dmg_att")
            add_precomputed_layer("dmg_vic")
        else:
            nt = nade_filter if nade_filter != "Alle" else None
            add_precomputed_layer(layer_key, nt)

        # Map watermark
        fig_map.add_annotation(
            text=chosen_map.upper(), xref="paper", yref="paper",
            x=0.97, y=0.03, showarrow=False,
            font=dict(family="Rajdhani", size=28, color="rgba(255,107,43,0.07)"),
            xanchor="right",
        )

        fig_map.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=450,
            xaxis=dict(range=[0,rx], showgrid=False, zeroline=False,
                       showticklabels=False, scaleanchor="y", scaleratio=1),
            yaxis=dict(range=[0,ry], showgrid=False, zeroline=False, showticklabels=False),
            margin=dict(l=0,r=0,t=4,b=0),
            showlegend=False,
        )
        st.plotly_chart(fig_map, use_container_width=True, config={"displayModeBar":False})
        st.markdown(f'<span style="font-family:Share Tech Mono,monospace;color:#39ff14;'
                    f'font-size:0.6rem">📍 {n_pts:,} pts · {hm_type}</span>',
                    unsafe_allow_html=True)

    # ──────────────────────── RIGHT ───────────────────────────────────────────
    with right:
        sec_label("Utility Effectiveness")
        sel = st.selectbox("Granadentyp", NADE_LIST, key="nade_sel")
        nc  = NADE_COLORS.get(sel, "#ff6b2b")

        if not G.empty and "nade" in G.columns:
            gn = G[G["nade"]==sel]
            thrown   = len(gn)
            dmg_tot  = int(gn["hp_dmg"].sum()) if "hp_dmg" in gn.columns else 0
            avg_dmg  = float(gn["hp_dmg"].mean()) if "hp_dmg" in gn.columns and thrown>0 else 0.0

            for label, val, fmt in [
                ("THROWN",        thrown,  f"{thrown:,}"),
                ("TOTAL DAMAGE",  dmg_tot, f"{dmg_tot:,}"),
                ("AVG DMG / THROW",avg_dmg,f"{avg_dmg:.1f}"),
            ]:
                st.markdown(f"""
                <div style="background:rgba(14,18,24,0.95);border:1px solid #1e2d40;
                            border-top:2px solid {nc};border-radius:2px;
                            padding:9px 12px;margin-bottom:5px;text-align:center">
                  <div style="font-family:Share Tech Mono,monospace;font-size:0.55rem;
                              color:#8892a4;letter-spacing:0.12em">{label}</div>
                  <div style="font-family:Rajdhani,sans-serif;font-size:2.1rem;
                              font-weight:700;color:{nc};line-height:1.1">{fmt}</div>
                </div>""", unsafe_allow_html=True)

        # CT vs T utility bar
        sec_label("All Utility — CT vs T")
        if not G.empty and "nade" in G.columns and "att_side" in G.columns:
            nd = G.groupby(["nade","att_side"]).size().reset_index(name="n")
            fig = px.bar(nd, x="nade", y="n", color="att_side", barmode="group",
                         color_discrete_map={"CounterTerrorist":"#00d4ff","Terrorist":"#ff6b2b"})
            fig.update_layout(**theme(), showlegend=False,
                              margin=dict(l=4,r=4,t=6,b=4), height=150,
                              xaxis=dict(**AX, title="", tickangle=-30,
                                         tickfont=dict(size=8,color="#8892a4")),
                              yaxis=dict(**AX, title=""))
            pc(fig, 150)

        # Flash effectiveness
        sec_label("Flash Effectiveness")
        fe = 0.0
        if not G.empty and not K.empty and "seconds" in G.columns and "seconds" in K.columns:
            fl = G[G["nade"]=="Flashbang"][["file","round","seconds"]].rename(columns={"seconds":"fs"})
            if len(fl)>0:
                mg = K[["file","round","seconds"]].merge(fl, on=["file","round"], how="inner")
                mg["dt"] = mg["seconds"]-mg["fs"]
                fk = mg[(mg["dt"]>=0)&(mg["dt"]<=3)]
                fe = len(fk)/len(fl)*100
        st.markdown(f"""
        <div style="background:rgba(14,18,24,0.95);border:1px solid #1e2d40;
                    border-left:3px solid #ffcc00;border-radius:2px;
                    padding:8px 12px;display:flex;align-items:center;
                    justify-content:space-between;margin-top:4px">
          <span style="font-family:Share Tech Mono,monospace;font-size:0.58rem;color:#8892a4">
            FLASH → KILL (3s)</span>
          <span style="font-family:Rajdhani,sans-serif;font-size:1.7rem;
                       font-weight:700;color:#ffcc00">{fe:.1f}%</span>
        </div>""", unsafe_allow_html=True)


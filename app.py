# =========================================================
# KTT Premium Management System - FINAL OPTIMIZED
# =========================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from folium.plugins import MarkerCluster, MiniMap, Fullscreen
from streamlit_folium import st_folium
from streamlit_option_menu import option_menu
import os

# =========================================================
# 1. Page Config
# =========================================================
st.set_page_config(
    page_title="KTT Premium Management System",
    page_icon="💎",
    layout="wide"
)

# =========================================================
# 2. Session State (Safe Init)
# =========================================================
st.session_state.setdefault("map_center", [37.5665, 126.9780])
st.session_state.setdefault("map_zoom", 11)
st.session_state.setdefault("selected_rows_indices", [])

# =========================================================
# 3. Data Loader (Single Source of Truth)
# =========================================================
@st.cache_data(show_spinner=False)
def load_data():
    result = {"new": None, "old": None}

    # ---------- NEW DB ----------
    if os.path.exists("db.csv"):
        df = pd.read_csv("db.csv")

        df["위도"] = pd.to_numeric(df.get("위도"), errors="coerce").fillna(0)
        df["경도"] = pd.to_numeric(df.get("경도"), errors="coerce").fillna(0)

        if "합산월정료(KTT+KT)" in df.columns:
            df["월정료_숫자"] = pd.to_numeric(
                df["합산월정료(KTT+KT)"].astype(str).str.replace(",", ""),
                errors="coerce"
            ).fillna(0)

        df["계약번호"] = df.get("계약번호", "").astype(str).str.replace(r"\.0$", "", regex=True)
        df["변경요청"] = df.get("변경요청", "")
        df["해지여부"] = df["변경요청"].apply(
            lambda x: "해지예정" if str(x).strip() == "삭제" else "유지"
        )

        df["비고(관리고객 제외)"] = df.get("비고(관리고객 제외)", "")

        if {"군구", "읍면동"}.issubset(df.columns):
            df["주소(지역)"] = df["군구"].fillna("") + " " + df["읍면동"].fillna("")
        else:
            df["주소(지역)"] = df.get("설치주소", "")

        df["지도링크_URL"] = df.get("지도링크_URL", "")

        if "담당부서2" in df.columns:
            df["담당부서2"] = df["담당부서2"].astype(str).str.replace("지사", "")
            order = ["중앙", "강북", "서대문", "고양", "의정부", "남양주", "강릉", "원주"]
            df["담당부서2"] = pd.Categorical(df["담당부서2"], categories=order, ordered=True)
            df = df.sort_values("담당부서2")

        result["new"] = df.reset_index(drop=True)

    # ---------- OLD DASHBOARD ----------
    for fname in ["papp.csv", "papp.xlsx"]:
        if os.path.exists(fname):
            old = pd.read_csv(fname) if fname.endswith(".csv") else pd.read_excel(fname)
            if "구분" in old.columns:
                old = old[old["구분"] != "소계"]
            for c in ["대상", "해지", "해지율"]:
                if c in old.columns:
                    old[c] = pd.to_numeric(
                        old[c].astype(str).str.replace(r"[,%]", "", regex=True),
                        errors="coerce"
                    ).fillna(0)
            if "유지(방어)율" not in old.columns and "해지율" in old.columns:
                old["유지(방어)율"] = 100 - old["해지율"]

            result["old"] = old
            break

    return result


data = load_data()
df_new = data["new"]
df_old = data["old"]

# =========================================================
# 4. Filter Engine (Pure + Cached)
# =========================================================
@st.cache_data(show_spinner=False)
def filter_new(df, search, exclude_note, show_churn, price, branches, sales):
    f = df

    if exclude_note:
        f = f[f["비고(관리고객 제외)"].astype(str).str.strip() == ""]

    if not show_churn:
        f = f[f["해지여부"] == "유지"]

    if search:
        mask = (
            f["관리고객명"].str.contains(search, case=False, na=False) |
            f["계약번호"].str.contains(search, case=False, na=False)
        )
        f = f[mask]

    if price != "전체":
        limit = 100000 if "10만" in price else (300000 if "30만" in price else 500000)
        f = f[f["월정료_숫자"] >= limit] if "이상" in price else f[f["월정료_숫자"] < limit]

    if branches:
        f = f[f["담당부서2"].isin(branches)]

    if sales:
        f = f[f["영업구역정보"].isin(sales)]

    return f.reset_index(drop=True)

# =========================================================
# 5. Sidebar
# =========================================================
with st.sidebar:
    menu = option_menu(
        "KTT System",
        ["2026 관리고객 DB", "기존 대시보드"],
        icons=["database-fill", "bar-chart-fill"],
        default_index=0
    )

    if menu == "2026 관리고객 DB" and df_new is not None:
        search_txt = st.text_input("검색 (고객명 / 계약번호)")
        exclude_note = st.toggle("비고 제외")
        show_churn = st.toggle("해지예정 포함", value=True)
        sel_price = st.radio("월정료", ["전체", "10만 미만", "30만 미만", "50만 이상"])
        sel_branch = st.multiselect("지사", sorted(df_new["담당부서2"].dropna().unique()))
        sel_sales = st.multiselect("영업구역", sorted(df_new["영업구역정보"].dropna().unique()))

# =========================================================
# 6. MAIN : 2026 DB
# =========================================================
if menu == "2026 관리고객 DB":

    filtered = filter_new(
        df_new,
        search_txt,
        exclude_note,
        show_churn,
        sel_price,
        sel_branch,
        sel_sales
    )

    # ---------- KPI ----------
    c1, c2, c3 = st.columns(3)
    c1.metric("총 Rows", f"{len(filtered):,}")
    c2.metric("계약 수", f"{filtered['계약번호'].nunique():,}")
    c3.metric("총 월정료", f"{filtered['월정료_숫자'].sum()/10000:,.0f} 만원")

    # ---------- MAP ----------
    map_df = filtered.query("위도 > 0 and 경도 > 0")
    m = folium.Map(
        location=st.session_state.map_center,
        zoom_start=st.session_state.map_zoom,
        tiles="cartodbpositron"
    )
    MiniMap().add_to(m)
    Fullscreen().add_to(m)

    layer = MarkerCluster(disableClusteringAtZoom=15).add_to(m)

    for _, r in map_df.iterrows():
        folium.Marker(
            [r["위도"], r["경도"]],
            tooltip=r["상호"],
            icon=folium.Icon(color="red" if r["해지여부"] == "해지예정" else "blue")
        ).add_to(layer)

    st_folium(m, height=500, returned_objects=[])

    # ---------- TABLE ----------
    sel = st.dataframe(
        filtered[
            ["관리고객명", "상호", "계약번호", "담당부서2", "합산월정료(KTT+KT)", "해지여부"]
        ],
        use_container_width=True,
        hide_index=True,
        selection_mode="multi-row"
    )

    try:
        rows = sel.selection.rows
        if rows != st.session_state.selected_rows_indices:
            st.session_state.selected_rows_indices = rows
    except Exception:
        pass

    # ---------- CHART ----------
    indigo = [(0, "#e0e7ff"), (1, "#3730a3")]
    counts = filtered["담당부서2"].value_counts().reset_index()
    counts.columns = ["지사", "고객수"]

    fig = px.bar(
        counts,
        x="지사",
        y="고객수",
        color="고객수",
        color_continuous_scale=indigo
    )
    fig.update_traces(render_mode="webgl")
    fig.update_layout(height=320)

    st.plotly_chart(fig, use_container_width=True)

# =========================================================
# 7. MAIN : 기존 대시보드
# =========================================================
if menu == "기존 대시보드" and df_old is not None:

    regions = sorted(df_old["구분"].unique())
    sel_regions = st.multiselect("지사 선택", regions, default=regions)
    sub = df_old[df_old["구분"].isin(sel_regions)]

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("총 대상", int(sub["대상"].sum()))
    k2.metric("총 해지", int(sub["해지"].sum()))
    k3.metric("해지율", f"{sub['해지율'].mean():.1f}%")
    k4.metric("방어율", f"{sub['유지(방어)율'].mean():.1f}%")

    indigo = [(0, "#e0e7ff"), (1, "#3730a3")]

    fig = px.bar(
        sub.groupby("구분")["유지(방어)율"].mean().reset_index(),
        x="구분",
        y="유지(방어)율",
        color="유지(방어)율",
        color_continuous_scale=indigo
    )
    fig.update_traces(render_mode="webgl")
    fig.update_layout(height=350)

    st.plotly_chart(fig, use_container_width=True)

# ======================= END ===============================

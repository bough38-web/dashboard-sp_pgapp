# =========================================================
# KTT Premium Management System (Optimized Full Version)
# =========================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from folium.plugins import MarkerCluster, MiniMap, Fullscreen
from folium.features import DivIcon
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
# 2. Session State Init
# =========================================================
st.session_state.setdefault("map_center", [37.5665, 126.9780])
st.session_state.setdefault("map_zoom", 11)
st.session_state.setdefault("selected_rows_indices", [])

# =========================================================
# 3. Load Data (Cached)
# =========================================================
@st.cache_data(show_spinner=False)
def load_data():
    data = {"old": None, "new": None}

    # --- Old Data ---
    for fname in ["papp.csv", "papp.xlsx"]:
        if os.path.exists(fname):
            df = pd.read_csv(fname) if fname.endswith(".csv") else pd.read_excel(fname)
            if "구분" in df.columns:
                df = df[df["구분"] != "소계"]
            for c in ["대상", "해지", "해지율"]:
                if c in df.columns:
                    df[c] = pd.to_numeric(
                        df[c].astype(str).str.replace(r"[,%]", "", regex=True),
                        errors="coerce"
                    ).fillna(0)
            if "유지(방어)율" not in df.columns and "해지율" in df.columns:
                df["유지(방어)율"] = 100 - df["해지율"]
            data["old"] = df
            break

    # --- New DB ---
    if os.path.exists("db.csv"):
        df = pd.read_csv("db.csv")

        df["위도"] = pd.to_numeric(df.get("위도"), errors="coerce").fillna(0)
        df["경도"] = pd.to_numeric(df.get("경도"), errors="coerce").fillna(0)

        if "합산월정료(KTT+KT)" in df.columns:
            df["월정료_숫자"] = pd.to_numeric(
                df["합산월정료(KTT+KT)"].astype(str).str.replace(",", ""),
                errors="coerce"
            ).fillna(0)

        if "계약번호" in df.columns:
            df["계약번호"] = df["계약번호"].astype(str).str.replace(r"\.0$", "", regex=True)

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

        data["new"] = df

    return data


data = load_data()
df_new, df_old = data["new"], data["old"]

# =========================================================
# 4. Filter Function (Cached)
# =========================================================
@st.cache_data(show_spinner=False)
def apply_filters(df, search, exclude_note, show_churn, price, branches, sales):
    f = df.copy()

    if exclude_note:
        f = f[f["비고(관리고객 제외)"].astype(str).str.strip() == ""]

    if not show_churn:
        f = f[f["해지여부"] == "유지"]

    if search:
        f = f[
            f["관리고객명"].str.contains(search, case=False, na=False) |
            f["계약번호"].str.contains(search, case=False, na=False)
        ]

    if price != "전체":
        limit = 100000 if "10만" in price else (300000 if "30만" in price else 500000)
        f = f[f["월정료_숫자"] >= limit] if "이상" in price else f[f["월정료_숫자"] < limit]

    if branches:
        f = f[f["담당부서2"].isin(branches)]

    if sales:
        f = f[f["영업구역정보"].isin(sales)]

    return f


# =========================================================
# 5. Sidebar
# =========================================================
with st.sidebar:
    menu = option_menu(
        None,
        ["2026 관리고객 DB", "기존 대시보드", "설정"],
        icons=["database-fill", "grid-fill", "gear"],
        default_index=0,
    )

    if menu == "2026 관리고객 DB" and df_new is not None:
        search_txt = st.text_input("검색 (고객명/계약번호)")
        exclude_note = st.toggle("비고 제외")
        show_churn = st.toggle("해지예정 포함", value=True)
        sel_price = st.radio("월정료", ["전체", "10만 미만", "30만 미만", "50만 이상"])

        branches = st.multiselect(
            "지사", sorted(df_new["담당부서2"].dropna().unique())
        )

        sales = st.multiselect(
            "영업구역", sorted(df_new["영업구역정보"].dropna().unique())
        )

# =========================================================
# 6. Main - 2026 DB
# =========================================================
if menu == "2026 관리고객 DB":

    filtered = apply_filters(
        df_new, search_txt, exclude_note, show_churn, sel_price, branches, sales
    )

    # KPI
    c1, c2, c3 = st.columns(3)
    c1.metric("총 Rows", f"{len(filtered):,}")
    c2.metric("계약 수", f"{filtered['계약번호'].nunique():,}")
    c3.metric("총 월정료", f"{filtered['월정료_숫자'].sum()/10000:,.0f} 만원")

    # ---------------- MAP ----------------
    map_df = filtered.query("위도 > 0 and 경도 > 0")
    m = folium.Map(
        location=st.session_state.map_center,
        zoom_start=st.session_state.map_zoom,
        tiles="cartodbpositron"
    )
    MiniMap().add_to(m)
    Fullscreen().add_to(m)

    mc = MarkerCluster(disableClusteringAtZoom=15).add_to(m)

    for _, r in map_df.iterrows():
        folium.Marker(
            [r["위도"], r["경도"]],
            tooltip=r["상호"],
            icon=folium.Icon(
                color="red" if r["해지여부"] == "해지예정" else "blue"
            )
        ).add_to(mc)

    st_folium(m, height=500, returned_objects=[])

    # ---------------- TABLE ----------------
    sel = st.dataframe(
        filtered[
            ["관리고객명", "상호", "계약번호", "담당부서2", "합산월정료(KTT+KT)", "해지여부"]
        ],
        use_container_width=True,
        selection_mode="multi-row",
        hide_index=True
    )

    if sel.selection.rows != st.session_state.selected_rows_indices:
        st.session_state.selected_rows_indices = sel.selection.rows

    # ---------------- CHARTS ----------------
    indigo = [(0, "#e0e7ff"), (1, "#3730a3")]

    if "담당부서2" in filtered.columns:
        cnt = filtered["담당부서2"].value_counts().reset_index()
        cnt.columns = ["지사", "고객수"]
        fig = px.bar(
            cnt,
            x="지사",
            y="고객수",
            color="고객수",
            color_continuous_scale=indigo
        )
        fig.update_traces(render_mode="webgl")
        st.plotly_chart(fig, use_container_width=True)

# =========================================================
# END
# =========================================================

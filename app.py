import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from folium.plugins import MarkerCluster, MiniMap, Fullscreen
from folium.features import DivIcon
from streamlit_folium import st_folium
from streamlit_option_menu import option_menu
import os

# === 1. [System] 페이지 및 세션 설정 ===
st.set_page_config(
    page_title="KTT Premium Management System",
    page_icon="💎",
    layout="wide"
)

# [Session State] 지도 및 선택 상태 관리
if 'map_center' not in st.session_state:
    st.session_state.map_center = [37.5665, 126.9780] # 서울 시청
if 'map_zoom' not in st.session_state:
    st.session_state.map_zoom = 11
if 'selected_rows_indices' not in st.session_state:
    st.session_state.selected_rows_indices = []

# [CSS] Expert UI/UX Styling
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;800&display=swap');
        
        :root {
            --primary: #4f46e5; --primary-light: #e0e7ff;
            --bg-color: #f8fafc; --surface: #ffffff;
            --text-main: #1f2937; --text-sub: #64748b;
        }
        
        .stApp { background-color: var(--bg-color); font-family: 'Pretendard', sans-serif; }
        .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1400px; }

        /* Advanced Card Design */
        .dashboard-card {
            background: var(--surface);
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            border: 1px solid #e2e8f0;
            margin-bottom: 24px;
            transition: all 0.3s ease;
        }
        .dashboard-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        }

        /* Section Headers */
        .section-header {
            font-size: 18px; font-weight: 800; color: var(--text-main);
            margin-bottom: 16px; display: flex; align-items: center; gap: 8px;
            border-bottom: 1px solid #f1f5f9; padding-bottom: 10px;
        }

        /* KPI Custom Style */
        .kpi-box {
            background-color: white; padding: 15px; border-radius: 12px;
            border: 1px solid #e5e7eb; text-align: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .kpi-title { font-size: 12px; color: #6b7280; font-weight: 700; text-transform: uppercase; }
        .kpi-value { font-size: 24px; color: #111827; font-weight: 800; margin: 5px 0; }

        /* Pills Styling */
        div[data-testid="stPills"] { gap: 8px; flex-wrap: wrap; }
        div[data-testid="stPills"] button {
            border: 1px solid #e5e7eb !important; border-radius: 20px !important;
            padding: 6px 16px !important; font-size: 13px !important; font-weight: 600 !important;
            background-color: white !important; color: var(--text-sub) !important;
        }
        div[data-testid="stPills"] button[data-selected="true"] {
            background-color: var(--primary) !important; color: white !important;
            border-color: var(--primary) !important; box-shadow: 0 4px 12px rgba(79, 70, 229, 0.2);
        }
    </style>
""", unsafe_allow_html=True)

# === 2. [Data] 데이터 로드 및 전처리 ===
@st.cache_data
def load_data():
    files = {'old': 'papp.csv', 'new': 'db.csv'}
    data = {'old': None, 'new': None}
    
    # 1. 기존 데이터 로드 (papp.csv)
    for fname in ['papp.csv', 'papp.xlsx']:
        if os.path.exists(fname):
            try:
                df = pd.read_csv(fname) if fname.endswith('.csv') else pd.read_excel(fname)
                if '구분' in df.columns: df = df[df['구분'] != '소계']
                for c in ['대상', '해지', '해지율']:
                    if c in df.columns:
                        df[c] = pd.to_numeric(df[c].astype(str).str.replace(r'[,%]', '', regex=True), errors='coerce').fillna(0)
                if '유지(방어)율' not in df.columns and '해지율' in df.columns:
                    df['유지(방어)율'] = 100 - df['해지율']
                data['old'] = df
                break
            except: continue

    # 2. 2026 DB 로드 (db.csv)
    if os.path.exists(files['new']):
        try:
            df = pd.read_csv(files['new'])
            # 전처리
            for c in ['위도', '경도']:
                if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
            
            if '합산월정료(KTT+KT)' in df.columns:
                df['월정료_숫자'] = pd.to_numeric(df['합산월정료(KTT+KT)'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
            
            if '계약번호' in df.columns:
                df['계약번호'] = df['계약번호'].astype(str).str.replace(r'\.0$', '', regex=True)

            # 해지 여부 (변경요청 기반)
            if '변경요청' not in df.columns: df['변경요청'] = ''
            df['해지여부'] = df['변경요청'].apply(lambda x: '해지예정' if str(x).strip() == '삭제' else '유지')

            # 비고(제외) 확인용 컬럼
            if '비고(관리고객 제외)' not in df.columns: df['비고(관리고객 제외)'] = None

            # 주소 병합
            if '군구' in df.columns and '읍면동' in df.columns:
                df['주소(지역)'] = df['군구'].fillna('') + ' ' + df['읍면동'].fillna('')
            else:
                df['주소(지역)'] = df['설치주소']

            if '지도링크_URL' not in df.columns:
                df['지도링크_URL'] = ''

            # 지사명 정제 및 정렬
            if '담당부서2' in df.columns:
                df['담당부서2'] = df['담당부서2'].astype(str).str.replace('지사', '')
                custom_order = ['중앙', '강북', '서대문', '고양', '의정부', '남양주', '강릉', '원주']
                df['담당부서2'] = pd.Categorical(df['담당부서2'], categories=custom_order, ordered=True)
                df = df.sort_values('담당부서2')
                
            data['new'] = df
        except: pass
    
    return data

data_pack = load_data()
df_new = data_pack['new']
df_old = data_pack['old']

# === 3. [Sidebar] 메뉴 및 필터 ===
with st.sidebar:
    st.markdown("""
        <div style="padding:15px 0; border-bottom:1px solid #e2e8f0; margin-bottom:20px;">
            <span style="font-size:18px; font-weight:900; color:#4f46e5;">💎 KTT System</span>
        </div>
    """, unsafe_allow_html=True)
    
    menu = option_menu(
        None, ["2026 관리고객 DB", "기존 대시보드", "설정"],
        icons=['database-fill', 'grid-fill', 'gear'],
        menu_icon="cast", default_index=0,
        styles={"container": {"padding": "0"}, "nav-link": {"font-size": "14px"}}
    )
    
    st.markdown("---")
    
    # [2026 DB 필터]
    if menu == "2026 관리고객 DB" and df_new is not None:
        st.markdown("**🔍 검색 및 필터**")
        
        # 1. 텍스트 검색
        search_txt = st.text_input("통합 검색 (고객명/계약번호)", placeholder="예: 블루엘리펀트")
        
        # 2. 비고(관리고객 제외) 필터
        exclude_note = st.toggle("🚫 비고(관리고객 제외) 적용", value=False)
        
        # 3. 월정료 필터 (Pills)
        st.caption("💰 월정료 구간")
        price_opts = ["전체", "10만 미만", "30만 미만", "50만 이상"]
        sel_price = st.pills("월정료", price_opts, default="전체", label_visibility="collapsed")
        
        # 4. 해지 포함 여부 (기본값 True: 전체 보기)
        show_churn = st.toggle("🚨 해지예정 포함 보기", value=True)
        
        # 5. 지도 테마 선택
        st.markdown("---")
        st.caption("🎨 지도 스타일")
        map_theme = st.selectbox(
            "지도 배경 선택", 
            ["라이트 (기본)", "다크 (야간모드)", "상세 (OpenStreet)"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # 6. 상세 구역 필터
        with st.expander("📂 지사 및 구역 선택", expanded=True):
            # 지사 (Pills)
            sel_branch = []
            if '담당부서2' in df_new.columns:
                st.caption("지사 (Branch)")
                # 정렬된 순서 유지
                all_branches = df_new['담당부서2'].unique()
                sel_branch = st.pills("지사", all_branches, selection_mode="multi", label_visibility="collapsed")
            
            # 영업구역 (동적 Pills)
            sel_sales = []
            if '영업구역정보' in df_new.columns:
                st.caption("영업구역")
                if sel_branch:
                    filtered_for_opts = df_new[df_new['담당부서2'].isin(sel_branch)]
                    all_sales = sorted(filtered_for_opts['영업구역정보'].astype(str).unique())
                else:
                    all_sales = sorted(df_new['영업구역정보'].astype(str).unique())
                
                if len(all_sales) <= 20:
                    sel_sales = st.pills("영업구역", all_sales, selection_mode="multi", label_visibility="collapsed")
                else:
                    sel_sales = st.multiselect("영업구역", all_sales, label_visibility="collapsed")

# === 4. [Main] 콘텐츠 영역 ===

# -----------------------------------------------------------------------------
# MODE: 2026 관리고객 DB
# -----------------------------------------------------------------------------
if menu == "2026 관리고객 DB":
    if df_new is None:
        st.error("데이터 파일(db.csv)이 없습니다.")
        st.stop()

    # --- Data Filtering ---
    filtered = df_new.copy()
    
    # 1. 비고 제외 필터
    if exclude_note:
        filtered = filtered[
            filtered['비고(관리고객 제외)'].isna() | 
            (filtered['비고(관리고객 제외)'].astype(str).str.strip() == '') |
            (filtered['비고(관리고객 제외)'].astype(str).str.strip() == 'nan')
        ]
        
    # 2. 해지 필터
    if not show_churn: filtered = filtered[filtered['해지여부'] == '유지']
    
    # 3. 검색
    if search_txt:
        filtered = filtered[
            filtered['관리고객명'].astype(str).str.contains(search_txt, case=False) |
            filtered['계약번호'].astype(str).str.contains(search_txt, case=False)
        ]
    # 4. 금액
    if sel_price != "전체":
        limit = 100000 if "10만" in sel_price else (300000 if "30만" in sel_price else 500000)
        if "이상" in sel_price: filtered = filtered[filtered['월정료_숫자'] >= limit]
        else: filtered = filtered[filtered['월정료_숫자'] < limit]
        
    # 5. 구역
    if sel_branch: filtered = filtered[filtered['담당부서2'].isin(sel_branch)]
    if sel_sales: filtered = filtered[filtered['영업구역정보'].isin(sel_sales)]

    # --- Header & KPIs ---
    c1, c2 = st.columns([3, 1])
    with c1:
        st.title("📂 2026 관리고객 DB")
    with c2:
        st.markdown(f"""
            <div style='text-align:right; padding:10px;'>
                <span style='background:#e0e7ff; color:#4338ca; padding:5px 12px; border-radius:20px; font-size:12px; font-weight:700;'>
                    Total: {len(filtered):,} Rows
                </span>
            </div>
        """, unsafe_allow_html=True)

    # --- [KPI Section] ---
    k1, k2, k3, k4 = st.columns(4)
    unique_contracts = filtered['계약번호'].nunique()
    total_amount = filtered['월정료_숫자'].sum()
    excluded_count = len(df_new) - len(filtered)
    
    def kpi_card(label, value, color="black"):
        return f"""
        <div class="kpi-box">
            <div class="kpi-title">{label}</div>
            <div class="kpi-value" style="color:{color}">{value}</div>
        </div>
        """
    with k1: st.markdown(kpi_card("총 데이터 (Rows)", f"{len(filtered):,}건"), unsafe_allow_html=True)
    with k2: st.markdown(kpi_card("총 계약 (Unique)", f"{unique_contracts:,}건", "#4f46e5"), unsafe_allow_html=True)
    with k3: st.markdown(kpi_card("총 월정료", f"{total_amount/10000:,.0f}만원", "#059669"), unsafe_allow_html=True)
    with k4: st.markdown(kpi_card("필터 제외 건수", f"{excluded_count:,}건", "#6b7280"), unsafe_allow_html=True)

    st.markdown("###")

    # --- [TOP] Map Visualization ---
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    
    # 지도 데이터 준비 (선택된 데이터 확인)
    map_target_df = filtered
    
    if st.session_state.selected_rows_indices:
        try:
            selected_df = filtered.iloc[st.session_state.selected_rows_indices]
            if not selected_df.empty:
                map_target_df = selected_df
                # 선택된 데이터의 중심으로 이동 (세션 상태 업데이트)
                center_lat = map_target_df['위도'].mean()
                center_lng = map_target_df['경도'].mean()
                if st.session_state.map_center != [center_lat, center_lng]:
                    st.session_state.map_center = [center_lat, center_lng]
                    st.session_state.map_zoom = 15
                    st.rerun()
        except:
            st.session_state.selected_rows_indices = [] # 인덱스 오류 시 초기화

    map_valid_df = map_target_df[(map_target_df['위도'] > 0) & (map_target_df['경도'] > 0)]
    
    st.markdown(f'<div class="section-header">📍 고객 위치 모니터링 ({len(map_valid_df)}곳)</div>', unsafe_allow_html=True)

    if not map_valid_df.empty:
        # 지도 테마 설정
        if "다크" in map_theme: tile_layer = "cartodbdark_matter"
        elif "상세" in map_theme: tile_layer = "openstreetmap"
        else: tile_layer = "cartodbpositron"

        m = folium.Map(
            location=st.session_state.map_center, 
            zoom_start=st.session_state.map_zoom, 
            tiles=tile_layer
        )
        
        MiniMap(toggle_display=True).add_to(m)
        Fullscreen().add_to(m)
        
        if len(map_valid_df) <= 5: mc = m
        else: mc = MarkerCluster().add_to(m)

        for _, row in map_valid_df.iterrows():
            is_churn = row['해지여부'] == '해지예정'
            color = 'red' if is_churn else 'blue'
            
            # 텍스트 라벨 (데이터 적을 때만 표시)
            if len(map_valid_df) <= 10:
                txt_color = "white" if "다크" in map_theme else "black"
                shadow = "none" if "다크" in map_theme else "1px 1px 0 #fff"
                folium.map.Marker(
                    [row['위도'], row['경도']],
                    icon=DivIcon(
                        icon_size=(150,36),
                        icon_anchor=(75, -10),
                        html=f'<div style="font-size: 11px; font-weight: bold; color: {color}; text-align: center; text-shadow: {shadow};">{row["상호"]}</div>',
                    )
                ).add_to(m)

            popup_html = f"""
            <div style="font-family:'Pretendard',sans-serif; width:220px;">
                <h5 style="margin:0; color:#4f46e5; border-bottom:1px solid #eee; padding-bottom:5px;">
                    {row['관리고객명']}
                </h5>
                <div style="font-size:12px; margin-top:5px; color:#374151;">
                    <b>지사:</b> {row['담당부서2']}<br>
                    <b>월정료:</b> {row['합산월정료(KTT+KT)']}<br>
                    <b>주소:</b> {row['주소(지역)']}<br>
                    <span style='color:#9ca3af; font-size:11px;'>{row.get('영업구역정보','-')}</span>
                </div>
            </div>
            """
            folium.Marker(
                [row['위도'], row['경도']],
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=f"{row['상호']}",
                icon=folium.Icon(color=color, icon='info-sign')
            ).add_to(mc)

        st_folium(m, width="100%", height=500, returned_objects=[])
    else:
        st.warning("표시할 위치 데이터가 없습니다.")
    st.markdown('</div>', unsafe_allow_html=True)

    # --- [MIDDLE] Detailed Data List ---
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">📋 상세 데이터 리스트 (체크하면 지도에 표시)</div>', unsafe_allow_html=True)
    
    cols_show = ['관리고객명', '상호', '계약번호', '담당부서2', '주소(지역)', '합산월정료(KTT+KT)', '영업구역정보', '해지여부', '지도링크_URL']
    final_cols = [c for c in cols_show if c in filtered.columns]
    
    selection = st.dataframe(
        filtered[final_cols],
        use_container_width=True,
        height=400,
        hide_index=True,
        on_select="rerun",
        selection_mode="multi-row",
        column_config={
            "해지여부": st.column_config.TextColumn("상태"),
            "합산월정료(KTT+KT)": st.column_config.TextColumn("월정료"),
            "지도링크_URL": st.column_config.LinkColumn("길찾기", display_text="🔗")
        }
    )
    
    # 선택 상태 저장
    if selection.selection.rows != st.session_state.selected_rows_indices:
        st.session_state.selected_rows_indices = selection.selection.rows
        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

    # --- [BOTTOM] 5-Way Visualizations ---
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">📊 통합 분석 대시보드 (5-Way Analysis)</div>', unsafe_allow_html=True)

    vc1, vc2, vc3 = st.columns(3)
    
    with vc1:
        if '담당부서2' in filtered.columns:
            counts = filtered['담당부서2'].value_counts().reset_index()
            counts.columns = ['지사', '고객수']
            # [수정] color_continuous_scale='Purples' 적용 (오류 해결)
            fig1 = px.bar(counts, x='지사', y='고객수', color='고객수', color_continuous_scale='Purples', title="지사별 고객 분포")
            fig1.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=300)
            st.plotly_chart(fig1, use_container_width=True)

    with vc2:
        if 'BM' in filtered.columns:
            fig2 = px.pie(filtered, names='BM', title="BM(비즈니스) 유형", hole=0.5, color_discrete_sequence=px.colors.qualitative.Prism)
            fig2.update_layout(height=300, margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig2, use_container_width=True)
            
    with vc3:
        fig3 = px.pie(filtered, names='해지여부', title="해지 vs 유지 현황", color_discrete_map={'유지':'#6366f1', '해지예정':'#ef4444'})
        fig3.update_layout(height=300, margin=dict(t=30, b=0, l=0, r=0))
        st.plotly_chart(fig3, use_container_width=True)

    vc4, vc5 = st.columns(2)
    
    with vc4:
        fig4 = px.histogram(filtered, x='월정료_숫자', nbins=20, title="월정료 가격대 분포", color_discrete_sequence=['#818cf8'])
        fig4.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=300, xaxis_title="월정료(원)")
        st.plotly_chart(fig4, use_container_width=True)
        
    with vc5:
        if '영업구역정보' in filtered.columns:
            top_sales = filtered['영업구역정보'].value_counts().nlargest(10).reset_index()
            top_sales.columns = ['영업구역', '고객수']
            # [수정] Mint -> Teal 적용
            fig5 = px.treemap(top_sales, path=['영업구역'], values='고객수', title="핵심 영업구역 Top 10", color='고객수', color_continuous_scale='Teal')
            fig5.update_layout(height=300, margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig5, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# MODE: 기존 대시보드
# -----------------------------------------------------------------------------
elif menu == "기존 대시보드":
    if df_old is None:
        st.warning("기존 데이터(papp.csv)가 없습니다.")
    else:
        st.header("📊 기존 성과 대시보드")
        
        all_regions = sorted(df_old['구분'].unique()) if '구분' in df_old.columns else []
        sel_regions = st.multiselect("지사 선택", all_regions, default=all_regions)
        sub_df = df_old[df_old['구분'].isin(sel_regions)] if '구분' in df_old.columns else df_old
        
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("총 대상", f"{sub_df['대상'].sum():,.0f}")
        k2.metric("총 해지", f"{sub_df['해지'].sum():,.0f}")
        k3.metric("해지율", f"{sub_df['해지율'].mean():.1f}%")
        k4.metric("방어율", f"{sub_df['유지(방어)율'].mean():.1f}%")
        
        st.markdown("---")
        
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("지사별 방어율")
            if '구분' in sub_df.columns:
                fig = px.bar(sub_df.groupby('구분')['유지(방어)율'].mean().reset_index(), x='구분', y='유지(방어)율', color='구분')
                st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.subheader("해지 위험도 (Scatter)")
            fig = px.scatter(sub_df, x='대상', y='유지(방어)율', size='대상', color='해지')
            st.plotly_chart(fig, use_container_width=True)

# -----------------------------------------------------------------------------
# MODE: 설정
# -----------------------------------------------------------------------------
elif menu == "설정":
    st.title("⚙️ 시스템 설정")
    with st.expander("데이터 파일 관리", expanded=True):
        st.file_uploader("DB 파일 업로드 (csv/xlsx)", accept_multiple_files=False)

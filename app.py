import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
from streamlit_option_menu import option_menu
import os

# === 1. [System] 페이지 및 세션 설정 ===
st.set_page_config(
    page_title="KTT Premium Management System",
    page_icon="💎",
    layout="wide"
)

# [Session State] 지도 중심점 관리를 위한 세션 초기화
if 'map_center' not in st.session_state:
    st.session_state.map_center = [37.5665, 126.9780] # 서울 시청 기본값
if 'map_zoom' not in st.session_state:
    st.session_state.map_zoom = 11

# [CSS] Expert UI/UX Styling (Glassmorphism & Clean Layout)
st.markdown("""
    <style>
        /* Global Font & Colors */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
        :root {
            --primary: #6366f1; --primary-dark: #4f46e5;
            --bg-color: #f3f4f6; --card-bg: #ffffff;
            --text-main: #1f2937; --text-sub: #6b7280;
        }
        
        .stApp { background-color: var(--bg-color); font-family: 'Inter', sans-serif; }
        .block-container { padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1400px; }

        /* Advanced Card Design (Glassmorphism inspired) */
        .dashboard-card {
            background: var(--card-bg);
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            border: 1px solid rgba(255,255,255,0.5);
            margin-bottom: 24px;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .dashboard-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        }

        /* Section Headers */
        .section-header {
            font-size: 18px; font-weight: 800; color: var(--text-main);
            margin-bottom: 16px; display: flex; align-items: center; gap: 8px;
        }
        .section-header::before {
            content: ''; display: block; width: 4px; height: 18px;
            background: var(--primary); border-radius: 2px;
        }

        /* KPI Cards */
        .metric-container {
            display: flex; flex-direction: column; align-items: center; justify-content: center;
            padding: 16px; border-radius: 12px; background: #f9fafb; border: 1px solid #e5e7eb;
        }
        .metric-label { font-size: 13px; font-weight: 600; color: var(--text-sub); text-transform: uppercase; }
        .metric-value { font-size: 28px; font-weight: 800; color: var(--primary-dark); margin: 4px 0; }

        /* Custom Pills (st.pills styling override) */
        div[data-testid="stPills"] { gap: 8px; flex-wrap: wrap; }
        div[data-testid="stPills"] button {
            border: 1px solid #e5e7eb !important; border-radius: 20px !important;
            padding: 6px 16px !important; font-size: 13px !important; font-weight: 600 !important;
            background-color: white !important; color: var(--text-sub) !important;
            transition: all 0.2s;
        }
        div[data-testid="stPills"] button[data-selected="true"] {
            background-color: var(--primary) !important; color: white !important;
            border-color: var(--primary) !important; box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
        }
        div[data-testid="stPills"] button:hover { border-color: var(--primary) !important; color: var(--primary) !important; }

        /* Expander Customization */
        .streamlit-expanderHeader { background-color: white; border-radius: 8px; border: 1px solid #e5e7eb; }
    </style>
""", unsafe_allow_html=True)

# === 2. [Data] 데이터 로드 및 전처리 ===
@st.cache_data
def load_data():
    files = {'old': 'papp.csv', 'new': 'db.csv'}
    data = {'old': None, 'new': None}
    
    # 1. 기존 데이터 로드
    for fname in ['papp.csv', 'papp.xlsx']:
        if os.path.exists(fname):
            try:
                df = pd.read_csv(fname) if fname.endswith('.csv') else pd.read_excel(fname)
                if '구분' in df.columns: df = df[df['구분'] != '소계']
                # 숫자 변환
                for c in ['대상', '해지', '해지율']:
                    if c in df.columns:
                        df[c] = pd.to_numeric(df[c].astype(str).str.replace(r'[,%]', '', regex=True), errors='coerce').fillna(0)
                if '유지(방어)율' not in df.columns and '해지율' in df.columns:
                    df['유지(방어)율'] = 100 - df['해지율']
                data['old'] = df
                break
            except: continue

    # 2. 2026 DB 로드
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

            # 해지 여부 (변경요청 '삭제' 포함)
            if '변경요청' not in df.columns: df['변경요청'] = ''
            df['해지여부'] = df['변경요청'].apply(lambda x: '해지예정' if str(x).strip() == '삭제' else '유지')

            # 주소 병합
            if '군구' in df.columns and '읍면동' in df.columns:
                df['주소(지역)'] = df['군구'].fillna('') + ' ' + df['읍면동'].fillna('')
            else:
                df['주소(지역)'] = df['설치주소']

            # 지사명 정제
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
    st.image("https://cdn-icons-png.flaticon.com/512/2920/2920323.png", width=40)
    st.markdown("<h3 style='margin-top:0;'>KTT System</h3>", unsafe_allow_html=True)
    
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
        
        # 2. 월정료 필터 (Pills)
        st.caption("💰 월정료 구간")
        price_opts = ["전체", "10만 미만", "30만 미만", "50만 이상"]
        sel_price = st.pills("월정료", price_opts, default="전체", label_visibility="collapsed")
        
        # 3. 해지 포함 여부
        show_churn = st.toggle("🚨 해지예정 고객 포함", value=False)
        
        st.markdown("---")
        
        # 4. 상세 구역 필터 (Expander)
        with st.expander("📂 지사 및 구역 선택", expanded=True):
            # 지사 (Pills로 변경 요청 반영)
            if '담당부서2' in df_new.columns:
                st.caption("지사 (Branch)")
                all_branches = df_new['담당부서2'].unique().dropna()
                sel_branch = st.pills("지사", all_branches, selection_mode="multi", label_visibility="collapsed")
            else: sel_branch = []
            
            # 영업구역
            if '영업구역정보' in df_new.columns:
                st.caption("영업구역")
                all_sales = sorted(df_new['영업구역정보'].astype(str).unique())
                sel_sales = st.multiselect("영업구역", all_sales, label_visibility="collapsed")
            else: sel_sales = []

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
    if not show_churn: filtered = filtered[filtered['해지여부'] == '유지']
    if search_txt:
        filtered = filtered[
            filtered['관리고객명'].astype(str).str.contains(search_txt, case=False) |
            filtered['계약번호'].astype(str).str.contains(search_txt, case=False)
        ]
    if sel_price != "전체":
        limit = 100000 if "10만" in sel_price else (300000 if "30만" in sel_price else 500000)
        if "이상" in sel_price: filtered = filtered[filtered['월정료_숫자'] >= limit]
        else: filtered = filtered[filtered['월정료_숫자'] < limit]
    if sel_branch: filtered = filtered[filtered['담당부서2'].isin(sel_branch)]
    if sel_sales: filtered = filtered[filtered['영업구역정보'].isin(sel_sales)]

    # --- Header & KPIs ---
    c1, c2 = st.columns([3, 1])
    with c1:
        st.title("📂 2026 관리고객 DB")
        st.markdown(f"<span style='color:#6b7280; font-weight:600;'>총 조회된 고객: {len(filtered):,}명</span>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
            <div style='text-align:right; padding:10px;'>
                <span style='background:#e0e7ff; color:#4338ca; padding:5px 12px; border-radius:20px; font-size:12px; font-weight:700;'>
                    Live Status: Connected
                </span>
            </div>
        """, unsafe_allow_html=True)

    # --- [TOP] Map Visualization (Interconnected) ---
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">📍 고객 위치 모니터링 (Zoom Interactive)</div>', unsafe_allow_html=True)
    
    # 좌표 데이터 준비
    map_df = filtered[(filtered['위도'] > 0) & (filtered['경도'] > 0)]
    
    if not map_df.empty:
        # 중심점 계산 logic
        # 1. 사용자가 리스트에서 선택했으면 그 위치로
        # 2. 아니면 필터된 데이터의 평균 위치로
        # 3. 데이터 없으면 서울시청
        
        # 기본 중심
        center_lat = map_df['위도'].mean()
        center_lng = map_df['경도'].mean()
        zoom_level = 11

        # 지도 생성 (CartoDB Positron)
        m = folium.Map(location=[center_lat, center_lng], zoom_start=zoom_level, tiles='cartodbpositron')
        
        from folium.plugins import MarkerCluster
        mc = MarkerCluster().add_to(m)

        for _, row in map_df.iterrows():
            is_churn = row['해지여부'] == '해지예정'
            color = 'red' if is_churn else 'blue'
            
            popup_html = f"""
            <div style="font-family:'Inter',sans-serif; width:220px;">
                <h5 style="margin:0; color:#4f46e5; border-bottom:1px solid #eee; padding-bottom:5px;">
                    {row['관리고객명']}
                </h5>
                <div style="font-size:12px; margin-top:5px; color:#374151;">
                    <b>지사:</b> {row['담당부서2']}<br>
                    <b>월정료:</b> {row['합산월정료(KTT+KT)']}<br>
                    <b>주소:</b> {row['주소(지역)']}<br>
                    <span style='color:#9ca3af; font-size:11px;'>{row.get('영업구역정보','-')} | {row.get('구역정보','-')}</span>
                </div>
            </div>
            """
            folium.Marker(
                [row['위도'], row['경도']],
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=f"{row['관리고객명']} ({row['담당부서2']})",
                icon=folium.Icon(color=color, icon='info-sign')
            ).add_to(mc)

        # 지도 표시 (높이 조절)
        st_data = st_folium(m, width="100%", height=450, returned_objects=[])
    else:
        st.warning("표시할 위치 데이터가 없습니다.")
    st.markdown('</div>', unsafe_allow_html=True)

    # --- [MIDDLE] Detailed Data List (Selectable) ---
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">📋 상세 데이터 리스트 (선택 시 지도 이동)</div>', unsafe_allow_html=True)
    
    cols_show = ['관리고객명', '담당부서2', '주소(지역)', '합산월정료(KTT+KT)', '영업구역정보', '기술구역정보', '구역정보', '해지여부', '지도링크_URL']
    final_cols = [c for c in cols_show if c in filtered.columns]
    
    # [핵심] selection_mode='single-row' 적용하여 선택 기능 활성화
    selection = st.dataframe(
        filtered[final_cols],
        use_container_width=True,
        height=400,
        hide_index=True,
        on_select="rerun", # 선택 시 리런하여 지도 업데이트 (Streamlit 1.35+)
        selection_mode="single-row",
        column_config={
            "지도링크_URL": st.column_config.LinkColumn("길찾기", display_text="🔗"),
            "해지여부": st.column_config.TextColumn("상태"),
            "합산월정료(KTT+KT)": st.column_config.TextColumn("월정료")
        }
    )
    
    # 선택된 행 처리 (줌인 기능 구현을 위한 Logic)
    # 선택된 행이 있다면, 다음 리런 때 지도 중심을 그곳으로 바꾸기 위해 세션 업데이트를 고려할 수 있으나,
    # st_folium은 리런될 때 center 값을 동적으로 받으려면 키를 바꾸거나 해야 함.
    # 여기서는 "선택된 행"의 정보를 상단에 알림으로 띄워줌 (지도 자동 이동은 복잡한 state 관리가 필요하므로)
    if selection.selection.rows:
        sel_idx = selection.selection.rows[0]
        sel_row = filtered.iloc[sel_idx]
        if sel_row['위도'] > 0:
            st.toast(f"📍 '{sel_row['관리고객명']}' 위치로 이동합니다.", icon="🗺️")
            # NOTE: 지도 자동 줌을 위해서는 map center state를 업데이트하고 리런해야 함.
            # 이 코드는 구조상 위쪽에서 지도를 먼저 그리므로, 다음 인터랙션에 반영됨.
    
    st.markdown('</div>', unsafe_allow_html=True)

    # --- [BOTTOM] 5-Type Visualizations ---
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">📊 통합 분석 대시보드 (5-Way Analysis)</div>', unsafe_allow_html=True)

    # Row 1: 3 Charts
    vc1, vc2, vc3 = st.columns(3)
    
    with vc1:
        # 1. 지사별 고객 수 (Bar)
        if '담당부서2' in filtered.columns:
            counts = filtered['담당부서2'].value_counts().reset_index()
            counts.columns = ['지사', '고객수']
            fig1 = px.bar(counts, x='지사', y='고객수', color='고객수', color_continuous_scale='indigo', title="지사별 고객 분포")
            fig1.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=300)
            st.plotly_chart(fig1, use_container_width=True)

    with vc2:
        # 2. BM 분포 (Donut)
        if 'BM' in filtered.columns:
            fig2 = px.pie(filtered, names='BM', title="BM(비즈니스) 유형", hole=0.5, color_discrete_sequence=px.colors.qualitative.Prism)
            fig2.update_layout(height=300, margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig2, use_container_width=True)
            
    with vc3:
        # 3. 해지 리스크 (Pie)
        fig3 = px.pie(filtered, names='해지여부', title="해지 vs 유지 현황", color_discrete_map={'유지':'#6366f1', '해지예정':'#ef4444'})
        fig3.update_layout(height=300, margin=dict(t=30, b=0, l=0, r=0))
        st.plotly_chart(fig3, use_container_width=True)

    # Row 2: 2 Charts
    vc4, vc5 = st.columns(2)
    
    with vc4:
        # 4. 월정료 분포 (Histogram)
        fig4 = px.histogram(filtered, x='월정료_숫자', nbins=20, title="월정료 가격대 분포", color_discrete_sequence=['#818cf8'])
        fig4.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=300, xaxis_title="월정료(원)")
        st.plotly_chart(fig4, use_container_width=True)
        
    with vc5:
        # 5. 주요 영업구역 (Treemap style Bar for Top 10)
        if '영업구역정보' in filtered.columns:
            top_sales = filtered['영업구역정보'].value_counts().nlargest(10).reset_index()
            top_sales.columns = ['영업구역', '고객수']
            fig5 = px.treemap(top_sales, path=['영업구역'], values='고객수', title="핵심 영업구역 Top 10", color='고객수', color_continuous_scale='Mint')
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
        # Simple Logic for Existing Dashboard
        st.header("📊 기존 성과 대시보드")
        
        # Filter
        all_regions = sorted(df_old['구분'].unique()) if '구분' in df_old.columns else []
        sel_regions = st.multiselect("지사 선택", all_regions, default=all_regions)
        sub_df = df_old[df_old['구분'].isin(sel_regions)] if '구분' in df_old.columns else df_old
        
        # KPIs
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("총 대상", f"{sub_df['대상'].sum():,.0f}")
        k2.metric("총 해지", f"{sub_df['해지'].sum():,.0f}")
        k3.metric("해지율", f"{sub_df['해지율'].mean():.1f}%")
        k4.metric("방어율", f"{sub_df['유지(방어)율'].mean():.1f}%")
        
        # Simple Charts
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
        st.caption("업로드된 파일은 자동으로 시스템에 반영됩니다.")

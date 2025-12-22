import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
from streamlit_option_menu import option_menu
import os

# === 1. [System] 페이지 및 스타일 설정 ===
st.set_page_config(
    page_title="KTT 통합 성과 관리 시스템",
    page_icon="🏢",
    layout="wide"
)

# [CSS] 고급 스타일링 (기존 디자인 + 탭/카드 스타일 강화)
st.markdown("""
    <style>
        :root { --primary: #4f46e5; --bg: #f8fafc; --surface: #ffffff; }
        .stApp { background-color: var(--bg); }
        .block-container { padding-top: 2rem; padding-bottom: 3rem; }
        
        /* 카드 UI */
        .dashboard-card {
            background-color: var(--surface); padding: 24px; border-radius: 16px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.03); border: 1px solid #f1f5f9; margin-bottom: 20px;
        }
        
        /* KPI 카드 */
        .kpi-card-box {
            background-color: var(--surface); padding: 20px; border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04); border-left: 5px solid #ccc; text-align: center;
        }
        .kpi-label { font-size: 13px; font-weight: 700; color: #64748b; text-transform: uppercase; margin-bottom: 5px; }
        .kpi-val { font-size: 32px; font-weight: 800; color: #1e293b; letter-spacing: -1px; }
        .kpi-sub { font-size: 13px; font-weight: 500; color: #94a3b8; }

        /* 탭 스타일 커스텀 */
        .stTabs [data-baseweb="tab-list"] { gap: 8px; }
        .stTabs [data-baseweb="tab"] {
            height: 45px; white-space: nowrap; border-radius: 8px;
            padding: 0 20px; color: #4b5563; font-weight: 600;
            background-color: white; border: 1px solid #e5e7eb;
        }
        .stTabs [aria-selected="true"] {
            background-color: #4f46e5; color: white; border-color: #4f46e5;
        }
    </style>
""", unsafe_allow_html=True)

# === 2. [Data] 데이터 로드 함수 ===
@st.cache_data
def load_existing_data():
    # 기존 대시보드용 데이터 (papp.csv)
    file_names = ['papp.csv', 'papp.xlsx', '시각화.csv']
    df = None
    for file in file_names:
        if os.path.exists(file):
            try:
                if file.endswith('.csv'): df = pd.read_csv(file, header=0)
                else: df = pd.read_excel(file, header=0)
                break
            except: continue
            
    if df is not None:
        if '구분' in df.columns: df = df[df['구분'] != '소계']
        target_cols = ['대상', '해지', '해지율', '유지(방어)율']
        for col in target_cols:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(',', '').str.replace('%', '').str.strip()
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                if col in ['해지율', '유지(방어)율']:
                    if df[col].max() <= 1.0: df[col] = df[col] * 100
                    df[col] = df[col].round(1)
        if '유지(방어)율' not in df.columns and '해지율' in df.columns:
            df['유지(방어)율'] = 100 - df['해지율']
    return df

@st.cache_data
def load_2026_db():
    # 2026 관리고객 DB (db.csv)
    db_file = 'db.csv'
    if os.path.exists(db_file):
        try:
            df = pd.read_csv(db_file)
            # 좌표 및 계약번호 전처리
            for col in ['위도', '경도']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            if '계약번호' in df.columns:
                df['계약번호'] = df['계약번호'].astype(str).str.replace(r'\.0$', '', regex=True)
            
            # [해지 관리] '변경요청'에 '삭제'가 있으면 해지로 간주
            if '해지여부' not in df.columns:
                # 변경요청 컬럼이 없으면 기본 유지로 생성
                if '변경요청' not in df.columns: df['변경요청'] = ''
                df['해지여부'] = df['변경요청'].apply(lambda x: '해지예정' if str(x).strip() == '삭제' else '유지')
            return df
        except: return None
    return None

df_old = load_existing_data()
df_new = load_2026_db()

# === 3. [Sidebar] 메뉴 및 필터 ===
with st.sidebar:
    st.markdown("""
        <div style="padding:15px 0; border-bottom:1px solid #e2e8f0; margin-bottom:20px;">
            <span style="font-size:18px; font-weight:900; color:#4f46e5;">💎 KTT System</span>
        </div>
    """, unsafe_allow_html=True)
    
    # 메뉴 분리
    menu = option_menu(
        None, ["기존 대시보드", "2026 관리고객 DB", "설정"],
        icons=['grid-fill', 'database-fill', 'gear'],
        menu_icon="cast", default_index=1,
        styles={"container": {"padding": "0"}, "nav-link": {"font-size": "14px", "font-weight":"600"}}
    )
    
    st.markdown("---")
    
    # [기존 대시보드 필터]
    if menu == "기존 대시보드" and df_old is not None:
        st.markdown("**필터 (Filters)**")
        custom_order = ['중앙', '강북', '서대문', '고양', '의정부', '남양주', '강릉', '원주']
        region_col = '구분' if '구분' in df_old.columns else df_old.columns[0]
        
        # 지사 정렬
        def sort_key(x):
            try: return custom_order.index(x)
            except: return 999
            
        all_regions = sorted(df_old[region_col].unique().dropna(), key=sort_key)
        
        # 전체 선택/해제 기능
        c1, c2 = st.columns(2)
        if c1.button("전체 선택"): st.session_state.old_regions = all_regions
        if c2.button("초기화"): st.session_state.old_regions = []
        
        if 'old_regions' not in st.session_state: st.session_state.old_regions = all_regions
        
        selected_regions = st.multiselect("지사 선택", all_regions, key='ms_old_regions', default=st.session_state.old_regions)
        
    # [2026 DB 안내]
    elif menu == "2026 관리고객 DB":
        st.info("💡 2026년도 신규 관리 DB 모드입니다.\n\n상단 탭을 통해 리스트, 지도, 통계를 전환하세요.")


# === 4. [Main] 콘텐츠 영역 ===

# ---------------------------------------------------------
# CASE 1: 2026 관리고객 DB
# ---------------------------------------------------------
if menu == "2026 관리고객 DB":
    if df_new is None:
        st.error("'db.csv' 파일을 찾을 수 없습니다.")
        st.stop()
        
    # [헤더]
    c1, c2 = st.columns([3, 1])
    with c1:
        st.title("📂 2026년 관리고객 DB")
        st.caption(f"총 데이터: {len(df_new):,}건 | 위치 정보 보유: {len(df_new[df_new['위도']>0]):,}건")
    with c2:
        # 해지 고객 관리 스위치
        show_churn = st.toggle("🚨 해지(삭제) 고객 포함", value=False)

    # [검색 및 필터 컨테이너]
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.subheader("🔍 검색 및 구역 필터")
    
    # 1. 검색 (상호/계약번호)
    search_txt = st.text_input("통합 검색", placeholder="계약번호 또는 상호명 입력 (예: 52308742, 블루엘리펀트)")
    
    # 2. 3단 구역 필터
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        opts_sales = sorted(df_new['영업구역정보'].astype(str).unique())
        sel_sales = st.multiselect("영업구역 정보", opts_sales)
    with fc2:
        opts_tech = sorted(df_new['기술구역정보'].astype(str).unique())
        sel_tech = st.multiselect("기술구역 정보", opts_tech)
    with fc3:
        opts_zone = sorted(df_new['구역정보'].astype(str).unique())
        sel_zone = st.multiselect("구역 정보", opts_zone)
    st.markdown('</div>', unsafe_allow_html=True)

    # [데이터 필터링]
    filtered_df = df_new.copy()
    
    # 해지 필터 (기본은 제외)
    if not show_churn:
        filtered_df = filtered_df[filtered_df['해지여부'] == '유지']
        
    # 텍스트 검색
    if search_txt:
        filtered_df = filtered_df[
            filtered_df['계약번호'].astype(str).str.contains(search_txt, case=False) |
            filtered_df['상호'].astype(str).str.contains(search_txt, case=False)
        ]
        
    # 구역 필터
    if sel_sales: filtered_df = filtered_df[filtered_df['영업구역정보'].astype(str).isin(sel_sales)]
    if sel_tech: filtered_df = filtered_df[filtered_df['기술구역정보'].astype(str).isin(sel_tech)]
    if sel_zone: filtered_df = filtered_df[filtered_df['구역정보'].astype(str).isin(sel_zone)]

    # [탭 구성: 리스트 / 지도 / 통계]
    tab1, tab2, tab3 = st.tabs(["📋 상세 데이터 리스트", "🗺️ 지도 시각화", "📊 구역별 통계"])

    # TAB 1: 리스트
    with tab1:
        st.markdown(f"##### 검색 결과: {len(filtered_df):,}건")
        display_cols = ['관리고객명', '상호', '계약번호', '해지여부', '영업구역정보', '기술구역정보', '구역정보', '설치주소', '합산월정료(KTT+KT)', '변경요청']
        final_cols = [c for c in display_cols if c in filtered_df.columns]
        
        st.dataframe(
            filtered_df[final_cols],
            use_container_width=True,
            height=600,
            column_config={
                "해지여부": st.column_config.TextColumn("상태", help="변경요청 '삭제' 시 해지예정"),
            }
        )

    # TAB 2: 지도
    with tab2:
        st.markdown("##### 📍 고객 위치 분포")
        map_df = filtered_df[(filtered_df['위도'] > 0) & (filtered_df['경도'] > 0)]
        
        if not map_df.empty:
            center = [map_df['위도'].mean(), map_df['경도'].mean()]
            m = folium.Map(location=center, zoom_start=11, tiles="cartodbpositron")
            
            from folium.plugins import MarkerCluster
            marker_cluster = MarkerCluster().add_to(m)
            
            for _, row in map_df.iterrows():
                # 해지예정은 빨간색, 유지는 파란색
                is_churn = row['해지여부'] == '해지예정'
                color = 'red' if is_churn else 'blue'
                status_html = f"<span style='color:red; font-weight:bold'>[해지예정]</span><br>" if is_churn else ""
                
                popup_html = f"""
                <div style="font-family:sans-serif; width:200px;">
                    <h5 style="margin:0;">{row['상호']}</h5>
                    {status_html}
                    <hr style="margin:5px 0;">
                    <small>계약: {row['계약번호']}</small><br>
                    <small>주소: {row['설치주소']}</small>
                </div>
                """
                folium.Marker(
                    location=[row['위도'], row['경도']],
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=row['상호'],
                    icon=folium.Icon(color=color, icon='info-sign')
                ).add_to(marker_cluster)
            
            st_folium(m, width="100%", height=600)
        else:
            st.warning("위치 정보가 있는 데이터가 없습니다.")

    # TAB 3: 통계
    with tab3:
        st.markdown("##### 📊 구역별 데이터 분석")
        c1, c2 = st.columns(2)
        with c1:
            if '영업구역정보' in filtered_df.columns:
                fig = px.bar(filtered_df['영업구역정보'].value_counts().reset_index(), x='영업구역정보', y='count', title="영업구역별 고객 수")
                st.plotly_chart(fig, use_container_width=True)
        with c2:
            if '해지여부' in filtered_df.columns:
                fig = px.pie(filtered_df['해지여부'].value_counts().reset_index(), values='count', names='해지여부', title="해지 vs 유지 비율",
                             color_discrete_map={'유지':'#4f46e5', '해지예정':'#ef4444'})
                st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------
# CASE 2: 기존 대시보드 (기존 로직 유지)
# ---------------------------------------------------------
elif menu == "기존 대시보드":
    if df_old is None:
        st.error("기존 데이터(papp.csv)가 없습니다.")
        st.stop()
        
    # 필터 적용
    selected = st.session_state.get('ms_old_regions', [])
    if not selected: selected = all_regions
    
    region_col = '구분' if '구분' in df_old.columns else df_old.columns[0]
    code_col = '구역' if '구역' in df_old.columns else df_old.columns[1]
    
    df = df_old[df_old[region_col].isin(selected)]
    
    # KPI
    st.markdown("### 📊 기존 성과 대시보드")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("총 대상", f"{df['대상'].sum():,.0f}건")
    k2.metric("총 해지", f"{df['해지'].sum():,.0f}건")
    k3.metric("평균 해지율", f"{df['해지율'].mean():.1f}%")
    k4.metric("평균 방어율", f"{df['유지(방어)율'].mean():.1f}%")
    
    st.markdown("---")
    
    # 차트
    c1, c2 = st.columns([1, 1])
    with c1:
        st.subheader("지사별 방어율")
        fig = px.bar(df.groupby(region_col)['유지(방어)율'].mean().reset_index(), x=region_col, y='유지(방어)율', color=region_col)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.subheader("해지 위험 분석 (4분면)")
        fig = px.scatter(df, x='대상', y='유지(방어)율', size='대상', color='해지', hover_name=code_col)
        fig.add_hline(y=df['유지(방어)율'].mean(), line_dash="dot", line_color="green")
        fig.add_vline(x=df['대상'].mean(), line_dash="dot", line_color="blue")
        st.plotly_chart(fig, use_container_width=True)

elif menu == "설정":
    st.title("⚙️ 시스템 설정")
    st.info("파일 업로드 및 관리자 설정")
    with st.expander("파일 업로드 (csv)", expanded=True):
        st.file_uploader("데이터 파일 업로드", type=['csv'])

import streamlit as st
import pandas as pd
import plotly.express as px  # [수정] 누락되었던 라이브러리 추가
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

# [CSS] 고급 스타일링
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

        /* 탭 스타일 */
        .stTabs [data-baseweb="tab-list"] { gap: 8px; }
        .stTabs [data-baseweb="tab"] {
            height: 45px; white-space: nowrap; border-radius: 8px;
            padding: 0 20px; color: #4b5563; font-weight: 600;
            background-color: white; border: 1px solid #e5e7eb;
        }
        .stTabs [aria-selected="true"] {
            background-color: #4f46e5; color: white; border-color: #4f46e5;
        }

        /* [Pills] 버튼 스타일 */
        div[data-testid="stPills"] { gap: 6px; flex-wrap: wrap; }
        div[data-testid="stPills"] button {
            border-radius: 20px !important; border: 1px solid #d1d5db !important;
            padding: 4px 12px !important; font-size: 12px !important;
            background-color: white; color: #4b5563;
        }
        div[data-testid="stPills"] button[data-selected="true"] {
            background-color: #4f46e5 !important; color: white !important;
            border-color: #4f46e5 !important;
        }
        
        /* Expander 헤더 스타일 */
        .streamlit-expanderHeader {
            font-weight: 600; color: #374151; background-color: #f9fafb; border-radius: 8px;
        }
    </style>
""", unsafe_allow_html=True)

# === 2. [Data] 데이터 로드 함수 ===
@st.cache_data
def load_existing_data():
    """기존 대시보드용 데이터 로드 (papp.csv)"""
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
    """2026 관리고객 DB 로드 (db.csv)"""
    db_file = 'db.csv'
    if os.path.exists(db_file):
        try:
            df = pd.read_csv(db_file)
            
            # 1. 숫자 데이터 변환 (위도, 경도, 금액)
            for col in ['위도', '경도']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            if '합산월정료(KTT+KT)' in df.columns:
                df['월정료_숫자'] = df['합산월정료(KTT+KT)'].astype(str).str.replace(',', '').str.strip()
                df['월정료_숫자'] = pd.to_numeric(df['월정료_숫자'], errors='coerce').fillna(0)
                
            # 2. 계약번호 처리
            if '계약번호' in df.columns:
                df['계약번호'] = df['계약번호'].astype(str).str.replace(r'\.0$', '', regex=True)

            # 3. [해지 관리]
            if '해지여부' not in df.columns:
                if '변경요청' not in df.columns: df['변경요청'] = ''
                df['해지여부'] = df['변경요청'].apply(lambda x: '해지예정' if str(x).strip() == '삭제' else '유지')

            # 4. 주소 데이터 결합 (군구 + 읍면동) -> 주소(지역)
            if '군구' in df.columns and '읍면동' in df.columns:
                df['주소(지역)'] = df['군구'].fillna('') + ' ' + df['읍면동'].fillna('')
                df['주소(지역)'] = df['주소(지역)'].str.strip()
            else:
                df['주소(지역)'] = df['설치주소']
                
            # 5. 지도 링크 확인
            if '지도링크_URL' not in df.columns:
                df['지도링크_URL'] = ''

            # 6. [지사명 정리 및 정렬] "지사" 글자 제거 및 지정된 순서 정렬
            if '담당부서2' in df.columns:
                # "지사" 글자 제거 (예: 강북지사 -> 강북)
                df['담당부서2'] = df['담당부서2'].astype(str).str.replace('지사', '')
                
                # 사용자 지정 정렬 순서
                custom_order = ['중앙', '강북', '서대문', '고양', '의정부', '남양주', '강릉', '원주']
                
                # Categorical 데이터를 사용하여 정렬 (순서에 없는 값은 맨 뒤로)
                df['담당부서2'] = pd.Categorical(df['담당부서2'], categories=custom_order, ordered=True)
                df = df.sort_values('담당부서2')

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
    
    # -------------------------------------------------------------------------
    # 필터: [기존 대시보드]
    # -------------------------------------------------------------------------
    if menu == "기존 대시보드" and df_old is not None:
        st.markdown("**필터 (Filters)**")
        custom_order = ['중앙', '강북', '서대문', '고양', '의정부', '남양주', '강릉', '원주']
        region_col = '구분' if '구분' in df_old.columns else df_old.columns[0]
        
        def sort_key(x):
            try: return custom_order.index(x)
            except: return 999
            
        try:
            unique_regions = df_old[region_col].dropna().unique()
            all_regions = sorted(unique_regions, key=sort_key)
        except: all_regions = []
        
        # 전체 선택 기능
        c1, c2 = st.columns(2)
        if c1.button("전체 선택"): st.session_state.old_regions = all_regions
        if c2.button("초기화"): st.session_state.old_regions = []
        
        if 'old_regions' not in st.session_state: st.session_state.old_regions = all_regions
        selected_regions = st.multiselect("지사 선택", all_regions, key='ms_old_regions', default=st.session_state.old_regions)
        
    # -------------------------------------------------------------------------
    # 필터: [2026 관리고객 DB]
    # -------------------------------------------------------------------------
    elif menu == "2026 관리고객 DB" and df_new is not None:
        # 1. 고객명 검색
        st.markdown("**🔍 고객 검색**")
        search_name = st.text_input("관리고객명 검색", placeholder="고객명 입력...")

        st.markdown("---")
        st.markdown("**🎛️ 상세 필터**")

        # 2. 금액대 필터 (버튼식)
        st.caption("💰 월정료 구간 선택")
        price_options = ["전체", "10만 미만", "20만 미만", "30만 미만", "30만 이상", "50만 이상"]
        selected_price = st.pills("월정료 필터", price_options, default="전체", label_visibility="collapsed")
        
        st.markdown("---")

        # 3. 접기/펼치기 필터 그룹 (Expander)
        
        # (1) 담당부서2 (지사)
        with st.expander("📂 담당부서(지사) 선택", expanded=True):
            if '담당부서2' in df_new.columns:
                # 이미 로드할 때 정렬했으므로 unique()만 호출해도 순서 유지
                opts_branch = df_new['담당부서2'].unique()
                sel_branch = st.multiselect("지사 선택", opts_branch, default=[], placeholder="지사 선택...")
            else: sel_branch = []

        # (2) 영업구역정보
        with st.expander("📍 영업구역 정보", expanded=False):
            if '영업구역정보' in df_new.columns:
                opts_sales = sorted(df_new['영업구역정보'].astype(str).unique())
                sel_sales = st.multiselect("영업구역 선택", opts_sales, default=[])
            else: sel_sales = []

        # (3) 기술구역정보
        with st.expander("🛠️ 기술구역 정보", expanded=False):
            if '기술구역정보' in df_new.columns:
                opts_tech = sorted(df_new['기술구역정보'].astype(str).unique())
                sel_tech = st.multiselect("기술구역 선택", opts_tech, default=[])
            else: sel_tech = []

        # (4) 구역정보
        with st.expander("🗺️ 구역 정보", expanded=False):
            if '구역정보' in df_new.columns:
                opts_zone = sorted(df_new['구역정보'].astype(str).unique())
                sel_zone = st.multiselect("구역 선택", opts_zone, default=[])
            else: sel_zone = []


# === 4. [Main] 콘텐츠 영역 ===

# ---------------------------------------------------------
# CASE 1: 2026 관리고객 DB
# ---------------------------------------------------------
if menu == "2026 관리고객 DB":
    if df_new is None:
        st.error("'db.csv' 파일을 찾을 수 없습니다. (2026 DB 파일 필요)")
        st.stop()
        
    # [헤더]
    c1, c2 = st.columns([3, 1])
    with c1:
        st.title("📂 2026년 관리고객 DB")
        st.caption(f"총 데이터: {len(df_new):,}건 | 위치 정보 보유: {len(df_new[df_new['위도']>0]):,}건")
    with c2:
        show_churn = st.toggle("🚨 해지(삭제) 고객 포함", value=False)

    # [데이터 필터링 로직]
    filtered_df = df_new.copy()
    
    # 1. 해지 필터
    if not show_churn:
        filtered_df = filtered_df[filtered_df['해지여부'] == '유지']
    
    # 2. 고객명 검색 (사이드바 입력)
    if search_name:
        filtered_df = filtered_df[filtered_df['관리고객명'].astype(str).str.contains(search_name, case=False)]

    # 3. 금액 필터
    if selected_price != "전체":
        if selected_price == "10만 미만": filtered_df = filtered_df[filtered_df['월정료_숫자'] < 100000]
        elif selected_price == "20만 미만": filtered_df = filtered_df[filtered_df['월정료_숫자'] < 200000]
        elif selected_price == "30만 미만": filtered_df = filtered_df[filtered_df['월정료_숫자'] < 300000]
        elif selected_price == "30만 이상": filtered_df = filtered_df[filtered_df['월정료_숫자'] >= 300000]
        elif selected_price == "50만 이상": filtered_df = filtered_df[filtered_df['월정료_숫자'] >= 500000]

    # 4. 사이드바 상세 필터 적용
    if sel_branch: filtered_df = filtered_df[filtered_df['담당부서2'].isin(sel_branch)]
    if sel_sales: filtered_df = filtered_df[filtered_df['영업구역정보'].isin(sel_sales)]
    if sel_tech: filtered_df = filtered_df[filtered_df['기술구역정보'].isin(sel_tech)]
    if sel_zone: filtered_df = filtered_df[filtered_df['구역정보'].isin(sel_zone)]

    # [메인 검색창] (계약번호/상호)
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.subheader("🔍 통합 검색")
    search_txt = st.text_input("계약번호 또는 상호 입력", placeholder="예: 52308742, 블루엘리펀트")
    
    if search_txt:
        filtered_df = filtered_df[
            filtered_df['계약번호'].astype(str).str.contains(search_txt, case=False) |
            filtered_df['상호'].astype(str).str.contains(search_txt, case=False)
        ]
    st.markdown('</div>', unsafe_allow_html=True)

    # [탭 구성]
    tab1, tab2, tab3 = st.tabs(["📋 상세 데이터 리스트", "🗺️ 지도 시각화", "📊 구역별 통계"])

    # TAB 1: 상세 리스트
    with tab1:
        st.markdown(f"##### 조회 결과: {len(filtered_df):,}건")
        
        # [요청사항] 표시 컬럼 순서 및 구성
        cols_to_show = [
            '관리고객명', '상호', '계약번호', '해지여부', '담당부서2', 
            '주소(지역)', '합산월정료(KTT+KT)', 
            '영업구역정보', '기술구역정보', '구역정보', # 구역정보 3종 추가
            '지도링크_URL'
        ]
        final_cols = [c for c in cols_to_show if c in filtered_df.columns]
        
        st.dataframe(
            filtered_df[final_cols],
            use_container_width=True,
            height=600,
            column_config={
                "해지여부": st.column_config.TextColumn("상태", width="small"),
                "담당부서2": st.column_config.TextColumn("지사", width="small"),
                "주소(지역)": st.column_config.TextColumn("지역 (군/구+읍/면/동)", width="medium"),
                "합산월정료(KTT+KT)": st.column_config.TextColumn("월정료", width="small"),
                "영업구역정보": st.column_config.TextColumn("영업구역", width="small"),
                "기술구역정보": st.column_config.TextColumn("기술구역", width="small"),
                "구역정보": st.column_config.TextColumn("구역", width="small"),
                "지도링크_URL": st.column_config.LinkColumn(
                    "길찾기", help="클릭 시 지도로 이동", display_text="지도보기 🔗"
                )
            },
            hide_index=True
        )

    # TAB 2: 지도 시각화
    with tab2:
        st.markdown("##### 📍 고객 위치 분포")
        map_df = filtered_df[(filtered_df['위도'] > 0) & (filtered_df['경도'] > 0)]
        
        if not map_df.empty:
            # 지도 초기화
            center = [map_df['위도'].mean(), map_df['경도'].mean()]
            m = folium.Map(location=center, zoom_start=11, tiles="cartodbpositron")
            
            from folium.plugins import MarkerCluster
            marker_cluster = MarkerCluster().add_to(m)
            
            for _, row in map_df.iterrows():
                is_churn = row['해지여부'] == '해지예정'
                color = 'red' if is_churn else 'blue'
                status_html = f"<span style='color:red; font-weight:bold'>[해지예정]</span><br>" if is_churn else ""
                
                # [수정] 팝업 내용 강화: 상호(지사), 구역정보 3종 포함
                popup_html = f"""
                <div style="font-family:sans-serif; width:260px;">
                    <h5 style="margin:0; color:#4f46e5;">{row['상호']} ({row['담당부서2']})</h5>
                    {status_html}
                    <hr style="margin:5px 0;">
                    <div style="font-size:12px; color:#555; line-height:1.4;">
                        <b>주소:</b> {row['주소(지역)']}<br>
                        <b>월정료:</b> {row['합산월정료(KTT+KT)']}<br>
                        <div style="background:#f3f4f6; padding:5px; margin:5px 0; border-radius:4px;">
                            <b>영업:</b> {row.get('영업구역정보', '-')}<br>
                            <b>기술:</b> {row.get('기술구역정보', '-')}<br>
                            <b>구역:</b> {row.get('구역정보', '-')}
                        </div>
                    </div>
                    <div style="margin-top:8px;">
                        <a href="{row['지도링크_URL']}" target="_blank" 
                           style="background:#4f46e5; color:white; padding:4px 8px; text-decoration:none; font-size:11px; border-radius:4px;">
                           길찾기 🔗
                        </a>
                    </div>
                </div>
                """
                
                folium.Marker(
                    location=[row['위도'], row['경도']],
                    tooltip=f"{row['상호']} ({row['담당부서2']})",
                    popup=folium.Popup(popup_html, max_width=300),
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
# CASE 2: 기존 대시보드
# ---------------------------------------------------------
elif menu == "기존 대시보드":
    if df_old is None:
        st.error("기존 데이터(papp.csv)가 없습니다.")
        st.stop()
        
    selected = st.session_state.get('ms_old_regions', [])
    if not selected: selected = all_regions
    
    region_col = '구분' if '구분' in df_old.columns else df_old.columns[0]
    code_col = '구역' if '구역' in df_old.columns else df_old.columns[1]
    
    df = df_old[df_old[region_col].isin(selected)]
    
    st.markdown("### 📊 기존 성과 대시보드")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("총 대상", f"{df['대상'].sum():,.0f}건")
    k2.metric("총 해지", f"{df['해지'].sum():,.0f}건")
    k3.metric("평균 해지율", f"{df['해지율'].mean():.1f}%")
    k4.metric("평균 방어율", f"{df['유지(방어)율'].mean():.1f}%")
    
    st.markdown("---")
    
    c1, c2 = st.columns([1, 1])
    with c1:
        st.subheader("지사별 방어율")
        fig = px.bar(df.groupby(region_col)['유지(방어)율'].mean().reset_index(), x=region_col, y='유지(방어)율', color=region_col)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.subheader("해지 위험 분석 (4분면)")
        fig = px.scatter(df, x='대상', y='유지(방어)율', size='대상', color='해지', hover_name=code_col)
        # [수정] 오류가 발생했던 px 사용 부분 정상화
        mean_ret = df['유지(방어)율'].mean()
        mean_tgt = df['대상'].mean()
        fig.add_hline(y=mean_ret, line_dash="dot", line_color="green")
        fig.add_vline(x=mean_tgt, line_dash="dot", line_color="blue")
        st.plotly_chart(fig, use_container_width=True)

elif menu == "설정":
    st.title("⚙️ 시스템 설정")
    st.info("파일 업로드 및 관리자 설정")
    with st.expander("파일 업로드 (csv)", expanded=True):
        st.file_uploader("데이터 파일 업로드", type=['csv'])

import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_option_menu import option_menu
import os

# === 1. 페이지 및 스타일 설정 ===
st.set_page_config(
    page_title="KTT 관리고객 시스템",
    page_icon="🏢",
    layout="wide"
)

st.markdown("""
    <style>
        :root { --primary: #4f46e5; --bg: #f8fafc; }
        .stApp { background-color: var(--bg); }
        .block-container { padding-top: 2rem; padding-bottom: 3rem; }
        
        /* 사이드바 스타일 */
        [data-testid="stSidebar"] {
            background-color: #ffffff;
            border-right: 1px solid #e5e7eb;
        }
        
        /* 카드 UI */
        .dashboard-card {
            background-color: white; padding: 20px; border-radius: 12px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05); border: 1px solid #e5e7eb; margin-bottom: 20px;
        }
        
        /* 필터 확장 메뉴 스타일 */
        .streamlit-expanderHeader {
            font-weight: 600; color: #374151; background-color: #f9fafb; border-radius: 8px;
        }
        
        /* 금액 버튼(Pills) 스타일 */
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
    </style>
""", unsafe_allow_html=True)

# === 2. 데이터 로드 및 전처리 ===
@st.cache_data
def load_data():
    db_file = 'db.csv'
    if not os.path.exists(db_file):
        return None
    
    try:
        df = pd.read_csv(db_file)
        
        # 1. 숫자 데이터 변환 (위도, 경도, 금액)
        for col in ['위도', '경도']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        if '합산월정료(KTT+KT)' in df.columns:
            # 콤마, 공백 제거 후 숫자로 변환
            df['월정료_숫자'] = df['합산월정료(KTT+KT)'].astype(str).str.replace(',', '').str.strip()
            df['월정료_숫자'] = pd.to_numeric(df['월정료_숫자'], errors='coerce').fillna(0)
            
        # 2. 주소 데이터 결합 (군구 + 읍면동)
        if '군구' in df.columns and '읍면동' in df.columns:
            df['주소(지역)'] = df['군구'].fillna('') + ' ' + df['읍면동'].fillna('')
            df['주소(지역)'] = df['주소(지역)'].str.strip()
        else:
            df['주소(지역)'] = df['설치주소'] # 컬럼 없으면 기본 주소 사용
            
        # 3. 지도 링크 확인
        if '지도링크_URL' not in df.columns:
            df['지도링크_URL'] = '' # 없으면 빈 값 처리

        return df
    except Exception as e:
        st.error(f"데이터 로드 중 오류 발생: {e}")
        return None

df = load_data()


# === 3. 사이드바 (검색 및 필터) ===
with st.sidebar:
    st.markdown("### 🏢 KTT Management")
    
    # 1. 고객명 검색 (최상단)
    st.markdown("**🔍 고객 검색**")
    search_name = st.text_input("관리고객명 검색", placeholder="고객명 입력...")

    st.markdown("---")
    st.markdown("**🎛️ 상세 필터**")

    # 데이터가 있을 때만 필터 표시
    if df is not None:
        
        # 2. 금액대 필터 (버튼식)
        st.caption("💰 월정료 구간 선택")
        price_options = ["전체", "10만 미만", "20만 미만", "30만 미만", "30만 이상", "50만 이상"]
        selected_price = st.pills("월정료 필터", price_options, default="전체", label_visibility="collapsed")
        
        st.markdown("---")

        # 3. 접기/펼치기 필터 그룹
        
        # (1) 담당부서2 (지사)
        with st.expander("📂 담당부서(지사) 선택", expanded=True):
            if '담당부서2' in df.columns:
                opts_branch = sorted(df['담당부서2'].astype(str).unique())
                sel_branch = st.multiselect("지사 선택", opts_branch, default=[], placeholder="지사 선택...")
            else: sel_branch = []

        # (2) 영업구역정보
        with st.expander("📍 영업구역 정보", expanded=False):
            if '영업구역정보' in df.columns:
                opts_sales = sorted(df['영업구역정보'].astype(str).unique())
                sel_sales = st.multiselect("영업구역 선택", opts_sales, default=[])
            else: sel_sales = []

        # (3) 기술구역정보
        with st.expander("🛠️ 기술구역 정보", expanded=False):
            if '기술구역정보' in df.columns:
                opts_tech = sorted(df['기술구역정보'].astype(str).unique())
                sel_tech = st.multiselect("기술구역 선택", opts_tech, default=[])
            else: sel_tech = []

        # (4) 구역정보
        with st.expander("🗺️ 구역 정보", expanded=False):
            if '구역정보' in df.columns:
                opts_zone = sorted(df['구역정보'].astype(str).unique())
                sel_zone = st.multiselect("구역 선택", opts_zone, default=[])
            else: sel_zone = []


# === 4. 데이터 필터링 로직 ===
if df is not None:
    filtered_df = df.copy()

    # 1. 고객명 검색
    if search_name:
        filtered_df = filtered_df[filtered_df['관리고객명'].astype(str).str.contains(search_name, case=False)]

    # 2. 금액 필터
    if selected_price != "전체":
        if selected_price == "10만 미만":
            filtered_df = filtered_df[filtered_df['월정료_숫자'] < 100000]
        elif selected_price == "20만 미만":
            filtered_df = filtered_df[filtered_df['월정료_숫자'] < 200000]
        elif selected_price == "30만 미만":
            filtered_df = filtered_df[filtered_df['월정료_숫자'] < 300000]
        elif selected_price == "30만 이상":
            filtered_df = filtered_df[filtered_df['월정료_숫자'] >= 300000]
        elif selected_price == "50만 이상":
            filtered_df = filtered_df[filtered_df['월정료_숫자'] >= 500000]

    # 3. 사이드바 상세 필터
    if sel_branch: filtered_df = filtered_df[filtered_df['담당부서2'].isin(sel_branch)]
    if sel_sales: filtered_df = filtered_df[filtered_df['영업구역정보'].isin(sel_sales)]
    if sel_tech: filtered_df = filtered_df[filtered_df['기술구역정보'].isin(sel_tech)]
    if sel_zone: filtered_df = filtered_df[filtered_df['구역정보'].isin(sel_zone)]


# === 5. 메인 콘텐츠 ===
if df is None:
    st.error("'db.csv' 파일을 찾을 수 없습니다.")
    st.stop()

# 헤더
st.title("📂 2026 관리고객 현황")
st.caption(f"조회된 고객: {len(filtered_df):,}건")

# 탭 구성
tab_list, tab_map = st.tabs(["📋 상세 리스트", "🗺️ 지도 보기"])

# TAB 1: 데이터 리스트
with tab_list:
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    
    # 표시할 컬럼 정의 (설치주소 제외, 주소(지역) 및 길찾기 추가)
    cols_to_show = [
        '관리고객명', '상호', '계약번호', '담당부서2', 
        '주소(지역)', '합산월정료(KTT+KT)', '지도링크_URL'
    ]
    # 실제 존재하는 컬럼만 선택
    display_cols = [c for c in cols_to_show if c in filtered_df.columns]
    
    st.dataframe(
        filtered_df[display_cols],
        use_container_width=True,
        height=600,
        column_config={
            "관리고객명": st.column_config.TextColumn("고객명", width="medium"),
            "담당부서2": st.column_config.TextColumn("지사", width="small"),
            "주소(지역)": st.column_config.TextColumn("지역 (군/구+읍/면/동)", width="medium"),
            "합산월정료(KTT+KT)": st.column_config.TextColumn("월정료", width="small"),
            "지도링크_URL": st.column_config.LinkColumn(
                "길찾기", 
                help="클릭 시 지도로 이동", 
                display_text="지도보기 🔗"
            )
        },
        hide_index=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

# TAB 2: 지도 시각화
with tab_map:
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    
    # 좌표 있는 데이터만 추출
    map_df = filtered_df[(filtered_df['위도'] > 0) & (filtered_df['경도'] > 0)]
    
    if not map_df.empty:
        # 지도 초기화 (CartoDB Positron: 깔끔하고 현실적인 스타일)
        center_lat = map_df['위도'].mean()
        center_lng = map_df['경도'].mean()
        m = folium.Map(location=[center_lat, center_lng], zoom_start=11, tiles='cartodbpositron')
        
        # 마커 클러스터링
        from folium.plugins import MarkerCluster
        marker_cluster = MarkerCluster().add_to(m)
        
        for idx, row in map_df.iterrows():
            # 팝업 HTML 디자인
            popup_html = f"""
            <div style="width:200px; font-family:sans-serif;">
                <h4 style="margin:0 0 5px 0; color:#4f46e5;">{row['관리고객명']}</h4>
                <div style="font-size:12px; color:#555;">
                    <b>상호:</b> {row['상호']}<br>
                    <b>지사:</b> {row['담당부서2']}<br>
                    <b>주소:</b> {row['주소(지역)']}<br>
                    <b>월정료:</b> {row['합산월정료(KTT+KT)']}
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
                tooltip=f"{row['관리고객명']} ({row['담당부서2']})",
                popup=folium.Popup(popup_html, max_width=250),
                icon=folium.Icon(color='blue', icon='info-sign')
            ).add_to(marker_cluster)
            
        st_folium(m, width="100%", height=600)
    else:
        st.warning("📍 지도에 표시할 위치 데이터(위도/경도)가 없습니다.")
    
    st.markdown('</div>', unsafe_allow_html=True)

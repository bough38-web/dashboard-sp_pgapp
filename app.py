import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from streamlit_option_menu import option_menu # 새롭게 추가된 라이브러리

# === 1. 페이지 및 스타일 설정 ===
st.set_page_config(
    page_title="2025 해지 방어 성과 대시보드",
    page_icon="🛡️",
    layout="wide"
)

# 커스텀 CSS 적용 (스크린샷과 같은 디자인을 위해)
st.markdown("""
    <style>
        /* 전체 배경색 및 폰트 */
        .stApp {
            background-color: #f8f9fa;
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        }
        /* 메인 컨테이너 패딩 */
        .block-container {padding-top: 2rem; padding-bottom: 2rem;}
        
        /* KPI 카드 스타일 */
        .kpi-card {
            background-color: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.05);
            text-align: left;
            height: 100%;
        }
        .kpi-title {
            font-size: 14px;
            color: #6c757d;
            margin-bottom: 10px;
            font-weight: 600;
        }
        .kpi-value {
            font-size: 28px;
            font-weight: bold;
            color: #212529;
            margin-bottom: 10px;
        }
        .kpi-delta {
            font-size: 13px;
            font-weight: 500;
        }
        .delta-up { color: #28a745; }
        .delta-down { color: #dc3545; }
        .kpi-icon {
            float: right;
            font-size: 24px;
            color: #adb5bd;
            margin-top: -40px;
        }

        /* 탭 스타일 */
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
            background-color: transparent;
        }
        .stTabs [data-baseweb="tab"] {
            height: 45px;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            padding: 0 20px;
            font-weight: 600;
            color: #495057;
        }
        .stTabs [aria-selected="true"] {
            background-color: #0d6efd !important;
            color: white !important;
        }
        
        /* 데이터 테이블 스타일 */
        [data-testid="stDataFrame"] {
            background-color: white;
            padding: 15px;
            border-radius: 12px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        }
    </style>
""", unsafe_allow_html=True)

# === 2. 데이터 로드 함수 (기존과 동일) ===
@st.cache_data
def load_data():
    file_names = ['papp.csv', 'papp.xlsx', '시각화.csv']
    df = None
    for file in file_names:
        if os.path.exists(file):
            try:
                if file.endswith('.csv'):
                    df = pd.read_csv(file)
                else:
                    df = pd.read_excel(file)
                break
            except:
                continue
    if df is None: return None

    if '구분' in df.columns: df = df[df['구분'] != '소계']

    cols = ['해지율', '유지(방어)율']
    for col in cols:
        if col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.replace('%', '').astype(float)
            elif df[col].max() <= 1.0:
                df[col] = df[col] * 100
            df[col] = df[col].round(1)
            
    if '유지(방어)율' not in df.columns and '해지율' in df.columns:
        df['유지(방어)율'] = 100 - df['해지율']
    return df

raw_df = load_data()

# === 3. 사이드바 (아이콘 메뉴 스타일 적용) ===
with st.sidebar:
    # 깔끔한 메뉴바 적용
    selected_menu = option_menu(
        "성과 분석 시스템", 
        ["대시보드 홈", "지사별 상세 분석", "설정"], 
        icons=['house-door-fill', 'bar-chart-fill', 'gear-fill'], 
        menu_icon="shield-shaded", default_index=0,
        styles={
            "container": {"padding": "5px", "background-color": "#f8f9fa"},
            "icon": {"color": "#495057", "font-size": "16px"}, 
            "nav-link": {"font-size": "15px", "text-align": "left", "margin":"5px", "--hover-color": "#e9ecef"},
            "nav-link-selected": {"background-color": "#0d6efd"},
        }
    )
    
    st.divider()
    
    # 필터 기능은 '대시보드 홈'이나 '상세 분석'에서만 보이도록 설정
    if selected_menu in ["대시보드 홈", "지사별 상세 분석"]:
        st.subheader("🎛️ 데이터 필터")
        if raw_df is not None:
            region_col = '구분' if '구분' in raw_df.columns else raw_df.columns[0]
            all_regions = sorted(raw_df[region_col].unique())
            selected_regions = st.multiselect("🏢 지사 선택", all_regions, default=all_regions)
            
            code_col = '구역' if '구역' in raw_df.columns else ('구분' if region_col != '구분' else raw_df.columns[1])
            if code_col:
                filtered_codes_source = raw_df[raw_df[region_col].isin(selected_regions)]
                all_codes = sorted(filtered_codes_source[code_col].unique())
                selected_codes = st.multiselect("📍 구역 선택", all_codes, default=all_codes)
            else:
                selected_codes = []
        st.divider()

# === 4. 메인 콘텐츠 ===
if raw_df is None:
    st.error("데이터 파일을 찾을 수 없습니다. (papp.csv 또는 papp.xlsx)")
    st.stop()

# 데이터 필터링
df = raw_df[(raw_df[region_col].isin(selected_regions)) & (raw_df[code_col].isin(selected_codes))]

# 메뉴별 화면 구성
if selected_menu == "대시보드 홈":
    st.title("2025년 해지 방어 성과 현황")
    st.markdown(f"**총 {len(df)}개 구역**에 대한 실시간 모니터링 결과입니다.")
    st.markdown("###") # 여백

    # --- 디자인된 KPI 카드 영역 ---
    col1, col2, col3, col4 = st.columns(4)
    
    total_target = df['대상'].sum()
    total_churn = df['해지'].sum()
    avg_churn_rate = (total_churn / total_target * 100) if total_target > 0 else 0
    avg_retention = 100 - avg_churn_rate
    
    # KPI 카드 HTML 생성 함수
    def create_kpi_card(title, value, icon, delta_text, delta_color):
        return f"""
        <div class="kpi-card">
            <div class="kpi-title">{title}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-icon"><i class="bi bi-{icon}"></i></div>
            <div class="kpi-delta {delta_color}">
                {'▲' if delta_color=='delta-up' else '▼'} {delta_text}
            </div>
        </div>
        """
    
    # (참고: 전월 대비 데이터는 예시입니다)
    with col1:
        st.markdown(create_kpi_card("총 관리 대상", f"{total_target:,.0f}건", "people-fill", "전월 대비 +2.5%", "delta-up"), unsafe_allow_html=True)
    with col2:
        st.markdown(create_kpi_card("총 해지 건수", f"{total_churn:,.0f}건", "person-x-fill", "전월 대비 -1.2%", "delta-up"), unsafe_allow_html=True) # 해지는 줄어야 좋음(up)
    with col3:
        st.markdown(create_kpi_card("평균 해지율", f"{avg_churn_rate:.1f}%", "graph-down-arrow", "전월 대비 -0.3%p", "delta-up"), unsafe_allow_html=True)
    with col4:
        st.markdown(create_kpi_card("평균 방어율", f"{avg_retention:.1f}%", "shield-check-fill", "목표(90%) 달성", "delta-up"), unsafe_allow_html=True)

    st.markdown("###") # 여백

    # --- 차트 영역 (흰색 박스 스타일 적용) ---
    c1, c2 = st.columns([3, 2])
    with c1:
        st.markdown('<div style="background:white; padding:20px; border-radius:12px; box-shadow:0 2px 6px rgba(0,0,0,0.05);">', unsafe_allow_html=True)
        st.subheader("🎯 규모 대비 방어 성과 (4분면)")
        
        mean_target = raw_df['대상'].mean()
        mean_ret = raw_df['유지(방어)율'].mean()

        fig_scatter = px.scatter(
            df, x='대상', y='유지(방어)율', size='대상', color='해지',
            hover_name=code_col, text=region_col, color_continuous_scale='Reds',
            height=450
        )
        fig_scatter.add_hline(y=mean_ret, line_dash="dash", line_color="#28a745")
        fig_scatter.add_vline(x=mean_target, line_dash="dash", line_color="#0d6efd")
        fig_scatter.add_shape(type="rect", x0=mean_target, y0=mean_ret, x1=df['대상'].max()*1.2, y1=105, 
                      fillcolor="#28a745", opacity=0.1, line_width=0)
        fig_scatter.update_traces(textposition='top center')
        fig_scatter.update_layout(
            xaxis_title="관리 대상 (건)", yaxis_title="방어율 (%)",
            plot_bgcolor='white', paper_bgcolor='white',
            margin=dict(t=20, b=20, l=20, r=20)
        )
        st.plotly_chart(fig_scatter, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div style="background:white; padding:20px; border-radius:12px; box-shadow:0 2px 6px rgba(0,0,0,0.05); height:100%;">', unsafe_allow_html=True)
        st.subheader("🏆 지사별 평균 방어율 Top 10")
        group_df = df.groupby(region_col)[['대상', '해지']].sum().reset_index()
        group_df['방어율'] = 100 - (group_df['해지'] / group_df['대상'] * 100)
        group_df = group_df.sort_values('방어율', ascending=False).head(10)

        fig_bar = px.bar(
            group_df, x='방어율', y=region_col, orientation='h',
            text='방어율', color='방어율', color_continuous_scale='Teal',
            height=450
        )
        fig_bar.update_traces(texttemplate='%{text:.1f}%', textposition='inside')
        fig_bar.update_layout(
            xaxis_title="방어율 (%)", yaxis_title=None, xaxis_range=[80, 100],
            plot_bgcolor='white', paper_bgcolor='white',
            margin=dict(t=20, b=20, l=20, r=20),
            yaxis={'categoryorder':'total ascending'}
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

elif selected_menu == "지사별 상세 분석":
    st.title("📋 지사/구역별 상세 성과 리스트")
    st.markdown("각 구역별 세부 실적을 확인하고 비교 분석합니다.")
    st.markdown("###")

    display_cols = [region_col, code_col, '대상', '해지', '해지율', '유지(방어)율']
    final_cols = [c for c in display_cols if c in df.columns]
    
    st.dataframe(
        df[final_cols].sort_values(by='해지', ascending=False),
        use_container_width=True,
        column_config={
            region_col: "지사",
            code_col: "구역 코드",
            "대상": st.column_config.NumberColumn("관리 대상", format="%d건"),
            "해지": st.column_config.NumberColumn("해지 건수", format="%d건"),
            "해지율": st.column_config.ProgressColumn("해지율", format="%.1f%%", min_value=0, max_value=20),
            "유지(방어)율": st.column_config.ProgressColumn("방어율", format="%.1f%%", min_value=80, max_value=100),
        },
        hide_index=True,
        height=600
    )

elif selected_menu == "설정":
    st.title("⚙️ 설정")
    st.info("데이터 소스 연결 및 대시보드 환경 설정 메뉴입니다. (현재 준비 중)")

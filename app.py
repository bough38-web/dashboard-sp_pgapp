import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
from streamlit_option_menu import option_menu

# === 1. 페이지 및 스타일 설정 (참고 이미지 스타일 적용) ===
st.set_page_config(
    page_title="KTT 지사별 성과 대시보드",
    page_icon="📊",
    layout="wide"
)

# KTT Dashboard 스타일 (회색 배경 + 흰색 카드 + 둥근 모서리)
st.markdown("""
    <style>
        /* 전체 배경색 (연한 회색) */
        .stApp { background-color: #f8f9fa; }
        
        /* 메인 컨테이너 패딩 조정 */
        .block-container { padding-top: 2rem; padding-bottom: 3rem; }
        
        /* 카드(White Box) 스타일 정의 */
        .dashboard-card {
            background-color: white;
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            margin-bottom: 20px;
        }
        
        /* KPI 텍스트 스타일 */
        .kpi-title { font-size: 14px; color: #888; font-weight: 600; margin-bottom: 5px; }
        .kpi-value { font-size: 26px; font-weight: 800; color: #333; }
        .kpi-sub { font-size: 12px; color: #28a745; font-weight: 500; }
        
        /* 사이드바 스타일 커스텀 */
        section[data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #eee; }
        
        /* 버튼형 필터(Pills) 스타일 미세 조정 */
        div[data-testid="stPills"] { gap: 8px; }
    </style>
""", unsafe_allow_html=True)

# === 2. 데이터 로드 및 전처리 ===
@st.cache_data
def load_data():
    file_names = ['papp.csv', 'papp.xlsx', '시각화.csv']
    df = None
    for file in file_names:
        if os.path.exists(file):
            try:
                if file.endswith('.csv'): df = pd.read_csv(file)
                else: df = pd.read_excel(file)
                break
            except: continue
            
    if df is None: return None

    # 전처리
    if '구분' in df.columns: df = df[df['구분'] != '소계']

    # 숫자 변환
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

if raw_df is None:
    st.error("데이터 파일을 찾을 수 없습니다.")
    st.stop()

# === [핵심] 사용자 지정 정렬 순서 적용 ===
custom_order = ['중앙', '강북', '서대문', '고양', '의정부', '남양주', '강릉', '원주']
# 데이터프레임의 '구분' 컬럼을 이 순서로 강제 정렬 (Sorting)
region_col = '구분' if '구분' in raw_df.columns else raw_df.columns[0]
raw_df[region_col] = pd.Categorical(raw_df[region_col], categories=custom_order, ordered=True)
raw_df = raw_df.sort_values(region_col)


# === 3. 사이드바 (KTT 대시보드 스타일) ===
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2920/2920323.png", width=50)
    st.markdown("### **KTT Dashboard**")
    st.markdown("---")
    
    # 1. 메뉴 네비게이션
    st.caption("SYSTEM")
    menu = option_menu(
        None, ["통합 대시보드", "상세 리스트", "설정"],
        icons=['grid-1x2-fill', 'list-task', 'gear'],
        menu_icon="cast", default_index=0,
        styles={"container": {"padding": "0!important", "background-color": "transparent"},
                "nav-link": {"font-size": "14px", "margin":"0px"}}
    )
    
    st.markdown("---")
    
    # 2. 버튼형 필터 (보내주신 이미지 스타일)
    st.caption("지사 필터 (BRANCH)")
    
    # 지사 목록 가져오기 (정렬된 순서대로)
    all_regions = sorted(raw_df[region_col].unique().dropna()) # 이미 위에서 정렬됨
    
    # [핵심 기능] st.pills 사용 (버튼형 다중 선택)
    # Streamlit 1.40.0 이상 필요
    selected_regions = st.pills(
        "지사를 선택하세요",
        options=all_regions,
        selection_mode="multi",
        default=all_regions, # 기본값: 전체 선택
        help="클릭하여 지사를 켜고 끌 수 있습니다."
    )
    
    # 만약 다 끄면 데이터가 안 보이므로 방지
    if not selected_regions:
        st.warning("최소 1개 이상의 지사를 선택해주세요.")
        selected_regions = all_regions # 강제 전체 선택

    # 3. 구역 필터
    code_col = '구역' if '구역' in raw_df.columns else raw_df.columns[1]
    if code_col:
        st.caption("구역 필터 (ZONE)")
        filtered_codes_source = raw_df[raw_df[region_col].isin(selected_regions)]
        available_codes = sorted(filtered_codes_source[code_col].unique())
        # 구역은 너무 많을 수 있으므로 multiselect 유지하되 스타일 맞춤
        selected_codes = st.multiselect("구역 코드", available_codes, default=available_codes, label_visibility="collapsed")
    
    st.markdown("---")
    st.caption(f"Ver 2.1 | 사용자: 관리자")


# === 4. 데이터 필터링 적용 ===
df = raw_df[
    (raw_df[region_col].isin(selected_regions)) & 
    (raw_df[code_col].isin(selected_codes))
]

# === 5. 메인 대시보드 영역 (White Card Layout) ===

if menu == "통합 대시보드":
    # 상단 헤더
    c1, c2 = st.columns([3, 1])
    with c1: st.title("관리고객(VOC) 해지 방어 현황")
    with c2: st.markdown(f"<div style='text-align:right; color:#888; padding-top:20px;'> 기준일: 2025.12.22 </div>", unsafe_allow_html=True)
    
    st.markdown("###")

    # (1) KPI 카드 영역
    col1, col2, col3, col4 = st.columns(4)
    
    total_target = df['대상'].sum()
    total_churn = df['해지'].sum()
    avg_retention = df['유지(방어)율'].mean()
    
    # KPI 카드 HTML 함수
    def kpi_card(title, value, sub_text, color="#28a745"):
        return f"""
        <div class="dashboard-card" style="text-align:center;">
            <div class="kpi-title">{title}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-sub" style="color:{color};">{sub_text}</div>
        </div>
        """
        
    with col1: st.markdown(kpi_card("총 관리 대상", f"{total_target:,.0f}", "전월 대비 ▲ 12건"), unsafe_allow_html=True)
    with col2: st.markdown(kpi_card("처리 완료(방어)", f"{total_target - total_churn:,.0f}", "진행률 100%"), unsafe_allow_html=True)
    with col3: st.markdown(kpi_card("해지 접수", f"{total_churn:,.0f}", "방어 실패", color="#dc3545"), unsafe_allow_html=True) # 빨간색
    with col4: st.markdown(kpi_card("평균 방어율", f"{avg_retention:.1f}%", "목표 달성", color="#007bff"), unsafe_allow_html=True) # 파란색

    # (2) 차트 영역 (2열 배치)
    cl1, cl2 = st.columns([1, 1])
    
    with cl1:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.subheader("📊 지사별 처리 현황 (막대)")
        
        # 지사별 그룹화
        group_df = df.groupby(region_col)[['대상', '해지']].sum().reset_index()
        # 정렬 순서 보장을 위해 다시 Categorical 적용
        group_df[region_col] = pd.Categorical(group_df[region_col], categories=custom_order, ordered=True)
        group_df = group_df.sort_values(region_col)
        
        fig_bar = px.bar(
            group_df, x=region_col, y='대상', 
            text='대상',
            title=None,
            color=region_col, # 지사별 색상 다르게
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_bar.update_layout(paper_bgcolor='white', plot_bgcolor='white', height=350, showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with cl2:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.subheader("🎯 규모 대비 방어 성과 (4분면)")
        
        mean_target = raw_df['대상'].mean()
        mean_ret = raw_df['유지(방어)율'].mean()

        fig_scatter = px.scatter(
            df, x='대상', y='유지(방어)율', size='대상', color='해지',
            hover_name=code_col, text=region_col, 
            color_continuous_scale='Reds',
            height=350
        )
        # 기준선
        fig_scatter.add_hline(y=mean_ret, line_dash="dash", line_color="green", annotation_text="평균 방어율")
        fig_scatter.add_vline(x=mean_target, line_dash="dash", line_color="blue")
        
        fig_scatter.update_layout(paper_bgcolor='white', plot_bgcolor='white', margin=dict(t=20, b=20))
        fig_scatter.update_traces(textposition='top center')
        st.plotly_chart(fig_scatter, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # (3) 하단 테이블 영역
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.subheader("📋 상세 리스트 (클릭 시 정렬)")
    
    # 보기 좋은 컬럼 순서
    display_cols = [region_col, code_col, '대상', '해지', '해지율', '유지(방어)율']
    final_cols = [c for c in display_cols if c in df.columns]
    
    st.dataframe(
        df[final_cols].sort_values(by=region_col), # 기본 정렬: 지사순
        use_container_width=True,
        column_config={
            region_col: "지사",
            "해지율": st.column_config.ProgressColumn("해지율", format="%.1f%%", min_value=0, max_value=20),
            "유지(방어)율": st.column_config.ProgressColumn("방어율", format="%.1f%%", min_value=80, max_value=100),
        },
        hide_index=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

elif menu == "상세 리스트":
    st.title("구역별 상세 데이터")
    st.dataframe(df, use_container_width=True)

elif menu == "설정":
    st.title("환경 설정")
    st.info("데이터 소스 연결 및 관리자 설정 메뉴입니다.")

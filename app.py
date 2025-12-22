import streamlit as st
import pandas as pd
import plotly.express as px
import os
from streamlit_option_menu import option_menu

# === 1. 페이지 및 스타일 설정 ===
st.set_page_config(
    page_title="KTT 영업구역 성과 분석",
    page_icon="📊",
    layout="wide"
)

# KTT Dashboard 스타일 (회색 배경 + 흰색 카드 + 둥근 모서리 + 버튼 스타일)
st.markdown("""
    <style>
        .stApp { background-color: #f8f9fa; }
        .block-container { padding-top: 2rem; padding-bottom: 3rem; }
        
        /* 카드(White Box) 스타일 */
        .dashboard-card {
            background-color: white;
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            margin-bottom: 20px;
        }
        
        /* 텍스트 스타일 */
        .kpi-title { font-size: 14px; color: #888; font-weight: 600; margin-bottom: 5px; }
        .kpi-value { font-size: 26px; font-weight: 800; color: #333; }
        .kpi-sub { font-size: 12px; color: #28a745; font-weight: 500; }
        
        /* 사이드바 스타일 */
        section[data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #eee; }
        
        /* 버튼(Pills) 간격 조정 */
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

if raw_df is None:
    st.error("데이터 파일을 찾을 수 없습니다.")
    st.stop()

# === [정렬] 사용자 지정 순서 (중앙 ~ 원주) ===
custom_order = ['중앙', '강북', '서대문', '고양', '의정부', '남양주', '강릉', '원주']
region_col = '구분' if '구분' in raw_df.columns else raw_df.columns[0]
code_col = '구역' if '구역' in raw_df.columns else raw_df.columns[1]

raw_df[region_col] = pd.Categorical(raw_df[region_col], categories=custom_order, ordered=True)
raw_df = raw_df.sort_values(region_col)


# === 3. 사이드바 (필터링) ===
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2920/2920323.png", width=50)
    st.markdown("### **KTT Dashboard**")
    st.markdown("---")
    
    menu = option_menu(
        None, ["통합 대시보드", "상세 리스트", "설정"],
        icons=['grid-1x2-fill', 'list-task', 'gear'],
        menu_icon="cast", default_index=0,
        styles={"container": {"padding": "0!important", "background-color": "transparent"},
                "nav-link": {"font-size": "14px", "margin":"0px"}}
    )
    
    st.markdown("---")
    
    # 지사 필터
    st.caption("지사 필터 (BRANCH)")
    all_regions = sorted(raw_df[region_col].unique().dropna())
    
    selected_regions = st.pills(
        "지사를 선택하세요",
        options=all_regions,
        selection_mode="multi",
        default=all_regions,
        key="region_filter"
    )
    
    if not selected_regions:
        st.warning("최소 1개 이상의 지사를 선택해주세요.")
        selected_regions = all_regions

    # 구역 필터
    if code_col:
        st.caption("구역 필터 (ZONE)")
        filtered_codes_source = raw_df[raw_df[region_col].isin(selected_regions)]
        available_codes = sorted(filtered_codes_source[code_col].unique())
        selected_codes = st.multiselect("구역 코드", available_codes, default=available_codes, label_visibility="collapsed")
    
    st.markdown("---")


# === 4. 데이터 필터링 ===
df = raw_df[
    (raw_df[region_col].isin(selected_regions)) & 
    (raw_df[code_col].isin(selected_codes))
]

# === 5. 메인 대시보드 ===

if menu == "통합 대시보드":
    # 헤더
    c1, c2 = st.columns([3, 1])
    with c1: st.title("지사 및 구역별 성과 분석")
    with c2: st.markdown(f"<div style='text-align:right; color:#888; padding-top:20px;'> 총 구역 수: {len(df)}개 </div>", unsafe_allow_html=True)
    
    st.markdown("###")

    # (1) KPI 카드
    col1, col2, col3, col4 = st.columns(4)
    total_target = df['대상'].sum()
    total_churn = df['해지'].sum()
    avg_retention = df['유지(방어)율'].mean()
    
    def kpi_card(title, value, sub_text, color="#28a745"):
        return f"""
        <div class="dashboard-card" style="text-align:center;">
            <div class="kpi-title">{title}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-sub" style="color:{color};">{sub_text}</div>
        </div>
        """
    with col1: st.markdown(kpi_card("총 관리 대상", f"{total_target:,.0f}", "전체 합계"), unsafe_allow_html=True)
    with col2: st.markdown(kpi_card("방어 성공", f"{total_target - total_churn:,.0f}", "계약 유지"), unsafe_allow_html=True)
    with col3: st.markdown(kpi_card("해지 건수", f"{total_churn:,.0f}", "방어 실패", color="#dc3545"), unsafe_allow_html=True)
    with col4: st.markdown(kpi_card("평균 방어율", f"{avg_retention:.1f}%", "구역 평균", color="#007bff"), unsafe_allow_html=True)

    # (2) 차트 영역
    cl1, cl2 = st.columns([1, 1])
    
    # [차트 1: 지사별 비교] 동적 버튼 기능 추가
    with cl1:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.subheader("📊 지사별 성과 비교")
        
        # 1. 지표 선택 버튼 (Pills)
        metric_map = {
            "관리 대상": "대상",
            "해지 건수": "해지",
            "해지율(%)": "해지율",
            "방어율(%)": "유지(방어)율"
        }
        selected_metric_label = st.pills(
            "비교할 지표를 선택하세요",
            options=list(metric_map.keys()),
            default="방어율(%)",
            selection_mode="single",
            key="chart_metric_select"
        )
        selected_metric = metric_map[selected_metric_label]

        # 2. 데이터 집계
        if selected_metric in ['해지율', '유지(방어)율']:
            # 비율 지표는 '평균'으로 집계
            group_df = df.groupby(region_col)[selected_metric].mean().reset_index()
            text_format = '.1f'
        else:
            # 절대값 지표는 '합계'로 집계
            group_df = df.groupby(region_col)[selected_metric].sum().reset_index()
            text_format = ',.0f'
            
        # 정렬 적용
        group_df[region_col] = pd.Categorical(group_df[region_col], categories=custom_order, ordered=True)
        group_df = group_df.sort_values(region_col)
        
        # 3. 차트 그리기
        fig_bar = px.bar(
            group_df, x=region_col, y=selected_metric, 
            text=selected_metric,
            color=region_col, 
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_bar.update_traces(texttemplate='%{text:' + text_format + '}', textposition='outside')
        fig_bar.update_layout(
            paper_bgcolor='white', plot_bgcolor='white', 
            height=400, showlegend=False,
            margin=dict(t=30, b=10),
            yaxis_title=None, xaxis_title=None
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # [차트 2: 4분면 분석]
    with cl2:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.subheader("🎯 구역(Zone)별 성과 매트릭스")
        
        mean_target = raw_df['대상'].mean()
        mean_ret = raw_df['유지(방어)율'].mean()

        fig_scatter = px.scatter(
            df, x='대상', y='유지(방어)율', size='대상', color='해지',
            hover_name=code_col, hover_data={region_col: True, code_col: True},
            text=code_col, color_continuous_scale='Reds', height=460
        )
        fig_scatter.add_hline(y=mean_ret, line_dash="dash", line_color="green", annotation_text="평균 방어율")
        fig_scatter.add_vline(x=mean_target, line_dash="dash", line_color="blue", annotation_text="평균 규모")
        fig_scatter.add_shape(type="rect", x0=mean_target, y0=mean_ret, x1=df['대상'].max()*1.2, y1=105, 
                              fillcolor="green", opacity=0.05, line_width=0)

        fig_scatter.update_layout(
            paper_bgcolor='white', plot_bgcolor='white', margin=dict(t=30, b=20),
            xaxis_title="관리 대상 (규모)", yaxis_title="방어율 (%)"
        )
        fig_scatter.update_traces(textposition='top center')
        st.plotly_chart(fig_scatter, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # (3) 하단 테이블
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.subheader("📋 구역별 상세 성과 리스트")
    
    display_cols = [region_col, code_col, '대상', '해지', '해지율', '유지(방어)율']
    final_cols = [c for c in display_cols if c in df.columns]
    
    st.dataframe(
        df[final_cols].sort_values(by=[region_col, '해지'], ascending=[True, False]),
        use_container_width=True,
        column_config={
            region_col: "지사",
            code_col: "구역 코드",
            "해지율": st.column_config.ProgressColumn("해지율", format="%.1f%%", min_value=0, max_value=20),
            "유지(방어)율": st.column_config.ProgressColumn("방어율", format="%.1f%%", min_value=80, max_value=100),
        },
        hide_index=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

elif menu == "상세 리스트":
    st.title("전체 데이터 원본")
    st.dataframe(df, use_container_width=True)

elif menu == "설정":
    st.title("환경 설정")
    st.info("관리자 전용 메뉴입니다.")

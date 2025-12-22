import streamlit as st
import pandas as pd
import plotly.express as px
import os
from streamlit_option_menu import option_menu

# === 1. [System] 페이지 설정 및 세션 초기화 ===
st.set_page_config(
    page_title="KTT Premium Dashboard v42.0",
    page_icon="💎",
    layout="wide"
)

# 세션 상태 초기화 (필터 버튼 동작용)
if 'region_selection' not in st.session_state:
    st.session_state.region_selection = []  # 초기값: 빈 리스트 (전체 조회)

# [CSS] 스타일 설정
st.markdown("""
    <style>
        :root {
            --primary: #4f46e5; --success: #10b981; --warning: #f59e0b; --danger: #ef4444;
            --bg: #f8fafc; --surface: #ffffff; --text: #1e293b; --text-sub: #64748b;
        }
        .stApp { background-color: var(--bg); }
        .block-container { padding-top: 2rem; padding-bottom: 3rem; }
        
        /* 카드 UI */
        .dashboard-card {
            background-color: var(--surface);
            padding: 24px;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            border: 1px solid #e2e8f0;
            margin-bottom: 20px;
        }
        
        /* KPI UI */
        .kpi-card-box {
            background-color: var(--surface);
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            border-left: 5px solid #ccc;
            text-align: center;
        }
        .kpi-label { font-size: 13px; font-weight: 700; color: var(--text-sub); text-transform: uppercase; margin-bottom: 8px; }
        .kpi-val { font-size: 32px; font-weight: 800; color: var(--text); letter-spacing: -1px; }
        .kpi-sub { font-size: 14px; font-weight: 500; color: var(--text-sub); }
        
        /* [Pills] 버튼 스타일 */
        div[data-testid="stPills"] { gap: 6px; flex-wrap: wrap; }
        div[data-testid="stPills"] button {
            border-radius: 20px !important;
            border: 1px solid #e2e8f0 !important;
            padding: 4px 12px !important;
            font-size: 12px !important;
            font-weight: 600 !important;
            background-color: white;
            color: #64748b;
        }
        div[data-testid="stPills"] button[data-selected="true"] {
            background-color: var(--primary) !important;
            color: white !important;
            border-color: var(--primary) !important;
        }
        
        /* 컨트롤 버튼 (전체선택/초기화) */
        .control-btn { width: 100%; margin-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

# === 2. [Data] 데이터 로드 및 전처리 ===
@st.cache_data
def load_data():
    file_names = ['papp.csv', 'papp.xlsx', '시각화.csv']
    df = None
    
    for file in file_names:
        if os.path.exists(file):
            try:
                if file.endswith('.csv'): df = pd.read_csv(file, header=0)
                else: df = pd.read_excel(file, header=0)
                break
            except: continue
            
    if df is None: return None

    # 소계 제거
    if '구분' in df.columns: df = df[df['구분'] != '소계']

    # 숫자 데이터 정밀 변환
    target_cols = ['대상', '해지', '해지율', '유지(방어)율']
    for col in target_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(',', '').str.replace('%', '').str.strip()
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            # 비율 데이터(0.xx) 보정
            if col in ['해지율', '유지(방어)율']:
                if df[col].max() <= 1.0: df[col] = df[col] * 100
                df[col] = df[col].round(1)

    # 결측 컬럼 자동 계산
    if '유지(방어)율' not in df.columns and '해지율' in df.columns:
        df['유지(방어)율'] = 100 - df['해지율']
        
    return df

raw_df = load_data()

if raw_df is None:
    st.error("데이터 파일을 찾을 수 없습니다. (papp.csv)")
    st.stop()

# 정렬 순서 설정
custom_order = ['중앙', '강북', '서대문', '고양', '의정부', '남양주', '강릉', '원주']
region_col = '구분' if '구분' in raw_df.columns else raw_df.columns[0]
code_col = '구역' if '구역' in raw_df.columns else raw_df.columns[1]

# 데이터 정렬
raw_df[region_col] = pd.Categorical(raw_df[region_col], categories=custom_order, ordered=True)
raw_df = raw_df.sort_values(region_col)
all_regions = sorted(raw_df[region_col].unique().dropna())


# === 3. [Sidebar] 필터링 UI ===
with st.sidebar:
    st.markdown(f"""
        <div style="padding:10px 0; border-bottom:1px solid #e2e8f0; margin-bottom:20px;">
            <span style="font-size:18px; font-weight:800; color:#4f46e5;">
                💎 KTT Dashboard
            </span>
        </div>
    """, unsafe_allow_html=True)
    
    menu = option_menu(
        None, ["Dashboard", "System"],
        icons=['grid-fill', 'hdd-stack'],
        menu_icon="cast", default_index=0,
        styles={"container": {"padding": "0"}, "nav-link": {"font-size": "14px"}}
    )
    
    if menu == "Dashboard":
        st.markdown("<div style='font-size:11px; font-weight:800; color:#64748b; margin:20px 0 10px 0; text-transform:uppercase;'>Filters</div>", unsafe_allow_html=True)
        
        # [기능 1] 전체 선택 / 초기화 버튼
        col_b1, col_b2 = st.columns(2)
        if col_b1.button("✅ 전체 선택", use_container_width=True):
            st.session_state.region_selection = all_regions
        if col_b2.button("🔄 초기화", use_container_width=True):
            st.session_state.region_selection = []

        # [필터] 지사 선택 (세션 상태와 연동)
        selected_regions = st.pills(
            "지사 (Branch)", 
            options=all_regions, 
            selection_mode="multi", 
            default=st.session_state.region_selection,
            key="region_pills"
        )
        
        # 로직: 선택 없음 = 전체 조회
        if not selected_regions:
            regions_to_show = all_regions
            is_all_regions = True
        else:
            regions_to_show = selected_regions
            is_all_regions = False
            # 사용자가 직접 클릭했을 때 세션 업데이트
            st.session_state.region_selection = selected_regions

        # [필터] 구역 선택
        if code_col:
            filtered_codes_source = raw_df[raw_df[region_col].isin(regions_to_show)]
            available_codes = sorted(filtered_codes_source[code_col].unique())
            
            with st.expander("구역 (Zone) 상세 선택", expanded=True):
                selected_codes = st.pills(
                    "구역 코드", 
                    options=available_codes, 
                    selection_mode="multi",
                    default=None,
                    key="zone_pills", 
                    label_visibility="collapsed"
                )
            
            if not selected_codes:
                codes_to_show = available_codes
            else:
                codes_to_show = selected_codes


# === 4. [Main] 대시보드 뷰 ===
if menu == "Dashboard":
    # 데이터 필터링
    df = raw_df[
        (raw_df[region_col].isin(regions_to_show)) & 
        (raw_df[code_col].isin(codes_to_show))
    ]
    
    # [Header]
    c1, c2 = st.columns([3, 1])
    with c1:
        status_text = "전체 지사 데이터" if is_all_regions else f"{len(regions_to_show)}개 지사 선택됨"
        st.markdown(f"""
            <h2 style='margin:0; font-size:24px; font-weight:800; color:#1e293b;'>관리고객 현황</h2>
            <p style='margin:0; font-size:14px; color:#64748b;'>{status_text} | 총 {len(df)}개 구역</p>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("<div style='text-align:right; padding-top:10px;'><span style='background:#dcfce7; color:#166534; padding:5px 10px; border-radius:8px; font-size:12px; font-weight:700;'>Live Data</span></div>", unsafe_allow_html=True)
    
    st.markdown("###")

    # [Section 1] KPI Cards
    total_target = df['대상'].sum()
    total_churn = df['해지'].sum()
    avg_retention = df['유지(방어)율'].mean() if len(df) > 0 else 0
    
    def kpi_html(label, value, sub, color):
        return f"""
        <div class="kpi-card-box" style="border-left-color: {color};">
            <div class="kpi-label">{label}</div>
            <div class="kpi-val">{value}</div>
            <div class="kpi-sub">{sub}</div>
        </div>
        """
    
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.markdown(kpi_html("총 계약 (Total)", f"{total_target:,.0f}", "건", "#4f46e5"), unsafe_allow_html=True)
    with col2: st.markdown(kpi_html("처리 완료 (Done)", f"{total_target-total_churn:,.0f}", f"방어율 {avg_retention:.1f}%", "#10b981"), unsafe_allow_html=True)
    with col3: st.markdown(kpi_html("진행중 (Ing)", "0", "건 (Demo)", "#f59e0b"), unsafe_allow_html=True)
    with col4: st.markdown(kpi_html("해지 건수 (Churn)", f"{total_churn:,.0f}", "건", "#ef4444"), unsafe_allow_html=True)

    # [Section 2] Charts
    st.markdown("###")
    cl1, cl2 = st.columns([1, 1])
    
    # [차트 1] 지사별 비교 (기능 개선: 로그 스케일)
    with cl1:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        
        # 헤더와 옵션 배치
        h_col1, h_col2 = st.columns([2, 1])
        with h_col1:
            st.markdown("<h3 style='font-size:16px; font-weight:700; margin:0;'>📊 지사별 처리 현황</h3>", unsafe_allow_html=True)
        with h_col2:
            # [기능 2] 로그 스케일 토글 (값이 클 때 길이 줄이기)
            use_log = st.toggle("Log Scale", help="값의 차이가 너무 클 때 그래프 길이를 조정합니다.")
            
        metric_map = {"관리 대상": "대상", "해지 건수": "해지", "방어율(%)": "유지(방어)율"}
        sel_metric_label = st.pills("", list(metric_map.keys()), default="방어율(%)", selection_mode="single", key="chart_opt")
        sel_metric = metric_map[sel_metric_label]

        # 집계
        if sel_metric in ['해지율', '유지(방어)율']:
            group_df = df.groupby(region_col)[sel_metric].mean().reset_index()
            text_fmt = '.1f'; suffix = '%'
        else:
            group_df = df.groupby(region_col)[sel_metric].sum().reset_index()
            text_fmt = ',.0f'; suffix = '건'
            
        fig_bar = px.bar(
            group_df, x=region_col, y=sel_metric, text=sel_metric,
            color=region_col, color_discrete_sequence=px.colors.qualitative.Prism,
            log_y=use_log # 로그 스케일 적용 여부
        )
        fig_bar.update_traces(
            texttemplate='%{text:' + text_fmt + '}' + suffix, 
            textposition='outside', 
            marker_line_width=0,
            width=0.6 # 막대 너비 조정 (너무 굵지 않게)
        )
        fig_bar.update_layout(
            paper_bgcolor='white', plot_bgcolor='white', height=350, showlegend=False,
            margin=dict(t=30, b=10, l=10, r=10),
            xaxis=dict(showgrid=False), 
            yaxis=dict(showgrid=True, gridcolor='#f1f5f9', showticklabels=use_log) # 로그일 땐 축 표시
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # [차트 2] 4분면 분석
    with cl2:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.markdown("<h3 style='font-size:16px; font-weight:700; margin-bottom:15px; color:#ef4444;'>🎯 해지 위험 구역 매트릭스</h3>", unsafe_allow_html=True)
        
        mean_target = raw_df['대상'].mean()
        mean_ret = raw_df['유지(방어)율'].mean()

        fig_scatter = px.scatter(
            df, x='대상', y='유지(방어)율', size='대상', color='해지',
            hover_name=code_col, hover_data={region_col: True},
            text=code_col, color_continuous_scale='Reds', height=420
        )
        fig_scatter.add_hline(y=mean_ret, line_dash="dot", line_color="#10b981", annotation_text="평균 방어율")
        fig_scatter.add_vline(x=mean_target, line_dash="dot", line_color="#4f46e5", annotation_text="평균 규모")
        
        fig_scatter.update_layout(
            paper_bgcolor='white', plot_bgcolor='white',
            margin=dict(t=20, b=20, l=10, r=10),
            xaxis_title="관리 대상 (건)", yaxis_title="방어율 (%)"
        )
        fig_scatter.update_traces(textposition='top center')
        st.plotly_chart(fig_scatter, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # [Section 3] 상세 리스트
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.markdown("<h3 style='font-size:16px; font-weight:700; margin-bottom:15px;'>📋 상세 리스트</h3>", unsafe_allow_html=True)
    
    display_cols = [region_col, code_col, '대상', '해지', '해지율', '유지(방어)율']
    final_cols = [c for c in display_cols if c in df.columns]
    
    # [기능 3] Progress Bar 최대값 동적 설정 (그래프 꽉 참 방지)
    max_churn_rate = df['해지율'].max() if '해지율' in df.columns and not df.empty else 20
    
    st.dataframe(
        df[final_cols].sort_values(by=[region_col, '해지'], ascending=[True, False]),
        use_container_width=True,
        column_config={
            region_col: "지사",
            code_col: "구역 코드",
            "대상": st.column_config.NumberColumn("관리 대상", format="%d건"),
            "해지": st.column_config.NumberColumn("해지 건수", format="%d건"),
            "해지율": st.column_config.ProgressColumn(
                "해지율", 
                format="%.1f%%", 
                min_value=0, 
                max_value=max(20, int(max_churn_rate)) # 데이터에 맞춰 최대 길이 자동 조절
            ),
            "유지(방어)율": st.column_config.ProgressColumn("방어율", format="%.1f%%", min_value=0, max_value=100),
        },
        hide_index=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

elif menu == "System":
    st.title("📂 System Management")
    st.info("관리자 권한이 필요합니다.")
    with st.expander("파일 교체 (Upload)", expanded=True):
        st.file_uploader("CSV 파일을 업로드하세요", type=['csv'])

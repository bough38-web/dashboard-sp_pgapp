import streamlit as st
import pandas as pd
import plotly.express as px
import os
from streamlit_option_menu import option_menu

# === 1. [Expert UI] 페이지 설정 ===
st.set_page_config(
    page_title="KTT 프리미엄 성과 대시보드",
    page_icon="💎",
    layout="wide"
)

# 고급 CSS (디자인 유지)
st.markdown("""
    <style>
        .stApp { background-color: #f1f3f6; }
        .block-container { padding-top: 2rem; padding-bottom: 3rem; }
        .dashboard-card {
            background-color: white;
            padding: 25px;
            border-radius: 20px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.05);
            margin-bottom: 25px;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        .dashboard-card:hover { transform: translateY(-5px); box-shadow: 0 15px 35px rgba(0,0,0,0.1); }
        .kpi-title { font-size: 15px; color: #6c757d; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
        .kpi-value { font-size: 32px; font-weight: 800; color: #2c3e50; font-family: 'Helvetica Neue', sans-serif; }
        .kpi-sub { font-size: 13px; font-weight: 600; margin-top: 5px; display: flex; align-items: center; gap: 5px; }
        section[data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e9ecef; }
        div[data-testid="stPills"] { gap: 8px; flex-wrap: wrap; }
        div[data-testid="stPills"] button { 
            border-radius: 20px !important; padding: 5px 15px !important;
            font-size: 13px !important; border: 1px solid #e0e0e0;
        }
    </style>
""", unsafe_allow_html=True)

# === 2. [핵심 수정] 데이터 로드 및 정밀 전처리 ===
@st.cache_data
def load_data():
    file_names = ['papp.csv', 'papp.xlsx', '시각화.csv']
    df = None
    
    # 1. 파일 읽기 (1행 헤더, 2행 데이터)
    for file in file_names:
        if os.path.exists(file):
            try:
                # header=0 : 엑셀의 1행을 컬럼명으로 지정 (기본값)
                if file.endswith('.csv'): 
                    df = pd.read_csv(file, header=0)
                else: 
                    df = pd.read_excel(file, header=0)
                break
            except: continue
            
    if df is None: return None

    # 2. '소계' 행 제거 (집계 중복 방지)
    if '구분' in df.columns: 
        df = df[df['구분'] != '소계']

    # 3. [중요] 숫자 컬럼 강제 변환 (콤마, 공백 제거)
    # 계산에 필요한 컬럼들이 문자로 되어있을 경우를 대비해 싹 청소합니다.
    target_numeric_cols = ['대상', '해지', '해지율', '유지(방어)율']
    
    for col in target_numeric_cols:
        if col in df.columns:
            # (1) 먼저 문자열로 변환하여 콤마(,)와 퍼센트(%) 제거
            df[col] = df[col].astype(str).str.replace(',', '').str.replace('%', '').str.strip()
            
            # (2) 숫자로 변환 (에러나면 0으로 처리)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            # (3) 비율 데이터(0.xx)가 아니라면 100을 곱해야 하는지 체크 (해지율/방어율만)
            if col in ['해지율', '유지(방어)율']:
                if df[col].max() <= 1.0: # 최댓값이 1 이하면 0.95 같은 소수로 판단
                    df[col] = df[col] * 100
                df[col] = df[col].round(1)

    # 4. 결측값 자동 계산 (방어율이 비어있으면 자동 채움)
    if '유지(방어)율' not in df.columns and '해지율' in df.columns:
        df['유지(방어)율'] = 100 - df['해지율']
        
    return df

raw_df = load_data()

if raw_df is None:
    st.error("데이터 파일을 찾을 수 없습니다. (papp.csv 또는 papp.xlsx)")
    st.stop()

# === 정렬 및 기본 설정 ===
custom_order = ['중앙', '강북', '서대문', '고양', '의정부', '남양주', '강릉', '원주']
region_col = '구분' if '구분' in raw_df.columns else raw_df.columns[0]
code_col = '구역' if '구역' in raw_df.columns else raw_df.columns[1]

# 데이터 정렬 적용
raw_df[region_col] = pd.Categorical(raw_df[region_col], categories=custom_order, ordered=True)
raw_df = raw_df.sort_values(region_col)


# === 3. 사이드바 (필터링) ===
with st.sidebar:
    st.markdown("### 📊 KTT Analytics")
    st.caption("Premium Dashboard Ver 3.1")
    st.markdown("---")
    
    menu = option_menu(
        None, ["대시보드", "데이터 리스트", "설정"],
        icons=['speedometer2', 'table', 'sliders'],
        menu_icon="cast", default_index=0,
        styles={"container": {"padding": "0", "background": "transparent"}, "nav-link": {"font-size": "14px"}}
    )
    
    st.markdown("### 🎛️ 필터링 (Filter)")
    
    # 지사 필터
    st.markdown("**1. 지사 선택 (Branch)**")
    all_regions = sorted(raw_df[region_col].unique().dropna())
    selected_regions = st.pills(
        "지사를 선택하세요", options=all_regions, selection_mode="multi", 
        default=all_regions, key="branch_pills"
    )
    if not selected_regions: selected_regions = all_regions

    # 구역 필터
    if code_col:
        st.markdown("**2. 구역 선택 (Zone)**")
        filtered_codes_source = raw_df[raw_df[region_col].isin(selected_regions)]
        available_codes = sorted(filtered_codes_source[code_col].unique())
        
        with st.expander("구역 상세 선택 펼치기", expanded=True):
            selected_codes = st.pills(
                "구역을 선택하세요", options=available_codes, selection_mode="multi",
                default=available_codes, key="zone_pills", label_visibility="collapsed"
            )
        if not selected_codes: selected_codes = available_codes

    st.markdown("---")


# === 4. 데이터 필터링 적용 ===
df = raw_df[
    (raw_df[region_col].isin(selected_regions)) & 
    (raw_df[code_col].isin(selected_codes))
]

# === 5. 메인 대시보드 ===

if menu == "대시보드":
    # Header
    c1, c2 = st.columns([3, 1])
    with c1: 
        st.title("지사별 성과 모니터링")
        st.caption(f"데이터 기준: 1행 헤더 / 2행 데이터 시작 | 총 {len(df)}개 구역 집계")
    with c2: 
        st.markdown(f"<div style='text-align:right; padding-top:20px;'><span style='background:#e9ecef; padding:5px 10px; border-radius:10px; font-size:12px;'>🟢 System Normal</span></div>", unsafe_allow_html=True)
    
    st.markdown("###")

    # [Section 1] KPI Cards (정확한 계산 적용)
    col1, col2, col3, col4 = st.columns(4)
    
    # 콤마가 제거된 순수 숫자 데이터이므로 sum()이 정확하게 작동함
    total_target = df['대상'].sum() 
    total_churn = df['해지'].sum()
    avg_retention = df['유지(방어)율'].mean()
    
    def create_card(icon, title, value, sub_text, sub_color):
        return f"""
        <div class="dashboard-card">
            <div style="display:flex; justify-content:space-between;">
                <div class="kpi-title">{title}</div>
                <div style="font-size:20px;">{icon}</div>
            </div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-sub" style="color:{sub_color};">{sub_text}</div>
        </div>
        """
        
    with col1: st.markdown(create_card("👥", "총 관리 대상", f"{total_target:,.0f}건", "▲ 정확한 집계 완료", "#28a745"), unsafe_allow_html=True)
    with col2: st.markdown(create_card("🛡️", "방어 성공", f"{total_target - total_churn:,.0f}건", "● 계약 유지 중", "#0d6efd"), unsafe_allow_html=True)
    with col3: st.markdown(create_card("🚨", "해지 건수", f"{total_churn:,.0f}건", "▼ 방어 실패", "#dc3545"), unsafe_allow_html=True)
    with col4: st.markdown(create_card("📈", "평균 방어율", f"{avg_retention:.1f}%", "● 목표 달성률", "#6610f2"), unsafe_allow_html=True)

    # [Section 2] Charts
    cl1, cl2 = st.columns([1, 1])
    
    # Chart 1: 지표 비교
    with cl1:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.markdown("##### 📊 지사별 성과 비교")
        
        metric_map = {"관리 대상": "대상", "해지 건수": "해지", "해지율(%)": "해지율", "방어율(%)": "유지(방어)율"}
        sel_metric_label = st.pills("지표 선택", list(metric_map.keys()), default="방어율(%)", selection_mode="single", key="chart_opt")
        sel_metric = metric_map[sel_metric_label]

        if sel_metric in ['해지율', '유지(방어)율']:
            group_df = df.groupby(region_col)[sel_metric].mean().reset_index()
            text_fmt = '.1f'
            suffix = '%'
        else:
            group_df = df.groupby(region_col)[sel_metric].sum().reset_index()
            text_fmt = ',.0f'
            suffix = '건'
            
        group_df[region_col] = pd.Categorical(group_df[region_col], categories=custom_order, ordered=True)
        group_df = group_df.sort_values(region_col)
        
        fig_bar = px.bar(
            group_df, x=region_col, y=sel_metric, text=sel_metric,
            color=region_col, color_discrete_sequence=px.colors.qualitative.Prism
        )
        fig_bar.update_traces(texttemplate='%{text:' + text_fmt + '}' + suffix, textposition='outside')
        fig_bar.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            height=380, showlegend=False, margin=dict(t=20, b=10, l=10, r=10),
            xaxis=dict(showgrid=False), yaxis=dict(showgrid=False, showticklabels=False)
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Chart 2: Matrix
    with cl2:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.markdown("##### 🎯 구역별 성과 매트릭스")
        
        mean_target = raw_df['대상'].mean()
        mean_ret = raw_df['유지(방어)율'].mean()

        fig_scatter = px.scatter(
            df, x='대상', y='유지(방어)율', size='대상', color='해지',
            hover_name=code_col, hover_data={region_col: True},
            text=code_col, color_continuous_scale='Reds', height=450
        )
        fig_scatter.add_hline(y=mean_ret, line_dash="dot", line_color="#28a745")
        fig_scatter.add_vline(x=mean_target, line_dash="dot", line_color="#0d6efd")
        fig_scatter.add_shape(type="rect", x0=mean_target, y0=mean_ret, x1=df['대상'].max()*1.2, y1=105, 
                              fillcolor="#28a745", opacity=0.08, line_width=0)

        fig_scatter.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(t=20, b=20, l=10, r=10),
            xaxis_title="관리 대상 (건)", yaxis_title="방어율 (%)"
        )
        fig_scatter.update_traces(textposition='top center')
        st.plotly_chart(fig_scatter, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # [Section 3] Table
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.markdown("##### 📋 상세 리스트 (Data Grid)")
    
    display_cols = [region_col, code_col, '대상', '해지', '해지율', '유지(방어)율']
    final_cols = [c for c in display_cols if c in df.columns]
    
    st.dataframe(
        df[final_cols].sort_values(by=[region_col, '해지'], ascending=[True, False]),
        use_container_width=True,
        column_config={
            region_col: "지사",
            code_col: "구역 코드",
            "대상": st.column_config.NumberColumn("관리 대상", format="%d건"),
            "해지": st.column_config.NumberColumn("해지 건수", format="%d건"),
            "해지율": st.column_config.ProgressColumn("해지율", format="%.1f%%", min_value=0, max_value=20),
            "유지(방어)율": st.column_config.ProgressColumn("방어율", format="%.1f%%", min_value=80, max_value=100),
        },
        hide_index=True
    )
    st.markdown('</div>', unsafe_allow_html=True)

elif menu == "데이터 리스트":
    st.title("📂 전체 데이터 원본")
    st.dataframe(df, use_container_width=True, height=800)

elif menu == "설정":
    st.title("⚙️ 시스템 설정")
    st.info("관리자 권한이 필요합니다.")

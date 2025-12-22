import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# === 1. 페이지 기본 설정 ===
st.set_page_config(
    page_title="2025 지사별 성과 분석 시스템",
    page_icon="🏆",
    layout="wide"
)

# === 2. 스타일 커스텀 (CSS) ===
st.markdown("""
    <style>
        .block-container {padding-top: 1.5rem; padding-bottom: 1rem;}
        div[data-testid="stMetricValue"] {font-size: 24px;}
        .big-font {font-size:20px !important; font-weight: bold;}
    </style>
""", unsafe_allow_html=True)

# === 3. 데이터 로드 및 전처리 ===
@st.cache_data
def load_data():
    # GitHub 등 서버 환경과 로컬 환경 모두 대응
    file_names = ['papp.csv', 'papp.xlsx', '시각화.csv']
    df = None
    
    for file in file_names:
        if os.path.exists(file):
            try:
                if file.endswith('.csv'):
                    df = pd.read_csv(file) # 인코딩 문제시 encoding='cp949' 추가
                else:
                    df = pd.read_excel(file)
                break
            except:
                continue
    
    if df is None:
        return None

    # 전처리: '소계' 제거
    if '구분' in df.columns:
        df = df[df['구분'] != '소계']

    # 전처리: 컬럼명 통일 (사용자 요청 반영: 지사, 구역 등)
    # 엑셀의 '구분' -> '지사', '구역' 컬럼이 있다면 그대로 사용, 없다면 생성
    if '지사' not in df.columns and '구분' in df.columns:
        # 데이터에 '지사' 컬럼이 없고 '구분'만 있다면, '구분'을 '지사'로 씁니다.
        # 하지만 이미지상 '중앙', '강북' 등이 '구분'에 있고, 코드가 '구역'인 것 같습니다.
        # 엑셀 파일 구조에 맞춰 조정이 필요할 수 있습니다. 
        # 여기서는 가장 일반적인 형태로 처리합니다.
        pass 

    # 숫자 변환 (퍼센트 제거 등)
    cols = ['해지율', '유지(방어)율']
    for col in cols:
        if col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.replace('%', '').astype(float)
            elif df[col].max() <= 1.0: # 0.xx 형태라면 100 곱하기
                df[col] = df[col] * 100
            df[col] = df[col].round(1)
            
    # 방어율 자동 계산
    if '유지(방어)율' not in df.columns and '해지율' in df.columns:
        df['유지(방어)율'] = 100 - df['해지율']

    return df

raw_df = load_data()

# === 4. 사이드바 (필터링 컨트롤 타워) ===
with st.sidebar:
    st.header("🎛️ 분석 필터")
    
    if raw_df is not None:
        # 1. 지사 선택 (버튼식 다중 선택)
        # 데이터에 '지사' 컬럼이 있다면 그것을 쓰고, 없다면 '본부'나 '구분' 사용 추정
        # 사용자가 올린 이미지의 '구분' 열이 '중앙', '고양' 등 지사명으로 보임.
        region_col = '구분' if '구분' in raw_df.columns else raw_df.columns[0]
        
        all_regions = sorted(raw_df[region_col].unique())
        selected_regions = st.multiselect(
            "🏢 지사 선택",
            all_regions,
            default=all_regions,
            placeholder="지사를 선택하세요"
        )
        
        # 2. 구역 선택 (선택된 지사에 해당하는 구역만 표시)
        # 이미지상 '구역' 컬럼(G000401 등)이 있다면 사용
        code_col = '구역' if '구역' in raw_df.columns else (
            '구분' if region_col != '구분' else None
        )
        # 만약 구역 컬럼을 못 찾으면 두 번째 컬럼을 구역으로 가정
        if code_col is None and len(raw_df.columns) > 1:
             code_col = raw_df.columns[1]

        if code_col:
            filtered_codes_source = raw_df[raw_df[region_col].isin(selected_regions)]
            all_codes = sorted(filtered_codes_source[code_col].unique())
            
            selected_codes = st.multiselect(
                "📍 구역(코드) 선택",
                all_codes,
                default=all_codes,
                placeholder="특정 구역만 보려면 선택하세요"
            )
        else:
            selected_codes = []

    else:
        st.error("데이터를 불러올 수 없습니다.")
        st.stop()
    
    st.info("💡 **Tip:** 여러 항목을 선택하거나 지울 수 있습니다.")
    st.divider()
    st.caption("Created with Streamlit")

# === 5. 메인 데이터 필터링 적용 ===
# 선택한 지사와 구역에 맞는 데이터만 남깁니다.
df = raw_df[
    (raw_df[region_col].isin(selected_regions)) &
    (raw_df[code_col].isin(selected_codes))
]

# === 6. 대시보드 본문 ===
st.title("📊 지사별 해지 방어율 성과분석")
st.markdown(f"**총 {len(df)}개 구역**에 대한 분석 결과입니다.")

# (1) 탭 구조 생성
tab1, tab2, tab3 = st.tabs(["📈 종합 대시보드", "🔍 상세 분석 리스트", "📋 원본 데이터"])

with tab1:
    # --- KPI 카드 ---
    st.markdown("##### 핵심 성과 지표 (KPI)")
    k1, k2, k3, k4 = st.columns(4)
    
    total_target = df['대상'].sum()
    total_churn = df['해지'].sum()
    avg_churn_rate = (total_churn / total_target * 100) if total_target > 0 else 0
    avg_retention = 100 - avg_churn_rate
    
    k1.metric("총 관리 대상", f"{total_target:,.0f}건", border=True)
    k2.metric("총 해지 건수", f"{total_churn:,.0f}건", border=True)
    k3.metric("평균 해지율", f"{avg_churn_rate:.1f}%", delta_color="inverse", border=True)
    k4.metric("평균 방어율", f"{avg_retention:.1f}%", delta=f"{avg_retention-90:.1f}% (목표90%)", border=True)

    st.markdown("---")

    # --- 차트 영역 ---
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.subheader("🎯 규모 대비 성과 (4분면 분석)")
        st.caption("점의 크기는 관리 대상 규모, 색상은 해지 건수(붉을수록 많음)를 의미합니다.")
        
        # 4분면 차트
        mean_target = raw_df['대상'].mean() # 전체 평균 기준
        mean_ret = raw_df['유지(방어)율'].mean()

        fig_scatter = px.scatter(
            df,
            x='대상',
            y='유지(방어)율',
            size='대상',
            color='해지',
            hover_name=code_col,
            text=region_col, # 점 옆에 지사명 표시
            color_continuous_scale='Reds',
            labels={'대상': '관리 대상 규모', '유지(방어)율': '해지 방어율(%)'},
            height=500
        )
        
        # 기준선 및 영역 표시
        fig_scatter.add_hline(y=mean_ret, line_dash="dash", line_color="green", annotation_text="평균 방어율")
        fig_scatter.add_vline(x=mean_target, line_dash="dash", line_color="blue", annotation_text="평균 규모")
        
        # Best 영역 (우상단)
        fig_scatter.add_shape(type="rect", x0=mean_target, y0=mean_ret, x1=df['대상'].max()*1.2, y1=105, 
                      fillcolor="green", opacity=0.1, line_width=0)
        
        fig_scatter.update_traces(textposition='top center')
        fig_scatter.update_layout(xaxis_title="관리 대상 (건)", yaxis_title="방어율 (%)")
        st.plotly_chart(fig_scatter, use_container_width=True)

    with c2:
        st.subheader("🏆 지사별 평균 방어율")
        # 지사별로 그룹화하여 평균 계산
        group_df = df.groupby(region_col)[['대상', '해지']].sum().reset_index()
        group_df['방어율'] = 100 - (group_df['해지'] / group_df['대상'] * 100)
        group_df = group_df.sort_values('방어율', ascending=True) # 낮은 순부터 표시 (막대 그래프용)

        fig_bar = px.bar(
            group_df,
            x='방어율',
            y=region_col,
            orientation='h',
            text='방어율',
            color='방어율',
            color_continuous_scale='Mint',
            height=500
        )
        fig_bar.update_traces(texttemplate='%{text:.1f}%', textposition='inside')
        fig_bar.update_layout(xaxis_range=[80, 100]) # 방어율 차이 잘 보이게 축 조정
        st.plotly_chart(fig_bar, use_container_width=True)

with tab2:
    st.subheader("📋 구역별 상세 성과표")
    st.caption("헤더를 클릭하면 정렬됩니다. 우측 상단 검색 아이콘으로 특정 구역을 찾을 수 있습니다.")
    
    # 보기 좋은 컬럼 순서로 정리
    display_cols = [region_col, code_col, '대상', '해지', '해지율', '유지(방어)율']
    # 실제 존재하는 컬럼만 선택
    final_cols = [c for c in display_cols if c in df.columns]
    
    # 데이터프레임 표시 (Column Config 활용)
    st.dataframe(
        df[final_cols].sort_values(by='해지', ascending=False),
        use_container_width=True,
        column_config={
            region_col: "지사",
            code_col: "구역 코드",
            "대상": st.column_config.NumberColumn("관리 대상", format="%d건"),
            "해지": st.column_config.NumberColumn("해지 건수", format="%d건"),
            "해지율": st.column_config.ProgressColumn(
                "해지율 (%)",
                format="%.1f%%",
                min_value=0,
                max_value=20, # 최대 20% 기준으로 바 표시
                help="낮을수록 좋습니다."
            ),
            "유지(방어)율": st.column_config.ProgressColumn(
                "방어율 (%)",
                format="%.1f%%",
                min_value=80, # 80%부터 시작해서 차이 강조
                max_value=100,
                help="높을수록 좋습니다."
            ),
        },
        hide_index=True
    )

with tab3:
    st.subheader("💾 원본 데이터 확인")
    st.dataframe(df)

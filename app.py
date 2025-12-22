import streamlit as st
import pandas as pd
import plotly.express as px
import os

# 페이지 설정
st.set_page_config(page_title="지사별 성과 대시보드", layout="wide")

# === 데이터 로드 함수 ===
@st.cache_data
def load_data():
    # 1. GitHub 저장소에 있는 파일을 우선 찾음
    if os.path.exists('papp.csv'):
        df = pd.read_csv('papp.csv')
    # 2. 없으면 엑셀 파일을 찾음
    elif os.path.exists('papp.xlsx'):
        df = pd.read_excel('papp.xlsx')
    else:
        return None

    # 전처리: '소계' 제거
    if '구분' in df.columns:
        df = df[df['구분'] != '소계']

    # 전처리: 퍼센트(%) 문자열 숫자로 변환
    cols = ['해지율', '유지(방어)율']
    for col in cols:
        if col in df.columns:
            # 문자열인 경우 % 제거
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.replace('%', '').astype(float)
            # 숫자가 1보다 작으면(0.94 등) 100 곱하기
            elif df[col].max() <= 1.0:
                df[col] = df[col] * 100
            
            df[col] = df[col].round(1)
            
    # 방어율 없는 경우 자동 계산
    if '유지(방어)율' not in df.columns and '해지율' in df.columns:
        df['유지(방어)율'] = 100 - df['해지율']

    return df

# === 메인 화면 ===
st.title("📊 지사별 해지 방어율 대시보드")

df = load_data()

if df is not None:
    # 1. KPI 지표
    st.markdown("### 핵심 성과 지표 (KPI)")
    k1, k2, k3 = st.columns(3)
    k1.metric("총 관리 대상", f"{df['대상'].sum():,.0f}건")
    k2.metric("총 해지 건수", f"{df['해지'].sum():,.0f}건")
    k3.metric("평균 방어율", f"{df['유지(방어)율'].mean():.1f}%")

    st.divider()

    # 2. 차트 (4분면 분석)
    st.subheader("📈 규모 대비 성과 분석 (4분면)")
    
    mean_target = df['대상'].mean()
    mean_retention = df['유지(방어)율'].mean()

    fig = px.scatter(
        df,
        x='대상',
        y='유지(방어)율',
        size='대상',
        color='해지',
        hover_name='구분',
        text='구분',
        color_continuous_scale='Reds',
        title="우상단(초록 영역)일수록 우수 지사입니다."
    )

    # 기준선 및 배경
    fig.add_hline(y=mean_retention, line_dash="dash", line_color="green", annotation_text="평균 방어율")
    fig.add_vline(x=mean_target, line_dash="dash", line_color="blue", annotation_text="평균 규모")
    
    # 우수 영역(우상단) 표시
    fig.add_shape(type="rect", x0=mean_target, y0=mean_retention, x1=df['대상'].max()*1.2, y1=105, 
                  fillcolor="green", opacity=0.1, line_width=0)

    fig.update_traces(textposition='top center')
    fig.update_layout(height=600, yaxis_range=[0, 110])
    st.plotly_chart(fig, use_container_width=True)

    # 3. 데이터 표
    with st.expander("📋 전체 데이터 보기"):
        st.dataframe(df)
else:
    st.warning("데이터 파일(papp.csv)을 찾을 수 없습니다. GitHub에 파일을 함께 업로드해주세요.")
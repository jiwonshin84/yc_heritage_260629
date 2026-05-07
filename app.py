import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="문화재 위험도 AI 분석",
    layout="wide"
)

st.title("🏛 공공데이터 기반 문화재 훼손 위험 예측 시스템")

st.markdown("""
### 프로젝트 목적

공공데이터를 활용하여  
문화재의 환경 노출 위험을 분석하고  
AI 기반 훼손 위험 예측 모델을 개발합니다.
""")

# 데이터 로드
df = pd.read_csv("data/processed/yc_heritage_detail_enriched.csv")

# 통계 카드
c1, c2, c3, c4 = st.columns(4)

c1.metric("영천 문화재 수", len(df))
c2.metric("국보/보물 수",
          len(df[df["국가유산종목"].isin(["국보","보물"])]))
c3.metric("시대 종류", df["시대"].nunique())
c4.metric("문화재 유형", df["국가유산종목"].nunique())

st.divider()

st.subheader("📌 연구 흐름")

st.markdown("""
국가유산 데이터  
+ 기상 데이터  
+ 미세먼지 데이터  
+ 재질/노출형태 분석  
↓  
AI 군집분석  
↓  
문화재 훼손 위험 예측
""")

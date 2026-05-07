import streamlit as st
import pandas as pd
import plotly.express as px

st.title("🌦 환경 데이터 분석")

temp_df = pd.read_csv(
    "data/environment/온습도데이터.csv"
)

dust_df = pd.read_csv(
    "data/environment/미세먼지데이터.csv"
)

st.subheader("온도 변화")

fig1 = px.line(
    temp_df,
    x="date",
    y="temp"
)

st.plotly_chart(fig1)

st.subheader("미세먼지 변화")

fig2 = px.line(
    dust_df,
    x="date",
    y="pm10"
)

st.plotly_chart(fig2)

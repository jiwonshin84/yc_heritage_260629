import streamlit as st
import pandas as pd
import plotly.express as px

st.title("🇰🇷 전국 문화유산 현황")

df = pd.read_csv("data/raw/all_heritage.csv")

st.subheader("국가유산 종목별 현황")

type_count = (
    df["국가유산종목"]
    .value_counts()
    .reset_index()
)

fig = px.bar(
    type_count,
    x="국가유산종목",
    y="count"
)

st.plotly_chart(fig, use_container_width=True)

st.subheader("시도별 문화재 현황")

region_count = (
    df["시도명"]
    .value_counts()
    .reset_index()
)

fig2 = px.pie(
    region_count,
    names="시도명",
    values="count"
)

st.plotly_chart(fig2, use_container_width=True)

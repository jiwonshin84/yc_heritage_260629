import streamlit as st
import pandas as pd
import plotly.express as px

st.title("🤖 문화재 군집분석")

df = pd.read_csv(
    "data/processed/yc_clustering.csv"
)

st.subheader("군집별 분포")

fig = px.scatter(

    df,

    x="경도",

    y="위도",

    color="cluster",

    hover_data=[
        "문화재명(국문)",
        "국가유산종목",
        "시대"
    ]
)

st.plotly_chart(
    fig,
    use_container_width=True
)

st.subheader("군집별 평균")

summary = (
    df.groupby("cluster")[
        ["가치점수","시대점수"]
    ]
    .mean()
)

st.dataframe(summary)

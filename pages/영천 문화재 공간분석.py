import streamlit as st
import pandas as pd
import folium

from streamlit_folium import st_folium
from folium.plugins import HeatMap

st.title("🗺 영천 문화재 공간분석")

df = pd.read_csv(
    "data/processed/yc_heritage_detail_enriched.csv"
)

center = [
    df["위도"].mean(),
    df["경도"].mean()
]

m = folium.Map(
    location=center,
    zoom_start=10
)

# 마커
for idx, row in df.iterrows():

    folium.Marker(
        [row["위도"], row["경도"]],
        popup=row["문화재명(국문)"]
    ).add_to(m)

# Heatmap
heat_data = df[
    ["위도", "경도"]
].values.tolist()

HeatMap(heat_data).add_to(m)

st_folium(m, width=1200, height=700)

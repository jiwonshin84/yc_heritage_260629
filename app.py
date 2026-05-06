# ==========================================================
# app.py
# 영천 국가유산 AI 인터랙티브 지도
# ==========================================================

import streamlit as st
import pandas as pd
import folium
import requests

from streamlit_folium import st_folium
from folium.plugins import MarkerCluster, HeatMap

# ==========================================================
# 페이지 설정
# ==========================================================
st.set_page_config(
    page_title="영천 국가유산 AI 지도",
    page_icon="🏛️",
    layout="wide"
)

# ==========================================================
# 제목
# ==========================================================
st.title("🏛️ 영천 국가유산 AI 인터랙티브 지도")

st.markdown("""
영천 지역 국가유산 데이터를 활용하여  
지도 기반 탐색 및 AI 분석 결과를 시각화한 프로젝트입니다.
""")

# ==========================================================
# GitHub CSV URL
# raw.githubusercontent.com 형태로 변경 필요
# ==========================================================
CSV_URL = (
    "https://raw.githubusercontent.com/"
    "YOUR_GITHUB_ID/YOUR_REPO/main/"
    "영천_국가유산_상세_좌표보완.csv"
)

# ==========================================================
# 데이터 불러오기
# ==========================================================
@st.cache_data
def load_data():

    df = pd.read_csv(
        CSV_URL,
        encoding="utf-8-sig"
    )

    # 좌표 숫자형 변환
    df["위도"] = pd.to_numeric(
        df["위도"],
        errors="coerce"
    )

    df["경도"] = pd.to_numeric(
        df["경도"],
        errors="coerce"
    )

    # 결측 제거
    df = df.dropna(
        subset=["위도", "경도"]
    )

    return df

df = load_data()

# ==========================================================
# 사이드바
# ==========================================================
st.sidebar.header("🔎 필터")

# ----------------------------------------------------------
# 국가유산종목 선택
# ----------------------------------------------------------
type_list = sorted(
    df["국가유산종목"]
    .dropna()
    .unique()
)

selected_types = st.sidebar.multiselect(

    "국가유산종목 선택",

    options=type_list,

    default=type_list
)

# ----------------------------------------------------------
# 시대 검색
# ----------------------------------------------------------
era_keyword = st.sidebar.text_input(
    "시대 검색",
    placeholder="예: 신라, 고려, 조선"
)

# ----------------------------------------------------------
# 이름 검색
# ----------------------------------------------------------
name_keyword = st.sidebar.text_input(
    "문화재명 검색"
)

# ==========================================================
# 데이터 필터링
# ==========================================================
filtered_df = df.copy()

# 종목 필터
filtered_df = filtered_df[
    filtered_df["국가유산종목"]
    .isin(selected_types)
]

# 시대 검색
if era_keyword:

    filtered_df = filtered_df[
        filtered_df["시대"]
        .astype(str)
        .str.contains(
            era_keyword,
            na=False
        )
    ]

# 이름 검색
if name_keyword:

    filtered_df = filtered_df[
        filtered_df["문화재명(국문)"]
        .astype(str)
        .str.contains(
            name_keyword,
            na=False
        )
    ]

# ==========================================================
# 데이터 수 표시
# ==========================================================
st.subheader(
    f"📌 검색 결과 : {len(filtered_df)}건"
)

# ==========================================================
# 지도 생성
# ==========================================================
center_lat = 35.9733
center_lon = 128.9386

m = folium.Map(

    location=[center_lat, center_lon],

    zoom_start=11,

    tiles="CartoDB positron"
)

# ==========================================================
# HeatMap
# ==========================================================
heat_data = filtered_df[
    ["위도", "경도"]
].values.tolist()

HeatMap(

    heat_data,

    radius=18,

    blur=18,

    min_opacity=0.4

).add_to(m)

# ==========================================================
# MarkerCluster
# ==========================================================
marker_cluster = MarkerCluster().add_to(m)

# ==========================================================
# 마커 추가
# ==========================================================
for _, row in filtered_df.iterrows():

    # ------------------------------------------------------
    # 이미지 URL
    # ------------------------------------------------------
    img_url = str(row.get("이미지URL", ""))

    if img_url == "nan":
        img_url = ""

    # ------------------------------------------------------
    # 내용
    # ------------------------------------------------------
    content = str(row.get("내용", ""))

    if content == "nan":
        content = ""

    # 내용 너무 길면 자르기
    short_content = content[:300] + "..."

    # ------------------------------------------------------
    # popup HTML
    # ------------------------------------------------------
    popup_html = f"""
    <div style="width:320px">

    <h3 style="margin-bottom:10px;">
    {row['문화재명(국문)']}
    </h3>

    <b>국가유산종목</b><br>
    {row['국가유산종목']}<br><br>

    <b>시대</b><br>
    {row['시대']}<br><br>

    <b>소재지</b><br>
    {row['소재지상세']}<br><br>

    """

    # ------------------------------------------------------
    # 이미지 표시
    # ------------------------------------------------------
    if img_url != "":

        popup_html += f"""
        <img src="{img_url}"
             width="280"
             style="
             border-radius:10px;
             margin-bottom:10px;
             ">
        <br>
        """

    # ------------------------------------------------------
    # 내용 추가
    # ------------------------------------------------------
    popup_html += f"""
    <b>설명</b><br>

    <div style="
    max-height:180px;
    overflow-y:auto;
    line-height:1.5;
    font-size:13px;
    ">

    {short_content}

    </div>

    </div>
    """

    # ------------------------------------------------------
    # 마커 생성
    # ------------------------------------------------------
    folium.Marker(

        location=[
            row["위도"],
            row["경도"]
        ],

        popup=folium.Popup(
            popup_html,
            max_width=350
        ),

        tooltip=row["문화재명(국문)"],

        icon=folium.Icon(
            color="blue",
            icon="info-sign"
        )

    ).add_to(marker_cluster)

# ==========================================================
# 지도 출력
# ==========================================================
st_data = st_folium(

    m,

    width=None,

    height=700
)

# ==========================================================
# 통계
# ==========================================================
st.subheader("📊 국가유산 종목 분포")

type_count = (
    filtered_df["국가유산종목"]
    .value_counts()
)

st.bar_chart(type_count)

# ==========================================================
# 데이터 테이블
# ==========================================================
st.subheader("📄 데이터 보기")

show_cols = [

    "문화재명(국문)",
    "국가유산종목",
    "시대",
    "소재지상세"

]

st.dataframe(

    filtered_df[show_cols],

    use_container_width=True
)

# ==========================================================
# 푸터
# ==========================================================
st.markdown("---")

st.caption(
    "공공데이터포털 · 국가유산청 OpenAPI · Kakao Local API 활용"
)

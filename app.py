# ==========================================================
# 영천 문화유산 AI 분석 플랫폼 (최종 완성판 V4)
# GitHub CSV + 상세 API + 카카오 좌표 + Gemini
# ==========================================================

import streamlit as st
import pandas as pd
import requests
import time
import xml.etree.ElementTree as ET
import folium
import plotly.express as px
from folium.plugins import HeatMap
from streamlit_folium import st_folium
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import google.generativeai as genai

# ==========================================================
# API KEY
# ==========================================================
KAKAO_API_KEY = "YOUR_KAKAO_API_KEY"
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"

genai.configure(api_key=GEMINI_API_KEY)

# ==========================================================
# 기본 설정
# ==========================================================
st.set_page_config(
    page_title="영천 문화유산 AI 플랫폼",
    page_icon="🏛️",
    layout="wide"
)

st.title("🏛️ 영천 문화유산 AI 분석 플랫폼")
st.caption("CSV 기반 + 상세 API + 지도 + AI 분석")

# ==========================================================
# 영천 중심 좌표
# ==========================================================
YEONGCHEON_LAT = 35.9733
YEONGCHEON_LON = 128.9386

# ==========================================================
# API 기본 설정
# ==========================================================
BASE_URL = "https://www.khs.go.kr"

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})


def safe_request(url, params=None, retry=5):
    for _ in range(retry):
        try:
            res = session.get(url, params=params, timeout=15)
            res.encoding = "utf-8"
            if res.status_code == 200:
                return res
        except:
            time.sleep(1)
    return None


# ==========================================================
# CSV 데이터 로드
# ==========================================================
@st.cache_data(ttl=86400)
def load_data():
    df = pd.read_csv("All_Heritage.csv")

    df["위도"] = pd.to_numeric(df["위도"], errors="coerce")
    df["경도"] = pd.to_numeric(df["경도"], errors="coerce")

    # 영천 필터
    df = df[df["시군구명"].str.contains("영천", na=False)]

    df = df.dropna(subset=["위도", "경도"])

    return df.reset_index(drop=True)


df = load_data()

# ==========================================================
# 상세 조회 API
# ==========================================================
def get_detail(ccbaKdcd, ccbaAsno, ccbaCtcd):

    url = BASE_URL + "/cha/SearchKindOpenapiDt.do"

    params = {
        "ccbaKdcd": ccbaKdcd,
        "ccbaAsno": ccbaAsno,
        "ccbaCtcd": ccbaCtcd
    }

    res = safe_request(url, params)

    if res is None:
        return None

    root = ET.fromstring(res.text)
    item = root.find(".//item")

    if item is None:
        return None

    return {
        "이미지": item.findtext("imageUrl"),
        "내용": item.findtext("content"),
        "시대": item.findtext("ccceName"),
        "소재지": item.findtext("ccbaLcad"),
        "종목": item.findtext("ccmaName")
    }


# ==========================================================
# 메뉴
# ==========================================================
menu = st.sidebar.radio(
    "메뉴 선택",
    ["홈", "문화재 현황", "문화재 지도", "HeatMap", "AI 군집분석", "문화재 검색", "Gemini 챗봇"]
)

# ==========================================================
# 홈
# ==========================================================
if menu == "홈":

    c1, c2, c3 = st.columns(3)

    c1.metric("전체 문화재 수", len(df))
    c2.metric("종목 수", df["국가유산종목"].nunique())
    c3.metric("지역", "영천")

    st.markdown("---")

    st.info("GitHub CSV + 국가유산 API + AI 분석 기반 플랫폼")

# ==========================================================
# 문화재 현황
# ==========================================================
elif menu == "문화재 현황":

    count = df["국가유산종목"].value_counts()

    fig = px.bar(
        x=count.values,
        y=count.index,
        orientation="h",
        color=count.values,
        title="영천 문화재 종목별 현황"
    )

    st.plotly_chart(fig, use_container_width=True)

# ==========================================================
# 지도
# ==========================================================
elif menu == "문화재 지도":

    m = folium.Map(location=[YEONGCHEON_LAT, YEONGCHEON_LON], zoom_start=11)

    for _, row in df.iterrows():
        folium.Marker(
            [row["위도"], row["경도"]],
            tooltip=row["문화재명"],
            popup=f"{row['문화재명']} ({row['국가유산종목']})"
        ).add_to(m)

    st_folium(m, width=1300, height=700)

# ==========================================================
# HeatMap
# ==========================================================
elif menu == "HeatMap":

    m = folium.Map(location=[YEONGCHEON_LAT, YEONGCHEON_LON], zoom_start=11)

    HeatMap(df[["위도", "경도"]].values.tolist()).add_to(m)

    st_folium(m, width=1300, height=700)

# ==========================================================
# 군집분석
# ==========================================================
elif menu == "AI 군집분석":

    df["가치점수"] = 5
    df["시대점수"] = 5

    X = df[["위도", "경도", "가치점수", "시대점수"]]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = KMeans(n_clusters=4, random_state=42, n_init=10)
    df["cluster"] = model.fit_predict(X_scaled)

    fig = px.scatter_mapbox(
        df,
        lat="위도",
        lon="경도",
        color="cluster",
        hover_name="문화재명",
        zoom=10
    )

    fig.update_layout(mapbox_style="open-street-map")

    st.plotly_chart(fig, use_container_width=True)

# ==========================================================
# 문화재 검색 + 상세보기
# ==========================================================
elif menu == "문화재 검색":

    keyword = st.text_input("문화재명 검색")

    if keyword:
        result = df[df["문화재명"].str.contains(keyword, na=False)]

        if len(result) == 0:
            st.warning("검색 결과 없음")
        else:
            selected = st.selectbox("문화재 선택", result["문화재명"])

            row = result[result["문화재명"] == selected].iloc[0]

            st.markdown("### 📍 기본 정보")
            st.write(f"종목: {row['국가유산종목']}")
            st.write(f"위치: {row['시군구명']}")

            if st.button("🔎 상세 정보 보기"):

                detail = get_detail(
                    row["종목코드"],   # ccbaKdcd
                    row["관리번호"],   # ccbaAsno
                    row["시도코드"]    # ccbaCtcd
                )

                if detail:

                    if detail["이미지"]:
                        st.image(detail["이미지"])

                    st.markdown("### 📖 설명")
                    st.write(detail["내용"])

                    st.markdown("### 🏺 추가 정보")
                    st.write(f"시대: {detail['시대']}")
                    st.write(f"소재지: {detail['소재지']}")

                else:
                    st.error("상세정보 불러오기 실패")

# ==========================================================
# Gemini 챗봇
# ==========================================================
elif menu == "Gemini 챗봇":

    q = st.text_area("질문 입력")

    if st.button("질문하기"):

        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = f"""
        너는 문화재 전문가다.

        영천 문화재 데이터:
        - 총 개수: {len(df)}
        - 주요 종목: {', '.join(df['국가유산종목'].unique()[:10])}

        질문:
        {q}

        학생 발표 수준으로 설명해라.
        """

        response = model.generate_content(prompt)

        st.success(response.text)

# app.py
# ==========================================================
# 영천 문화유산 AI 분석 플랫폼 (최종 완성판 V3)
# 문화재청 API + 카카오 좌표보정 + Gemini + 군집분석
# Streamlit Cloud 배포용
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
KAKAO_API_KEY = "4b2bd2c723594d75ace03ff0e80d65fc"
GEMINI_API_KEY = "AIzaSyCeNS_TTBIU6LmchWVdpki-Z9k0-MbKL6E"


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
st.caption("문화재청 API + 카카오맵 좌표보정 + AI 군집분석 + Gemini")

# ==========================================================
# 영천 중심 좌표
# ==========================================================
YEONGCHEON_LAT = 35.9733
YEONGCHEON_LON = 128.9386

# ==========================================================
# 문화재청 API 요청
# ==========================================================
BASE_URL = "https://www.khs.go.kr"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0"
})

def safe_request(url, params=None, retry=5):

    for _ in range(retry):
        try:
            res = session.get(url, params=params, timeout=20)
            res.encoding = "utf-8"

            if res.status_code == 200:
                return res
        except:
            time.sleep(2)

    return None

# ==========================================================
# 카카오 주소 → 좌표 변환
# ==========================================================
@st.cache_data(ttl=86400)
def get_coord(address):

    url = "https://dapi.kakao.com/v2/local/search/address.json"

    headers = {
        "Authorization": f"KakaoAK {KAKAO_API_KEY}"
    }

    params = {
        "query": address
    }

    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        data = r.json()

        if data["documents"]:
            lat = float(data["documents"][0]["y"])
            lon = float(data["documents"][0]["x"])
            return lat, lon

    except:
        pass

    return None, None

# ==========================================================
# 데이터 수집
# ==========================================================
@st.cache_data(ttl=86400)
def load_data():

    url = BASE_URL + "/cha/SearchKindOpenapiList.do"

    all_data = []
    page = 1

    while True:

        params = {
            "pageUnit": "300",
            "pageIndex": str(page),
            "ccbaCncl": "N"
        }

        response = safe_request(url, params)

        if response is None:
            break

        root = ET.fromstring(response.text)
        items = list(root.iter("item"))

        if len(items) == 0:
            break

        for item in items:

            city = item.findtext("ccsiName")

            if city and "영천" in city:

                name = item.findtext("ccbaMnm1")
                category = item.findtext("ccmaName")
                lat = item.findtext("latitude")
                lon = item.findtext("longitude")

                lat = pd.to_numeric(lat, errors="coerce")
                lon = pd.to_numeric(lon, errors="coerce")

                # 좌표 없으면 카카오 보정
                if pd.isna(lat) or pd.isna(lon):
                    lat, lon = get_coord("경북 영천시 " + name)

                all_data.append({
                    "국가유산종목": category,
                    "문화재명": name,
                    "시군구명": city,
                    "위도": lat,
                    "경도": lon
                })

        page += 1
        time.sleep(0.3)

    df = pd.DataFrame(all_data)

    df = df.dropna()

    # 점수 생성
    df["시대점수"] = 5
    df["가치점수"] = 5

    return df.reset_index(drop=True)

df = load_data()

# ==========================================================
# 메뉴
# ==========================================================
menu = st.sidebar.radio(
    "메뉴 선택",
    [
        "홈",
        "문화재 현황",
        "문화재 지도",
        "HeatMap",
        "AI 군집분석",
        "문화재 검색",
        "Gemini 챗봇"
    ]
)

# ==========================================================
# 홈
# ==========================================================
if menu == "홈":

    c1, c2, c3 = st.columns(3)

    c1.metric("전체 문화재 수", len(df))
    c2.metric("국가유산 종목 수", df["국가유산종목"].nunique())
    c3.metric("분석 지역", "영천시")

    st.markdown("---")

    st.write("""
    본 플랫폼은 문화재청 API 데이터를 활용하여
    영천 지역 문화유산을 분석합니다.

    카카오맵 좌표 보정과 Gemini AI 설명 기능이 포함되어 있습니다.
    """)

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

    m = folium.Map(
        location=[YEONGCHEON_LAT, YEONGCHEON_LON],
        zoom_start=11
    )

    for _, row in df.iterrows():

        popup = f"""
        <b>{row['문화재명']}</b><br>
        종목: {row['국가유산종목']}
        """

        folium.Marker(
            [row["위도"], row["경도"]],
            popup=popup,
            tooltip=row["문화재명"]
        ).add_to(m)

    st_folium(m, width=1300, height=700)

# ==========================================================
# HeatMap
# ==========================================================
elif menu == "HeatMap":

    m = folium.Map(
        location=[YEONGCHEON_LAT, YEONGCHEON_LON],
        zoom_start=11
    )

    HeatMap(
        df[["위도", "경도"]].values.tolist(),
        radius=18,
        blur=15
    ).add_to(m)

    st_folium(m, width=1300, height=700)

# ==========================================================
# 군집분석
# ==========================================================
elif menu == "AI 군집분석":

    X = df[["위도", "경도", "가치점수", "시대점수"]]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = KMeans(
        n_clusters=4,
        random_state=42,
        n_init=10
    )

    df["cluster"] = model.fit_predict(X_scaled)

    fig = px.scatter_mapbox(
        df,
        lat="위도",
        lon="경도",
        color="cluster",
        hover_name="문화재명",
        zoom=10,
        height=700
    )

    fig.update_layout(mapbox_style="open-street-map")

    st.plotly_chart(fig, use_container_width=True)

# ==========================================================
# 검색
# ==========================================================
elif menu == "문화재 검색":

    keyword = st.text_input("문화재명 검색")

    if keyword:
        result = df[df["문화재명"].str.contains(keyword, na=False)]
        st.dataframe(result)

# ==========================================================
# Gemini 챗봇
# ==========================================================
elif menu == "Gemini 챗봇":

    q = st.text_area("질문 입력")

    if st.button("질문하기"):

        model = genai.GenerativeModel("gemini-1.5-pro")

        prompt = f"""
        너는 문화재 분석 전문가다.

        영천 문화재 수: {len(df)}
        종목 종류: {', '.join(df['국가유산종목'].unique()[:10])}

        질문:
        {q}

        학생 발표 수준으로 쉽게 설명해줘.
        """

        response = model.generate_content(prompt)

        st.success(response.text)

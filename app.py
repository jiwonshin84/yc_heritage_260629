# ==========================================================
# 영천 문화유산 AI 분석 플랫폼 (최종 완성판 V6)
# 전국 + 영천 분석 + 지도 + AI + Gemini
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
st.caption("전국 + 영천 국가유산 분석 / 지도 / AI 분석")


# ==========================================================
# 영천 중심 좌표
# ==========================================================
YEONGCHEON_LAT = 35.9733
YEONGCHEON_LON = 128.9386


# ==========================================================
# API 설정
# ==========================================================
BASE_URL = "https://www.khs.go.kr"

session = requests.Session()

session.headers.update({
    "User-Agent": "Mozilla/5.0"
})


# ==========================================================
# 안전 요청 함수
# ==========================================================
def safe_request(url, params=None, retry=5):

    for _ in range(retry):

        try:
            res = session.get(
                url,
                params=params,
                timeout=15
            )

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

    # ------------------------------------------------------
    # 전국 데이터
    # ------------------------------------------------------
    all_df = pd.read_csv("All_Heritage.csv")

    # 좌표 숫자형 변환
    all_df["위도"] = pd.to_numeric(
        all_df["위도"],
        errors="coerce"
    )

    all_df["경도"] = pd.to_numeric(
        all_df["경도"],
        errors="coerce"
    )

    # ------------------------------------------------------
    # 영천 데이터
    # ------------------------------------------------------
    yc_df = all_df[
        all_df["시군구명"].astype(str).str.contains(
            "영천",
            na=False
        )
    ].copy()

    yc_df = yc_df.dropna(
        subset=["위도", "경도"]
    )

    return (
        all_df.reset_index(drop=True),
        yc_df.reset_index(drop=True)
    )


# 데이터 로드
all_df, df = load_data()


# ==========================================================
# 상세조회 API
# ==========================================================
@st.cache_data(ttl=86400)
def get_detail(ccbaKdcd, ccbaAsno, ccbaCtcd):

    url = BASE_URL + "/cha/SearchKindOpenapiDt.do"

    params = {
        "ccbaKdcd": str(ccbaKdcd).split(".")[0].zfill(2),
        "ccbaAsno": str(ccbaAsno).split(".")[0].zfill(4),
        "ccbaCtcd": str(ccbaCtcd).split(".")[0].zfill(2)
    }

    res = safe_request(url, params)

    if res is None:
        return None

    try:
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

    except:
        return None


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

    st.subheader("📌 플랫폼 소개")

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "전국 문화재 수",
        len(all_df)
    )

    c2.metric(
        "영천 문화재 수",
        len(df)
    )

    c3.metric(
        "국가유산 종목 수",
        all_df["국가유산종목"].nunique()
    )

    st.info(
        "국가유산 데이터를 기반으로 "
        "영천 문화재를 분석하는 AI 플랫폼입니다."
    )

    st.markdown("---")

    st.markdown("""
    ### 주요 기능

    - 전국 국가유산 분석
    - 영천 문화재 분석
    - 지도 시각화
    - HeatMap 분석
    - AI 군집분석
    - 문화재 상세조회 API
    - Gemini AI 챗봇
    """)


# ==========================================================
# 문화재 현황
# ==========================================================
elif menu == "문화재 현황":

    st.subheader("📊 국가유산 현황 분석")

    tab1, tab2 = st.tabs([
        "🇰🇷 전국 현황",
        "🏛️ 영천 현황"
    ])

    # ======================================================
    # 전국 현황
    # ======================================================
    with tab1:

        nation_count = all_df["국가유산종목"].value_counts()

        fig1 = px.bar(
            x=nation_count.values,
            y=nation_count.index,
            orientation="h",
            color=nation_count.values,
            text=nation_count.values,
            title=f"전국 국가유산 종목별 현황 (총 {len(all_df)}건)"
        )

        fig1.update_layout(
            height=700,
            xaxis_title="개수",
            yaxis_title="국가유산종목"
        )

        st.plotly_chart(
            fig1,
            use_container_width=True
        )

        st.dataframe(
            nation_count.reset_index().rename(
                columns={
                    "index": "국가유산종목",
                    "국가유산종목": "개수"
                }
            ),
            use_container_width=True
        )

    # ======================================================
    # 영천 현황
    # ======================================================
    with tab2:

        yc_count = df["국가유산종목"].value_counts()

        fig2 = px.bar(
            x=yc_count.values,
            y=yc_count.index,
            orientation="h",
            color=yc_count.values,
            text=yc_count.values,
            title=f"영천 국가유산 종목별 현황 (총 {len(df)}건)"
        )

        fig2.update_layout(
            height=600,
            xaxis_title="개수",
            yaxis_title="국가유산종목"
        )

        st.plotly_chart(
            fig2,
            use_container_width=True
        )

        st.dataframe(
            yc_count.reset_index().rename(
                columns={
                    "index": "국가유산종목",
                    "국가유산종목": "개수"
                }
            ),
            use_container_width=True
        )


# ==========================================================
# 문화재 지도
# ==========================================================
elif menu == "문화재 지도":

    st.subheader("🗺️ 영천 문화재 지도")

    m = folium.Map(
        location=[YEONGCHEON_LAT, YEONGCHEON_LON],
        zoom_start=11
    )

    for _, row in df.iterrows():

        popup_text = f"""
        <b>{row['문화재명']}</b><br>
        종목: {row['국가유산종목']}<br>
        지역: {row['시군구명']}
        """

        folium.Marker(
            [row["위도"], row["경도"]],
            tooltip=row["문화재명"],
            popup=popup_text
        ).add_to(m)

    st_folium(
        m,
        width=1300,
        height=700
    )


# ==========================================================
# HeatMap
# ==========================================================
elif menu == "HeatMap":

    st.subheader("🔥 영천 문화재 HeatMap")

    m = folium.Map(
        location=[YEONGCHEON_LAT, YEONGCHEON_LON],
        zoom_start=11
    )

    HeatMap(
        df[["위도", "경도"]]
        .dropna()
        .values
        .tolist()
    ).add_to(m)

    st_folium(
        m,
        width=1300,
        height=700
    )


# ==========================================================
# AI 군집분석
# ==========================================================
elif menu == "AI 군집분석":

    st.subheader("🤖 AI 군집분석")

    cluster_df = df.copy()

    # 임시 점수
    cluster_df["가치점수"] = 5
    cluster_df["시대점수"] = 5

    X = cluster_df[
        ["위도", "경도", "가치점수", "시대점수"]
    ]

    scaler = StandardScaler()

    X_scaled = scaler.fit_transform(X)

    model = KMeans(
        n_clusters=4,
        random_state=42,
        n_init=10
    )

    cluster_df["cluster"] = model.fit_predict(X_scaled)

    fig = px.scatter_mapbox(
        cluster_df,
        lat="위도",
        lon="경도",
        color="cluster",
        hover_name="문화재명",
        zoom=10,
        height=700
    )

    fig.update_layout(
        mapbox_style="open-street-map"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.info(
        "문화재 위치 및 점수를 기반으로 "
        "AI 군집분석을 수행했습니다."
    )


# ==========================================================
# 문화재 검색
# ==========================================================
elif menu == "문화재 검색":

    st.subheader("🔎 문화재 검색")

    keyword = st.text_input(
        "문화재명 검색"
    )

    if keyword:

        result = df[
            df["문화재명"]
            .astype(str)
            .str.contains(keyword, na=False)
        ]

        if len(result) == 0:

            st.warning("검색 결과가 없습니다.")

        else:

            selected = st.selectbox(
                "문화재 선택",
                result["문화재명"]
            )

            row = result[
                result["문화재명"] == selected
            ].iloc[0]

            st.markdown("## 📍 기본 정보")

            c1, c2 = st.columns(2)

            c1.write(f"문화재명: {row['문화재명']}")
            c1.write(f"종목: {row['국가유산종목']}")

            c2.write(f"지역: {row['시군구명']}")
            c2.write(f"위도: {row['위도']}")

            st.markdown("---")

            # --------------------------------------------------
            # 상세조회 API
            # --------------------------------------------------
            try:

                detail = get_detail(
                    row["종목코드"],
                    row["관리번호"],
                    row["시도코드"]
                )

                if detail:

                    if detail["이미지"]:

                        st.image(
                            detail["이미지"],
                            use_container_width=True
                        )

                    st.markdown("## 📖 설명")

                    st.write(detail["내용"])

                    st.markdown("## 🏺 추가 정보")

                    st.write(f"시대: {detail['시대']}")
                    st.write(f"소재지: {detail['소재지']}")

                else:

                    st.error("상세정보 없음")

            except Exception as e:

                st.error(f"오류 발생: {e}")


# ==========================================================
# Gemini 챗봇
# ==========================================================
elif menu == "Gemini 챗봇":

    st.subheader("🤖 Gemini 문화재 AI")

    q = st.text_area(
        "질문 입력",
        height=150
    )

    if st.button("질문하기"):

        if q.strip() == "":

            st.warning("질문을 입력하세요.")

        else:

            with st.spinner("Gemini AI 분석 중..."):

                try:

                    model = genai.GenerativeModel(
                        "gemini-2.0-flash"
                    )

                    prompt = f"""
                    너는 문화재 전문가이다.

                    전국 문화재 수:
                    {len(all_df)}

                    영천 문화재 수:
                    {len(df)}

                    영천 주요 문화재 종목:
                    {', '.join(df['국가유산종목'].dropna().unique()[:10])}

                    질문:
                    {q}

                    답변 조건:
                    - 고등학생 수준으로 쉽게 설명
                    - 발표용 스타일
                    - 핵심 요약 포함
                    """

                    response = model.generate_content(prompt)

                    st.success(response.text)

                except Exception as e:

                    st.error(f"Gemini 오류: {e}")

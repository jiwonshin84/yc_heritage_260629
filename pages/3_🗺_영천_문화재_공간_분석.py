import streamlit as st
import pandas as pd
import folium

from streamlit_folium import st_folium
from folium.plugins import HeatMap, MarkerCluster

# =================================================
# 페이지 설정
# =================================================

st.set_page_config(
    page_title="영천 문화재 공간분석",
    layout="wide"
)

st.title("🗺 영천 문화재 공간분석")

# =================================================
# 데이터 불러오기
# =================================================

df = pd.read_csv(
    "data/processed/yc_heritage_detail_enriched.csv"
)

# 위경도 결측 제거
df = df.dropna(subset=["위도", "경도"])

# =================================================
# 사이드바 필터
# =================================================

st.sidebar.header("🔎 문화재 필터")

era_list = ["전체"] + sorted(
    df["시대"].dropna().unique().tolist()
)

selected_era = st.sidebar.selectbox(
    "시대 선택",
    era_list
)

if selected_era != "전체":
    df = df[df["시대"] == selected_era]

# =================================================
# 지도 중심
# =================================================

center = [
    df["위도"].mean(),
    df["경도"].mean()
]

# =================================================
# 지도 생성
# =================================================

m = folium.Map(
    location=center,
    zoom_start=10,
    tiles="CartoDB positron"
)

# =================================================
# 마커 클러스터
# =================================================

marker_cluster = MarkerCluster().add_to(m)

# =================================================
# 마커 생성
# =================================================

for idx, row in df.iterrows():

    heritage_name = row.get(
        "문화재명(국문)",
        "문화재"
    )

    image_url = str(
        row.get("이미지URL", "")
    ).strip()

    # http → https 변환
    image_url = image_url.replace(
        "http://",
        "https://"
    )

    # =================================================
    # 이미지 HTML
    # =================================================

    if (
        image_url == ""
        or image_url.lower() == "nan"
    ):

        image_html = """
        <div style="
            width:240px;
            height:160px;
            background:#f2f2f2;
            border-radius:12px;
            display:flex;
            justify-content:center;
            align-items:center;
            color:#777;
            font-size:14px;
            margin-bottom:10px;
        ">
            등록된 이미지 없음
        </div>
        """

    else:

        image_html = f"""
        <a href="{image_url}" target="_blank">

            <img
                src="{image_url}"

                style="
                    width:240px;
                    height:160px;
                    object-fit:cover;
                    border-radius:12px;
                    margin-bottom:10px;
                    cursor:pointer;
                    box-shadow:0 2px 8px rgba(0,0,0,0.2);
                "

                onerror="
                    this.style.display='none';
                    this.parentNode.innerHTML=
                    '<div style=
                    \\'width:240px;
                    height:160px;
                    background:#f2f2f2;
                    border-radius:12px;
                    display:flex;
                    justify-content:center;
                    align-items:center;
                    color:#777;
                    font-size:14px;
                    \\'>

                    이미지 로드 실패

                    </div>';
                "
            >

        </a>
        """

    # =================================================
    # Popup HTML
    # =================================================

    popup_html = f"""
    <div style="
        width:260px;
        padding:10px;
        text-align:center;
        font-family:sans-serif;
    ">

        <h3 style="
            margin-bottom:10px;
            color:#222;
        ">
            {heritage_name}
        </h3>

        {image_html}

        <table style="
            width:100%;
            font-size:14px;
            line-height:1.8;
        ">

            <tr>
                <td><b>시대</b></td>
                <td>{row.get("시대", "-")}</td>
            </tr>

            <tr>
                <td><b>종목</b></td>
                <td>{row.get("국가유산종목", "-")}</td>
            </tr>

            <tr>
                <td><b>재질</b></td>
                <td>{row.get("재질", "-")}</td>
            </tr>

            <tr>
                <td><b>노출형태</b></td>
                <td>{row.get("노출형태", "-")}</td>
            </tr>

        </table>

        <br>

        <div style="
            font-size:13px;
            color:#666;
        ">
            이미지를 클릭하면 새 창에서 크게 볼 수 있습니다.
        </div>

    </div>
    """

    # =================================================
    # IFrame Popup
    # =================================================

    iframe = folium.IFrame(
        html=popup_html,
        width=330,
        height=450
    )

    popup = folium.Popup(
        iframe,
        max_width=410
    )

    # =================================================
    # Marker 추가
    # =================================================

    folium.Marker(
        location=[
            row["위도"],
            row["경도"]
        ],

        popup=popup,

        tooltip=heritage_name,

        icon=folium.Icon(
            color="red",
            icon="info-sign"
        )

    ).add_to(marker_cluster)

# =================================================
# HeatMap
# =================================================

heat_data = df[
    ["위도", "경도"]
].values.tolist()

HeatMap(
    heat_data,
    radius=20,
    blur=15
).add_to(m)

# =================================================
# 지도 출력
# =================================================

st_folium(
    m,
    width=1400,
    height=750
)

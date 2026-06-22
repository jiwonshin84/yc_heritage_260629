# ==========================================================
# 라이브러리
# ==========================================================
import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# ==========================================================
# 페이지 설정
# ==========================================================
st.set_page_config(
    page_title="공공 환경 데이터 기반 영천 지역 문화재 훼손 위험 예측",
    page_icon="🏛",
    layout="wide"
)


# ==========================================================
# API KEY
# ==========================================================
SERVICE_KEY = "feb2bfabd299d5d05e89c7aec49ba7e706112603e76549a92e868bd86ec60323"


# ==========================================================
# 공통 함수
# ==========================================================
def get_latest_base_time():
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    target = now.replace(minute=0, second=0, microsecond=0)

    # 초단기실황은 정시+40분 이후 공개
    if now.minute < 40:
        target -= timedelta(hours=1)

    api_date = target.strftime("%Y%m%d")
    api_time = target.strftime("%H00")
    display_date = target.strftime("%Y-%m-%d")

    return api_date, api_time, display_date


def degree_to_direction(deg):
    try:
        deg = float(deg)

        dirs = [
            "북", "북동", "동", "남동",
            "남", "남서", "서", "북서"
        ]

        return dirs[round(deg / 45) % 8]

    except:
        return "-"


# ==========================================================
# CSV 데이터 불러오기
# ==========================================================
@st.cache_data
def load_heritage_data():
    return pd.read_csv("data/processed/yc_heritage_detail_enriched.csv")


try:
    df = load_heritage_data()

except Exception as e:
    df = pd.DataFrame()
    st.error("문화재 데이터 파일을 불러오지 못했습니다.")
    st.caption(str(e))


# ==========================================================
# 기상청 초단기실황 API
# ==========================================================
@st.cache_data(ttl=600)
def get_weather_data():
    ULTRA_URL = (
        "https://apis.data.go.kr/"
        "1360000/VilageFcstInfoService_2.0/"
        "getUltraSrtNcst"
    )

    NX = "92"
    NY = "106"

    api_date, api_time, display_date = get_latest_base_time()

    tm = f"{display_date} {api_time[:2]}:00"

    result = {
        "tm": tm,
        "temp": "-",
        "humidity": "-",
        "rainfall": "-",
        "wind_speed": "-",
        "rain_type": "-",
        "wind_dir": "-"
    }

    try:
        params = {
            "serviceKey": SERVICE_KEY,
            "pageNo": "1",
            "numOfRows": "1000",
            "dataType": "JSON",
            "base_date": api_date,
            "base_time": api_time,
            "nx": NX,
            "ny": NY
        }

        response = requests.get(
            ULTRA_URL,
            params=params,
            timeout=5
        )

        data = response.json()

        items = data["response"]["body"]["items"]["item"]

        rain_map = {
            "0": "없음",
            "1": "비",
            "2": "비/눈",
            "3": "눈",
            "5": "빗방울",
            "6": "빗방울눈날림",
            "7": "눈날림"
        }

        for item in items:
            category = item["category"]
            value = item["obsrValue"]

            if category == "T1H":
                result["temp"] = value

            elif category == "REH":
                result["humidity"] = value

            elif category == "RN1":
                result["rainfall"] = value

            elif category == "WSD":
                result["wind_speed"] = value

            elif category == "VEC":
                result["wind_dir"] = degree_to_direction(value)

            elif category == "PTY":
                result["rain_type"] = rain_map.get(str(value), str(value))

    except Exception:
        pass

    return result


# ==========================================================
# 대기오염 API
# ==========================================================
@st.cache_data(ttl=600)
def get_air_data():
    AIR_URL = (
        "https://apis.data.go.kr/"
        "B552584/ArpltnInforInqireSvc/"
        "getCtprvnRltmMesureDnsty"
    )

    result = {
        "pm10": "-",
        "pm25": "-",
        "o3": "-",
        "no2": "-",
        "co": "-",
        "so2": "-",
        "data_time": "-"
    }

    try:
        params = {
            "serviceKey": SERVICE_KEY,
            "returnType": "json",
            "numOfRows": "100",
            "pageNo": "1",
            "sidoName": "경북",
            "ver": "1.0"
        }

        response = requests.get(
            AIR_URL,
            params=params,
            timeout=5
        )

        air_data = response.json()

        items = air_data["response"]["body"]["items"]

        target = None

        for item in items:
            if "영천" in item.get("stationName", ""):
                target = item
                break

        if target:
            result["data_time"] = target.get("dataTime", "-")
            result["pm10"] = target.get("pm10Value", "-")
            result["pm25"] = target.get("pm25Value", "-")
            result["o3"] = target.get("o3Value", "-")
            result["no2"] = target.get("no2Value", "-")
            result["co"] = target.get("coValue", "-")
            result["so2"] = target.get("so2Value", "-")

    except Exception:
        pass

    return result


# ==========================================================
# API 데이터 호출
# ==========================================================
weather = get_weather_data()
air = get_air_data()

tm = weather["tm"]
temp = weather["temp"]
humidity = weather["humidity"]
rainfall = weather["rainfall"]
wind_speed = weather["wind_speed"]

pm10 = air["pm10"]
pm25 = air["pm25"]
o3 = air["o3"]
no2 = air["no2"]
co = air["co"]
so2 = air["so2"]
data_time = air["data_time"]


# ==========================================================
# 제목
# ==========================================================
st.markdown("""
<h1 style='font-size:30px;'>
🏛 공공 환경 데이터 기반 영천 지역 문화재 훼손 위험 예측
</h1>
""", unsafe_allow_html=True)

st.markdown("""
영천 지역 문화재와 공공 환경데이터를 분석하여 문화재 훼손 위험을 사전에 예측하는 데이터 분석 프로젝트입니다.
""")

st.divider()


# ==========================================================
# 상단 환경 대시보드
# ==========================================================
st.markdown("""
<h3 style="
    font-size:25px;
    margin-bottom:10px;
">
🌿 영천시 환경 데이터 및 문화재 현황
</h3>
""", unsafe_allow_html=True)

left, center, right = st.columns([1.4, 2.0, 1.0])


# ==========================================================
# 공통 스타일
# ==========================================================
card_style = """
background-color:#f8f9fa;
padding:22px;
border-radius:20px;
border:1px solid #e5e7eb;
box-shadow:0 4px 12px rgba(0,0,0,0.05);
height:350px;
"""

title_style = """
font-size:24px;
font-weight:700;
margin-bottom:14px;
color:#1f2937;
"""

label_style = """
font-size:14px;
color:#6b7280;
margin-bottom:4px;
"""

value_style = """
font-size:22px;
font-weight:700;
color:#111827;
margin-bottom:18px;
"""

time_style = """
font-size:13px;
color:#9ca3af;
margin-top:12px;
position:absolute;
bottom:20px;
"""


# ==========================================================
# 1열 : 기상 환경
# ==========================================================
with left:
    st.markdown(
        f"""
<div style="{card_style}; position:relative;">

<div style="{title_style}">
🌦 기상 환경
</div>

<hr>

<div style="
display:grid;
grid-template-columns:1fr 1fr;
gap:16px;
margin-top:20px;
">

<div>
<div style="{label_style}">🌡 기온</div>
<div style="{value_style}">{temp} °C</div>
</div>

<div>
<div style="{label_style}">💧 습도</div>
<div style="{value_style}">{humidity} %</div>
</div>

<div>
<div style="{label_style}">🌧 강수량</div>
<div style="{value_style}">{rainfall} mm</div>
</div>

<div>
<div style="{label_style}">💨 풍속</div>
<div style="{value_style}">{wind_speed} m/s</div>
</div>

</div>

<div style="{time_style}">
⏱ 측정 시각 : {tm}
</div>

</div>
        """,
        unsafe_allow_html=True
    )


# ==========================================================
# 2열 : 대기오염 현황
# ==========================================================
with center:
    st.markdown(
        f"""
<div style="{card_style}; position:relative;">

<div style="{title_style}">
🌫 대기오염 현황
</div>

<hr>

<div style="
display:grid;
grid-template-columns:1fr 1fr 1fr;
gap:20px;
margin-top:20px;
">

<div>
<div style="{label_style}">PM10</div>
<div style="{value_style}">{pm10}</div>

<div style="{label_style}">O₃</div>
<div style="{value_style}">{o3}</div>
</div>

<div>
<div style="{label_style}">PM2.5</div>
<div style="{value_style}">{pm25}</div>

<div style="{label_style}">NO₂</div>
<div style="{value_style}">{no2}</div>
</div>

<div>
<div style="{label_style}">CO</div>
<div style="{value_style}">{co}</div>

<div style="{label_style}">SO₂</div>
<div style="{value_style}">{so2}</div>
</div>

</div>

<div style="{time_style}">
⏱ 측정 시각 : {data_time}
</div>

</div>
        """,
        unsafe_allow_html=True
    )


# ==========================================================
# 3열 : 문화재 현황
# ==========================================================
with right:
    st.markdown(
        f"""
<div style="{card_style}; position:relative;">

<div style="{title_style}">
🏛 문화재 현황
</div>

<hr>

<div style="margin-top:20px;">

<div style="{label_style}">
분석 문화재 수
</div>

<div style="{value_style}">
{len(df)}개
</div>

<br>

<div style="{label_style}">
데이터 기준
</div>

<div style="{value_style}">
영천
</div>

</div>

</div>
        """,
        unsafe_allow_html=True
    )


st.divider()

st.caption(
    "제6회 학생 SW·AI 인재양성 프로젝트 | 선화여고 - 영천 헤리티지 AI 탐구단"
)

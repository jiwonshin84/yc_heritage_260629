# ==========================================================
# 라이브러리
# ==========================================================
import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# ============================================
# API KEY
# ============================================

SERVICE_KEY = "feb2bfabd299d5d05e89c7aec49ba7e706112603e76549a92e868bd86ec60323"

# ============================================
# 1. 기상청 ASOS 전날 최신 기상자료
# ============================================

ASOS_URL = (
    "https://apis.data.go.kr/"
    "1360000/AsosHourlyInfoService/getWthrDataList"
)

# 영천 관측소
STN_ID = "281"

# 한국시간
now = datetime.now(ZoneInfo("Asia/Seoul"))

# 전날
yesterday = now - timedelta(days=1)

base_date = yesterday.strftime("%Y%m%d")
base_hour = "23"

print("현재 한국시간:", now)
print("조회 날짜:", base_date)
print("조회 시간:", base_hour)

# ============================================
# ASOS 요청 파라미터
# ============================================

asos_params = {
    "serviceKey": SERVICE_KEY,
    "pageNo": "1",
    "numOfRows": "1",
    "dataType": "JSON",

    "dataCd": "ASOS",
    "dateCd": "HR",

    # 전날 23시 데이터
    "startDt": base_date,
    "startHh": base_hour,

    "endDt": base_date,
    "endHh": base_hour,

    # 영천 관측소
    "stnIds": STN_ID
}

# ============================================
# 기본값
# ============================================

tm = "-"

temp = "-"
humidity = "-"

rainfall = "-"
wind_speed = "-"

# ============================================
# ASOS API 요청
# ============================================

try:

    response = requests.get(
        ASOS_URL,
        params=asos_params,
        timeout=30
    )

    print("ASOS 응답코드:", response.status_code)

    data = response.json()

    print(data)

    item = data["response"]["body"]["items"]["item"][0]

    # 관측 시각
    tm = item["tm"]

    # 기온
    temp = item["ta"]

    # 습도
    humidity = item["hm"]

    # 강수량
    rainfall = item["rn"]

    # 풍속
    wind_speed = item["ws"]

    print()
    print("===== 전날 최신 기상 데이터 =====")
    print("관측시각:", tm)

    print("기온:", temp, "°C")
    print("습도:", humidity, "%")

    print("강수량:", rainfall, "mm")
    print("풍속:", wind_speed, "m/s")

except Exception as e:

    print("기상 데이터 조회 실패")
    print(e)

# ============================================
# 2. 대기오염 최신 데이터
# ============================================

AIR_URL = (
    "https://apis.data.go.kr/"
    "B552584/ArpltnInforInqireSvc/"
    "getCtprvnRltmMesureDnsty"
)

# 기본값
pm10 = "-"
pm25 = "-"

o3 = "-"
no2 = "-"

co = "-"
so2 = "-"

data_time = "-"

# ============================================
# 대기오염 API 요청
# ============================================

try:

    air_params = {
        "serviceKey": SERVICE_KEY,
        "returnType": "json",

        "numOfRows": "100",
        "pageNo": "1",

        # 경북
        "sidoName": "경북",

        "ver": "1.0"
    }

    air_response = requests.get(
        AIR_URL,
        params=air_params,
        timeout=30
    )

    print("대기오염 응답코드:", air_response.status_code)

    air_data = air_response.json()

    print(air_data)

    items = air_data["response"]["body"]["items"]

    # 영천 측정소 찾기
    target = None

    for item in items:

        if "영천" in item["stationName"]:
            target = item
            break

    if target:

        data_time = target["dataTime"]

        pm10 = target["pm10Value"]
        pm25 = target["pm25Value"]

        o3 = target["o3Value"]
        no2 = target["no2Value"]

        co = target["coValue"]
        so2 = target["so2Value"]

        print()
        print("===== 최신 대기오염 데이터 =====")

        print("측정시각:", data_time)

        print("PM10:", pm10)
        print("PM2.5:", pm25)

        print("O3:", o3)
        print("NO2:", no2)

        print("CO:", co)
        print("SO2:", so2)

except Exception as e:

    print("대기오염 데이터 조회 실패")
    print(e)


# ==========================================================
# 페이지 설정
# ==========================================================
st.set_page_config(
    page_title="공공 환경 데이터 기반 영천 지역 문화재 훼손 위험 예측",
    page_icon="🏛",
    layout="wide"
)

# ==========================================================
# 데이터 불러오기
# ==========================================================
df = pd.read_csv(
    "data/processed/yc_heritage_detail_enriched.csv"
)

# ==========================================================
# 제목
# ==========================================================
st.title("🏛 공공 환경 데이터 기반 영천 지역 문화재 훼손 위험 예측")

st.markdown("""

##영천 지역 문화재와 공공 환경데이터를 분석하여 
##문화재 훼손 위험을 사전에 예측하는 
##데이터 분석 프로젝트 입니다.
""")

st.divider()


# ============================================
# 상단 환경 대시보드
# ============================================

st.subheader("🌿 영천 문화재 보존 환경 현황")

# 메인 영역
left, center, right = st.columns([1.4, 2.0, 1.0])

# ============================================
# 공통 스타일
# ============================================

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

# ============================================
# 1열 : 기상 환경
# ============================================

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

# ============================================
# 2열 : 대기오염 현황
# ============================================

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

# ============================================
# 3열 : 문화재 현황
# ============================================

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
⚠ 고위험 문화재
</div>

<div style="{value_style}">
18개
</div>

</div>

<div>
- 
</div>
                    
</div>
        """,
        unsafe_allow_html=True
    )

st.divider()

# ==========================================================
# 연구 배경
# ==========================================================
st.subheader("📖 연구 배경")

st.markdown("""
영천 지역에는 은해사, 임고서원 등 역사적·예술적·종교적 가치를 지닌 다양한 문화재가 존재합니다. 

그러나 문화재는 습도 및 온도 변화, 미세먼지 및 대기오염, 강수량 및 기후 변화, 관광객 및 인간 활동 등 다양한 환경 요인에 의해 지속적으로 훼손 위험에 노출되어 있습니다. 

현재 문화재 관리는 대부분 훼손 이후 보수·복원 중심으로 이루어지고 있어, 사전에 위험을 예측하고 예방할 수 있는 데이터 기반 관리 방식의 필요성이 커지고 있습니다.
""")

st.divider()


# ==========================================================
# 핵심 연구 내용
# ==========================================================
st.subheader("🎯 핵심 연구 내용")

col1, col2 = st.columns(2)

with col1:

    st.markdown("""
    ### 📊 데이터 기반 분석

    - 영천 지역 문화재 데이터 수집
    - 기상 및 환경 공공데이터 분석
    - 문화재 환경 특성 데이터셋 구축
    - 문화재 공간정보 시각화
    """)

with col2:

    st.markdown("""
    ### 🤖 데이터 기반 예측

    - 군집분석 수행
    - 문화재 훼손 위험 예측 모델 개발
    - 데이터 기반 문화재 관리 방안 제시
    - 예방 중심 문화재 관리 가능성 탐색
    """)

st.divider()


# ==========================================================
# AI 분석 프로세스
# ==========================================================
st.subheader("🧠 공공데이터 기반 문화재 위험 분석 프로세스")

# ----------------------------------------------------------
# STEP 1
# ----------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)

with c1:

    st.info("""
    ### 📚 데이터 수집

    - 문화재청 국가유산 데이터
    - 기상청 환경 데이터
    - 미세먼지 공공데이터
    - 문화재 재질 데이터
    """)

with c2:

    st.warning("""
    ### ⚙ 데이터 전처리

    - 결측치 처리
    - 좌표 보완
    - 특징 추출
    - 환경 데이터 결합
    """)

with c3:

    st.success("""
    ### 🤖 AI 분석

    - 군집분석(KMeans)
    - 환경 특성 분석
    - 위험 패턴 탐색
    - 변수 중요도 분석
    """)

with c4:

    st.error("""
    ### ⚠ 위험 예측

    - 훼손 위험도 계산
    - 고위험 문화재 탐지
    - 위험 등급 분류
    - 예방 관리 방안 제시
    """)

st.divider()

# ==========================================================
# 활용 기술
# ==========================================================
st.subheader("💻 활용 기술")

c1, c2, c3, c4 = st.columns(4)

# ----------------------------------------------------------
# 데이터 분석
# ----------------------------------------------------------
with c1:

    st.info("""
    ### 📊 데이터 분석

    - Pandas
    - Numpy
    - Plotly
    - 데이터 전처리
    """)

# ----------------------------------------------------------
# 머신러닝
# ----------------------------------------------------------
with c2:

    st.success("""
    ### 🤖 머신러닝

    - Scikit-learn
    - KMeans
    - Random Forest
    - 위험도 예측
    """)

# ----------------------------------------------------------
# 공간 시각화
# ----------------------------------------------------------
with c3:

    st.warning("""
    ### 🗺 공간 시각화

    - Folium
    - HeatMap
    - GIS 분석
    - 위치 기반 분석
    """)

# ----------------------------------------------------------
# 생성형 AI
# ----------------------------------------------------------
with c4:

    st.error("""
    ### 🧠 생성형 AI

    - Gemini AI
    - 문화재 해설
    - AI 요약
    - 보고서 생성
    """)





st.divider()

# ==========================================================
# 기대 효과
# ==========================================================
st.subheader("🌟 기대 효과")

col1, col2 = st.columns(2)

with col1:

    st.markdown("""
    ### 📊 데이터 기반 문화재 보존 관리

    - 문화재 훼손 위험 사전 예측
    - 환경 영향 주요 변수 분석
    - 문화재 보존 우선순위 선정
    - 예방 중심 문화재 관리 가능성 제시
    """)

with col2:

    st.markdown("""
    ### 🤖 교육 및 연구 확장

    - 공공데이터 활용 역량 강화
    - 데이터 기반 문제 해결 능력 향상
    - AI·데이터 과학 실전 프로젝트 수행
    - 향후 IoT 기반 실시간 예측 시스템 확장 가능
    """)


st.divider()


# ==========================================================
# 활용 데이터
# ==========================================================
st.subheader("🗂 활용 데이터")

st.markdown("""
- 국가유산포털 전국 국가유산 기본 데이터
- 국가유산포털 영천 지역 국가유산 상세 정보 데이터
- 카카오 지도 API 활용 영천 지역 국가유산 좌표 보완 데이터
- 기상청 온도·습도·강수량 환경 데이터
- 에어코리아 미세먼지 환경 데이터
- AI 기반 문화재 환경위험 군집분석 데이터
""")

st.divider()

# ==========================================================
# 하단 안내
# ==========================================================
st.caption(
    "제6회 학생 SW·AI 인재양성 프로젝트 | 영천 헤리티지 AI 탐구단"
)

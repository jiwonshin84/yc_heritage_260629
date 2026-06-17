import streamlit as st
import requests
import pandas as pd


# ========================================
# 페이지 설정
# ========================================

st.set_page_config(
    page_title="문화재 환경 모니터링",
    page_icon="🏛️",
    layout="wide"
)

if st.button("🔄 최신 데이터 새로고침"):
    st.rerun()
    
# ========================================
# Firebase URL
# ========================================

FIREBASE_URL = (
    "https://heritage-project-4a361-default-rtdb.asia-southeast1.firebasedatabase.app/sensor.json"
)

# ========================================
# 데이터 읽기
# ========================================

try:

    response = requests.get(FIREBASE_URL, timeout=10)

    if response.status_code == 200:
        data = response.json()
    else:
        st.error(f"Firebase 오류 : {response.status_code}")
        st.stop()

except Exception as e:
    st.error(f"데이터 연결 실패 : {e}")
    st.stop()

# ========================================
# 값 추출
# ========================================

temp = data.get("temperature", "-")
hum = data.get("humidity", "-")
light = data.get("light_percent", "-")
dust = data.get("dust_percent", "-")
timestamp = data.get("timestamp", "-")
device = data.get("device", "-")

# ========================================
# 제목
# ========================================

st.title("🏛️ 문화재 실시간 환경 모니터링")

st.caption(f"마지막 측정 : {timestamp}")

# ========================================
# 실시간 센서값
# ========================================

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "🌡️ 기온",
        f"{temp} ℃"
    )

with col2:
    st.metric(
        "💧 습도",
        f"{hum} %"
    )

with col3:
    st.metric(
        "☀️ 조도",
        f"{light} %"
    )

with col4:
    st.metric(
        "🌫️ 먼지",
        f"{dust} %"
    )

# ========================================
# 위험도 계산
# ========================================

risk = 0

if temp >= 30:
    risk += 30

if hum >= 70:
    risk += 30

if dust >= 50:
    risk += 40

if risk < 30:
    risk_text = "🟢 안전"

elif risk < 60:
    risk_text = "🟡 주의"

else:
    risk_text = "🔴 위험"

st.divider()

st.subheader("문화재 환경 위험도")

st.progress(min(risk, 100))

st.markdown(
    f"### {risk_text} ({risk}점)"
)

# ========================================
# 상세 정보
# ========================================

st.divider()

info = pd.DataFrame(
    {
        "항목": [
            "측정시각",
            "기온",
            "습도",
            "조도",
            "미세먼지",
            "장치명"
        ],
        "값": [
            timestamp,
            f"{temp}℃",
            f"{hum}%",
            f"{light}%",
            f"{dust}%",
            device
        ]
    }
)

st.dataframe(
    info,
    use_container_width=True,
    hide_index=True
)

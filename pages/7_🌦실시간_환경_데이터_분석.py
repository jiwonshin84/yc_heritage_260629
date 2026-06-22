import streamlit as st
import requests
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# ========================================
# 페이지 설정
# ========================================

st.set_page_config(
    page_title="문화재 환경 모니터링",
    page_icon="🏛️",
    layout="wide"
)

# 20초마다 자동 새로고침
st_autorefresh(
    interval=20 * 1000,
    key="sensor_refresh"
)

# ========================================
# Firebase URL
# ========================================

FIREBASE_URL = "https://heritage-project-4a361-default-rtdb.asia-southeast1.firebasedatabase.app/sensor/realtime.json"

# ========================================
# 자동 확인용 HTML
# 10초마다 Firebase 확인을 위해 페이지 재실행
# ========================================

#st.markdown(
#    """
#    <meta http-equiv="refresh" content="10">
#    """,
#    unsafe_allow_html=True
#)

# ========================================
# 값 변환 함수
# ========================================

def to_float(value):
    try:
        return float(value)
    except:
        return 0.0

# ========================================
# Firebase 데이터 읽기
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

if data is None:
    st.warning("Firebase에 저장된 데이터가 없습니다.")
    st.stop()


# ========================================
# 값 추출
# ========================================

temp = to_float(data.get("temperature", 0))
hum = to_float(data.get("humidity", 0))
light = to_float(data.get("light_percent", 0))

pm1 = to_float(data.get("pm1", 0))
pm25 = to_float(data.get("pm25", 0))
pm10 = to_float(data.get("pm10", 0))

timestamp = data.get("timestamp", "-")
device = data.get("device", "-")

# ========================================
# 마지막 timestamp 비교
# ========================================

if "last_timestamp" not in st.session_state:
    st.session_state.last_timestamp = timestamp

is_new_data = timestamp != st.session_state.last_timestamp

if is_new_data:
    st.session_state.last_timestamp = timestamp

# ========================================
# 제목
# ========================================

st.title("🏛️ 문화재 실시간 환경 모니터링")

if is_new_data:
    st.toast("🆕 새로운 센서 데이터 수신")


st.caption(f"마지막 측정 : {timestamp}")
st.caption(f"측정 장치 : {device}")

# ========================================
# 실시간 센서값
# ========================================

# 첫 번째 줄
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("🌡️ 기온", f"{temp:.1f} ℃")

with col2:
    st.metric("💧 습도", f"{hum:.1f} %")

with col3:
    st.metric("☀️ 조도", f"{light:.1f} %")


# 두 번째 줄
col4, col5, col6 = st.columns(3)

with col4:
    st.metric("🌫️ PM1.0", f"{pm1:.1f} ㎍/㎥")

with col5:
    st.metric("🌫️ PM2.5", f"{pm25:.1f} ㎍/㎥")

with col6:
    st.metric("🌫️ PM10", f"{pm10:.1f} ㎍/㎥")

# ========================================
# 위험도 계산
# ========================================

risk = 0

if temp >= 30:
    risk += 30

if hum >= 70:
    risk += 30

if pm25 >= 50:
    risk += 40

risk = min(risk, 100)

if risk < 30:
    risk_text = "🟢 안전"

elif risk < 60:
    risk_text = "🟡 주의"

else:
    risk_text = "🔴 위험"

# ========================================
# 수동 새로고침 버튼
# ========================================

if st.button("🔄 수동 최신 데이터 새로고침"):
    st.rerun()

# ========================================
# 위험도 표시
# ========================================

st.divider()

st.subheader("문화재 환경 위험도")

st.progress(risk)

st.markdown(f"### {risk_text} ({risk}점)")

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
            "PM1.0",
            "PM2.5",
            "PM10",
            "장치명"
        ],
        "값": [
            timestamp,
            f"{temp:.1f}℃",
            f"{hum:.1f}%",
            f"{light:.1f}%",
            f"{pm1:.1f} ㎍/㎥",
            f"{pm25:.1f} ㎍/㎥",
            f"{pm10:.1f} ㎍/㎥",
            device
        ]
    }
)

st.dataframe(
    info,
    use_container_width=True,
    hide_index=True
)

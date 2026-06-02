```python
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from streamlit_autorefresh import st_autorefresh

# ==========================================================
# 페이지 설정
# ==========================================================
st.set_page_config(
    page_title="문화유산 실시간 환경 모니터링",
    page_icon="🏛",
    layout="wide"
)

# ==========================================================
# 자동 새로고침 (1분)
# ==========================================================
st_autorefresh(
    interval=60000,
    key="refresh"
)

# ==========================================================
# Google Sheet 연결
# ==========================================================
@st.cache_data(ttl=60)
def load_data():

    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp_service_account"],
        scope
    )

    client = gspread.authorize(creds)

    sheet = client.open_by_key(
        "15l2uXRqMwbl-YpghI6Gw_hf0Kr2bBuu7Pz4jyDZov7I"
    )

    worksheet = sheet.sheet1

    data = worksheet.get_all_records()

    df = pd.DataFrame(data)

    return df


# ==========================================================
# 데이터 불러오기
# ==========================================================
df = load_data()

if df.empty:
    st.error("데이터가 없습니다.")
    st.stop()

# ==========================================================
# 데이터 전처리
# ==========================================================
df["Timestamp"] = pd.to_datetime(df["Timestamp"])

latest = df.iloc[-1]

timestamp = latest["Timestamp"]
temp = latest["Temperature"]
humid = latest["Humidity"]

try:
    light = latest["Light"]
except:
    light = 0

# ==========================================================
# 위험도 계산
# ==========================================================
risk = 0

# 온도
if temp >= 35:
    risk += 30
elif temp >= 30:
    risk += 20
elif temp >= 25:
    risk += 10

# 습도
if humid >= 80:
    risk += 50
elif humid >= 70:
    risk += 30
elif humid >= 60:
    risk += 15

# 조도
if pd.notna(light):

    if light >= 500:
        risk += 20

    elif light >= 200:
        risk += 10

risk = min(risk, 100)

# ==========================================================
# 위험도 등급
# ==========================================================
if risk < 25:
    level = "🟢 안전"

elif risk < 50:
    level = "🟡 주의"

elif risk < 75:
    level = "🟠 위험"

else:
    level = "🔴 매우 위험"

# ==========================================================
# 제목
# ==========================================================
st.title("🏛 문화유산 실시간 환경 모니터링")

st.caption(
    f"최근 측정 시각 : {timestamp}"
)

# ==========================================================
# 실시간 센서 현황
# ==========================================================
st.subheader("📡 실시간 센서 데이터")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "🌡 기온",
        f"{temp} ℃"
    )

with col2:
    st.metric(
        "💧 습도",
        f"{humid} %"
    )

with col3:
    st.metric(
        "💡 조도",
        f"{light}"
    )

with col4:
    st.metric(
        "⚠ 위험도",
        f"{risk}/100"
    )

st.success(f"현재 상태 : {level}")

# ==========================================================
# 그래프
# ==========================================================
st.markdown("---")

tab1, tab2, tab3 = st.tabs([
    "기온",
    "습도",
    "조도"
])

with tab1:

    st.subheader("🌡 기온 변화")

    st.line_chart(
        df.set_index("Timestamp")["Temperature"]
    )

with tab2:

    st.subheader("💧 습도 변화")

    st.line_chart(
        df.set_index("Timestamp")["Humidity"]
    )

with tab3:

    if "Light" in df.columns:

        st.subheader("💡 조도 변화")

        st.line_chart(
            df.set_index("Timestamp")["Light"]
        )

# ==========================================================
# 최근 데이터
# ==========================================================
st.markdown("---")

st.subheader("📋 최근 측정 데이터")

show_df = df.sort_values(
    "Timestamp",
    ascending=False
).head(20)

st.dataframe(
    show_df,
    use_container_width=True
)

# ==========================================================
# 위험도 설명
# ==========================================================
with st.expander("위험도 산정 기준"):

    st.markdown("""
    ### 🌡 온도

    - 25℃ 이상 : +10점
    - 30℃ 이상 : +20점
    - 35℃ 이상 : +30점

    ### 💧 습도

    - 60% 이상 : +15점
    - 70% 이상 : +30점
    - 80% 이상 : +50점

    ### 💡 조도

    - 200 이상 : +10점
    - 500 이상 : +20점

    ### 등급

    - 0~24 : 안전
    - 25~49 : 주의
    - 50~74 : 위험
    - 75~100 : 매우 위험
    """)
```

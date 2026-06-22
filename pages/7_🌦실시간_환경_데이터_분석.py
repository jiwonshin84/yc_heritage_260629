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

# 5초마다 화면 확인
# Pico는 20초마다 보내고, Streamlit은 5초마다 확인
st_autorefresh(
    interval=5 * 1000,
    key="sensor_refresh"
)

# ========================================
# Firebase URL
# ========================================

FIREBASE_REALTIME_URL = "https://heritage-project-4a361-default-rtdb.asia-southeast1.firebasedatabase.app/sensor/realtime.json"
FIREBASE_HISTORY_URL = "https://heritage-project-4a361-default-rtdb.asia-southeast1.firebasedatabase.app/sensor/history.json"

# ========================================
# 값 변환 함수
# ========================================

def to_float(value):
    try:
        return float(value)
    except:
        return 0.0


# ========================================
# Firebase 최신 데이터 읽기
# ========================================

try:
    response = requests.get(FIREBASE_REALTIME_URL, timeout=10)

    if response.status_code == 200:
        data = response.json()
    else:
        st.error(f"Firebase 오류 : {response.status_code}")
        st.stop()

except Exception as e:
    st.error(f"데이터 연결 실패 : {e}")
    st.stop()

if data is None:
    st.warning("Firebase에 저장된 최신 데이터가 없습니다.")
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

st.title("🏛️ 문화재 실시간 환경 모니터링(20초 마다 센서 측정)")

if is_new_data:
    st.toast("🆕 새로운 센서 데이터 수신")

st.caption(f"마지막 측정 : {timestamp}")
st.caption(f"측정 장치 : {device}")


# ========================================
# 실시간 센서값
# ========================================

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("🌡️ 기온", f"{temp:.1f} ℃")

with col2:
    st.metric("💧 습도", f"{hum:.1f} %")

with col3:
    st.metric("☀️ 조도", f"{light:.1f} %")

col4, col5, col6 = st.columns(3)

with col4:
    st.metric("🌫️ PM1.0", f"{pm1:.1f} ㎍/㎥")

with col5:
    st.metric("🌫️ PM2.5", f"{pm25:.1f} ㎍/㎥")

with col6:
    st.metric("🌫️ PM10", f"{pm10:.1f} ㎍/㎥")


# ========================================
# 수동 새로고침 버튼
# ========================================

if st.button("🔄 수동 최신 데이터 새로고침"):
    st.rerun()

st.divider()


# ========================================
# 센서 데이터 이력 통계
# ========================================

st.subheader("📊 센서 데이터 이력 통계(5분 간격 측정)")


@st.cache_data(ttl=20)
def load_history_data():
    try:
        response = requests.get(FIREBASE_HISTORY_URL, timeout=10)

        if response.status_code != 200:
            return pd.DataFrame()

        history_data = response.json()

        if history_data is None:
            return pd.DataFrame()

        df = pd.DataFrame(history_data).T
        df.reset_index(drop=True, inplace=True)

        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(
                df["timestamp"],
                errors="coerce"
            )

        numeric_cols = [
            "temperature",
            "humidity",
            "light_percent",
            "pm1",
            "pm25",
            "pm10"
        ]

        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(
                    df[col],
                    errors="coerce"
                )

        df = df.dropna(subset=["timestamp"])
        df = df.sort_values("timestamp")

        return df

    except:
        return pd.DataFrame()


history_df = load_history_data()

if history_df.empty:
    st.info("아직 sensor/history에 누적된 데이터가 없습니다.")

else:
    st.caption(f"전체 누적 데이터 수 : {len(history_df)}개")

    # 날짜 컬럼 생성
    history_df["date"] = history_df["timestamp"].dt.date

    min_date = history_df["date"].min()
    max_date = history_df["date"].max()

    # ========================================
    # 기간 선택
    # ========================================

    st.markdown("#### 📅 조회 기간 선택")

    date_col1, date_col2 = st.columns(2)

    with date_col1:
        start_date = st.date_input(
            "시작 날짜",
            value=min_date,
            min_value=min_date,
            max_value=max_date
        )

    with date_col2:
        end_date = st.date_input(
            "종료 날짜",
            value=max_date,
            min_value=min_date,
            max_value=max_date
        )

    if start_date > end_date:
        st.error("시작 날짜가 종료 날짜보다 늦을 수 없습니다.")
        st.stop()

    filtered_df = history_df[
        (history_df["date"] >= start_date)
        &
        (history_df["date"] <= end_date)
    ]

    if filtered_df.empty:
        st.warning("선택한 기간에 해당하는 데이터가 없습니다.")
        st.stop()

    st.caption(
        f"선택 기간 데이터 수 : {len(filtered_df)}개 "
        f"({start_date} ~ {end_date})"
    )

    # ========================================
    # 선택 기간 통계 카드
    # ========================================

    st.markdown("#### 선택 기간 평균값")

    stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)

    with stat_col1:
        st.metric(
            "평균 기온",
            f"{filtered_df['temperature'].mean():.1f} ℃"
        )

    with stat_col2:
        st.metric(
            "평균 습도",
            f"{filtered_df['humidity'].mean():.1f} %"
        )

    with stat_col3:
        st.metric(
            "평균 조도",
            f"{filtered_df['light_percent'].mean():.1f} %"
        )

    with stat_col4:
        st.metric(
            "평균 PM2.5",
            f"{filtered_df['pm25'].mean():.1f} ㎍/㎥"
        )

    # ========================================
    # 최대 / 최소 요약
    # ========================================

    st.markdown("#### 선택 기간 최대·최소값")

    max_col1, max_col2, max_col3, max_col4 = st.columns(4)

    with max_col1:
        st.metric(
            "최고 기온",
            f"{filtered_df['temperature'].max():.1f} ℃"
        )

    with max_col2:
        st.metric(
            "최고 습도",
            f"{filtered_df['humidity'].max():.1f} %"
        )

    with max_col3:
        st.metric(
            "최고 PM2.5",
            f"{filtered_df['pm25'].max():.1f} ㎍/㎥"
        )

    with max_col4:
        st.metric(
            "최고 PM10",
            f"{filtered_df['pm10'].max():.1f} ㎍/㎥"
        )

    # ========================================
    # 그래프 선택
    # ========================================

    st.markdown("#### 선택 기간 데이터 변화")

    selected_cols = st.multiselect(
        "그래프로 표시할 항목",
        [
            "temperature",
            "humidity",
            "light_percent",
            "pm1",
            "pm25",
            "pm10"
        ],
        default=[
            "temperature",
            "humidity",
            "pm25"
        ]
    )

    if selected_cols:
        st.line_chart(
            filtered_df,
            x="timestamp",
            y=selected_cols
        )

    # ========================================
    # 미세먼지 변화 그래프
    # ========================================

    st.markdown("#### 미세먼지 변화")

    st.line_chart(
        filtered_df,
        x="timestamp",
        y=[
            "pm1",
            "pm25",
            "pm10"
        ]
    )

    # ========================================
    # 항목별 기초 통계
    # ========================================

    st.markdown("#### 항목별 기초 통계")

    stats_cols = [
        "temperature",
        "humidity",
        "light_percent",
        "pm1",
        "pm25",
        "pm10"
    ]

    stats = filtered_df[stats_cols].describe().T

    stats = stats[
        [
            "count",
            "mean",
            "min",
            "max"
        ]
    ]

    stats.columns = [
        "개수",
        "평균",
        "최솟값",
        "최댓값"
    ]

    st.dataframe(
        stats,
        use_container_width=True
    )

    # ========================================
    # 일별 평균 그래프
    # ========================================

    st.markdown("#### 일별 평균 변화")

    daily_df = (
        filtered_df
        .groupby("date")[
            [
                "temperature",
                "humidity",
                "light_percent",
                "pm1",
                "pm25",
                "pm10"
            ]
        ]
        .mean()
        .reset_index()
    )

    daily_selected_cols = st.multiselect(
        "일별 평균으로 표시할 항목",
        [
            "temperature",
            "humidity",
            "light_percent",
            "pm1",
            "pm25",
            "pm10"
        ],
        default=[
            "temperature",
            "humidity",
            "pm25"
        ],
        key="daily_chart_select"
    )

    if daily_selected_cols:
        st.line_chart(
            daily_df,
            x="date",
            y=daily_selected_cols
        )

    # ========================================
    # 원본 이력 데이터
    # ========================================

    with st.expander("🧾 선택 기간 원본 데이터 보기"):
        st.dataframe(
            filtered_df.sort_values(
                "timestamp",
                ascending=False
            ),
            use_container_width=True,
            hide_index=True
        )

    # ========================================
    # CSV 다운로드
    # ========================================

    csv = filtered_df.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        label="📥 선택 기간 센서 이력 CSV 다운로드",
        data=csv,
        file_name="firebase_sensor_history_filtered.csv",
        mime="text/csv"
    )

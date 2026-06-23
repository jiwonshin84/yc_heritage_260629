import streamlit as st
import requests
import pandas as pd
from streamlit_autorefresh import st_autorefresh
import time

# ========================================
# 페이지 설정
# ========================================

st.set_page_config(
    page_title="문화재 환경 모니터링",
    page_icon="🏛️",
    layout="wide"
)

# 2초마다 화면 확인
st_autorefresh(
    interval=2 * 1000,
    key="sensor_refresh"
)

# ========================================
# Firebase URL
# ========================================

FIREBASE_SENSOR_URL = "https://heritage-project-4a361-default-rtdb.asia-southeast1.firebasedatabase.app/sensor.json"
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
# 실시간 장치 데이터 읽기
# ========================================

@st.cache_data(ttl=2)
def load_realtime_devices():
    try:
        response = requests.get(
            FIREBASE_SENSOR_URL,
            params={"t": time.time()},
            timeout=10
        )

        if response.status_code != 200:
            return {}

        sensor_data = response.json()

        if sensor_data is None:
            return {}

        devices = {}

        for key, value in sensor_data.items():
            if key.startswith("realtime_device_"):
                devices[key] = value

        return devices

    except:
        return {}


# ========================================
# 이력 데이터 읽기
# ========================================

@st.cache_data(ttl=20)
def load_history_data():
    try:
        response = requests.get(
            FIREBASE_HISTORY_URL,
            params={"t": time.time()},
            timeout=10
        )

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


# ========================================
# 제목
# ========================================

st.title("🏛️ 문화재 실시간 환경 모니터링 (20초마다 센서 측정)")

# ========================================
# 실시간 데이터 표시
# ========================================

realtime_devices = load_realtime_devices()

if not realtime_devices:
    st.warning("Firebase에 저장된 실시간 장치 데이터가 없습니다.")

else:
    # 장치별 마지막 timestamp 저장용
    if "last_timestamps" not in st.session_state:
        st.session_state.last_timestamps = {}

    new_devices = []

    for device_key, data in realtime_devices.items():
        timestamp = data.get("timestamp", "-")
        device_name = data.get("device", device_key)

        old_timestamp = st.session_state.last_timestamps.get(device_key)

        if old_timestamp is not None and old_timestamp != timestamp:
            new_devices.append(device_name)

        st.session_state.last_timestamps[device_key] = timestamp

    if len(new_devices) > 0:
        st.success(
            f"🆕 {', '.join(new_devices)} 데이터 업데이트"
        )

    st.caption("장치별 최신 측정값")

    for device_key, data in sorted(realtime_devices.items()):

        temp = to_float(data.get("temperature", 0))
        hum = to_float(data.get("humidity", 0))
        light = to_float(data.get("light_percent", 0))

        pm1 = to_float(data.get("pm1", 0))
        pm25 = to_float(data.get("pm25", 0))
        pm10 = to_float(data.get("pm10", 0))

        timestamp = data.get("timestamp", "-")
        device = data.get("device", device_key)

        st.subheader(f"📡 {device}")
        st.caption(f"마지막 측정 : {timestamp}")

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

        st.divider()


# ========================================
# 센서 데이터 이력 통계
# ========================================

st.subheader("📊 센서 데이터 이력 통계")

history_df = load_history_data()

if history_df.empty:
    st.info("아직 sensor/history에 누적된 데이터가 없습니다.")

else:
    st.caption(f"전체 누적 데이터 수 : {len(history_df)}개")

    history_df["date"] = history_df["timestamp"].dt.date

    min_date = history_df["date"].min()
    max_date = history_df["date"].max()

    # ========================================
    # 장치 선택
    # ========================================

    if "device" in history_df.columns:
        device_list = sorted(history_df["device"].dropna().unique())

        selected_devices = st.multiselect(
            "조회할 장치 선택",
            device_list,
            default=device_list
        )

        history_df = history_df[
            history_df["device"].isin(selected_devices)
        ]

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
        st.warning("선택한 조건에 해당하는 데이터가 없습니다.")
        st.stop()

    st.caption(
        f"선택 데이터 수 : {len(filtered_df)}개 "
        f"({start_date} ~ {end_date})"
    )

    # ========================================
    # 선택 기간 평균값
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
    # 선택 기간 최대값
    # ========================================

    st.markdown("#### 선택 기간 최대값")

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
    # 선택 기간 데이터 변화
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
    # 장치별 평균 비교
    # ========================================

    if "device" in filtered_df.columns:
        st.markdown("#### 장치별 평균 비교")

        device_mean_df = (
            filtered_df
            .groupby("device")[
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

        st.dataframe(
            device_mean_df,
            use_container_width=True,
            hide_index=True
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

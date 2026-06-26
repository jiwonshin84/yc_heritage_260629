import streamlit as st
import requests
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timedelta
import time

st.set_page_config(
    page_title="문화재 환경 모니터링",
    page_icon="🏛️",
    layout="wide"
)

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
# CSS 디자인
# ========================================

st.markdown("""
<style>
.main-title {
    font-size: 38px;
    font-weight: 800;
    margin-bottom: 5px;
}

.sub-title {
    font-size: 20px;
    color: #555;
    font-weight: 600;
    margin-bottom: 30px;
}

.device-card {
    background-color: #ffffff;
    padding: 26px;
    border-radius: 20px;
    margin-bottom: 32px;
    border-left: 9px solid #2ecc71;
    box-shadow: 0 5px 18px rgba(0,0,0,0.08);
}

.device-card-warning {
    border-left: 9px solid #f39c12;
}

.device-card-error {
    border-left: 9px solid #e74c3c;
}

.device-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.device-name {
    font-size: 27px;
    font-weight: 800;
}

.status-normal {
    background-color: #eafaf1;
    color: #1e8449;
    padding: 7px 14px;
    border-radius: 20px;
    font-weight: 700;
}

.status-warning {
    background-color: #fff3cd;
    color: #b9770e;
    padding: 7px 14px;
    border-radius: 20px;
    font-weight: 700;
}

.status-error {
    background-color: #fdecea;
    color: #c0392b;
    padding: 7px 14px;
    border-radius: 20px;
    font-weight: 700;
}

.time-text {
    color: #777;
    font-size: 14px;
    margin-top: 8px;
    margin-bottom: 18px;
}

.sensor-box {
    background-color: #f8f9fb;
    padding: 18px;
    border-radius: 16px;
    min-height: 120px;
    border: 1px solid #eeeeee;
}

.sensor-label {
    font-size: 15px;
    color: #666;
    font-weight: 700;
}

.sensor-value {
    font-size: 30px;
    font-weight: 800;
    margin-top: 8px;
    color: #2f3542;
}

.sensor-warning {
    font-size: 26px;
    font-weight: 800;
    margin-top: 8px;
    color: #e74c3c;
}

.section-title {
    font-size: 25px;
    font-weight: 800;
    margin-top: 30px;
    margin-bottom: 15px;
}
</style>
""", unsafe_allow_html=True)


# ========================================
# 함수
# ========================================

def to_float(value):
    try:
        return float(value)
    except:
        return 0.0


def parse_time(timestamp):
    try:
        return datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
    except:
        return None


def get_device_status(timestamp):
    dt = parse_time(timestamp)

    if dt is None:
        return "error", "시간 오류"

    now = datetime.now()
    diff = now - dt

    if diff > timedelta(minutes=10):
        return "error", "수신 지연"

    elif diff > timedelta(minutes=2):
        return "warning", "확인 필요"

    else:
        return "normal", "정상 수신"


def value_display(label, value, unit, zero_check=False):
    if zero_check and value == 0:
        return f"""
        <div class="sensor-box">
            <div class="sensor-label">{label}</div>
            <div class="sensor-warning">센서 확인</div>
        </div>
        """

    return f"""
    <div class="sensor-box">
        <div class="sensor-label">{label}</div>
        <div class="sensor-value">{value:.1f} {unit}</div>
    </div>
    """


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
            "pressure",
            "light",
            "pm1",
            "pm25",
            "pm10"
        ]

        for col in numeric_cols:
            if col not in df.columns:
                df[col] = 0

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            ).fillna(0)

        df = df.dropna(subset=["timestamp"])
        df = df.sort_values("timestamp")

        return df

    except:
        return pd.DataFrame()


# ========================================
# 화면 제목
# ========================================

st.markdown(
    '<div class="main-title">🏛️ 문화재 실시간 환경 모니터링</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="sub-title">BME280 온습도·기압 센서 / BH1750 조도 센서 / PMS7003 미세먼지 센서 · 20초마다 측정</div>',
    unsafe_allow_html=True
)

realtime_devices = load_realtime_devices()


# ========================================
# 실시간 장치 데이터
# ========================================

if not realtime_devices:
    st.warning("Firebase에 저장된 실시간 장치 데이터가 없습니다.")

else:
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
        st.success(f"🆕 {', '.join(new_devices)} 데이터 업데이트")

    for device_key, data in sorted(realtime_devices.items()):

        temp = to_float(data.get("temperature", 0))
        hum = to_float(data.get("humidity", 0))
        pressure = to_float(data.get("pressure", 0))
        light = to_float(data.get("light", 0))

        pm1 = to_float(data.get("pm1", 0))
        pm25 = to_float(data.get("pm25", 0))
        pm10 = to_float(data.get("pm10", 0))

        timestamp = data.get("timestamp", "-")
        device = data.get("device", device_key)

        status_type, status_text = get_device_status(timestamp)

        if status_type == "normal":
            card_class = "device-card"
            status_class = "status-normal"
        elif status_type == "warning":
            card_class = "device-card device-card-warning"
            status_class = "status-warning"
        else:
            card_class = "device-card device-card-error"
            status_class = "status-error"

        st.markdown(f"""
        <div class="{card_class}">
            <div class="device-header">
                <div class="device-name">📡 {device}</div>
                <div class="{status_class}">{status_text}</div>
            </div>
            <div class="time-text">마지막 측정 : {timestamp}</div>
        """, unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown(
                value_display("🌡️ 기온", temp, "℃"),
                unsafe_allow_html=True
            )

        with col2:
            st.markdown(
                value_display("💧 습도", hum, "%"),
                unsafe_allow_html=True
            )

        with col3:
            st.markdown(
                value_display("🌬️ 기압", pressure, "hPa", zero_check=True),
                unsafe_allow_html=True
            )

        with col4:
            st.markdown(
                value_display("☀️ 조도", light, "lux", zero_check=True),
                unsafe_allow_html=True
            )

        col5, col6, col7 = st.columns(3)

        with col5:
            st.markdown(
                value_display("🌫️ PM1.0", pm1, "㎍/㎥"),
                unsafe_allow_html=True
            )

        with col6:
            st.markdown(
                value_display("🌫️ PM2.5", pm25, "㎍/㎥"),
                unsafe_allow_html=True
            )

        with col7:
            st.markdown(
                value_display("🌫️ PM10", pm10, "㎍/㎥"),
                unsafe_allow_html=True
            )

        st.markdown("</div>", unsafe_allow_html=True)


# ========================================
# 센서 이력 통계
# ========================================

st.markdown(
    '<div class="section-title">📊 센서 데이터 이력 통계</div>',
    unsafe_allow_html=True
)

history_df = load_history_data()

if history_df.empty:
    st.info("아직 sensor/history에 누적된 데이터가 없습니다.")

else:
    st.caption(f"전체 누적 데이터 수 : {len(history_df)}개")

    history_df["date"] = history_df["timestamp"].dt.date

    min_date = history_df["date"].min()
    max_date = history_df["date"].max()

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

    st.markdown("#### 선택 기간 평균값")

    stat_col1, stat_col2, stat_col3, stat_col4, stat_col5 = st.columns(5)

    with stat_col1:
        st.metric("평균 기온", f"{filtered_df['temperature'].mean():.1f} ℃")

    with stat_col2:
        st.metric("평균 습도", f"{filtered_df['humidity'].mean():.1f} %")

    with stat_col3:
        st.metric("평균 기압", f"{filtered_df['pressure'].mean():.1f} hPa")

    with stat_col4:
        st.metric("평균 조도", f"{filtered_df['light'].mean():.1f} lux")

    with stat_col5:
        st.metric("평균 PM2.5", f"{filtered_df['pm25'].mean():.1f} ㎍/㎥")

    st.markdown("#### 선택 기간 최대값")

    max_col1, max_col2, max_col3, max_col4, max_col5 = st.columns(5)

    with max_col1:
        st.metric("최고 기온", f"{filtered_df['temperature'].max():.1f} ℃")

    with max_col2:
        st.metric("최고 습도", f"{filtered_df['humidity'].max():.1f} %")

    with max_col3:
        st.metric("최고 기압", f"{filtered_df['pressure'].max():.1f} hPa")

    with max_col4:
        st.metric("최고 조도", f"{filtered_df['light'].max():.1f} lux")

    with max_col5:
        st.metric("최고 PM2.5", f"{filtered_df['pm25'].max():.1f} ㎍/㎥")

    st.markdown("#### 선택 기간 최소값")

    min_col1, min_col2, min_col3, min_col4, min_col5 = st.columns(5)

    with min_col1:
        st.metric("최저 기온", f"{filtered_df['temperature'].min():.1f} ℃")

    with min_col2:
        st.metric("최저 습도", f"{filtered_df['humidity'].min():.1f} %")

    with min_col3:
        st.metric("최저 기압", f"{filtered_df['pressure'].min():.1f} hPa")

    with min_col4:
        st.metric("최저 조도", f"{filtered_df['light'].min():.1f} lux")

    with min_col5:
        st.metric("최저 PM2.5", f"{filtered_df['pm25'].min():.1f} ㎍/㎥")

    st.markdown("#### 선택 기간 데이터 변화")

    chart_cols = [
        "temperature",
        "humidity",
        "pressure",
        "light",
        "pm1",
        "pm25",
        "pm10"
    ]

    selected_cols = st.multiselect(
        "그래프로 표시할 항목",
        chart_cols,
        default=[
            "temperature",
            "humidity",
            "pressure",
            "pm25"
        ]
    )

    if selected_cols:
        st.line_chart(
            filtered_df,
            x="timestamp",
            y=selected_cols
        )

    if "device" in filtered_df.columns:
        st.markdown("#### 장치별 평균 비교")

        device_mean_df = (
            filtered_df
            .groupby("device")[
                [
                    "temperature",
                    "humidity",
                    "pressure",
                    "light",
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

    st.markdown("#### 항목별 기초 통계")

    stats_cols = [
        "temperature",
        "humidity",
        "pressure",
        "light",
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

    st.markdown("#### 일별 평균 변화")

    daily_df = (
        filtered_df
        .groupby("date")[
            [
                "temperature",
                "humidity",
                "pressure",
                "light",
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
        chart_cols,
        default=[
            "temperature",
            "humidity",
            "pressure",
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

    with st.expander("🧾 선택 기간 원본 데이터 보기"):
        st.dataframe(
            filtered_df.sort_values(
                "timestamp",
                ascending=False
            ),
            use_container_width=True,
            hide_index=True
        )

    csv = filtered_df.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        label="📥 선택 기간 센서 이력 CSV 다운로드",
        data=csv,
        file_name="firebase_sensor_history_filtered.csv",
        mime="text/csv"
    )

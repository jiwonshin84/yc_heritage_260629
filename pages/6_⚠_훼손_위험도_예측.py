import streamlit as st
import pandas as pd
import numpy as np
import requests
import os

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sklearn.ensemble import RandomForestClassifier

# ==========================================================
# 0. 설정 및 API 키
# ==========================================================

st.set_page_config(
    page_title="영천 지역 문화재 훼손 위험 예측",
    page_icon="🏛",
    layout="wide"
)

SERVICE_KEY = "YOUR_SERVICE_KEY"

now = datetime.now(ZoneInfo("Asia/Seoul"))
yesterday = now - timedelta(days=1)

base_date = yesterday.strftime("%Y%m%d")

if 'danger_count' not in st.session_state:
    st.session_state['danger_count'] = 0

# ==========================================================
# 1. 파생변수 생성 함수
# ==========================================================

def add_derived_features(df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()

    df["temp_change"] = df["temp"].diff().fillna(0)

    df["humidity_change"] = (
        df["humidity"].diff().fillna(0)
    )

    df["dew_point"] = (
        df["temp"]
        - ((100 - df["humidity"]) / 5)
    )

    df["dew_gap"] = (
        df["temp"] - df["dew_point"]
    )

    df["humidity_ma3"] = (
        df["humidity"]
        .rolling(3)
        .mean()
        .fillna(df["humidity"])
    )

    df["pm10_ma3"] = (
        df["pm10"]
        .rolling(3)
        .mean()
        .fillna(df["pm10"])
    )

    df["temp_std"] = (
        df["temp"]
        .rolling(3)
        .std()
        .fillna(0)
    )

    df["humidity_std"] = (
        df["humidity"]
        .rolling(3)
        .std()
        .fillna(0)
    )

    df["condensation_risk"] = (
        df["dew_gap"]
        .apply(lambda x: 1 if x < 2 else (0.5 if x < 5 else 0))
    )

    df["mold_risk"] = (
        (df["humidity"] >= 75)
        .rolling(3)
        .sum() >= 2
    ).astype(int)

    df["pm_load"] = (
        (df["pm10"] + df["pm25"])
        .rolling(3)
        .sum()
        .fillna(0)
    )

    return df

# ==========================================================
# 2. 위험도 분류 함수
# ==========================================================

def classify_humidity(h):

    if h >= 75 or h < 35:
        return 2

    elif h >= 65 or h < 45:
        return 1

    else:
        return 0


def classify_temp(t):

    if t > 30 or t < 5:
        return 2

    elif t > 25 or t < 15:
        return 1

    else:
        return 0


def classify_dew(d):

    if d < 2:
        return 2

    elif d < 5:
        return 1

    else:
        return 0


def classify_pm10(p):

    if p >= 80:
        return 2

    elif p >= 30:
        return 1

    else:
        return 0


def classify_temp_change(tc):

    if abs(tc) >= 10:
        return 2

    elif abs(tc) >= 5:
        return 1

    else:
        return 0


def classify_humidity_change(hc):

    if abs(hc) >= 30:
        return 2

    elif abs(hc) >= 15:
        return 1

    else:
        return 0

# ==========================================================
# 3. 가중합 위험도 계산
# ==========================================================

def calc_weighted_risk(row):

    return (
        classify_humidity(row["humidity"]) * 0.30
        + classify_temp(row["temp"]) * 0.20
        + classify_dew(row["dew_gap"]) * 0.20
        + classify_pm10(row["pm10"]) * 0.15
        + classify_temp_change(row["temp_change"]) * 0.10
        + classify_humidity_change(row["humidity_change"]) * 0.05
    )


def final_classify(score):

    if score >= 1.2:
        return 2

    elif score >= 0.5:
        return 1

    else:
        return 0

# ==========================================================
# 4. 재질 및 노출 보정
# ==========================================================

def exposure_multiplier(exp):

    return {
        "실외": 1.0,
        "반실외": 0.7,
        "실내": 0.3
    }.get(exp, 1.0)


def material_extra_risk(mat, row):

    extra = 0.0

    dew = row.get("dew_gap", 5.0)
    hum = row.get("humidity", 50.0)
    rain = row.get("rainfall", 0.0)

    if mat == "목조":

        if hum > 75 or hum < 35:
            extra += 0.3

        if dew < 2:
            extra += 0.3

    elif mat == "석조":

        if rain > 15:
            extra += 0.3

        if dew < 5:
            extra += 0.2

    elif mat == "금속":

        if hum > 70:
            extra += 0.2

        if dew < 3:
            extra += 0.2

    elif mat == "벽화":

        if hum > 70 or hum < 40:
            extra += 0.4

        if dew < 3:
            extra += 0.4

    return extra

# ==========================================================
# 5. 모델 입력 변수
# ==========================================================

FEATURES = [

    "temp",
    "humidity",
    "rainfall",
    "wind",

    "pm10",
    "pm25",

    "so2",
    "no2",
    "co",
    "o3",

    "temp_change",
    "humidity_change",

    "dew_gap",
    "humidity_ma3",
    "pm10_ma3",

    "temp_std",
    "humidity_std",

    "pm_load",

    "mat_code",
    "exp_code"
]

# ==========================================================
# 6. 모델 학습
# ==========================================================

@st.cache_resource
def train_heritage_model():

    weather_path = (
        "data/processed/[2016_2025] yeongcheon_weather_daily.csv"
    )

    air_path = (
        "data/processed/[2019_2025] air_quality.csv"
    )

    if (
        not os.path.exists(weather_path)
        or
        not os.path.exists(air_path)
    ):
        return None, None

    w_df = pd.read_csv(weather_path)
    a_df = pd.read_csv(air_path)

    w_df = w_df.rename(columns={
        'avg_temperature_c': 'temp',
        'daily_precipitation_mm': 'rainfall',
        'avg_wind_speed_ms': 'wind',
        'avg_relative_humidity_pct': 'humidity'
    })

    w_df["date"] = pd.to_datetime(w_df["date"])
    a_df["date"] = pd.to_datetime(a_df["date"])

    m_df = pd.merge(
        w_df,
        a_df,
        on="date",
        how="inner"
    ).ffill()

    m_df = add_derived_features(m_df)

    mats = {
        '목조': 0,
        '석조': 1,
        '금속': 2,
        '벽화': 3,
        '기타': 4
    }

    exps = {
        '실외': 0,
        '실내': 1,
        '반실외': 2
    }

    train_rows = []

    for _, r in m_df.tail(1200).iterrows():

        base_score = calc_weighted_risk(r)

        for m_name, m_code in mats.items():

            for e_name, e_code in exps.items():

                adj = exposure_multiplier(e_name)

                extra = material_extra_risk(
                    m_name,
                    r
                )

                score = min(
                    base_score * adj + extra,
                    2.0
                )

                danger = final_classify(score)

                train_rows.append({

                    **{
                        k: r.get(k, 0)
                        for k in [

                            "temp",
                            "humidity",
                            "rainfall",
                            "wind",

                            "pm10",
                            "pm25",

                            "so2",
                            "no2",
                            "co",
                            "o3",

                            "temp_change",
                            "humidity_change",

                            "dew_gap",
                            "humidity_ma3",
                            "pm10_ma3",

                            "temp_std",
                            "humidity_std",

                            "pm_load"
                        ]
                    },

                    "mat_code": m_code,
                    "exp_code": e_code,
                    "target": danger
                })

    tdf = pd.DataFrame(train_rows).fillna(0)

    model = RandomForestClassifier(
        n_estimators=200,
        class_weight="balanced",
        random_state=42
    )

    model.fit(
        tdf[FEATURES],
        tdf["target"]
    )

    return model, FEATURES

ai_model, feature_names = train_heritage_model()

# ==========================================================
# 7. 실시간 일자료 API 수집
# ==========================================================

tm, temp, humidity, rainfall, wind_speed = (
    "-", "-", "-", "-", "-"
)

try:

    asos_params = {

        "serviceKey": SERVICE_KEY,

        "numOfRows": "3",

        "dataType": "JSON",

        "dataCd": "ASOS",

        "dateCd": "DAY",

        "startDt": (
            yesterday - timedelta(days=2)
        ).strftime("%Y%m%d"),

        "endDt": base_date,

        "stnIds": "281"
    }

    res = requests.get(
        "https://apis.data.go.kr/1360000/AsosDailyInfoService/getWthrDataList",
        params=asos_params,
        timeout=10
    ).json()

    items = (
        res["response"]["body"]["items"]["item"]
    )

    daily_df = pd.DataFrame(items)

    daily_df = daily_df.rename(columns={

        "avgTa": "temp",
        "avgRhm": "humidity",
        "sumRn": "rainfall",
        "avgWs": "wind"
    })

    for col in [
        "temp",
        "humidity",
        "rainfall",
        "wind"
    ]:

        daily_df[col] = pd.to_numeric(
            daily_df[col],
            errors="coerce"
        ).fillna(0)

    latest = daily_df.iloc[-1]

    tm = latest["tm"]

    temp = latest["temp"]

    humidity = latest["humidity"]

    rainfall = latest["rainfall"]

    wind_speed = latest["wind"]

except Exception as e:

    print("기상 API 오류:", e)

# ==========================================================
# 8. 대기오염 데이터
# ==========================================================

pm10, pm25, o3, no2, co, so2, data_time = (
    "-", "-", "-", "-", "-", "-", "-"
)

try:

    air_params = {

        "serviceKey": SERVICE_KEY,

        "returnType": "json",

        "numOfRows": "100",

        "sidoName": "경북",

        "ver": "1.0"
    }

    res = requests.get(
        "https://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getCtprvnRltmMesureDnsty",
        params=air_params,
        timeout=10
    ).json()

    target = next(

        (
            i
            for i in res["response"]["body"]["items"]
            if "영천" in i["stationName"]
        ),

        None
    )

    if target:

        pm10 = target["pm10Value"]
        pm25 = target["pm25Value"]

        o3 = target["o3Value"]
        no2 = target["no2Value"]

        co = target["coValue"]
        so2 = target["so2Value"]

        data_time = target["dataTime"]

except:
    pass

# ==========================================================
# 9. 현재 환경 파생변수 계산
# ==========================================================

def safe_f(v):

    try:
        return float(v)

    except:
        return 0.0

curr_raw = {

    "temp": safe_f(temp),

    "humidity": safe_f(humidity),

    "rainfall": safe_f(rainfall),

    "wind": safe_f(wind_speed),

    "pm10": safe_f(pm10),

    "pm25": safe_f(pm25),

    "so2": safe_f(so2),

    "no2": safe_f(no2),

    "co": safe_f(co),

    "o3": safe_f(o3),
}

if 'daily_df' in locals() and len(daily_df) >= 3:

    temp_change = (
        daily_df.iloc[-1]["temp"]
        - daily_df.iloc[-2]["temp"]
    )

    humidity_change = (
        daily_df.iloc[-1]["humidity"]
        - daily_df.iloc[-2]["humidity"]
    )

    humidity_ma3 = (
        daily_df["humidity"]
        .tail(3)
        .mean()
    )

    temp_std = (
        daily_df["temp"]
        .tail(3)
        .std()
    )

    humidity_std = (
        daily_df["humidity"]
        .tail(3)
        .std()
    )

else:

    temp_change = 0

    humidity_change = 0

    humidity_ma3 = curr_raw["humidity"]

    temp_std = 0

    humidity_std = 0

pm10_ma3 = curr_raw["pm10"]

dew_point = (
    curr_raw["temp"]
    - ((100 - curr_raw["humidity"]) / 5)
)

dew_gap = (
    curr_raw["temp"] - dew_point
)

pm_load = (
    curr_raw["pm10"]
    + curr_raw["pm25"]
) * 3

curr_env = {

    **curr_raw,

    "temp_change": temp_change,

    "humidity_change": humidity_change,

    "dew_gap": dew_gap,

    "humidity_ma3": humidity_ma3,

    "pm10_ma3": pm10_ma3,

    "temp_std": temp_std,

    "humidity_std": humidity_std,

    "pm_load": pm_load
}

curr_weighted_risk = calc_weighted_risk(
    curr_env
)

curr_risk_grade = final_classify(
    curr_weighted_risk
)

print(curr_env)
print("현재 위험등급:", curr_risk_grade)

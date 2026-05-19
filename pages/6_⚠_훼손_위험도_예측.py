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

SERVICE_KEY = "feb2bfabd299d5d05e89c7aec49ba7e706112603e76549a92e868bd86ec60323"
now = datetime.now(ZoneInfo("Asia/Seoul"))
yesterday = now - timedelta(days=1)
base_date = yesterday.strftime("%Y%m%d")
base_hour = "23"

if 'danger_count' not in st.session_state:
    st.session_state['danger_count'] = 0

# ==========================================================
# 1. 파생변수 생성 및 위험도 분류 함수 (논문 기반)
# ==========================================================

def add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """온습도·공기질 데이터프레임에 파생변수를 추가하여 반환"""
    df = df.copy()
    df["temp_change"]      = df["temp"].diff().fillna(0)
    df["humidity_change"]  = df["humidity"].diff().fillna(0)
    df["dew_point"]        = df["temp"] - ((100 - df["humidity"]) / 5)
    df["dew_gap"]          = df["temp"] - df["dew_point"]
    df["humidity_ma3"]     = df["humidity"].rolling(3).mean().fillna(df["humidity"])
    df["pm10_ma3"]         = df["pm10"].rolling(3).mean().fillna(df["pm10"])
    df["temp_std"]         = df["temp"].rolling(3).std().fillna(0)
    df["humidity_std"]     = df["humidity"].rolling(3).std().fillna(0)
    df["condensation_risk"]= df["dew_gap"].apply(lambda x: 1 if x < 2 else (0.5 if x < 5 else 0))
    df["mold_risk"]        = ((df["humidity"] >= 75).rolling(3).sum() >= 2).astype(int)
    df["pm_load"]          = (df["pm10"] + df["pm25"]).rolling(3).sum().fillna(0)
    return df


def classify_humidity(h):
    if h >= 75 or h < 35:   return 2
    elif h >= 65 or h < 45: return 1
    else:                    return 0

def classify_temp(t):
    if t > 30 or t < 5:     return 2
    elif t > 25 or t < 15:  return 1
    else:                    return 0

def classify_dew(d):
    if d < 2:    return 2
    elif d < 5:  return 1
    else:        return 0

def classify_pm10(p):
    if p >= 80:  return 2
    elif p >= 30:return 1
    else:        return 0

def classify_temp_change(tc):
    if abs(tc) >= 10:  return 2
    elif abs(tc) >= 5: return 1
    else:              return 0

def classify_humidity_change(hc):
    if abs(hc) >= 30:  return 2
    elif abs(hc) >= 15:return 1
    else:              return 0


def calc_weighted_risk(row) -> float:
    """
    논문 기반 가중합 위험지수 (0.0 ~ 2.0)
    가중치: 습도 0.30 | 온도 0.20 | 결로 0.20 | PM10 0.15 | 온도급변 0.10 | 습도급변 0.05
    """
    return (
        classify_humidity(row["humidity"])         * 0.30 +
        classify_temp(row["temp"])                 * 0.20 +
        classify_dew(row["dew_gap"])               * 0.20 +
        classify_pm10(row["pm10"])                 * 0.15 +
        classify_temp_change(row["temp_change"])   * 0.10 +
        classify_humidity_change(row["humidity_change"]) * 0.05
    )


def final_classify(score: float) -> int:
    """가중합 점수 → 최종 위험 등급 (0=안전, 1=주의, 2=위험)"""
    if score >= 1.2:   return 2
    elif score >= 0.5: return 1
    else:              return 0


def exposure_multiplier(exp: str) -> float:
    return {"실외": 1.0, "반실외": 0.7, "실내": 0.3}.get(exp, 1.0)


def material_extra_risk(mat: str, row: dict) -> float:
    """
    재질별 추가 위험 보정값
    - 목조  : 습도 극단 / 결로 위험 / 곰팡이 위험에 민감
    - 석조  : 강수(rainfall) 및 결로에 민감
    - 금속  : 습도·결로에 민감
    - 벽화  : 습도변동·결로에 극도로 민감
    """
    extra = 0.0
    dew   = row.get("dew_gap", 5.0)
    hum   = row.get("humidity", 50.0)
    rain  = row.get("rainfall", 0.0)

    if mat == "목조":
        if hum > 75 or hum < 35: extra += 0.3
        if dew < 2:               extra += 0.3
    elif mat == "석조":
        if rain > 15:             extra += 0.3
        if dew < 5:               extra += 0.2
    elif mat == "금속":
        if hum > 70:              extra += 0.2
        if dew < 3:               extra += 0.2
    elif mat == "벽화":
        if hum > 70 or hum < 40: extra += 0.4
        if dew < 3:               extra += 0.4

    return extra


# ==========================================================
# 2. 모델 학습 (파생변수 포함)
# ==========================================================
FEATURES = [
    "temp", "humidity", "rainfall", "wind",
    "pm10", "pm25", "so2", "no2", "co", "o3",
    "temp_change", "humidity_change",
    "dew_gap", "humidity_ma3", "pm10_ma3",
    "temp_std", "humidity_std", "pm_load",
    "mat_code", "exp_code"
]


@st.cache_resource
def train_heritage_model():
    weather_path = "data/processed/[2016_2025] yeongcheon_weather_daily.csv"
    air_path     = "data/processed/[2019_2025] air_quality.csv"

    if not os.path.exists(weather_path) or not os.path.exists(air_path):
        return None, None

    w_df = pd.read_csv(weather_path)
    a_df = pd.read_csv(air_path)

    w_df = w_df.rename(columns={
        'avg_temperature_c':       'temp',
        'daily_precipitation_mm':  'rainfall',
        'avg_wind_speed_ms':       'wind',
        'avg_relative_humidity_pct': 'humidity'
    })

    # ── 날짜 타입 통일 후 병합
    w_df["date"] = pd.to_datetime(w_df["date"])
    a_df["date"] = pd.to_datetime(a_df["date"])
    m_df = pd.merge(w_df, a_df, on="date", how="inner").ffill()

    # ── 파생변수 추가 (전체 이력에 대해 한 번에)
    m_df = add_derived_features(m_df)

    mats = {'목조': 0, '석조': 1, '금속': 2, '벽화': 3, '기타': 4}
    exps = {'실외': 0, '실내': 1, '반실외': 2}

    train_rows = []
    for _, r in m_df.tail(1200).iterrows():
        base_score  = calc_weighted_risk(r)

        for m_name, m_code in mats.items():
            for e_name, e_code in exps.items():
                adj    = exposure_multiplier(e_name)
                extra  = material_extra_risk(m_name, r)
                score  = min(base_score * adj + extra, 2.0)
                danger = final_classify(score)

                train_rows.append({
                    **{k: r.get(k, 0) for k in [
                        "temp", "humidity", "rainfall", "wind",
                        "pm10", "pm25", "so2", "no2", "co", "o3",
                        "temp_change", "humidity_change",
                        "dew_gap", "humidity_ma3", "pm10_ma3",
                        "temp_std", "humidity_std", "pm_load"
                    ]},
                    "mat_code": m_code,
                    "exp_code": e_code,
                    "target":   danger
                })

    tdf   = pd.DataFrame(train_rows).fillna(0)
    model = RandomForestClassifier(
        n_estimators=200, class_weight="balanced", random_state=42
    )
    model.fit(tdf[FEATURES], tdf["target"])
    return model, FEATURES


ai_model, feature_names = train_heritage_model()

# ==========================================================
# 3. 실시간 데이터 수집 (API)
# ==========================================================
tm, temp, humidity, rainfall, wind_speed = "-", "-", "-", "-", "-"
try:
    asos_params = {
        "serviceKey": SERVICE_KEY, "numOfRows": "1", "dataType": "JSON",
        "dataCd": "ASOS", "dateCd": "HR",
        "startDt": base_date, "startHh": base_hour,
        "endDt":   base_date, "endHh":   base_hour,
        "stnIds": "281"
    }
    res  = requests.get(
        "https://apis.data.go.kr/1360000/AsosHourlyInfoService/getWthrDataList",
        params=asos_params, timeout=10
    ).json()
    item = res["response"]["body"]["items"]["item"][0]
    tm, temp, humidity, rainfall, wind_speed = (
        item["tm"], item["ta"], item["hm"], item["rn"], item["ws"]
    )
except:
    pass

pm10, pm25, o3, no2, co, so2, data_time = "-", "-", "-", "-", "-", "-", "-"
try:
    air_params = {
        "serviceKey": SERVICE_KEY, "returnType": "json",
        "numOfRows": "100", "sidoName": "경북", "ver": "1.0"
    }
    res    = requests.get(
        "https://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getCtprvnRltmMesureDnsty",
        params=air_params, timeout=10
    ).json()
    target = next(
        (i for i in res["response"]["body"]["items"] if "영천" in i["stationName"]),
        None
    )
    if target:
        pm10, pm25, o3, no2, co, so2, data_time = (
            target["pm10Value"], target["pm25Value"], target["o3Value"],
            target["no2Value"],  target["coValue"],  target["so2Value"],
            target["dataTime"]
        )
except:
    pass

# ==========================================================
# 4. 현재 환경값 → 파생변수 계산 (실시간 단일 행)
# ==========================================================
def safe_f(v):
    try: return float(v)
    except: return 0.0

curr_raw = {
    "temp":     safe_f(temp),
    "humidity": safe_f(humidity),
    "rainfall": safe_f(rainfall),
    "wind":     safe_f(wind_speed),
    "pm10":     safe_f(pm10),
    "pm25":     safe_f(pm25),
    "so2":      safe_f(so2),
    "no2":      safe_f(no2),
    "co":       safe_f(co),
    "o3":       safe_f(o3),
}

# 실시간 단일 행 파생변수 (이전 값 없으므로 변화량=0, std=0, ma=현재값)
curr_env = {
    **curr_raw,
    "temp_change":      0.0,
    "humidity_change":  0.0,
    "dew_gap":          curr_raw["temp"] - (curr_raw["temp"] - ((100 - curr_raw["humidity"]) / 5)),
    "humidity_ma3":     curr_raw["humidity"],
    "pm10_ma3":         curr_raw["pm10"],
    "temp_std":         0.0,
    "humidity_std":     0.0,
    "pm_load":          (curr_raw["pm10"] + curr_raw["pm25"]) * 3,  # 3일치 추정
}

# dew_gap 재계산 (이슬점 = temp - (100-humidity)/5)
dew_point       = curr_raw["temp"] - ((100 - curr_raw["humidity"]) / 5)
curr_env["dew_gap"] = curr_raw["temp"] - dew_point

# 현재 환경 기반 가중합 위험지수
curr_weighted_risk = calc_weighted_risk({**curr_raw, "dew_gap": curr_env["dew_gap"],
                                         "temp_change": 0, "humidity_change": 0})
curr_risk_grade    = final_classify(curr_weighted_risk)

# ==========================================================
# 5. UI 스타일
# ==========================================================
card_style      = "background-color:#f8f9fa; padding:22px; border-radius:20px; border:1px solid #e5e7eb; box-shadow:0 4px 12px rgba(0,0,0,0.05); height:350px;"
stat_card_style = "padding:20px; border-radius:15px; text-align:center; color:white; box-shadow:0 4px 10px rgba(0,0,0,0.1);"
title_style     = "font-size:24px; font-weight:700; margin-bottom:14px; color:#1f2937;"
label_style     = "font-size:14px; color:#6b7280; margin-bottom:4px;"
value_style     = "font-size:22px; font-weight:700; color:#111827; margin-bottom:18px;"
time_style      = "font-size:13px; color:#9ca3af; margin-top:12px; position:absolute; bottom:20px;"

# ==========================================================
# 6. AI 분석 (문화재별 위험 예측)
# ==========================================================
heritage_df = pd.read_csv("data/processed/yc_heritage_feature.csv")
res_df      = pd.DataFrame()

mat_map = {'목조': 0, '석조': 1, '금속': 2, '벽화': 3}
exp_map = {'실외': 0, '실내': 1, '반실외': 2}

if ai_model:
    results = []
    for _, row in heritage_df.iterrows():
        mat   = str(row['재질']).strip()
        exp   = str(row['노출형태']).strip()
        m_code = mat_map.get(mat, 4)
        e_code = exp_map.get(exp, 0)

        input_v = pd.DataFrame([{**curr_env, "mat_code": m_code, "exp_code": e_code}])
        pred    = ai_model.predict(input_v[feature_names])[0]
        prob    = ai_model.predict_proba(input_v[feature_names])[0]

        # ── 재질·노출 보정값으로 위험지수 표시값 산출
        adj   = exposure_multiplier(exp)
        extra = material_extra_risk(mat, curr_env)
        adj_score  = min(curr_weighted_risk * adj + extra, 2.0)
        danger_pct = round(min(prob[2] * 100 + extra * 15, 100), 1)

        results.append({
            '문화재명': row['문화재명(국문)'],
            '재질':     mat,
            '노출':     exp,
            '위험지수': round(adj_score, 3),
            '위험수치': danger_pct,
            '등급':     pred
        })

    res_df   = pd.DataFrame(results)
    cnt_safe = len(res_df[res_df['등급'] == 0])
    cnt_warn = len(res_df[res_df['등급'] == 1])
    cnt_dang = len(res_df[res_df['등급'] == 2])
    st.session_state['danger_count'] = cnt_dang

# ==========================================================
# 7. 메인 화면 구성
# ==========================================================
st.markdown(
    "<h1 style='font-size:30px;'>🏛 공공 환경 데이터 기반 영천 지역 문화재 훼손 위험 예측</h1>",
    unsafe_allow_html=True
)
st.divider()

# ── 환경 현황 카드 3열
st.markdown(
    '<h3 style="font-size:22px; margin-bottom:15px;">🌿 실시간 영천 환경 지표 및 분석 요약</h3>',
    unsafe_allow_html=True
)
left, center, right = st.columns([1.4, 2.0, 1.0])

with left:
    st.markdown(f"""
    <div style="{card_style}; position:relative;">
      <div style="{title_style}">🌦 기상 환경</div><hr>
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-top:20px;">
        <div><div style="{label_style}">🌡 기온</div><div style="{value_style}">{temp} °C</div></div>
        <div><div style="{label_style}">💧 습도</div><div style="{value_style}">{humidity} %</div></div>
        <div><div style="{label_style}">🌧 강수량</div><div style="{value_style}">{rainfall} mm</div></div>
        <div><div style="{label_style}">💨 풍속</div><div style="{value_style}">{wind_speed} m/s</div></div>
      </div>
      <div style="{time_style}">⏱ {tm}</div>
    </div>""", unsafe_allow_html=True)

with center:
    st.markdown(f"""
    <div style="{card_style}; position:relative;">
      <div style="{title_style}">🌫 대기오염 현황</div><hr>
      <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:20px; margin-top:20px;">
        <div>
          <div style="{label_style}">PM10</div><div style="{value_style}">{pm10}</div>
          <div style="{label_style}">O₃</div><div style="{value_style}">{o3}</div>
        </div>
        <div>
          <div style="{label_style}">PM2.5</div><div style="{value_style}">{pm25}</div>
          <div style="{label_style}">NO₂</div><div style="{value_style}">{no2}</div>
        </div>
        <div>
          <div style="{label_style}">CO</div><div style="{value_style}">{co}</div>
          <div style="{label_style}">SO₂</div><div style="{value_style}">{so2}</div>
        </div>
      </div>
      <div style="{time_style}">⏱ {data_time}</div>
    </div>""", unsafe_allow_html=True)

with right:
    risk_color = {"안전": "#2E7D32", "주의": "#F9A825", "위험": "#C62828"}
    grade_kor  = {0: "안전", 1: "주의", 2: "위험"}
    curr_label = grade_kor[curr_risk_grade]
    st.markdown(f"""
    <div style="{card_style}; position:relative;">
      <div style="{title_style}">🏛 문화재 현황</div><hr>
      <div style="margin-top:20px;">
        <div style="{label_style}">분석 문화재 수</div>
        <div style="{value_style}">{len(heritage_df)}개</div>
        <div style="{label_style}">🌡 현재 환경 위험지수</div>
        <div style="font-size:18px; font-weight:700; color:{risk_color[curr_label]}; margin-bottom:8px;">
          {curr_weighted_risk:.2f} ({curr_label})
        </div>
        <div style="{label_style}">🚨 고위험 문화재 (현재)</div>
        <div style="{value_style} color:#C62828;">{st.session_state['danger_count']}개</div>
      </div>
      <div style="{time_style}">📍 경북 영천시</div>
    </div>""", unsafe_allow_html=True)

st.divider()

# ── 파생변수 현황 패널 (expander)
with st.expander("🔬 현재 환경 파생변수 상세 보기 (논문 기반)", expanded=False):
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("이슬점 (℃)",      f"{dew_point:.1f}")
    d1.metric("결로 위험 간격",   f"{curr_env['dew_gap']:.1f} ℃",
              delta="위험" if curr_env['dew_gap'] < 2 else ("주의" if curr_env['dew_gap'] < 5 else "안전"))
    d2.metric("PM 누적 노출",    f"{curr_env['pm_load']:.1f}")
    d2.metric("가중합 위험지수", f"{curr_weighted_risk:.3f}")
    d3.metric("온도 변화량 (당일)", f"{curr_env['temp_change']:.1f} ℃")
    d3.metric("습도 변화량 (당일)", f"{curr_env['humidity_change']:.1f} %")
    d4.metric("결로위험 등급",   classify_dew(curr_env['dew_gap']))
    d4.metric("PM10 위험 등급",  classify_pm10(curr_raw['pm10']))

    st.markdown("""
    **가중치 구성 (합계 1.0)**

    | 항목 | 가중치 | 근거 |
    |------|--------|------|
    | 습도 | 0.30 | 목재·단청 직접 영향 (문화재청 권고) |
    | 온도 | 0.20 | 수축·팽창 (국립중앙박물관 기준) |
    | 결로 위험 | 0.20 | 박락·곰팡이 (이슬점 기반) |
    | PM10 | 0.15 | 표면 오염 (환경부 기준) |
    | 온도 급변 | 0.10 | 균열 위험 |
    | 습도 급변 | 0.05 | 단청 박락 |
    """)

st.divider()

# ── AI 판정 통계
if not res_df.empty:
    st.markdown(
        '<h3 style="font-size:22px; margin-bottom:15px;">📊 AI 위험도 판정 통계</h3>',
        unsafe_allow_html=True
    )
    s1, s2, s3 = st.columns(3)
    s1.markdown(
        f'<div style="{stat_card_style} background-color:#2E7D32;"><h4>✅ 안전</h4>'
        f'<span style="font-size:30px; font-weight:bold;">{cnt_safe}</span> 건</div>',
        unsafe_allow_html=True
    )
    s2.markdown(
        f'<div style="{stat_card_style} background-color:#F9A825;"><h4>⚠️ 주의</h4>'
        f'<span style="font-size:30px; font-weight:bold;">{cnt_warn}</span> 건</div>',
        unsafe_allow_html=True
    )
    s3.markdown(
        f'<div style="{stat_card_style} background-color:#C62828;"><h4>🚨 위험</h4>'
        f'<span style="font-size:30px; font-weight:bold;">{st.session_state["danger_count"]}</span> 건</div>',
        unsafe_allow_html=True
    )

    st.write("")
    st.write("#### 🔎 상세 분석 리스트")

    display_df = (
        res_df
        .assign(판정=res_df['등급'].map({0: '안전', 1: '주의', 2: '위험'}))
        .sort_values('위험수치', ascending=False)
        [['문화재명', '재질', '노출', '위험지수', '위험수치', '판정']]
    )

    st.dataframe(
        display_df,
        column_config={
            "위험지수": st.column_config.NumberColumn("위험지수 (0~2)", format="%.3f"),
            "위험수치": st.column_config.ProgressColumn(
                "훼손 위험 지수", min_value=0, max_value=100, format="%f%%"
            ),
        },
        use_container_width=True,
        hide_index=True
    )

    # ── 위험 문화재 상세 표시
    danger_list = res_df[res_df['등급'] == 2]
    if not danger_list.empty:
        st.error(f"🚨 현재 위험 등급 문화재 {len(danger_list)}건")
        for _, r in danger_list.iterrows():
            st.markdown(
                f"- **{r['문화재명']}** | 재질: {r['재질']} | 노출: {r['노출']} "
                f"| 위험지수: `{r['위험지수']:.3f}` | 위험수치: `{r['위험수치']}%`"
            )
else:
    st.error("분석 데이터를 불러오지 못했습니다.")

# ── 기준값 요약
with st.expander("📋 적용된 절대 기준값 요약 (문화재청·환경부 근거)", expanded=False):
    st.markdown("""
    | 항목 | 안전 | 주의 | 위험 |
    |------|------|------|------|
    | **습도** | 45 ~ 65% | 35 ~ 44% 또는 65 ~ 74% | <35% 또는 ≥75% |
    | **온도** | 15 ~ 25℃ | 5 ~ 14℃ 또는 26 ~ 30℃ | <5℃ 또는 >30℃ |
    | **결로 간격** | ≥5℃ | 2 ~ 5℃ | <2℃ |
    | **PM10** | <30 | 30~79 | ≥80 |
    | **일간 온도 변화** | <5℃ | 5 ~ 9℃ | ≥10℃ |
    | **일간 습도 변화** | <15% | 15 ~ 29% | ≥30% |

    **최종 위험 등급 (가중합)**
    - 안전(0) : weighted_risk < 0.5
    - 주의(1) : 0.5 ≤ weighted_risk < 1.2
    - 위험(2) : weighted_risk ≥ 1.2

    **참고 문헌**
    - 국립중앙박물관 보존환경 기준 (목재: 온도 15 ~ 25℃, 습도 45 ~ 65%)
    - 문화재보존을 위한 온습도 기준, 헤리티지:역사와 과학, 1971
    - 환경부 미세먼지 예보 기준 (PM10: 좋음<30, 보통<80, 나쁨≥80)
    """)

st.caption("제6회 학생 SW·AI 인재양성 프로젝트 | 선화여고 - 영천 헤리티지 AI 탐구단")

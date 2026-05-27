import streamlit as st
import pandas as pd
import numpy as np
import requests
import os
import urllib.parse
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

# 시계열 변수 계산을 위해 날짜 구간 정의 (어제 기준 최근 3일간)
now = datetime.now(ZoneInfo("Asia/Seoul"))
end_date_dt = now - timedelta(days=1)       # 어제 (종료일)
start_date_dt = now - timedelta(days=3)     # 3일 전 (시작일)

end_date = end_date_dt.strftime("%Y%m%d")      # 예: 20260526
start_date = start_date_dt.strftime("%Y%m%d")  # 예: 20260524

if 'danger_count' not in st.session_state:
    st.session_state['danger_count'] = 0

# ==========================================================
# 1. 파생변수 생성 및 위험도 분류 함수 (논문 기반)
# ==========================================================

def add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """온습도·공기질 데이터프레임에 파생변수를 추가하여 반환"""
    df = df.copy().sort_values('date').reset_index(drop=True)
    
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
    """재질별 추가 위험 보정값"""
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
        'avg_temperature_c':        'temp',
        'daily_precipitation_mm':  'rainfall',
        'avg_wind_speed_ms':       'wind',
        'avg_relative_humidity_pct': 'humidity'
    })

    w_df["date"] = pd.to_datetime(w_df["date"])
    a_df["date"] = pd.to_datetime(a_df["date"])
    m_df = pd.merge(w_df, a_df, on="date", how="inner").ffill()

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
# 3. 실시간 데이터 수집 (안전한 시계열 수집 및 포맷 통일)
# ==========================================================
weather_list = []
try:
    asos_params = {
        "serviceKey": SERVICE_KEY, "numOfRows": "3", "dataType": "JSON",
        "dataCd": "ASOS", "dateCd": "DAY",
        "startDt": start_date, "endDt": end_date,
        "stnIds": "281"
    }
    res = requests.get(
        "https://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList",
        params=asos_params, timeout=10
    ).json()
    items = res["response"]["body"]["items"]["item"]
    
    for item in items:
        rf = item.get("sumRn", "0.0")
        if rf == "" or rf is None: rf = "0.0"
        date_str = datetime.strptime(item["tm"], "%Y-%m-%d").strftime("%Y-%m-%d")
        weather_list.append({
            "date": date_str,
            "temp": float(item["avgTa"]),
            "humidity": float(item["avgRhm"]),
            "rainfall": float(rf),
            "wind": float(item["avgWs"])
        })
except Exception as e:
    pass

air_list = []
try:
    air_url = "http://apis.data.go.kr/B552584/ArpltnStatsSvc/getMsrstnAcctoRDyrg"
    safe_service_key = urllib.parse.unquote(SERVICE_KEY)
    
    air_params = {
        "serviceKey": safe_service_key, "returnType": "json", "numOfRows": "10",
        "pageNo": "1", "inqBginDt": start_date, "inqEndDt": end_date, "msrstnName": "영천",
    }
    air_response = requests.get(air_url, params=air_params, timeout=15)
    
    if air_response.status_code == 200 and air_response.text.strip().startswith("{"):
        air_data = air_response.json()
        items = air_data["response"]["body"]["items"]
        
        for item in items:
            raw_msur_dt = item.get("msurDt", "")
            if raw_msur_dt:
                date_str = datetime.strptime(raw_msur_dt, "%Y-%m-%d").strftime("%Y-%m-%d")
                air_list.append({
                    "date": date_str,
                    "pm10": float(item.get("pm10Value", 0)),
                    "pm25": float(item.get("pm25Value", 0)),
                    "o3": float(item.get("o3Value", 0)),
                    "no2": float(item.get("no2Value", 0)),
                    "co": float(item.get("coValue", 0)),
                    "so2": float(item.get("so2Value", 0))
                })
except Exception as e:
    pass


# ==========================================================
# 4. [★수정★] 입력 프레임 하단에 최근 3일 검증용 데이터 수동 강제 주입
# ==========================================================
curr_env = {}
curr_raw = {}
tm, data_time = "-", "-"

# 기상/대기 리스트가 API 장애 등으로 비어있을 시를 방지하기 위해 기본 DataFrame 선언
w_df_curr = pd.DataFrame(weather_list) if weather_list else pd.DataFrame(columns=["date","temp","humidity","rainfall","wind"])
a_df_curr = pd.DataFrame(air_list) if air_list else pd.DataFrame(columns=["date","pm10","pm25","o3","no2","co","so2"])

# API 수집본 우선 병합
merged_curr = pd.merge(w_df_curr, a_df_curr, on="date", how="inner")

# [핵심] 질문자님이 제시하신 검증용 고정 3일치 데이터를 데이터프레임으로 구축
test_fixed_data = pd.DataFrame([
    {"date": "2026-05-24", "temp": 18.8, "rainfall": 0.0, "humidity": 75.8, "wind": 1.2, "pm10": 21.0, "pm25": 13.0, "so2": 0.004, "no2": 0.008, "co": 0.3, "o3": 0.044},
    {"date": "2026-05-25", "temp": 22.6, "rainfall": 0.0, "humidity": 74.6, "wind": 1.2, "pm10": 30.0, "pm25": 22.0, "so2": 0.004, "no2": 0.008, "co": 0.3, "o3": 0.044},
    {"date": "2026-05-26", "temp": 23.1, "rainfall": 1.2, "humidity": 77.8, "wind": 1.9, "pm10": 33.0, "pm25": 23.0, "so2": 0.004, "no2": 0.008, "co": 0.3, "o3": 0.044}
])

# 기존 수집 데이터 뒤에 검증용 3일 데이터를 이어 붙입니다.
merged_curr = pd.concat([merged_curr, test_fixed_data], ignore_index=True)

# 중복된 날짜가 있다면 수동 주입한 고정 데이터(나중 데이터)가 유지되도록 처리 후 오름차순 정렬
merged_curr = merged_curr.drop_duplicates(subset=['date'], keep='last')
merged_curr = merged_curr.sort_values('date', ascending=True).reset_index(drop=True)

if len(merged_curr) >= 1:
    # 정렬 완료된 프레임에 시계열 수식 적용 (이로 인해 변화량과 롤링값이 정상 계산됨)
    processed_curr = add_derived_features(merged_curr)
    
    # 정렬 상태이므로 맨 마지막 행인 '2026-05-26' 데이터가 최종 분석 타겟으로 추출됨
    target_row = processed_curr.iloc[-1]
    
    tm = target_row["date"]
    data_time = tm
    
    curr_raw = {k: target_row[k] for k in ["temp", "humidity", "rainfall", "wind", "pm10", "pm25", "so2", "no2", "co", "o3"]}
    curr_env = {k: target_row[k] for k in FEATURES[:-2]} 
else:
    curr_raw = {"temp": 0.0, "humidity": 0.0, "rainfall": 0.0, "wind": 0.0, "pm10": 0.0, "pm25": 0.0, "so2": 0.0, "no2": 0.0, "co": 0.0, "o3": 0.0}
    curr_env = {k: 0.0 for k in FEATURES[:-2]}

# 가중합 및 위험 등급 연산
dew_point = curr_raw["temp"] - ((100 - curr_raw["humidity"]) / 5)
curr_weighted_risk = calc_weighted_risk({**curr_raw, "dew_gap": curr_env.get("dew_gap", 5.0),
                                         "temp_change": curr_env.get("temp_change", 0.0), 
                                         "humidity_change": curr_env.get("humidity_change", 0.0)})
curr_risk_grade = final_classify(curr_weighted_risk)

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

if ai_model and curr_env:
    results = []
    for _, row in heritage_df.iterrows():
        mat   = str(row['재질']).strip()
        exp   = str(row['노출형태']).strip()
        m_code = mat_map.get(mat, 4)
        e_code = exp_map.get(exp, 0)

        input_v = pd.DataFrame([{**curr_env, "mat_code": m_code, "exp_code": e_code}])
        pred    = ai_model.predict(input_v[feature_names])[0]
        prob    = ai_model.predict_proba(input_v[feature_names])[0]

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

st.markdown(
    '<h3 style="font-size:22px; margin-bottom:15px;">🌿 전일 영천 환경 종합 지표 및 분석 요약 (3일 연속성 분석 적용)</h3>',
    unsafe_allow_html=True
)
left, center, right = st.columns([1.4, 2.0, 1.0])

with left:
    st.markdown(f"""
    <div style="{card_style}; position:relative;">
      <div style="{title_style}">🌦 기상 환경 (일평균)</div><hr>
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-top:20px;">
        <div><div style="{label_style}">🌡 평균기온</div><div style="{value_style}">{curr_raw['temp']:.1f} °C</div></div>
        <div><div style="{label_style}">💧 평균습도</div><div style="{value_style}">{curr_raw['humidity']:.1f} %</div></div>
        <div><div style="{label_style}">🌧 일강수량</div><div style="{value_style}">{curr_raw['rainfall']:.1f} mm</div></div>
        <div><div style="{label_style}">💨 평균풍속</div><div style="{value_style}">{curr_raw['wind']:.1f} m/s</div></div>
      </div>
      <div style="{time_style}">⏱ 기준일자: {tm}</div>
    </div>""", unsafe_allow_html=True)

with center:
    st.markdown(f"""
    <div style="{card_style}; position:relative;">
      <div style="{title_style}">🌫 대기오염 현황 (24h 평균)</div><hr>
      <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:20px; margin-top:20px;">
        <div>
          <div style="{label_style}">PM10</div><div style="{value_style}">{curr_raw['pm10']:.0f}</div>
          <div style="{label_style}">O₃</div><div style="{value_style}">{curr_raw['o3']:.3f}</div>
        </div>
        <div>
          <div style="{label_style}">PM2.5</div><div style="{value_style}">{curr_raw['pm25']:.0f}</div>
          <div style="{label_style}">NO₂</div><div style="{value_style}">{curr_raw['no2']:.3f}</div>
        </div>
        <div>
          <div style="{label_style}">CO</div><div style="{value_style}">{curr_raw['co']:.1f}</div>
          <div style="{label_style}">SO₂</div><div style="{value_style}">{curr_raw['so2']:.3f}</div>
        </div>
      </div>
      <div style="{time_style}">⏱ 측정시각: {data_time}</div>
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
        <div style="{label_style}">🌡 일평균 환경 위험지수</div>
        <div style="font-size:18px; font-weight:700; color:{risk_color[curr_label]}; margin-bottom:8px;">
          {curr_weighted_risk:.2f} ({curr_label})
        </div>
        <div style="{label_style}">🚨 고위험 문화재 (예측)</div>
        <div style="{value_style} color:#C62828;">{st.session_state['danger_count']}개</div>
      </div>
      <div style="{time_style}">📍 경북 영천시</div>
    </div>""", unsafe_allow_html=True)

st.divider()

with st.expander("🔬 현재 환경 파생변수 상세 보기 (정밀 연산 적용)", expanded=False):
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("이슬점 (℃)",      f"{dew_point:.1f}")
    d1.metric("결로 위험 간격",   f"{curr_env.get('dew_gap',0):.1f} ℃",
              delta="위험" if curr_env.get('dew_gap',9) < 2 else ("주의" if curr_env.get('dew_gap',9) < 5 else "안전"))
    d2.metric("PM 3일 누적 노출",    f"{curr_env.get('pm_load',0):.1f}")
    d2.metric("가중합 위험지수", f"{curr_weighted_risk:.3f}")
    d3.metric("온도 변화량 (전일대비)", f"{curr_env.get('temp_change',0):.1f} ℃")
    d3.metric("습도 변화량 (전일대비)", f"{curr_env.get('humidity_change',0):.1f} %")
    d4.metric("3일 습도 표준편차",   f"{curr_env.get('humidity_std',0):.2f}")
    d4.metric("3일 곰팡이 위험 등급",  f"{curr_env.get('mold_risk',0)}")

st.divider()

if not res_df.empty:
    st.markdown(
        '<h3 style="font-size:22px; margin-bottom:15px;">📊 AI 위험도 판정 통계 (정밀 파생변수 반영)</h3>',
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
                "### 훼손 위험 지수", min_value=0, max_value=100, format="%f%%"
            ),
        },
        use_container_width=True,
        hide_index=True
    )

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

st.caption("제6회 학생 SW·AI 인재양성 프로젝트 | 선화여고 - 영천 헤리티지 AI 탐구단")

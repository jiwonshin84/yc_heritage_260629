import streamlit as st
import pandas as pd
import numpy as np
import os
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

# ==========================================================
# 1. 보존과학 파생변수 생성 (결측치 처리 강화)
# ==========================================================
def add_heritage_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    
    # 1. 기본 기상/대기 데이터 결측치 채우기 (선형 보간 및 주변값)
    df = df.interpolate(method='linear').ffill().bfill()

    # 2. 파생변수 계산
    df["dew_point"] = df["temp"] - ((100 - df["humidity"]) / 5)
    df["dew_gap"] = df["temp"] - df["dew_point"]
    
    # 목재 부후균 활성 지수
    df["wood_decay_idx"] = np.where(df["temp"] > 2, (df["temp"] - 2) * (df["humidity"] - 30) / 100, 0)
    
    # 석재 풍화 지수
    df["stone_weathering_idx"] = (df.get("so2", 0) * 100) + (df.get("no2", 0) * 50) + (df["rainfall"] * 0.1)
    
    # 미세먼지 누적 노출 (Rolling 연산 후 발생하는 NaN 즉시 처리)
    df["pm_impact"] = (df["pm10"] * 0.7 + df["pm25"] * 0.3).rolling(window=3, min_periods=1).mean()
    
    # 3. 최종 무한대(inf) 값 및 혹시 모를 결측치 제거
    df = df.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    return df

# ==========================================================
# 2. 4단계 위험도 라벨링 함수
# ==========================================================
def label_risk_4step(row):
    score = 0
    if row["humidity"] >= 80 or row["humidity"] < 30: score += 0.35
    elif row["humidity"] >= 70 or row["humidity"] < 40: score += 0.15
    
    if row["temp"] > 33 or row["temp"] < -5: score += 0.25
    if row["dew_gap"] < 2: score += 0.3
    if row["pm10"] > 100: score += 0.2
    
    # 연령 가중치 (데이터에 '문화재연령'이 없는 경우 대비 0 처리)
    age = row.get("문화재연령", 0)
    age_boost = 0.25 if age > 500 else (0.1 if age > 100 else 0)
    
    # 노출 형태 보정
    exp = row.get("노출형태", "실외")
    exp_mult = 1.3 if exp == "실외" else (1.0 if exp == "반실외" else 0.6)
    
    final_idx = (score + age_boost) * exp_mult
    
    if final_idx >= 1.1: return 3
    elif final_idx >= 0.7: return 2
    elif final_idx >= 0.3: return 1
    else: return 0

# ==========================================================
# 3. 모델 학습 (오류 방지 로직 포함)
# ==========================================================
@st.cache_resource
def train_full_historical_model():
    path = "data/processed/"
    try:
        # 데이터 로드
        weather_df = pd.read_csv(path + "[2016_2025] yeongcheon_weather_daily.csv").rename(columns={
            'avg_temperature_c': 'temp', 'daily_precipitation_mm': 'rainfall',
            'avg_wind_speed_ms': 'wind', 'avg_relative_humidity_pct': 'humidity'
        })
        air_df = pd.read_csv(path + "[2019_2025] air_quality.csv")
        heritage_meta = pd.read_csv(path + "yc_heritage_feature.csv")
        
        weather_df["date"] = pd.to_datetime(weather_df["date"])
        air_df["date"] = pd.to_datetime(air_df["date"])
        
        # 병합
        merged_env = pd.merge(weather_df, air_df, on="date", how="inner").sort_values("date")
        
        # 파생변수 생성 및 결측치 완전 제거
        merged_env = add_heritage_features(merged_env)
        
        le_mat = LabelEncoder().fit(['목조', '석조', '금속', '벽화', '기타', '지석묘', '석탑'])
        le_exp = LabelEncoder().fit(['실외', '실내', '반실외'])
        
        train_rows = []
        # 메모리와 학습 속도를 위해 샘플링 (전체 데이터 중 1500일치 무작위 추출)
        sampled_env = merged_env.sample(n=min(1500, len(merged_env)), random_state=42)

        for _, h in heritage_meta.iterrows():
            for _, e in sampled_env.iterrows():
                row_combined = {**h.to_dict(), **e.to_dict()}
                target = label_risk_4step(row_combined)
                
                train_rows.append({
                    "age": h.get("문화재연령", 0),
                    "mat_code": le_mat.transform([h["재질"]])[0] if h["재질"] in le_mat.classes_ else 4,
                    "exp_code": le_exp.transform([h["노출형태"]])[0] if h["노출형태"] in le_exp.classes_ else 0,
                    "temp": e["temp"], "humidity": e["humidity"],
                    "dew_gap": e["dew_gap"], "pm_impact": e["pm_impact"],
                    "wood_decay": e["wood_decay_idx"], "stone_weather": e["stone_weathering_idx"],
                    "target": target
                })
        
        tdf = pd.DataFrame(train_rows)
        
        # [핵심] 학습 전 마지막 결측치 검사 및 제거
        tdf = tdf.replace([np.inf, -np.inf], np.nan).dropna()
        
        X = tdf.drop("target", axis=1)
        y = tdf["target"]
        
        model = RandomForestClassifier(n_estimators=100, class_weight="balanced", random_state=42)
        model.fit(X, y)
        
        return model, X.columns.tolist(), le_mat, le_exp, merged_env

    except Exception as e:
        st.error(f"❌ 학습 중 에러 발생: {e}")
        return None, None, None, None, None

# 모델 실행
model, features, le_mat, le_exp, env_history = train_full_historical_model()

# ==========================================================
# 4. 결과 출력 UI
# ==========================================================
st.title("🏛️ 영천 헤리티지 AI: 정밀 위험 예측 모델")

if model:
    st.info(f"💡 2019~2025 빅데이터 학습 완료 (총 {len(env_history)}일치 기후 패턴 학습)")
    
    # 테스트용 슬라이더
    c_temp = st.sidebar.slider("기온", -10.0, 40.0, 15.0)
    c_hum = st.sidebar.slider("습도", 0, 100, 50)
    
    # ... 이후 대시보드 및 결과 테이블 출력 로직 (이전 답변과 동일)

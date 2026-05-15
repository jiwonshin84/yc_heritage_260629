import streamlit as st
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import LabelEncoder

# ==========================================================
# 0. 경로 자동 최적화 (GitHub 구조 반영)
# ==========================================================
def get_absolute_path(filename):
    """스크립트 위치를 기준으로 data/processed/ 경로 내의 파일 절대경로 반환"""
    # 현재 파일의 부모의 부모 디렉토리를 기준으로 탐색 (pages 폴더에 있을 경우를 대비)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(current_dir, "..")) # 루트(yc_heritage_project)로 이동
    
    # 후보 경로 리스트
    candidate_paths = [
        os.path.join(root_dir, "data", "processed", filename),  # 루트 기준
        os.path.join(current_dir, "data", "processed", filename), # 현재 폴더 기준
        os.path.join("data", "processed", filename),             # 상대 경로
    ]
    
    for p in candidate_paths:
        if os.path.exists(p):
            return p
    return None

# ==========================================================
# 1. 데이터 정제 및 보존과학 알고리즘
# ==========================================================
def preprocess_env_data(df):
    """기상/대기 결측치 제거 및 파생변수 생성"""
    df = df.copy()
    # 결측치 보간
    df = df.interpolate(method='linear').ffill().bfill()
    
    # 보존과학 지수 계산
    df["dew_point"] = df["temp"] - ((100 - df["humidity"]) / 5)
    df["dew_gap"] = df["temp"] - df["dew_point"]
    df["wood_decay"] = np.where(df["temp"] > 2, (df["temp"] - 2) * (df["humidity"] - 30) / 100, 0)
    df["stone_weather"] = (df.get("so2", 0) * 100) + (df.get("no2", 0) * 50) + (df["rainfall"] * 0.1)
    df["pm_impact"] = (df["pm10"] * 0.7 + df["pm25"] * 0.3).rolling(window=3, min_periods=1).mean()
    
    return df.replace([np.inf, -np.inf], np.nan).fillna(0)

def label_risk_4step(row):
    """논문 기반 4단계 위험도 라벨링"""
    score = 0
    if row["humidity"] >= 80 or row["humidity"] < 30: score += 0.35
    if row["temp"] > 33 or row["temp"] < -5: score += 0.25
    if row["dew_gap"] < 2: score += 0.3
    if row["pm10"] > 100: score += 0.2
    
    age = row.get("문화재연령", 0)
    age_boost = 0.25 if age > 500 else (0.1 if age > 100 else 0)
    exp_mult = 1.3 if row.get("노출형태", "실외") == "실외" else (1.0 if row.get("노출형태", "반실외") == "반실외" else 0.6)
    
    total = (score + age_boost) * exp_mult
    if total >= 1.1: return 3   # 🚨 위험
    elif total >= 0.7: return 2  # ⚠️ 주의
    elif total >= 0.3: return 1  # 🟡 관심
    else: return 0               # ✅ 안전

# ==========================================================
# 2. 3대 모델 전수 학습 (2019-2025)
# ==========================================================
@st.cache_resource
def train_and_compare_models():
    # 파일 경로 자동 확보
    p_w = get_absolute_path("[2016_2025] yeongcheon_weather_daily.csv")
    p_a = get_absolute_path("[2019_2025] air_quality.csv")
    p_h = get_absolute_path("yc_heritage_feature.csv")

    if not all([p_w, p_a, p_h]):
        return None, None, None, None

    # 데이터 로딩 및 병합
    w_df = pd.read_csv(p_w).rename(columns={'avg_temperature_c': 'temp', 'daily_precipitation_mm': 'rainfall', 'avg_relative_humidity_pct': 'humidity'})
    a_df = pd.read_csv(p_a)
    h_meta = pd.read_csv(p_h)
    
    w_df["date"], a_df["date"] = pd.to_datetime(w_df["date"]), pd.to_datetime(a_df["date"])
    merged = pd.merge(w_df, a_df, on="date", how="inner").sort_values("date")
    merged = preprocess_env_data(merged)
    
    # 인코딩 및 학습 데이터 생성
    le_mat = LabelEncoder().fit(['목조', '석조', '금속', '벽화', '기타', '지석묘', '석탑'])
    le_exp = LabelEncoder().fit(['실외', '실내', '반실외'])
    
    train_data = []
    # 2019-2025 전체 기간 중 1500일 샘플링 학습
    sampled_env = merged.sample(n=min(1500, len(merged)), random_state=42)
    
    for _, h in h_meta.iterrows():
        for _, e in sampled_env.iterrows():
            combined_row = {**h.to_dict(), **e.to_dict()}
            train_data.append({
                "age": h.get("문화재연령", 0),
                "mat_code": le_mat.transform([h["재질"]])[0] if h["재질"] in le_mat.classes_ else 4,
                "exp_code": le_exp.transform([h["노출형태"]])[0] if h["노출형태"] in le_exp.classes_ else 0,
                "temp": e["temp"], "humidity": e["humidity"], "dew_gap": e["dew_gap"],
                "wood_decay": e["wood_decay"], "stone_weather": e["stone_weather"], "pm_impact": e["pm_impact"],
                "target": label_risk_4step(combined_row)
            })
            
    tdf = pd.DataFrame(train_data).dropna()
    X = tdf.drop("target", axis=1)
    y = tdf["target"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 3대 모델 정의
    model_dict = {
        "Random Forest": RandomForestClassifier(n_estimators=100, random_state=42),
        "Gradient Boosting": GradientBoostingClassifier(n_estimators=100, random_state=42),
        "Decision Tree": DecisionTreeClassifier(random_state=42)
    }

    results = {}
    for name, mdl in model_dict.items():
        mdl.fit(X_train, y_train)
        acc = accuracy_score(y_test, mdl.predict(X_test))
        results[name] = {"model": mdl, "accuracy": acc}
    
    return results, X.columns.tolist(), le_mat, le_exp

# ==========================================================
# 3. 메인 대시보드 화면
# ==========================================================
st.title("🧪 영천 문화재 훼손 위험 모델 분석 (2019-2025)")

with st.spinner("영천 빅데이터 기반 모델 학습 중..."):
    results, feat_cols, le_mat, le_exp = train_and_compare_models()

if results:
    # 모델 성능 시각화
    st.subheader("📊 3대 모델 예측 정확도(Accuracy) 비교")
    acc_df = pd.DataFrame({"Model": list(results.keys()), "Accuracy": [v["accuracy"] for v in results.values()]})
    
    fig, ax = plt.subplots(figsize=(10, 4))
    sns.barplot(x="Accuracy", y="Model", data=acc_df, palette="magma", ax=ax)
    st.pyplot(fig)

    # 피처 중요도 분석
    st.subheader("🔎 위험 등급 판단의 주요 변수 (Random Forest)")
    fi = results["Random Forest"]["model"].feature_importances_
    fi_df = pd.DataFrame({'지표': feat_cols, '중요도': fi}).sort_values('중요도', ascending=True)
    st.bar_chart(fi_df.set_index('지표'))

    # 실시간 예측 시뮬레이션
    st.divider()
    st.sidebar.header("📡 실시간 영천 환경")
    curr_t = st.sidebar.slider("기온", -10.0, 40.0, 18.0)
    curr_h = st.sidebar.slider("습도", 0, 100, 65)
    curr_p = st.sidebar.slider("미세먼지", 0, 200, 35)

    # 최적 모델(성능 제일 높은 것) 선택
    best_name = acc_df.loc[acc_df['Accuracy'].idxmax(), 'Model']
    best_mdl = results[best_name]["model"]

    h_path = get_absolute_path("yc_heritage_feature.csv")
    h_df = pd.read_csv(h_path)
    
    predict_list = []
    for _, h in h_df.iterrows():
        d_gap = curr_t - (curr_t - ((100 - curr_h) / 5))
        input_data = pd.DataFrame([{
            "age": h["문화재연령"],
            "mat_code": le_mat.transform([h["재질"]])[0] if h["재질"] in le_mat.classes_ else 4,
            "exp_code": le_exp.transform([h["노출형태"]])[0] if h["노출형태"] in le_exp.classes_ else 0,
            "temp": curr_t, "humidity": curr_h, "dew_gap": d_gap,
            "wood_decay": max(0, (curr_t-2)*(curr_h-30)/100),
            "stone_weather": (curr_p * 0.1), "pm_impact": curr_p
        }])
        
        pred = best_mdl.predict(input_data)[0]
        status = {0: "✅ 안전", 1: "🟡 관심", 2: "⚠️ 주의", 3: "🚨 위험"}[pred]
        predict_list.append({"문화재명": h["문화재명(국문)"], "재질": h["재질"], "위험등급": status, "분석모델": best_name})

    st.subheader(f"🏛️ {best_name} 모델 기반 실시간 위험도 예측")
    st.table(pd.DataFrame(predict_list))

else:
    st.error("파일 경로를 찾을 수 없습니다. GitHub의 data/processed/ 폴더 내에 CSV 파일이 있는지 다시 확인해주세요.")

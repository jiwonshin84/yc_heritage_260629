import streamlit as st
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import LabelEncoder

# ==========================================================
# 1. 환경 및 데이터 정제 설정
# ==========================================================
st.set_page_config(page_title="영천 헤리티지 AI 모델 분석", layout="wide")

def clean_and_feature_engineering(env_df):
    """환경 데이터 정제 및 보존과학 파생변수 생성"""
    df = env_df.copy()
    # 선형 보간으로 결측치 처리 후 앞뒤 값으로 채움
    df = df.interpolate(method='linear').ffill().bfill()
    
    # 파생변수: 결로 지수, 목재 부후 지수, 석재 풍화 지수
    df["dew_point"] = df["temp"] - ((100 - df["humidity"]) / 5)
    df["dew_gap"] = df["temp"] - df["dew_point"]
    df["wood_decay"] = np.where(df["temp"] > 2, (df["temp"] - 2) * (df["humidity"] - 30) / 100, 0)
    df["stone_weather"] = (df.get("so2", 0) * 100) + (df.get("no2", 0) * 50) + (df["rainfall"] * 0.1)
    df["pm_impact"] = (df["pm10"] * 0.7 + df["pm25"] * 0.3).rolling(window=3, min_periods=1).mean()
    
    # 무한대 값 및 잔여 결측치 0 처리
    df = df.replace([np.inf, -np.inf], np.nan).fillna(0)
    return df

def label_risk_4step(row):
    """4단계 위험도 라벨링 (0:안전, 1:관심, 2:주의, 3:위험)"""
    score = 0
    if row["humidity"] >= 80 or row["humidity"] < 30: score += 0.35
    elif row["humidity"] >= 70 or row["humidity"] < 40: score += 0.15
    if row["temp"] > 33 or row["temp"] < -5: score += 0.25
    if row["dew_gap"] < 2: score += 0.3
    if row["pm10"] > 100: score += 0.2
    
    age_boost = 0.25 if row.get("문화재연령", 0) > 500 else (0.1 if row.get("문화재연령", 0) > 100 else 0)
    exp_mult = 1.3 if row.get("노출형태", "실외") == "실외" else (1.0 if row.get("노출형태", "반실외") == "반실외" else 0.6)
    
    final_idx = (score + age_boost) * exp_mult
    if final_idx >= 1.1: return 3
    elif final_idx >= 0.7: return 2
    elif final_idx >= 0.3: return 1
    else: return 0

# ==========================================================
# 2. 3대 모델 통합 학습 함수
# ==========================================================
@st.cache_resource
def train_and_compare_models():
    path = "yc_heritage_project/data/processed/"
    # 데이터 로드
    w = pd.read_csv(path + "[2016_2025] yeongcheon_weather_daily.csv").rename(columns={
        'avg_temperature_c': 'temp', 'daily_precipitation_mm': 'rainfall', 'avg_relative_humidity_pct': 'humidity'
    })
    a = pd.read_csv(path + "[2019_2025] air_quality.csv")
    h_meta = pd.read_csv(path + "yc_heritage_feature.csv")
    
    w["date"], a["date"] = pd.to_datetime(w["date"]), pd.to_datetime(a["date"])
    env_merged = pd.merge(w, a, on="date", how="inner").sort_values("date")
    env_merged = clean_and_feature_engineering(env_merged)
    
    # 학습 데이터 생성 (샘플링을 통한 성능 최적화)
    le_mat = LabelEncoder().fit(['목조', '석조', '금속', '벽화', '기타', '지석묘', '석탑'])
    le_exp = LabelEncoder().fit(['실외', '실내', '반실외'])
    
    train_rows = []
    sampled_env = env_merged.sample(n=min(1000, len(env_merged)), random_state=42)
    
    for _, h in h_meta.iterrows():
        for _, e in sampled_env.iterrows():
            combined = {**h.to_dict(), **e.to_dict()}
            train_rows.append({
                "age": h.get("문화재연령", 0),
                "mat_code": le_mat.transform([h["재질"]])[0] if h["재질"] in le_mat.classes_ else 4,
                "exp_code": le_exp.transform([h["노출형태"]])[0] if h["노출형태"] in le_exp.classes_ else 0,
                "temp": e["temp"], "humidity": e["humidity"], "dew_gap": e["dew_gap"],
                "wood_decay": e["wood_decay"], "stone_weather": e["stone_weather"], "pm_impact": e["pm_impact"],
                "target": label_risk_4step(combined)
            })
            
    tdf = pd.DataFrame(train_rows).dropna()
    X = tdf.drop("target", axis=1)
    y = tdf["target"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 3가지 모델 정의
    models = {
        "Random Forest": RandomForestClassifier(n_estimators=100, random_state=42),
        "Gradient Boosting": GradientBoostingClassifier(n_estimators=100, random_state=42),
        "Decision Tree": DecisionTreeClassifier(random_state=42)
    }

    results = {}
    for name, mdl in models.items():
        mdl.fit(X_train, y_train)
        y_pred = mdl.predict(X_test)
        results[name] = {
            "model": mdl,
            "accuracy": accuracy_score(y_test, y_pred),
            "report": classification_report(y_test, y_pred, output_dict=True)
        }
    
    return results, X.columns.tolist(), le_mat, le_exp

# 모델 학습 실행
with st.spinner("2019-2025 빅데이터 기반 3대 모델 학습 중..."):
    results, feat_cols, le_mat, le_exp = train_and_compare_models()

# ==========================================================
# 3. 학습 결과 시각화 및 대시보드
# ==========================================================
st.title("🧪 영천 문화재 훼손 모델 비교 분석")

# 1. 성능 비교 지표
col1, col2, col3 = st.columns(3)
for i, (name, res) in enumerate(results.items()):
    cols = [col1, col2, col3]
    cols[i].metric(f"{name} 정확도", f"{res['accuracy']*100:.2f}%")

# 2. 성능 비교 그래프
st.subheader("📊 모델별 정확도(Accuracy) 비교")
acc_df = pd.DataFrame({
    "Model": list(results.keys()),
    "Accuracy": [res["accuracy"] for res in results.values()]
})
fig, ax = plt.subplots(figsize=(10, 4))
sns.barplot(x="Model", y="Accuracy", data=acc_df, palette="viridis", ax=ax)
ax.set_ylim(0, 1.0)
st.pyplot(fig)

# 3. 피처 중요도 분석 (Random Forest 기준)
st.subheader("🔎 위험 판단 주요 결정 요인 (Feature Importance)")
rf_model = results["Random Forest"]["model"]
fi_df = pd.DataFrame({'Feature': feat_cols, 'Importance': rf_model.feature_importances_}).sort_values('Importance', ascending=False)

fig2, ax2 = plt.subplots(figsize=(10, 5))
sns.barplot(x="Importance", y="Feature", data=fi_df, palette="magma", ax=ax2)
st.pyplot(fig2)

# 4. 실시간 문화재별 위험 예측 (최적 모델 적용)
st.divider()
st.subheader("🏛️ 최적 모델 기반 문화재별 실시간 위험도")

# 현재 환경 입력 슬라이더
with st.sidebar:
    st.header("📡 영천 실시간 환경 설정")
    s_temp = st.slider("기온(℃)", -10.0, 40.0, 22.0)
    s_hum = st.slider("습도(%)", 0, 100, 78)
    s_pm = st.slider("미세먼지", 0, 200, 45)

h_df = pd.read_csv("yc_heritage_project/data/processed/yc_heritage_feature.csv")
final_results = []

# 가장 성능이 좋은 모델 선택
best_model_name = max(results, key=lambda k: results[k]['accuracy'])
best_model = results[best_model_name]["model"]

for _, h_row in h_df.iterrows():
    # 파생변수 계산
    d_gap = s_temp - (s_temp - ((100 - s_hum) / 5))
    input_data = pd.DataFrame([{
        "age": h_row["문화재연령"],
        "mat_code": le_mat.transform([h_row["재질"]])[0] if h_row["재질"] in le_mat.classes_ else 4,
        "exp_code": le_exp.transform([h_row["노출형태"]])[0] if h_row["노출형태"] in le_exp.classes_ else 0,
        "temp": s_temp, "humidity": s_hum, "dew_gap": d_gap,
        "wood_decay": max(0, (s_temp-2)*(s_hum-30)/100),
        "stone_weather": (s_pm * 0.1), "pm_impact": s_pm
    }])
    
    pred = best_model.predict(input_data)[0]
    status_map = {0: "✅ 안전", 1: "🟡 관심", 2: "⚠️ 주의", 3: "🚨 위험"}
    
    final_results.append({
        "문화재명": h_row["문화재명(국문)"],
        "재질": h_row["재질"],
        "연령": f"{h_row['문화재연령']}년",
        "예측등급": status_map[pred],
        "분석모델": best_model_name
    })

st.table(pd.DataFrame(final_results))
st.caption("본 분석은 2019-2025 영천 기상/대기 데이터를 기반으로 학습되었습니다.")

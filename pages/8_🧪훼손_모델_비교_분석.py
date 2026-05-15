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
# 0. 경로 최적화 및 폰트 설정
# ==========================================================
def get_path(filename):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(current_dir, ".."))
    paths = [
        os.path.join(root_dir, "data", "processed", filename),
        os.path.join("data", "processed", filename),
        filename
    ]
    for p in paths:
        if os.path.exists(p): return p
    return None

# ==========================================================
# 1. 보존과학 알고리즘 및 4단계 라벨링
# ==========================================================
def preprocess_data(df):
    df = df.copy().interpolate().ffill().bfill()
    df["dew_point"] = df["temp"] - ((100 - df["humidity"]) / 5)
    df["dew_gap"] = df["temp"] - df["dew_point"]
    # 재질별 위험 지수 생성
    df["wood_risk"] = np.where(df["temp"] > 2, (df["temp"] - 2) * (df["humidity"] - 30) / 100, 0)
    df["stone_risk"] = (df.get("so2", 0) * 100) + (df.get("no2", 0) * 50) + (df["rainfall"] * 0.1)
    df["pm_load"] = (df["pm10"] * 0.7 + df["pm25"] * 0.3).rolling(3, min_periods=1).mean()
    return df.replace([np.inf, -np.inf], np.nan).fillna(0)

def label_logic(row):
    score = 0
    if row["humidity"] >= 80 or row["humidity"] < 30: score += 0.35
    if row["temp"] > 33 or row["temp"] < -5: score += 0.25
    if row["dew_gap"] < 2: score += 0.3
    
    age_weight = 0.25 if row.get("문화재연령", 0) > 500 else (0.1 if row.get("문화재연령", 0) > 100 else 0)
    exp_mult = 1.3 if row.get("노출형태", "실외") == "실외" else (1.0 if row.get("노출형태", "반실외") == "반실외" else 0.6)
    
    total = (score + age_weight) * exp_mult
    return 3 if total >= 1.1 else (2 if total >= 0.7 else (1 if total >= 0.3 else 0))

# ==========================================================
# 2. 모델 학습 (2019-2025 전수 데이터)
# ==========================================================
@st.cache_resource
def train_models():
    p_w, p_a, p_h = get_path("[2016_2025] yeongcheon_weather_daily.csv"), get_path("[2019_2025] air_quality.csv"), get_path("yc_heritage_feature.csv")
    if not all([p_w, p_a, p_h]): return None
    
    w_df = pd.read_csv(p_w).rename(columns={'avg_temperature_c': 'temp', 'daily_precipitation_mm': 'rainfall', 'avg_relative_humidity_pct': 'humidity'})
    a_df = pd.read_csv(p_a)
    h_df = pd.read_csv(p_h)
    
    merged = pd.merge(pd.to_datetime(w_df["date"]), w_df, left_index=True, right_index=True) # 중복방지
    merged = pd.merge(w_df, a_df, on="date", how="inner")
    merged = preprocess_data(merged)
    
    le_mat, le_exp = LabelEncoder().fit(['목조', '석조', '금속', '벽화', '기타']), LabelEncoder().fit(['실외', '실내', '반실외'])
    
    data = []
    for _, h in h_df.iterrows():
        for _, e in merged.sample(n=min(1200, len(merged)), random_state=42).iterrows():
            row = {**h.to_dict(), **e.to_dict()}
            data.append({
                "age": h["문화재연령"],
                "mat_code": le_mat.transform([h["재질"]])[0] if h["재질"] in le_mat.classes_ else 4,
                "exp_code": le_exp.transform([h["노출형태"]])[0] if h["노출형태"] in le_exp.classes_ else 0,
                "temp": e["temp"], "humidity": e["humidity"], "dew_gap": e["dew_gap"],
                "wood_risk": e["wood_risk"], "stone_risk": e["stone_risk"], "target": label_logic(row)
            })
            
    df_final = pd.DataFrame(data).dropna()
    X, y = df_final.drop("target", axis=1), df_final["target"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model_pool = {
        "Random Forest": RandomForestClassifier(n_estimators=100, random_state=42),
        "Gradient Boosting": GradientBoostingClassifier(random_state=42),
        "Decision Tree": DecisionTreeClassifier(random_state=42)
    }
    
    res = {}
    for name, mdl in model_pool.items():
        mdl.fit(X_train, y_train)
        res[name] = {"model": mdl, "acc": accuracy_score(y_test, mdl.predict(X_test))}
    return res, X.columns.tolist(), le_mat, le_exp

# ==========================================================
# 3. 시각화 대시보드
# ==========================================================
st.title("🧪 영천 헤리티지 AI 모델 비교 및 재질별 분석")

results, feat_names, le_mat, le_exp = train_models()

if results:
    # 1. 모델 정확도 비교 (수치 포함 꺾은선/점 그래프)
    st.subheader("📊 1. 모델별 예측 정확도 비교")
    acc_data = pd.DataFrame({"Model": results.keys(), "Accuracy": [v["acc"] for v in results.values()]})
    
    fig1, ax1 = plt.subplots(figsize=(10, 5))
    sns.pointplot(x="Model", y="Accuracy", data=acc_data, markers="o", linestyles="-", color="#2c3e50", ax=ax1)
    for i, v in enumerate(acc_data["Accuracy"]):
        ax1.text(i, v + 0.01, f"{v*100:.2f}%", ha='center', fontweight='bold', color='red')
    ax1.set_ylim(acc_data["Accuracy"].min() - 0.05, 1.0)
    ax1.grid(True, linestyle='--', alpha=0.6)
    st.pyplot(fig1)

    # 2. 재질별 변수 중요도 분석 (재질 코드에 따른 가중치 시각화)
    st.subheader("🔎 2. 재질 및 환경별 위험 결정 중요도")
    # RF 모델의 중요도 추출
    importance = results["Random Forest"]["model"].feature_importances_
    
    # 지표 한글 매핑
    kor_feats = {
        "age": "문화재 연령", "mat_code": "재질 유형", "exp_code": "노출 형태",
        "temp": "현재 기온", "humidity": "현재 습도", "dew_gap": "결로 위험(이슬점)",
        "wood_risk": "목조 부후 지수", "stone_risk": "석조 풍화 지수"
    }
    
    fi_df = pd.DataFrame({'지표': [kor_feats.get(f, f) for f in feat_names], '중요도': importance}).sort_values('중요도', ascending=True)

    fig2, ax2 = plt.subplots(figsize=(10, 6))
    # 재질 관련 지표는 강조색 처리
    colors = ['#f39c12' if '재질' in x or '목조' in x or '석조' in x else '#3498db' for x in fi_df['지표']]
    ax2.barh(fi_df['지표'], fi_df['중요도'], color=colors)
    for i, v in enumerate(fi_df['중요도']):
        ax2.text(v + 0.005, i, f"{v:.3f}", va='center')
    st.pyplot(fig2)
    st.info("💡 **분석:** 주황색 지표는 AI가 '재질'의 특성을 환경과 결합하여 위험도를 산출할 때 사용하는 핵심 데이터입니다.")

    # 3. 실시간 예측 결과
    st.divider()
    st.subheader("🏛️ 최적 모델 기반 실시간 위험도 (4단계)")
    
    with st.sidebar:
        st.header("⚙️ 환경 설정")
        t, h, p = st.slider("기온", -10.0, 40.0, 25.0), st.slider("습도", 0, 100, 85), st.slider("미세먼지", 0, 200, 50)

    best_mdl_name = max(results, key=lambda k: results[k]['acc'])
    best_mdl = results[best_mdl_name]["model"]
    
    h_df = pd.read_csv(get_path("yc_heritage_feature.csv"))
    final_res = []
    for _, r in h_df.iterrows():
        dg = t - (t - ((100 - h) / 5))
        inp = pd.DataFrame([{
            "age": r["문화재연령"], 
            "mat_code": le_mat.transform([r["재질"]])[0] if r["재질"] in le_mat.classes_ else 4,
            "exp_code": le_exp.transform([r["노출형태"]])[0] if r["노출형태"] in le_exp.classes_ else 0,
            "temp": t, "humidity": h, "dew_gap": dg,
            "wood_risk": max(0, (t-2)*(h-30)/100), "stone_risk": (p * 0.1)
        }])
        pred = best_mdl.predict(inp)[0]
        final_res.append({"문화재명": r["문화재명(국문)"], "재질": r["재질"], "예측등급": {0:"✅ 안전", 1:"🟡 관심", 2:"⚠️ 주의", 3:"🚨 위험"}[pred]})

    st.table(pd.DataFrame(final_res))

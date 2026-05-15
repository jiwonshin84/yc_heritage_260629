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
import platform
from matplotlib import font_manager, rc

# ==========================================================
# 0. 한글 폰트 설정 및 경로 최적화
# ==========================================================
@st.cache_resource
def set_korean_font():
    try:
        if platform.system() == 'Windows':
            font_name = font_manager.FontProperties(family='Malgun Gothic').get_name()
            rc('font', family=font_name)
        else:
            plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['axes.unicode_minus'] = False
    except:
        pass

set_korean_font()

def get_path(filename):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(current_dir, ".."))
    paths = [os.path.join(root_dir, "data", "processed", filename),
             os.path.join("data", "processed", filename), filename]
    for p in paths:
        if os.path.exists(p): return p
    return None

# ==========================================================
# 1. 데이터 정제 및 고도화된 라벨링 로직
# ==========================================================
def preprocess_env_data(df):
    df = df.copy()
    # 수치형 데이터 보간 (TypeError 방지)
    num_cols = df.select_dtypes(include=[np.number]).columns
    df[num_cols] = df[num_cols].interpolate(method='linear').ffill().bfill()
    # 비수치형 데이터 채우기
    non_num_cols = df.select_dtypes(exclude=[np.number]).columns
    df[non_num_cols] = df[non_num_cols].ffill().bfill()
    
    # [중요] 라벨링을 위한 내부 계산 (학습 변수에는 포함하지 않음)
    df["dew_point"] = df["temp"] - ((100 - df["humidity"]) / 5)
    df["dew_gap"] = df["temp"] - df["dew_point"]
    return df.replace([np.inf, -np.inf], np.nan).fillna(0)

def label_logic(row):
    """보존과학 논문 기반 위험 등급 생성 (모델이 맞춰야 할 정답)"""
    score = 0
    if row["humidity"] >= 80 or row["humidity"] < 30: score += 0.35
    if row["temp"] > 33 or row["temp"] < -5: score += 0.25
    if row["dew_gap"] < 2: score += 0.3
    age_w = 0.25 if row.get("문화재연령", 0) > 500 else (0.1 if row.get("문화재연령", 0) > 100 else 0)
    exp_m = 1.3 if row.get("노출형태", "실외") == "실외" else (1.0 if row.get("노출형태", "반실외") == "반실외" else 0.6)
    total = (score + age_w) * exp_m
    return 3 if total >= 1.1 else (2 if total >= 0.7 else (1 if total >= 0.3 else 0))

# ==========================================================
# 2. 모델 학습 (순수 데이터만 사용하여 응용 능력 강화)
# ==========================================================
@st.cache_resource
def train_intelligent_models():
    p_w, p_a, p_h = get_path("[2016_2025] yeongcheon_weather_daily.csv"), get_path("[2019_2025] air_quality.csv"), get_path("yc_heritage_feature.csv")
    if not all([p_w, p_a, p_h]): return None, None, None, None

    w_df = pd.read_csv(p_w).rename(columns={'avg_temperature_c': 'temp', 'daily_precipitation_mm': 'rainfall', 'avg_relative_humidity_pct': 'humidity'})
    a_df = pd.read_csv(p_a)
    h_df = pd.read_csv(p_h)
    
    merged = pd.merge(pd.to_datetime(w_df["date"]), w_df, left_index=True, right_index=True)
    merged = pd.merge(w_df, a_df, on="date", how="inner")
    merged = preprocess_env_data(merged)
    
    le_mat = LabelEncoder().fit(['목조', '석조', '금속', '벽화', '기타', '지석묘', '석탑'])
    le_exp = LabelEncoder().fit(['실외', '실내', '반실외'])
    
    data = []
    sampled_env = merged.sample(n=min(1500, len(merged)), random_state=42)
    
    for _, h in h_df.iterrows():
        for _, e in sampled_env.iterrows():
            row = {**h.to_dict(), **e.to_dict()}
            # [응용 학습 핵심] : dew_gap, wood_risk 등 결과론적인 지표는 제외함
            data.append({
                "age": h["문화재연령"],
                "mat_code": le_mat.transform([h["재질"]])[0] if h["재질"] in le_mat.classes_ else 4,
                "exp_code": le_exp.transform([h["노출형태"]])[0] if h["노출형태"] in le_exp.classes_ else 0,
                "temp": e["temp"], 
                "humidity": e["humidity"], 
                "rainfall": e["rainfall"],
                "pm10": e["pm10"],
                "target": label_logic(row)
            })
            
    df_final = pd.DataFrame(data).dropna()
    X = df_final.drop("target", axis=1)
    y = df_final["target"]
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

with st.spinner("빅데이터 기반 '응용 학습' 진행 중..."):
    results, feat_names, le_mat, le_exp = train_intelligent_models()

# ==========================================================
# 3. 결과 시각화 (정확도 및 지표 분석)
# ==========================================================
st.title("🏛️ 영천 헤리티지 AI: 고지능형 위험 예측 모델 분석")

if results:
    # 1. 모델 정확도 비교 (현실적인 수치 표시)
    st.subheader("📊 1. 알고리즘별 예측 정확도 (응용 학습 결과)")
    acc_df = pd.DataFrame({"Model": results.keys(), "Accuracy": [v["acc"] for v in results.values()]})
    
    fig1, ax1 = plt.subplots(figsize=(10, 5))
    sns.lineplot(x="Model", y="Accuracy", data=acc_df, marker="o", markersize=12, ax=ax1, linewidth=3, color='#2c3e50')
    for i, v in enumerate(acc_df["Accuracy"]):
        ax1.text(i, v + 0.005, f"{v*100:.2f}%", ha='center', fontweight='bold', color='#e74c3c', fontsize=12)
    ax1.set_ylim(0.7, 1.05) # 정확도가 100%가 아님을 시각적으로 표현
    st.pyplot(fig1)
    st.caption("💡 직접적인 계산 지표를 제외하여 모델이 스스로 환경 데이터를 해석하도록 학습되었습니다.")

    # 2. 중요도 분석
    st.subheader("🔎 2. 위험 등급 판단의 핵심 기초 변수")
    importance = results["Random Forest"]["model"].feature_importances_
    kor_map = {"age": "문화재 연령", "mat_code": "재질 유형", "exp_code": "노출 형태", "temp": "기온", "humidity": "습도", "rainfall": "강수량", "pm10": "미세먼지(PM10)"}
    
    fi_df = pd.DataFrame({'지표': [kor_map.get(f, f) for f in feat_names], '중요도': importance}).sort_values('중요도', ascending=True)
    
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    colors = ['#f39c12' if any(k in x for k in ['재질', '연령']) else '#3498db' for x in fi_df['지표']]
    bars = ax2.barh(fi_df['지표'], fi_df['중요도'], color=colors)
    for bar in bars:
        ax2.text(bar.get_width() + 0.005, bar.get_y() + bar.get_height()/2, f'{bar.get_width():.3f}', va='center', fontweight='bold')
    st.pyplot(fig2)

    # 3. 실시간 예측 테이블
    st.divider()
    best_name = max(results, key=lambda k: results[k]['acc'])
    st.subheader(f"🏟️ {best_name} 모델의 실시간 지능형 예측")
    
    with st.sidebar:
        st.header("⚙️ 실시간 환경 설정")
        t, h, r, p = st.slider("기온(℃)", -10.0, 40.0, 20.0), st.slider("습도(%)", 0, 100, 85), st.slider("강수량(mm)", 0, 100, 0), st.slider("미세먼지", 0, 200, 40)

    h_df = pd.read_csv(get_path("yc_heritage_feature.csv"))
    final_view = []
    for _, row in h_df.iterrows():
        # [예측 시에도 순수 데이터만 입력]
        inp = pd.DataFrame([{
            "age": row["문화재연령"], 
            "mat_code": le_mat.transform([row["재질"]])[0] if row["재질"] in le_mat.classes_ else 4,
            "exp_code": le_exp.transform([row["노출형태"]])[0] if row["노출형태"] in le_exp.classes_ else 0,
            "temp": t, "humidity": h, "rainfall": r, "pm10": p
        }])
        pred = results[best_name]["model"].predict(inp)[0]
        final_view.append({"문화재명": row["문화재명(국문)"], "재질": row["재질"], "연령": f"{row['문화재연령']}년", "예측등급": {0:"✅ 안전", 1:"🟡 관심", 2:"⚠️ 주의", 3:"🚨 위험"}[pred]})

    st.table(pd.DataFrame(final_view))

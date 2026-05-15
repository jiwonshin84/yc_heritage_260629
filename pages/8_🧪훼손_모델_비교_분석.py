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
# 0. 한글 폰트 설정 (Streamlit Cloud 및 로컬 공용)
# ==========================================================
@st.cache_resource
def set_korean_font():
    try:
        if platform.system() == 'Windows':
            font_name = font_manager.FontProperties(family='Malgun Gothic').get_name()
            rc('font', family=font_name)
        elif platform.system() == 'Darwin': # macOS
            rc('font', family='AppleGothic')
        else: # Linux/Streamlit Cloud
            # 시스템에 설치된 나눔 폰트 등이 있다면 사용, 없으면 기본 폰트 설정
            plt.rcParams['font.family'] = 'sans-serif'
            # 한글이 깨지는 경우를 대비해 깨짐 방지 설정만 적용
        plt.rcParams['axes.unicode_minus'] = False
    except:
        st.warning("한글 폰트 설정에 실패했습니다. 영문으로 표시될 수 있습니다.")

set_korean_font()

# ==========================================================
# 1. 경로 최적화 및 데이터 정제
# ==========================================================
def get_path(filename):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(current_dir, ".."))
    paths = [os.path.join(root_dir, "data", "processed", filename),
             os.path.join("data", "processed", filename), filename]
    for p in paths:
        if os.path.exists(p): return p
    return None

def preprocess_data(df):
    df = df.copy()
    num_cols = df.select_dtypes(include=[np.number]).columns
    df[num_cols] = df[num_cols].interpolate().ffill().bfill()
    df["dew_point"] = df["temp"] - ((100 - df["humidity"]) / 5)
    df["dew_gap"] = df["temp"] - df["dew_point"]
    df["wood_risk"] = np.where(df["temp"] > 2, (df["temp"] - 2) * (df["humidity"] - 30) / 100, 0)
    df["stone_risk"] = (df.get("so2", 0) * 100) + (df.get("no2", 0) * 50) + (df["rainfall"] * 0.1)
    return df.replace([np.inf, -np.inf], np.nan).fillna(0)

def label_logic(row):
    # 정확도 100% 방지를 위해 약간의 랜덤 노이즈나 복잡한 로직을 가정할 수 있으나, 
    # 현재는 수식에 의해 결정되므로 모델이 이 수식을 완벽히 학습(Overfitting)하는 것입니다.
    score = 0
    if row["humidity"] >= 80 or row["humidity"] < 30: score += 0.35
    if row["temp"] > 33 or row["temp"] < -5: score += 0.25
    if row["dew_gap"] < 2: score += 0.3
    age_weight = 0.25 if row.get("문화재연령", 0) > 500 else (0.1 if row.get("문화재연령", 0) > 100 else 0)
    exp_mult = 1.3 if row.get("노출형태", "실외") == "실외" else (1.0 if row.get("노출형태", "반실외") == "반실외" else 0.6)
    total = (score + age_weight) * exp_mult
    return 3 if total >= 1.1 else (2 if total >= 0.7 else (1 if total >= 0.3 else 0))

# ==========================================================
# 2. 모델 학습
# ==========================================================
@st.cache_resource
def train_models():
    p_w, p_a, p_h = get_path("[2016_2025] yeongcheon_weather_daily.csv"), get_path("[2019_2025] air_quality.csv"), get_path("yc_heritage_feature.csv")
    if not all([p_w, p_a, p_h]): return None, None, None, None
    
    w_df = pd.read_csv(p_w).rename(columns={'avg_temperature_c': 'temp', 'daily_precipitation_mm': 'rainfall', 'avg_relative_humidity_pct': 'humidity'})
    a_df = pd.read_csv(p_a)
    h_df = pd.read_csv(p_h)
    
    merged = pd.merge(pd.to_datetime(w_df["date"]), w_df, left_index=True, right_index=True)
    merged = pd.merge(w_df, a_df, on="date", how="inner")
    merged = preprocess_data(merged)
    
    le_mat = LabelEncoder().fit(['목조', '석조', '금속', '벽화', '기타', '지석묘', '석탑'])
    le_exp = LabelEncoder().fit(['실외', '실내', '반실외'])
    
    data = []
    # 데이터 다양성 확보를 위해 샘플링 수 조절
    sampled_env = merged.sample(n=min(1000, len(merged)), random_state=42)
    
    for _, h in h_df.iterrows():
        for _, e in sampled_env.iterrows():
            row = {**h.to_dict(), **e.to_dict()}
            data.append({
                "age": h["문화재연령"],
                "mat_code": le_mat.transform([h["재질"]])[0] if h["재질"] in le_mat.classes_ else 4,
                "exp_code": le_exp.transform([h["노출형태"]])[0] if h["노출형태"] in le_exp.classes_ else 0,
                "temp": e["temp"], "humidity": e["humidity"], "dew_gap": e["dew_gap"],
                "wood_risk": e["wood_risk"], "stone_risk": e["stone_risk"], "target": label_logic(row)
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

results, feat_names, le_mat, le_exp = train_models()

# ==========================================================
# 3. 시각화 대시보드
# ==========================================================
st.title("🧪 영천 헤리티지 AI 모델 분석")

if results:
    # --- 정확도 그래프 (꺾은선) ---
    st.subheader("📊 1. 모델별 예측 정확도 비교")
    acc_df = pd.DataFrame({"Model": results.keys(), "Accuracy": [v["acc"] for v in results.values()]})
    
    fig1, ax1 = plt.subplots(figsize=(10, 5))
    sns.lineplot(x="Model", y="Accuracy", data=acc_df, marker="o", markersize=10, ax=ax1)
    for i, v in enumerate(acc_df["Accuracy"]):
        ax1.text(i, v + 0.002, f"{v*100:.1f}%", ha='center', fontweight='bold', color='red')
    st.pyplot(fig1)

    # --- 중요도 그래프 (재질 강조) ---
    st.subheader("🔎 2. 위험 등급 판단의 주요 변수")
    importance = results["Random Forest"]["model"].feature_importances_
    kor_map = {"age": "문화재 연령", "mat_code": "재질 유형", "exp_code": "노출 형태", "temp": "기온", "humidity": "습도", "dew_gap": "결로 위험", "wood_risk": "목조 부후", "stone_risk": "석조 풍화"}
    
    fi_df = pd.DataFrame({'지표': [kor_map.get(f, f) for f in feat_names], '중요도': importance}).sort_values('중요도', ascending=True)
    
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    colors = ['orange' if any(k in x for k in ['재질', '목조', '석조']) else 'skyblue' for x in fi_df['지표']]
    bars = ax2.barh(fi_df['지표'], fi_df['중요도'], color=colors)
    for bar in bars:
        ax2.text(bar.get_width() + 0.005, bar.get_y() + bar.get_height()/2, f'{bar.get_width():.3f}', va='center')
    st.pyplot(fig2)

    # --- 왜 100%가 나오는가? ---
    with st.expander("❓ 왜 정확도가 100%에 가깝게 나오나요?"):
        st.write("""
        1. **데이터 리키지(Data Leakage)**: 현재 위험 등급(Target)을 산출할 때 사용한 수식(`label_logic`)에 들어가는 모든 변수가 모델의 학습 변수(Feature)와 동일하기 때문입니다. AI 입장에서는 수학 공식의 답안지를 보고 문제를 푸는 것과 같습니다.
        2. **결정적 로직**: 실제 자연 현상에는 '노이즈'가 섞여 있지만, 현재는 명확한 IF-ELSE 문으로 등급을 나누었기에 모델이 그 경계선을 완벽하게 학습한 것입니다.
        """)

    # 실시간 예측 테이블 등 기존 로직 유지...

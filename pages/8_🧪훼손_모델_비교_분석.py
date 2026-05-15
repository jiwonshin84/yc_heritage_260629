import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import platform
from matplotlib import font_manager, rc
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score

# ==========================================================
# 0. 그래프 한글 설정
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

# 한글 변수명 매핑 (새로운 파생 변수 포함)
KOR_NAMES = {
    "avg_temperature_c": "평균 기온(℃)",
    "avg_relative_humidity_pct": "평균 습도(%)",
    "pm10": "미세먼지(PM10)",
    "pm25": "초미세먼지(PM2.5)",
    "o3": "오존(O3)",
    "temp_change": "기온 변화량",
    "humidity_change": "습도 변화량",
    "dew_gap": "결로 위험도",
    "wood_risk_idx": "목조 부식 지수",
    "stone_risk_idx": "석조 풍화 지수",
    "daily_precipitation_mm": "강수량(mm)",
    "avg_wind_speed_ms": "풍속(m/s)"
}

# ==========================================================
# 1. 데이터 로드 및 전처리 (로컬 파일 경로 사용)
# ==========================================================
@st.cache_data
def load_and_preprocess_data():
    # 파일 경로 설정
    air_path = "data/processed/[2019_2025] air_quality.csv"
    weather_path = "data/processed/[2016_2025] yeongcheon_weather_daily.csv"
    
    # 데이터 읽기
    air = pd.read_csv(air_path)
    weather = pd.read_csv(weather_path)
    
    # 날짜 형식 통일 및 병합
    air["date"] = pd.to_datetime(air["date"])
    weather["date"] = pd.to_datetime(weather["date"])
    
    df = pd.merge(weather, air, on="date", how="inner").ffill()
    
    # [파생 변수 생성] 문화재 재질/노출별 영향 반영
    # 1. 기본 물리량 변화
    df["temp_change"] = df["avg_temperature_c"].diff().fillna(0)
    df["humidity_change"] = df["avg_relative_humidity_pct"].diff().fillna(0)
    
    # 2. 결로 지수 (이슬점 차이가 작을수록 결로 위험 상승)
    df["dew_point"] = df["avg_temperature_c"] - ((100 - df["avg_relative_humidity_pct"]) / 5)
    df["dew_gap"] = df["avg_temperature_c"] - df["dew_point"]
    
    # 3. 목조 문화재 특화 지수 (고습도 + 온도 -> 부후균 번식 위험)
    df["wood_risk_idx"] = (df["avg_relative_humidity_pct"] * 0.7) + (df["avg_temperature_c"] * 0.3)
    
    # 4. 석조 문화재 특화 지수 (대기오염물질 SO2, NO2 + 강수 -> 산성비/풍화)
    df["stone_risk_idx"] = (df["so2"] * 100) + (df["no2"] * 50) + (df["daily_precipitation_mm"] * 0.2)

    # [위험도 라벨링] 통합 위험 점수 산출
    def classify_complex_risk(r):
        # 목조: 습도 80% 이상이거나 결로 발생 시 위험
        w_risk = 1 if (r["avg_relative_humidity_pct"] > 80 or r["dew_gap"] < 2) else 0
        # 석조: 산성 환경 및 미세먼지 침착
        s_risk = 1 if (r["pm10"] > 80 or r["so2"] > 0.05) else 0
        # 환경: 급격한 온도 변화 (수축 팽창)
        e_risk = 1 if abs(r["temp_change"]) > 10 else 0
        
        total_score = w_risk + s_risk + e_risk
        return 2 if total_score >= 2 else (1 if total_score == 1 else 0)

    df["risk"] = df.apply(classify_complex_risk, axis=1)
    return df

# ==========================================================
# 2. 메인 화면 및 학습
# ==========================================================
st.title("🏛️ 영천 헤리티지 AI: 재질별 문화재 훼손 예측")
st.markdown("영천의 기상 데이터와 대기질 데이터를 통합하여 **목조 및 석조 문화재**의 훼손 위험을 예측합니다.")

try:
    df = load_and_preprocess_data()
    
    # 학습 피처 선택
    features = ["avg_temperature_c", "avg_relative_humidity_pct", "pm10", "pm25", "o3", 
                "temp_change", "humidity_change", "dew_gap", "wood_risk_idx", "stone_risk_idx"]
    
    X = df[features]
    y = df["risk"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    # 모델 정의
    models = {
        "의사결정나무": DecisionTreeClassifier(max_depth=6, class_weight="balanced"),
        "랜덤포레스트": RandomForestClassifier(n_estimators=300, random_state=42),
        "그라디언트 부스팅": GradientBoostingClassifier(n_estimators=200, random_state=42)
    }

    # 1. 성능 비교 시각화
    st.header("1. 모델별 예측 정확도")
    acc_scores = {}
    trained_models = {}

    col1, col2 = st.columns([2, 1])

    for name, model in models.items():
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        acc_scores[name] = acc
        trained_models[name] = model

    with col1:
        fig1, ax1 = plt.subplots()
        bars = ax1.bar(acc_scores.keys(), acc_scores.values(), color=['#3498db', '#e74c3c', '#2ecc71'])
        ax1.set_ylim(0, 1.1)
        for bar in bars:
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02, f'{bar.get_height():.2%}', ha='center')
        st.pyplot(fig1)

    # 2. 중요도 분석
    st.divider()
    st.header("2. 재질/환경별 위험 결정 요인")
    
    sel_model = st.selectbox("분석할 모델 선택", list(models.keys()))
    target_model = trained_models[sel_model]

    if hasattr(target_model, 'feature_importances_'):
        imp_df = pd.DataFrame({
            '지표': [KOR_NAMES.get(f, f) for f in features],
            '중요도': target_model.feature_importances_
        }).sort_values(by='중요도', ascending=True)

        fig2, ax2 = plt.subplots(figsize=(10, 6))
        ax2.barh(imp_df['지표'], imp_df['중요도'], color='#f1c40f')
        st.pyplot(fig2)
        
        top_feature = imp_df.iloc[-1]['지표']
        st.success(f"🔍 **핵심 분석:** 현재 모델은 위험 판단 시 **'{top_feature}'** 지표를장장 중요하게 고려하고 있습니다.")

    with st.expander("데이터 상세보기"):
        st.write(df.tail(20))

except FileNotFoundError:
    st.error("데이터 파일을 찾을 수 없습니다. 경로를 확인해주세요: `yc_heritage_project/data/processed/`")

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

# 한글 폰트 설정 (환경에 따라 조정 필요)
# Streamlit Cloud 등 리눅스 환경에서는 별도의 폰트 설치가 필요할 수 있습니다.
plt.rc('font', family='NanumGothic') 

def show_model_comparison_page():
    st.title("🧪 AI 모델별 성능 비교 분석")
    st.markdown("""
    이 페이지에서는 **문화재청 및 국립중앙박물관의 절대 기준값**으로 학습된 3가지 AI 모델의 성능을 비교합니다.
    어떤 알고리즘이 영천 지역 문화재 훼손 위험을 가장 잘 예측하는지 확인해보세요.
    """)

    # 1. 데이터 로드 (학습용 통합 데이터)
    # 실제 환경에서는 위에서 병합 완료된 m_df 또는 전처리된 csv를 사용하세요.
    @st.cache_data
    def load_training_data():
        # 예시: 기존 코드에서 병합했던 로직을 통해 생성된 데이터프레임
        # 여기서는 설명을 위해 전처리 로직이 완료된 데이터를 불러온다고 가정합니다.
        try:
            df = pd.read_csv("data/processed/integrated_learning_data.csv")
            return df
        except:
            st.error("학습용 데이터를 찾을 수 없습니다. 전처리를 먼저 진행해주세요.")
            return None

    df = load_training_data()

    if df is not None:
        # 2. 특징(Features) 및 타겟(Target) 설정
        features = [
            "temp", "humidity", "pm10", "pm25",
            "temp_change", "humidity_change",
            "dew_gap", "humidity_ma3", "pm10_ma3",
            "temp_std", "humidity_std", "pm_load"
        ]
        
        # 데이터에 해당 컬럼들이 있는지 확인 후 필터링
        available_features = [f for f in features if f in df.columns]
        X = df[available_features]
        y = df["risk"]

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        # 3. 모델 정의 및 학습
        models = {
            "Decision Tree": DecisionTreeClassifier(max_depth=6, class_weight="balanced"),
            "Random Forest": RandomForestClassifier(n_estimators=300, class_weight="balanced"),
            "Gradient Boosting": GradientBoostingClassifier(n_estimators=200)
        }

        results = {}
        model_objs = {}

        st.subheader("1️⃣ 모델별 정확도(Accuracy) 비교")
        cols = st.columns(3)

        for idx, (name, model) in enumerate(models.items()):
            model.fit(X_train, y_train)
            pred = model.predict(X_test)
            acc = accuracy_score(y_test, pred)
            
            results[name] = acc
            model_objs[name] = model
            
            cols[idx].metric(name, f"{acc:.2%}")

        # 4. 시각화: 정확도 비교 차트
        fig_acc, ax_acc = plt.subplots(figsize=(8, 4))
        sns.barplot(x=list(results.keys()), y=list(results.values()), ax=ax_acc, palette="viridis")
        ax_acc.set_ylim(0, 1.0)
        ax_acc.set_title("Model Accuracy Comparison")
        st.pyplot(fig_acc)

        st.divider()

        # 5. 변수 중요도 비교 (Best Model 기준)
        st.subheader("2️⃣ 주요 위험 요인 분석 (Feature Importance)")
        best_model_name = max(results, key=results.get)
        st.info(f"현재 가장 성능이 좋은 모델은 **{best_model_name}** 입니다.")

        best_model = model_objs[best_model_name]
        
        if hasattr(best_model, "feature_importances_"):
            importances = pd.Series(best_model.feature_importances_, index=available_features).sort_values(ascending=True)
            
            fig_imp, ax_imp = plt.subplots(figsize=(10, 6))
            importances.plot(kind='barh', color='skyblue', ax=ax_imp)
            ax_imp.set_title(f"변수 중요도: {best_model_name}")
            st.pyplot(fig_imp)
            
            with st.expander("💡 변수 중요도 해석 도움말"):
                st.write("""
                - **중요도가 높은 변수**: 해당 수치가 변할 때 AI가 위험 등급을 결정하는 데 가장 큰 영향을 미칩니다.
                - **습도 관련 변수**가 상단에 있다면, 해당 문화재는 기상 변화 중 습도 관리가 가장 시급함을 의미합니다.
                """)

        st.divider()

        # 6. 혼동 행렬 (Confusion Matrix)
        st.subheader("3️⃣ 예측 상세 진단 (Confusion Matrix)")
        selected_m = st.selectbox("진단할 모델을 선택하세요", list(models.keys()))
        
        y_pred_m = model_objs[selected_m].predict(X_test)
        cm = confusion_matrix(y_test, y_pred_m)
        
        fig_cm, ax_cm = plt.subplots()
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                    xticklabels=['안전', '주의', '위험'], 
                    yticklabels=['안전', '주의', '위험'], ax=ax_cm)
        ax_cm.set_xlabel('Predicted')
        ax_cm.set_ylabel('Actual')
        st.pyplot(fig_cm)
        st.caption(f"{selected_m} 모델이 실제로 '위험'인 데이터를 얼마나 잘 맞췄는지 확인할 수 있습니다.")

# 앱 실행 시 호출
if __name__ == "__main__":
    show_model_comparison_page()

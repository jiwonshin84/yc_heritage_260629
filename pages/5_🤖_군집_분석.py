import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, silhouette_samples

# =================================================
# 페이지 설정
# =================================================
st.set_page_config(
    page_title="영천 국가유산 군집분석 리포트",
    layout="wide"
)

st.title("🤖 국가유산 지능형 군집분석 시스템")
st.markdown("영천시 국가유산 105건의 데이터를 바탕으로 최적의 관리 그룹(군집 1~)을 생성합니다.")
st.divider()

# =================================================
# 데이터 로드 및 전처리
# =================================================
@st.cache_data
def load_base_data():
    df = pd.read_csv("data/processed/yc_clustering.csv")
    df = df.dropna(subset=['위도', '경도', '가치점수', '시대점수'])
    return df

df_base = load_base_data()

# =================================================
# 사이드바 설정
# =================================================
st.sidebar.header("⚙️ 분석 엔진 설정")
k_value = st.sidebar.slider("군집 수(k) 설정", min_value=2, max_value=10, value=3)

# =================================================
# 실시간 K-Means 분석 수행
# =================================================
features = df_base[['위도', '경도', '가치점수', '시대점수']]
kmeans = KMeans(n_clusters=k_value, init='k-means++', random_state=42, n_init=10)

# 군집 번호를 1부터 시작하도록 보정 (+1)
df_base['cluster_num'] = kmeans.fit_predict(features) + 1
df_base['cluster'] = df_base['cluster_num'].astype(str)

# 실루엣 계수 계산 (내부 품질 확인용)
sil_avg = silhouette_score(features, df_base['cluster'])
df_base['silhouette_val'] = silhouette_samples(features, df_base['cluster'])

# =================================================
# 상단 요약 지표 (Metrics)
# =================================================
c1, c2, c3, c4 = st.columns(4)
with c1: st.metric("분석 대상 전수", "105건")
with c2: st.metric("생성된 군집 수", f"{k_value}개")
with c3: st.metric("전체 평균 가치", f"{df_base['가치점수'].mean():.2f}")
with c4: st.metric("분석 신뢰도(실루엣)", f"{sil_avg:.3f}")

st.divider()

# =================================================
# 메인 분석 시각화
# =================================================
col_left, col_right = st.columns([1.2, 1])

with col_left:
    st.subheader(f"📍 공간적 군집 분포 (1번~{k_value}번)")
    fig_scatter = px.scatter(
        df_base, x="경도", y="위도", color="cluster", size="가치점수",
        hover_data=["문화재명(국문)", "국가유산종목"],
        color_discrete_sequence=px.colors.qualitative.Bold,
        template="plotly_white",
        # 카테고리 순서를 1, 2, 3... 순으로 강제 지정
        category_orders={"cluster": [str(i) for i in range(1, k_value + 1)]}
    )
    fig_scatter.update_layout(legend_title_text='군집 번호')
    st.plotly_chart(fig_scatter, use_container_width=True)

with col_right:
    st.subheader("📊 군집별 특성 요약")
    summary = df_base.groupby("cluster").agg({
        "가치점수": "mean", "시대점수": "mean", "silhouette_val": "mean", "문화재명(국문)": "count"
    }).rename(columns={"문화재명(국문)": "개수"}).reset_index()
    
    # 가비지 번호 정렬을 위해 정수형으로 변환 후 정렬
    summary['cluster_int'] = summary['cluster'].astype(int)
    summary = summary.sort_values('cluster_int')

    fig_bar = px.bar(
        summary, x="cluster", y=["가치점수", "시대점수"], barmode="group",
        template="plotly_white", color_discrete_map={"가치점수": "#636EFA", "시대점수": "#EF553B"},
        labels={"value": "평균 점수", "variable": "지표", "cluster": "군집"}
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# =================================================
# 하단: 군집별 상세 목록 (중복 지표 제거)
# =================================================
st.divider()
st.subheader("🔍 군집별 유산 상세 목록")

# 군집 1부터 순서대로 탭 생성
cluster_labels = [str(i) for i in range(1, k_value + 1)]
tabs = st.tabs([f"군집 {c}" for c in cluster_labels])

for i, tab in enumerate(tabs):
    cluster_id = cluster_labels[i]
    with tab:
        cluster_df = df_base[df_base['cluster'] == cluster_id].sort_values("가치점수", ascending=False)
        
        # 요약 정보 (평균 수치는 여기서만 표시)
        cnt = len(cluster_df)
        avg_v = cluster_df['가치점수'].mean()
        avg_sil = cluster_df['silhouette_val'].mean()
        
        # 품질 상태 판단
        sil_status = "높음(명확)" if avg_sil > 0.5 else "보통(혼재)"
        
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"**📦 유산 수:** {cnt}건")
        c2.markdown(f"**💎 평균 가치:** {avg_v:.2f}점")
        c3.markdown(f"**📈 군집 응집도:** {sil_status}")
        
        # 데이터프레임 (중복되는 가치점수, 실루엣 등은 목록에서 제외하여 깔끔하게 표시)
        st.dataframe(
            cluster_df[["문화재명(국문)", "국가유산종목", "시대", "소재지상세"]],
            use_container_width=True,
            hide_index=True
        )

# =================================================
# 하단 안내
# =================================================
st.info("""
**💡 목록 안내:** 개별 유산 리스트에서는 군집 내 공통 정보인 '평균 가치점수'와 통계 지표인 '실루엣 계수'를 제외하여 가독성을 높였습니다. 
군집 간의 비교는 상단 차트를, 상세 유산 확인은 하단 목록을 이용해 주세요.
""")

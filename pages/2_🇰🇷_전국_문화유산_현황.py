import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# =================================================
# 페이지 설정
# =================================================
st.set_page_config(
    page_title="전국 문화유산 현황",
    page_icon="🏛",
    layout="wide"
)

# =================================================
# 제목
# =================================================
st.markdown("""
<h1 style="font-size:34px; margin-bottom:5px;">
🇰🇷 전국 문화유산 현황
</h1>
<div style="font-size:17px; color:#6b7280; margin-bottom:20px;">
국가유산 공공데이터를 활용한 전국 문화유산 분포 시각화
</div>
""", unsafe_allow_html=True)

st.divider()

# =================================================
# 데이터 불러오기
# =================================================
@st.cache_data
def load_data():
    try:
        # 데이터 파일 경로 (환경에 맞춰 수정하세요)
        df = pd.read_csv("data/raw/all_heritage.csv")
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"데이터 파일을 찾을 수 없습니다: {e}")
        return None

df = load_data()

if df is not None:
    # =================================================
    # 문화유산 중요도 점수 및 데이터 전처리
    # =================================================
    importance_map = {
        "국보": 5, "보물": 4, "사적": 4, "명승": 3, 
        "천연기념물": 3, "국가민속문화유산": 3, 
        "국가등록문화유산": 2, "시도유형문화유산": 2, 
        "시도기념물": 2, "문화유산자료": 1
    }
    df["중요도점수"] = df["국가유산종목"].map(importance_map).fillna(1)

    # =================================================
    # 주요 지표 (Metrics)
    # =================================================
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("전체 문화유산", f"{len(df):,}개")
    with c2:
        st.metric("문화유산 종목 수", f"{df['국가유산종목'].nunique()}종")
    with c3:
        st.metric("시도 수", f"{df['시도명'].nunique()}개")
    with c4:
        st.metric("가장 많은 지역", df["시도명"].value_counts().idxmax())

    st.markdown("<br>", unsafe_allow_html=True)

    # =================================================
    # 1행: Treemap & Bubble Chart
    # =================================================
    row1_left, row1_right = st.columns([1.2, 1])

    with row1_left:
        st.markdown("### 🗺 시도별 문화유산 분포")
        region_count = df["시도명"].value_counts().reset_index()
        region_count.columns = ["시도명", "개수"]

        fig1 = px.treemap(
            region_count, path=["시도명"], values="개수",
            color="개수", color_continuous_scale="GnBu"
        )
        fig1.update_layout(margin=dict(t=20, l=10, r=10, b=10), height=500)
        fig1.update_traces(texttemplate="<b>%{label}</b><br>%{value}개", textfont_size=16)
        st.plotly_chart(fig1, use_container_width=True)

    with row1_right:
        st.markdown("### 🫧 국가유산 종목별 현황")
        type_count = df["국가유산종목"].value_counts().reset_index()
        type_count.columns = ["국가유산종목", "개수"]

        n = len(type_count)
        cols = 4
        type_count["x"] = [i % cols for i in range(n)]
        type_count["y"] = [-(i // cols) for i in range(n)]

        fig2 = px.scatter(
            type_count, x="x", y="y", size="개수", color="개수",
            text="국가유산종목", size_max=60, color_continuous_scale="Blues"
        )
        fig2.update_traces(textposition="middle center", marker=dict(opacity=0.85, line=dict(width=1, color="white")))
        fig2.update_layout(xaxis=dict(visible=False), yaxis=dict(visible=False), 
                          margin=dict(t=20, l=10, r=10, b=10), height=500, showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    # =================================================
    # 2행: 경북 지역 상세 (Polar Bar & Heatmap)
    # =================================================
    st.markdown("<br>", unsafe_allow_html=True)
    row2_left, row2_right = st.columns([1, 1])

    gb_df = df[df["시도명"] == "경북"].copy()

    with row2_left:
        st.markdown("### 🌀 경북 지역 문화유산 분포 (상위 15개)")
        city_count = gb_df["시군구명"].value_counts().head(15).reset_index()
        city_count.columns = ["시군구명", "개수"]

        fig3 = px.bar_polar(
            city_count, r="개수", theta="시군구명",
            color="개수", color_continuous_scale="Tealgrn"
        )
        fig3.update_layout(height=500, margin=dict(t=50, b=50), coloraxis_showscale=False)
        st.plotly_chart(fig3, use_container_width=True)

    with row2_right:
        st.markdown("### 🌡 경북 시군구별 종목 현황")
        heatmap_df = pd.pivot_table(gb_df, index="시군구명", columns="국가유산종목", aggfunc="size", fill_value=0)
        top_cities = gb_df["시군구명"].value_counts().head(15).index
        heatmap_df = heatmap_df.loc[top_cities]

        fig4 = px.imshow(heatmap_df, text_auto=True, color_continuous_scale="YlGnBu", aspect="auto")
        fig4.update_layout(height=500, margin=dict(t=20, l=10, r=10, b=10), coloraxis_showscale=False)
        st.plotly_chart(fig4, use_container_width=True)

    # =================================================
    # 3행: 순위 & 비중 (Bar Chart & Overlaid Bar Chart)
    # =================================================
    st.markdown("<br>", unsafe_allow_html=True)
    row3_left, row3_right = st.columns(2)

    with row3_right:
        st.markdown("### 🏆 경북 지역 문화유산 순위")
        gb_rank = gb_df["시군구명"].value_counts().head(15).reset_index()
        gb_rank.columns = ["시군구명", "개수"]
        
        fig5 = px.bar(gb_rank.sort_values("개수"), x="개수", y="시군구명", orientation="h",
                     text="개수", color="개수", color_continuous_scale="Tealgrn")
        fig5.update_traces(textposition="outside")
        fig5.update_layout(height=550, margin=dict(t=20, l=10, r=10, b=10), coloraxis_showscale=False)
        st.plotly_chart(fig5, use_container_width=True)

    with row3_left:
        st.markdown("### 🏺 지역별 국보 비중 (비율 높은 순)")
        
        # 1. 데이터 준비
        total_count = gb_df.groupby("시군구명").size().reset_index(name="전체개수")
        treasure_count = gb_df[gb_df["국가유산종목"].isin(["국보"])].groupby("시군구명").size().reset_index(name="국보개수")
        
        ratio_df = pd.merge(total_count, treasure_count, on="시군구명", how="left").fillna(0)
        ratio_df["비율"] = (ratio_df["국보개수"] / ratio_df["전체개수"]) * 100
        
        # [정렬 기준] '비율'이 높은 순서대로 상위 15개 추출
        ratio_df = ratio_df.sort_values("비율", ascending=False).head(15)

        # 2. 중첩 막대 차트 생성
        fig6 = go.Figure()
        
        # 배경: 전체 문화유산 (연한 회색)
        fig6.add_trace(go.Bar(
            y=ratio_df["시군구명"], x=ratio_df["전체개수"],
            name="전체 문화유산", orientation='h',
            marker=dict(color='rgba(200, 200, 200, 0.3)'),
            hovertemplate='전체: %{x}개<extra></extra>'
        ))

        # 전경: 국보 (강조 색상)
        fig6.add_trace(go.Bar(
            y=ratio_df["시군구명"], x=ratio_df["국보개수"],
            name="국보", orientation='h',
            marker=dict(color='#E67E22'), 
            text=ratio_df["비율"].apply(lambda x: f'{x:.1f}%'),
            textposition='outside',
            hovertemplate='국보: %{x}개<extra></extra>'
        ))

        # 3. 레이아웃 설정
        fig6.update_layout(
            barmode='overlay',
            height=550,
            margin=dict(t=20, l=10, r=60, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis_title="문화유산 개수 (막대 끝 숫자는 국보·보물 비율)",
            yaxis=dict(autorange="reversed") 
        )
        st.plotly_chart(fig6, use_container_width=True)

    # =================================================
# 영천 문화유산 종목 비율
# Radar Chart
# fig7
# =================================================

with right3:

    st.markdown("""
    <h3 style="
    font-size:24px;
    margin-bottom:10px;
    ">
    🎯 영천 문화유산 종목 특징
    </h3>
    """, unsafe_allow_html=True)

    # -------------------------------------------------
    # 영천 데이터
    # -------------------------------------------------

    yc_df = gb_df[
        gb_df["시군구명"] == "영천시"
    ]

    type_ratio = (

        yc_df["국가유산종목"]
        .value_counts(normalize=True)
        .reset_index()

    )

    type_ratio.columns = [
        "종목",
        "비율"
    ]

    type_ratio = (
        type_ratio
        .head(8)
    )

    type_ratio["비율"] = (
        type_ratio["비율"] * 100
    )

    # -------------------------------------------------
    # Radar Chart
    # -------------------------------------------------

    fig7 = px.line_polar(

        type_ratio,

        r="비율",

        theta="종목",

        line_close=True

    )

    fig7.update_traces(

        fill="toself"

    )

    fig7.update_layout(

        height=500,

        margin=dict(
            t=20,
            l=20,
            r=20,
            b=20
        ),

        showlegend=False

    )

    st.plotly_chart(
        fig7,
        use_container_width=True
    )

# =================================================
# 인구 대비 문화유산 밀도
# Bubble Chart
# fig8
# =================================================

with left4:

    st.markdown("""
    <h3 style="
    font-size:24px;
    margin-bottom:10px;
    ">
    👥 인구 대비 문화유산 밀도
    </h3>
    """, unsafe_allow_html=True)

    # -------------------------------------------------
    # 지역별 문화유산 수
    # -------------------------------------------------

    heritage_count = (

        gb_df["시군구명"]
        .value_counts()
        .reset_index()

    )

    heritage_count.columns = [
        "시군구명",
        "문화유산수"
    ]

    # -------------------------------------------------
    # 경북 시군 인구 데이터
    # (예시값)
    # -------------------------------------------------

    pop_df = pd.DataFrame({

        "시군구명": [
            "경주시","안동시","영천시","포항시",
            "구미시","문경시","영주시","상주시"
        ],

        "인구": [
            250000,
            155000,
            101000,
            500000,
            410000,
            70000,
            100000,
            93000
        ]

    })

    # -------------------------------------------------
    # 병합
    # -------------------------------------------------

    density_df = pd.merge(

        heritage_count,
        pop_df,

        on="시군구명",

        how="inner"

    )

    # 인구 1만명당 문화유산 수
    density_df["밀도"] = (

        density_df["문화유산수"]
        / density_df["인구"]

    ) * 10000

    # -------------------------------------------------
    # Bubble Chart
    # -------------------------------------------------

    fig8 = px.scatter(

        density_df,

        x="인구",

        y="문화유산수",

        size="밀도",

        color="밀도",

        hover_name="시군구명",

        text="시군구명",

        color_continuous_scale="Tealgrn"

    )

    fig8.update_traces(

        textposition="top center"

    )

    fig8.update_layout(

        height=550,

        margin=dict(
            t=20,
            l=10,
            r=10,
            b=10
        ),

        coloraxis_showscale=False

    )

    st.plotly_chart(
        fig8,
        use_container_width=True
    )
    

    # =================================================
    # 하단 설명
    # =================================================
    st.divider()
    st.info("""
    📌 **시도별 문화유산 분포**: 전체적인 규모를 한눈에 파악할 수 있는 트리맵입니다.  
    📌 **경북 지역별 종목 현황**: 히트맵을 통해 특정 지역에 어떤 종목이 집중되어 있는지 분석할 수 있습니다.  
    📌 **지역별 국보 · 보물 비중**: 전체 문화유산 수 대비 '국보·보물'이 차지하는 양과 비율을 동시에 시각화하여 문화적 가치 밀도를 보여줍니다.
    """)

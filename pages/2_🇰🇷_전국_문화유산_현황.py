import streamlit as st
import pandas as pd
import plotly.express as px

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
<h1 style="
font-size:34px;
margin-bottom:5px;
">
🇰🇷 전국 문화유산 현황
</h1>

<div style="
font-size:17px;
color:#6b7280;
margin-bottom:20px;
">
국가유산 공공데이터를 활용한 전국 문화유산 분포 시각화
</div>
""", unsafe_allow_html=True)

st.divider()

# =================================================
# 데이터 불러오기
# =================================================

df = pd.read_csv(
    "data/raw/all_heritage.csv"
)

# 컬럼 공백 제거
df.columns = df.columns.str.strip()

# =================================================
# 문화유산 중요도 점수
# =================================================

importance_map = {

    "국보": 5,
    "보물": 4,
    "사적": 4,
    "명승": 3,
    "천연기념물": 3,
    "국가민속문화유산": 3,
    "국가등록문화유산": 2,
    "시도유형문화유산": 2,
    "시도기념물": 2,
    "문화유산자료": 1

}

df["중요도점수"] = (
    df["국가유산종목"]
    .map(importance_map)
    .fillna(1)
)

# =================================================
# 주요 지표
# =================================================

c1, c2, c3, c4 = st.columns(4)

with c1:

    st.metric(
        "전체 문화유산",
        f"{len(df):,}개"
    )

with c2:

    st.metric(
        "문화유산 종목 수",
        df["국가유산종목"].nunique()
    )

with c3:

    st.metric(
        "시도 수",
        df["시도명"].nunique()
    )

with c4:

    st.metric(
        "가장 많은 지역",
        df["시도명"].value_counts().idxmax()
    )

st.markdown("<br>", unsafe_allow_html=True)

# =================================================
# 1행
# =================================================

left, right = st.columns([1.2, 1])

# =================================================
# 1. Treemap
# =================================================

with left:

    st.markdown("""
    <h3 style="
    font-size:24px;
    margin-bottom:10px;
    ">
    🗺 시도별 문화유산 분포
    </h3>
    """, unsafe_allow_html=True)

    region_count = (
        df["시도명"]
        .value_counts()
        .reset_index()
    )

    region_count.columns = [
        "시도명",
        "개수"
    ]

    fig1 = px.treemap(

        region_count,

        path=["시도명"],

        values="개수",

        color="개수",

        color_continuous_scale="YlOrRd"

    )

    fig1.update_layout(

        margin=dict(
            t=20,
            l=10,
            r=10,
            b=10
        ),

        height=650
    )

    fig1.update_traces(

        texttemplate=
        "<b>%{label}</b><br>%{value}개",
    
        textfont_size=18,
    
        hovertemplate=
        "<b>%{label}</b><br>" +
        "문화유산 수: %{value}개"

    )

    st.plotly_chart(
        fig1,
        use_container_width=True
    )

# =================================================
# 2. Bubble Chart
# =================================================

with right:

    st.markdown("""
    <h3 style="
    font-size:24px;
    margin-bottom:10px;
    ">
    🫧 국가유산 종목별 현황
    </h3>
    """, unsafe_allow_html=True)

    type_count = (
        df["국가유산종목"]
        .value_counts()
        .reset_index()
    )

    type_count.columns = [
        "국가유산종목",
        "개수"
    ]

    # Bubble 위치 자동 생성

    n = len(type_count)

    cols = 4

    type_count["x"] = [
        i % cols
        for i in range(n)
    ]

    type_count["y"] = [
        -(i // cols)
        for i in range(n)
    ]

    fig2 = px.scatter(

        type_count,

        x="x",
        y="y",

        size="개수",

        color="개수",

        text="국가유산종목",

        size_max=100,

        color_continuous_scale="Blues"

    )

    fig2.update_traces(

        textposition="middle center",

        marker=dict(
            opacity=0.85,
            line=dict(
                width=2,
                color="white"
            )
        ),

        hovertemplate=
        "<b>%{text}</b><br>" +
        "문화유산 수: %{marker.size}개"

    )

    fig2.update_layout(

        xaxis=dict(
            visible=False
        ),

        yaxis=dict(
            visible=False
        ),

        showlegend=False,

        margin=dict(
            t=20,
            l=10,
            r=10,
            b=10
        ),

        height=650
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

# =================================================
# 2행
# =================================================

st.markdown("<br>", unsafe_allow_html=True)

left2, right2 = st.columns([1, 1])

# =================================================
# 경북 지역 문화유산 분포
# Polar Bar Chart
# =================================================

with left2:

    st.markdown("""
    <h3 style="
    font-size:24px;
    margin-bottom:10px;
    ">
    🌀 경북 지역 문화유산 분포
    </h3>
    """, unsafe_allow_html=True)

    # -------------------------------------------------
    # 경북 데이터
    # -------------------------------------------------

    gb_df = df[
        df["시도명"] == "경북"
    ].copy()

    city_count = (

        gb_df["시군구명"]
        .value_counts()
        .reset_index()

    )

    city_count.columns = [
        "시군구명",
        "개수"
    ]

    city_count = (
        city_count
        .head(15)
    )

    # -------------------------------------------------
    # Polar Bar
    # -------------------------------------------------

    fig3 = px.bar_polar(

        city_count,

        r="개수",

        theta="시군구명",

        color="개수",

        color_continuous_scale="Tealgrn"

    )

    fig3.update_layout(

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
        fig3,
        use_container_width=True
    )


# =================================================
# 4. 경북 지역별 종목 현황 Heatmap
# =================================================

with right2:

    st.markdown("""
    <h3 style="
    font-size:24px;
    margin-bottom:10px;
    ">
    🌡 경북 지역별 문화유산 종목 현황
    </h3>
    """, unsafe_allow_html=True)

    # -------------------------------------------------
    # 경북 데이터
    # -------------------------------------------------

    gb_df = df[
        df["시도명"] == "경북"
    ].copy()

    # -------------------------------------------------
    # Pivot Table 생성
    # -------------------------------------------------

    heatmap_df = pd.pivot_table(

        gb_df,

        index="시군구명",

        columns="국가유산종목",

        aggfunc="size",

        fill_value=0

    )

    # -------------------------------------------------
    # 상위 도시만
    # -------------------------------------------------

    top_cities = (
        gb_df["시군구명"]
        .value_counts()
        .head(15)
        .index
    )

    heatmap_df = (
        heatmap_df
        .loc[top_cities]
    )

    # -------------------------------------------------
    # Heatmap
    # -------------------------------------------------

    fig4 = px.imshow(

        heatmap_df,

        text_auto=True,

        color_continuous_scale="YlGnBu",

        aspect="auto"

    )

    fig4.update_layout(

        height=500,

        margin=dict(
            t=20,
            l=10,
            r=10,
            b=10
        ),

        xaxis_title="문화유산 종목",

        yaxis_title="경북 지역",

        coloraxis_showscale=False

    )

    st.plotly_chart(
        fig4,
        use_container_width=True
    )


# =================================================
# 3행
# =================================================

st.markdown("<br>", unsafe_allow_html=True)

left3, right3 = st.columns(2)


# =================================================
# 경북 지역 문화유산 순위
# fig5
# =================================================

with right3:

    st.markdown("""
    <h3 style="
    font-size:24px;
    margin-bottom:10px;
    ">
    🏆 경북 지역 문화유산 순위
    </h3>
    """, unsafe_allow_html=True)

    # -------------------------------------------------
    # 경북 지역 시군구별 문화유산 개수
    # -------------------------------------------------

    gb_rank = (

        gb_df["시군구명"]
        .value_counts()
        .reset_index()

    )

    gb_rank.columns = [
        "시군구명",
        "개수"
    ]

    gb_rank = (
        gb_rank
        .sort_values(
            by="개수",
            ascending=False
        )
        .head(15)
    )

    # 순위 컬럼 추가
    gb_rank["순위"] = range(
        1,
        len(gb_rank) + 1
    )

    # -------------------------------------------------
    # Horizontal Bar Chart
    # -------------------------------------------------

    fig5 = px.bar(

        gb_rank.sort_values("개수"),

        x="개수",

        y="시군구명",

        orientation="h",

        text="개수",

        color="개수",

        color_continuous_scale="Tealgrn"

    )

    fig5.update_traces(

        textposition="outside"

    )

    fig5.update_layout(

        height=550,

        margin=dict(
            t=20,
            l=10,
            r=10,
            b=10
        ),

        yaxis_title="",

        xaxis_title="문화유산 개수",

        coloraxis_showscale=False

    )

    st.plotly_chart(
        fig5,
        use_container_width=True
    )
# =================================================
# 경북 지역별 국보 · 보물 비율
# fig6
# =================================================

left3, right3 = st.columns(2)

with left3:

    st.markdown("""
    <h3 style="
    font-size:24px;
    margin-bottom:10px;
    ">
    🏺 지역별 국보 · 보물 비율
    </h3>
    """, unsafe_allow_html=True)

    # -------------------------------------------------
    # 지역별 전체 문화유산 수
    # -------------------------------------------------

    total_df = (

        gb_df
        .groupby("시군구명")
        .size()
        .reset_index(name="전체개수")

    )

    # -------------------------------------------------
    # 지역별 국보·보물 수
    # -------------------------------------------------

    treasure_df = gb_df[

        gb_df["국가유산종목"].isin(
            ["국보", "보물"]
        )

    ]

    treasure_count = (

        treasure_df
        .groupby("시군구명")
        .size()
        .reset_index(name="국보보물개수")

    )

    # -------------------------------------------------
    # 병합
    # -------------------------------------------------

    ratio_df = pd.merge(

        total_df,
        treasure_count,

        on="시군구명",

        how="left"

    )

    ratio_df["국보보물개수"] = (
        ratio_df["국보보물개수"]
        .fillna(0)
    )

    # -------------------------------------------------
    # 비율 계산
    # -------------------------------------------------

    ratio_df["비율"] = (

        ratio_df["국보보물개수"]
        / ratio_df["전체개수"]

    ) * 100

    ratio_df = (
        ratio_df
        .sort_values(
            by="비율",
            ascending=False
        )
        .head(15)
    )

    # -------------------------------------------------
    # Bar Chart
    # -------------------------------------------------

    fig6 = px.bar(

        ratio_df.sort_values("비율"),

        x="비율",

        y="시군구명",

        orientation="h",

        text=ratio_df.sort_values("비율")["비율"].round(1).astype(str) + "%",

        color="비율",

        color_continuous_scale="Tealgrn"

    )

    fig6.update_traces(

        textposition="outside"

    )

    fig6.update_layout(

        height=550,

        margin=dict(
            t=20,
            l=10,
            r=10,
            b=10
        ),

        xaxis_title="국보 · 보물 비율 (%)",

        yaxis_title="",

        coloraxis_showscale=False

    )

    st.plotly_chart(
        fig6,
        use_container_width=True
    )

# =================================================
# 하단 설명
# =================================================

st.markdown("<br>", unsafe_allow_html=True)

st.info("""
📌 Treemap은 지역별 문화유산 규모를 면적으로 표현합니다.  

📌 Bubble Chart는 국가유산 종목별 규모를 직관적으로 보여줍니다.  

📌 중요도 시각화는 문화유산 종목의 상대적 가치를 표현합니다.  

📌 Sunburst Chart는 문화유산 분류 체계를 계층적으로 보여줍니다.
""")

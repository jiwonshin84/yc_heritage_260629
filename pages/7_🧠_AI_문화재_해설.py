import streamlit as st
import pandas as pd

# =====================================================
# 페이지 설정
# =====================================================
st.set_page_config(
    page_title="AI 문화재 해설",
    layout="wide"
)

# =====================================================
# 메인 제목
# =====================================================
st.title("🤖 AI 문화재 해설")

# =====================================================
# 데이터 로드
# =====================================================
@st.cache_data
def load_data():
    return pd.read_csv(
        "data/processed/yc_heritage_detail_enriched.csv"
    )

# =====================================================
# 문자열 정리 함수
# =====================================================
def clean(val):

    if pd.isna(val):
        return "-"

    s = str(val).strip()

    return s if s != "" else "-"

# =====================================================
# 메인 실행
# =====================================================
try:

    df = load_data()

    # -------------------------------------------------
    # 종목 컬럼 자동 선택
    # -------------------------------------------------
    if "종목" in df.columns:
        category_col = "종목"
    else:
        category_col = "국가유산종목"

    # -------------------------------------------------
    # 선택 영역
    # -------------------------------------------------
    select_col1, select_col2 = st.columns(2)

    with select_col1:

        category = st.selectbox(
            "📂 문화재 품목 선택",
            sorted(df[category_col].dropna().unique())
        )

    filtered_df = df[
        df[category_col] == category
    ]

    with select_col2:

        heritage = st.selectbox(
            "🏛 문화재 선택",
            filtered_df["문화재명(국문)"]
        )

    # -------------------------------------------------
    # 선택된 데이터
    # -------------------------------------------------
    row = filtered_df[
        filtered_df["문화재명(국문)"] == heritage
    ].iloc[0]

    # =================================================
    # 본문 영역
    # =================================================
    left_col, right_col = st.columns([1, 1])

    # -------------------------------------------------
    # 이미지 영역
    # -------------------------------------------------
    with left_col:

        image_url = row.get("이미지URL", None)

        if pd.notna(image_url) and str(image_url).strip() != "":

            st.image(
                image_url,
                use_container_width=True
            )

            st.caption(
                "출처: 국가유산청 - " + heritage
            )

        else:

            st.info(
                "🖼 등록된 이미지가 없습니다."
            )

    # -------------------------------------------------
    # 상세 정보 영역
    # -------------------------------------------------
    with right_col:

        st.markdown(
            f"""
            <h2 style='
                color:#2c3e50;
                margin-top:0;
                margin-bottom:20px;
                font-size:32px;
            '>
            📋 {heritage}
            </h2>
            """,
            unsafe_allow_html=True
        )

        info_data = {

            "종목":
                clean(row.get(category_col)),

            "분류":
                clean(row.get("국가유산분류"))
                + " ("
                + clean(row.get("국가유산분류2"))
                + ")",

            "한자명":
                clean(row.get("문화재명(한자)")),

            "시대":
                clean(row.get("시대")),

            "소재지":
                clean(row.get("소재지상세")),

            "소유자/관리자":
                clean(row.get("소유자"))
                + " / "
                + clean(row.get("관리자"))
        }

        # ---------------------------------------------
        # 상세정보 출력
        # ---------------------------------------------
        for key, value in info_data.items():

            c1, c2 = st.columns([1, 2.2])

            with c1:

                st.markdown(
                    f"""
                    <div style='
                        font-weight:700;
                        color:#2c3e50;
                        font-size:16px;
                        padding-top:5px;
                    '>
                    {key}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            with c2:

                st.markdown(
                    f"""
                    <div style='
                        color:#444;
                        font-size:15px;
                        line-height:1.6;
                    '>
                    {value}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            st.markdown(
                """
                <hr style='
                    margin:8px 0;
                    border:0.5px solid #eeeeee;
                '>
                """,
                unsafe_allow_html=True
            )

        # =================================================
        # 상세 설명
        # =================================================
        st.markdown("### 📖 상세 설명")

        content = str(
            row.get(
                "내용",
                "상세 설명 정보가 없습니다."
            )
        )

        st.markdown(
            f"""
            <div style='
                background-color:white;
                border:1px solid #eeeeee;
                border-radius:12px;
                padding:20px;
                line-height:1.9;
                font-size:16px;
            '>

                {content}

            </div>
            """,
            unsafe_allow_html=True
        )

    # =================================================
    # AI 스마트 해설
    # =================================================
    st.markdown("<br>", unsafe_allow_html=True)

    시대 = clean(row.get("시대"))
    소재지 = clean(row.get("소재지상세"))
    종목 = clean(row.get(category_col))

    st.success(f"""
### 🤖 AI 도슨트 가이드

**{heritage}**은(는)
**{시대}** 시대의 숨결을 간직한 소중한 유산입니다.

현재 **{소재지}**에 보존되어 있으며,
**{종목}**으로서 학술적 가치가 매우 높습니다.

특히 이 유산은
영천 지역의 역사적 정체성을 잘 보여주는 중요한 지표가 됩니다.
""")

# =====================================================
# 오류 처리
# =====================================================
except Exception as e:

    st.error(
        "데이터를 불러오거나 처리하는 중 오류가 발생했습니다.\n\n"
        + str(e)
    )

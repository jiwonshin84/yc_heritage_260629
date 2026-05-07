import streamlit as st
import pandas as pd
import google.generativeai as genai

# =====================================================
# 페이지 설정
# =====================================================
st.set_page_config(
    page_title="AI 문화재 해설",
    layout="wide"
)

# =====================================================
# Gemini API 설정
# =====================================================
GEMINI_API_KEY = "여기에_본인_API_KEY"

genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel(
    "gemini-1.5-flash"
)

# =====================================================
# 메인 제목
# =====================================================
st.title("🤖 AI 문화재 해설")

# =====================================================
# 세션 상태 초기화
# =====================================================
if "prev_category" not in st.session_state:
    st.session_state.prev_category = None

if "clear_image" not in st.session_state:
    st.session_state.clear_image = False

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
            sorted(
                df[category_col]
                .dropna()
                .unique()
            )
        )

    # -------------------------------------------------
    # 품목 변경 감지
    # -------------------------------------------------
    if (
        st.session_state.prev_category
        != category
    ):

        st.session_state.clear_image = True

        st.session_state.prev_category = category

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

        image_placeholder = st.empty()

        # ---------------------------------------------
        # 품목 변경 시 이미지 제거
        # ---------------------------------------------
        if st.session_state.clear_image:

            image_placeholder.empty()

            st.session_state.clear_image = False

        image_url = row.get(
            "이미지URL",
            None
        )

        # ---------------------------------------------
        # 이미지 출력
        # ---------------------------------------------
        if (
            pd.notna(image_url)
            and str(image_url).strip() != ""
        ):

            image_placeholder.image(
                image_url,
                use_container_width=True
            )

            st.caption(
                "출처: 국가유산청 - "
                + heritage
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
                + clean(row.get("관리자")),

            "상세 설명":
                clean(row.get("내용"))
        }

        # ---------------------------------------------
        # 상세 정보 출력
        # ---------------------------------------------
        for key, value in info_data.items():

            c1, c2 = st.columns(
                [1, 3]
            )

            with c1:

                st.markdown(
                    f"""
                    <div style='
                        font-weight:700;
                        color:#2c3e50;
                        font-size:16px;
                        padding-top:18px;
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
                        line-height:1.8;
                        padding-top:18px;
                        white-space:pre-line;
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

# =====================================================
# 오류 처리
# =====================================================
except Exception as e:

    st.error(
        "데이터 처리 중 오류 발생\n\n"
        + str(e)
    )

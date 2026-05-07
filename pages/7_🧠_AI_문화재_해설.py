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
GEMINI_API_KEY = "여기에_API_KEY_입력"

genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel(
    "gemini-1.5-flash"
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
            sorted(
                df[category_col]
                .dropna()
                .unique()
            )
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

        image_url = row.get(
            "이미지URL",
            None
        )

        if (
            pd.notna(image_url)
            and str(image_url).strip() != ""
        ):

            st.image(
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

        # ---------------------------------------------
        # 상세 정보 데이터
        # ---------------------------------------------
        info_data = {

            "종목":
                clean(
                    row.get(category_col)
                ),

            "분류":
                clean(
                    row.get("국가유산분류")
                )
                + " ("
                + clean(
                    row.get("국가유산분류2")
                )
                + ")",

            "한자명":
                clean(
                    row.get("문화재명(한자)")
                ),

            "시대":
                clean(
                    row.get("시대")
                ),

            "소재지":
                clean(
                    row.get("소재지상세")
                ),

            "소유자/관리자":
                clean(
                    row.get("소유자")
                )
                + " / "
                + clean(
                    row.get("관리자")
                ),

            "상세 설명":
                clean(
                    row.get("내용")
                )
        }

        # ---------------------------------------------
        # 상세 정보 출력
        # ---------------------------------------------
        for key, value in info_data.items():

            c1, c2 = st.columns(
                [1, 2.5]
            )

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
                        line-height:1.8;
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

    # =================================================
    # AI 도슨트 가이드
    # =================================================
    st.markdown("---")

    시대 = clean(row.get("시대"))
    소재지 = clean(row.get("소재지상세"))
    종목 = clean(row.get(category_col))
    분류 = clean(row.get("국가유산분류"))
    내용 = clean(row.get("내용"))

    with st.spinner(
        "AI 도슨트 해설 생성 중..."
    ):

        guide_prompt = f"""
        너는 전문 박물관 도슨트이다.

        아래 문화재 정보를 바탕으로
        학생들과 일반인이 흥미롭게
        이해할 수 있도록 설명해라.

        [문화재 정보]

        이름:
        {heritage}

        종목:
        {종목}

        분류:
        {분류}

        시대:
        {시대}

        소재지:
        {소재지}

        설명:
        {내용}

        아래 내용을 포함해라.

        1. 문화재 소개
        2. 역사적 의미
        3. 특징
        4. 영천 지역과의 관련성
        5. 흥미로운 이야기

        너무 딱딱하지 않게
        실제 전시관 해설처럼 설명해라.
        """

        guide_response = model.generate_content(
            guide_prompt
        )

    st.markdown(
        "## 🤖 AI 도슨트 가이드"
    )

    st.write(
        guide_response.text
    )

    # =================================================
    # Gemini 질문 기능
    # =================================================
    st.markdown("---")

    st.subheader(
        "💬 AI에게 문화재 질문하기"
    )

    user_question = st.text_input(
        "문화재에 대해 궁금한 점을 입력하세요"
    )

    if st.button("🤖 질문하기"):

        if user_question.strip() == "":

            st.warning(
                "질문을 입력해주세요."
            )

        else:

            with st.spinner(
                "AI가 답변 생성 중입니다..."
            ):

                prompt = f"""
                너는 한국 문화재 전문 AI이다.

                문화재 이름:
                {heritage}

                시대:
                {시대}

                소재지:
                {소재지}

                문화재 설명:
                {내용}

                사용자 질문:
                {user_question}

                쉽고 친절하게
                답변해라.
                """

                response = model.generate_content(
                    prompt
                )

                st.markdown(
                    "### 🤖 AI 답변"
                )

                st.write(
                    response.text
                )

# =====================================================
# 오류 처리
# =====================================================
except Exception as e:

    st.error(
        "데이터 처리 중 오류 발생\n\n"
        + str(e)
    )

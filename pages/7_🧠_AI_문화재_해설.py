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
genai.configure(
    api_key=st.secrets["GEMINI_API_KEY"]
)


model = genai.GenerativeModel(
    "gemini-2.0-flash"
)

# =====================================================
# 세션 상태
# =====================================================
if "prev_category" not in st.session_state:
    st.session_state.prev_category = None

if "clear_image" not in st.session_state:
    st.session_state.clear_image = False

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
    # 문화재 제목
    # =================================================
    st.markdown(
        f"""
        <div style='
            background-color:#f8f9fa;
            padding:6px 12px;
            border-radius:10px;
            margin-bottom:10px;
            border:1px solid #e9ecef;
        '>

        <h3 style='
            text-align:center;
            color:#2c3e50;
            margin:0;
            font-size:28px;
        '>

        🏛 {heritage}

        </h3>

        </div>
        """,
        unsafe_allow_html=True
    )

    # =================================================
    # 본문 영역
    # =================================================
    left_col, right_col = st.columns([1, 1.1])

    # -------------------------------------------------
    # 이미지
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
    # 상세정보
    # -------------------------------------------------
    with right_col:

        st.markdown(
            """
            <h3 style='
                margin-top:0;
                margin-bottom:8px;
                color:#2c3e50;
            '>
            📋 상세 정보
            </h3>
            """,
            unsafe_allow_html=True
        )

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
                )
        }

        # ---------------------------------------------
        # 상세정보 출력
        # ---------------------------------------------
        for key, value in info_data.items():

            c1, c2 = st.columns(
                [0.8, 3.2],
                vertical_alignment="center"
            )

            # -----------------------------------------
            # 왼쪽 제목
            # -----------------------------------------
            with c1:

                st.markdown(
                    f"""
                    <div style='
                        font-weight:700;
                        color:#2c3e50;
                        font-size:16px;
                        line-height:1.2;
                        padding:0;
                        margin:0;
                    '>

                    {key}

                    </div>
                    """,
                    unsafe_allow_html=True
                )

            # -----------------------------------------
            # 오른쪽 내용
            # -----------------------------------------
            with c2:

                st.markdown(
                    f"""
                    <div style='
                        color:#444;
                        font-size:15px;
                        line-height:1.3;
                        white-space:pre-line;
                        padding:0;
                        margin:0;
                    '>

                    {value}

                    </div>
                    """,
                    unsafe_allow_html=True
                )

            # -----------------------------------------
            # 구분선
            # -----------------------------------------
            st.markdown(
                """
                <hr style='
                    margin:2px 0;
                    border:0.5px solid #eeeeee;
                '>
                """,
                unsafe_allow_html=True
            )

        # =================================================
        # 상세 설명
        # =================================================
        st.markdown("### 📖 상세 설명")

        content = clean(
            row.get("내용")
        )

        st.write(content)

    # =================================================
    # AI 스마트 해설
    # =================================================
    st.markdown("<br>", unsafe_allow_html=True)

    시대 = clean(row.get("시대"))
    소재지 = clean(row.get("소재지상세"))
    종목 = clean(row.get(category_col))
    분류 = clean(row.get("국가유산분류"))
    내용 = clean(row.get("내용"))

    st.markdown("## 🤖 AI 도슨트 가이드")

    if st.button("🤖 AI 도슨트 해설 생성"):

        try:

            with st.spinner(
                "AI 도슨트 해설 생성 중..."
            ):

                guide_prompt = f"""
                너는 전문 박물관 도슨트이다.

                아래 문화재 정보를 바탕으로
                학생들과 일반인이 흥미롭게
                이해할 수 있도록 설명해라.

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

                실제 전시관 도슨트처럼 설명해라.
                """

                guide_response = model.generate_content(
                    guide_prompt
                )

                st.write(
                    guide_response.text
                )

        #except Exception:
        except Exception as e:
            st.error(f"오류 발생: {e}")
    
            st.error(f"Gemini 오류 상세: {e}")
            #st.error(
            #    "Gemini API 사용량 초과 또는 API 오류 발생"
            #)

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

            try:

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

                    쉽고 친절하게 답변해라.
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

            except Exception:

                st.error(
                    "Gemini API 사용량 초과 또는 API 오류 발생"
                )

# =====================================================
# 오류 처리
# =====================================================
except Exception as e:

    st.error(
        "데이터를 불러오거나 처리하는 중 오류가 발생했습니다.\n\n"
        + str(e)
    )

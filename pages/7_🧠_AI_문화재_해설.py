import streamlit as st
import pandas as pd

# =========================================================
# 페이지 설정
# =========================================================
st.set_page_config(
    page_title="AI 문화재 해설",
    layout="wide"
)

# =========================================================
# 제목
# =========================================================
st.markdown("""
<h1 style='
    text-align:center;
    font-size:50px;
    margin-bottom:40px;
'>
🤖 AI 문화재 해설
</h1>
""", unsafe_allow_html=True)

# =========================================================
# 데이터 불러오기
# =========================================================
df = pd.read_csv(
    "data/processed/yc_heritage_detail_enriched.csv"
)

# =========================================================
# 품목 선택
# =========================================================
category = st.selectbox(
    "문화재 품목 선택",
    sorted(df["국가유산종목"].dropna().unique())
)

# 품목 필터링
filtered_df = df[
    df["국가유산종목"] == category
]

# =========================================================
# 문화재 선택
# =========================================================
heritage = st.selectbox(
    "문화재 선택",
    filtered_df["문화재명(국문)"]
)

# 선택된 행
row = filtered_df[
    filtered_df["문화재명(국문)"] == heritage
].iloc[0]

# =========================================================
# 문화재 제목
# =========================================================
st.markdown(f"""
<h2 style='
    text-align:center;
    font-size:42px;
    margin-top:30px;
    margin-bottom:30px;
'>
🏛 {heritage}
</h2>
""", unsafe_allow_html=True)

# =========================================================
# 좌우 컬럼
# =========================================================
left_col, right_col = st.columns([1, 1.5])

# =========================================================
# 왼쪽 : 이미지
# =========================================================
with left_col:

    # 실제 이미지 URL 컬럼명에 맞게 수정
    image_url = row.get("imageUrl", None)

    if pd.notna(image_url):

        st.image(
            image_url,
            use_container_width=True
        )

    else:
        st.warning("이미지 없음")

# =========================================================
# 오른쪽 : 상세 정보
# =========================================================
with right_col:

    info_html = f"""
    <table style="
        width:100%;
        border-collapse:collapse;
        font-size:16px;
    ">

    <tr>
        <td style="font-weight:bold; width:30%; padding:8px;">
            국가유산종목
        </td>
        <td style="padding:8px;">
            {row['국가유산종목']}
        </td>
    </tr>

    <tr>
        <td style="font-weight:bold; padding:8px;">
            국가유산분류
        </td>
        <td style="padding:8px;">
            {row['국가유산분류']}
        </td>
    </tr>

    <tr>
        <td style="font-weight:bold; padding:8px;">
            국가유산분류2
        </td>
        <td style="padding:8px;">
            {row['국가유산분류2']}
        </td>
    </tr>

    <tr>
        <td style="font-weight:bold; padding:8px;">
            국가유산분류3
        </td>
        <td style="padding:8px;">
            {row['국가유산분류3']}
        </td>
    </tr>

    <tr>
        <td style="font-weight:bold; padding:8px;">
            국가유산분류4
        </td>
        <td style="padding:8px;">
            {row['국가유산분류4']}
        </td>
    </tr>

    <tr>
        <td style="font-weight:bold; padding:8px;">
            문화재명(국문)
        </td>
        <td style="padding:8px;">
            {row['문화재명(국문)']}
        </td>
    </tr>

    <tr>
        <td style="font-weight:bold; padding:8px;">
            문화재명(한자)
        </td>
        <td style="padding:8px;">
            {row['문화재명(한자)']}
        </td>
    </tr>

    <tr>
        <td style="font-weight:bold; padding:8px;">
            소재지상세
        </td>
        <td style="padding:8px;">
            {row['소재지상세']}
        </td>
    </tr>

    <tr>
        <td style="font-weight:bold; padding:8px;">
            시대
        </td>
        <td style="padding:8px;">
            {row['시대']}
        </td>
    </tr>

    <tr>
        <td style="font-weight:bold; padding:8px;">
            소유자
        </td>
        <td style="padding:8px;">
            {row['소유자']}
        </td>
    </tr>

    <tr>
        <td style="font-weight:bold; padding:8px;">
            관리자
        </td>
        <td style="padding:8px;">
            {row['관리자']}
        </td>
    </tr>

    </table>
    """

    st.markdown(
        info_html,
        unsafe_allow_html=True
    )

# =========================================================
# 설명
# =========================================================
st.markdown("---")

st.markdown("""
<h3 style='font-size:28px;'>
📖 문화재 설명
</h3>
""", unsafe_allow_html=True)

content = str(row["내용"])

st.info(content)

# =========================================================
# AI 해설
# =========================================================
st.markdown("""
<h3 style='font-size:28px; margin-top:30px;'>
🤖 AI 해설
</h3>
""", unsafe_allow_html=True)

st.success(f"""
{heritage}은(는)
{row['시대']} 시대의 문화재로,

영천 지역의 역사와 문화를
잘 보여주는 중요한 국가유산입니다.

특히 {row['국가유산분류']} 분야에서
높은 역사적 가치를 지니고 있습니다.
""")

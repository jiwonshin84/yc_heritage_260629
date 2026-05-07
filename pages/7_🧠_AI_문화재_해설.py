import streamlit as st
import pandas as pd

st.markdown("""
<h1 style='font-size:40px; text-align:center;'>
🤖 AI 문화재 해설
</h1>
""", unsafe_allow_html=True)

# 데이터 불러오기
df = pd.read_csv(
    "data/processed/yc_heritage_detail_enriched.csv"
)

# =========================
# 품목 선택
# =========================
category = st.selectbox(
    "문화재 품목 선택",
    sorted(df["종목"].dropna().unique())
)

# 선택한 품목만 필터링
filtered_df = df[
    df["종목"] == category
]

# =========================
# 문화재 선택
# =========================
heritage = st.selectbox(
    "문화재 선택",
    filtered_df["문화재명(국문)"]
)

# 선택 데이터
row = filtered_df[
    filtered_df["문화재명(국문)"] == heritage
].iloc[0]

# =========================
# 제목
# =========================
st.subheader(heritage)

# =========================
# 이미지 표시
# =========================
# CSV 안 이미지 URL 컬럼명 확인 필요
# 예시: "imageUrl" 또는 "이미지URL"

image_url = row.get("imageUrl", None)

if pd.notna(image_url):
    st.image(
        image_url,
        caption=heritage,
        use_container_width=True
    )

# =========================
# 기본 정보
# =========================
col1, col2 = st.columns(2)

with col1:
    st.write("### 시대")
    st.info(row["시대"])

with col2:
    st.write("### 종목")
    st.info(row["종목"])

# =========================
# 설명
# =========================
st.write("### 설명")

content = str(row["내용"])

if len(content) > 500:
    content = content[:500] + "..."

st.write(content)

# =========================
# AI 해설
# =========================
st.write("### 🤖 AI 해설")

st.success(f"""
{heritage}은(는)

{row["시대"]} 시대에 만들어진
{row["종목"]} 문화재입니다.

역사적·문화적 가치가 높으며,
영천 지역의 역사와 문화를 이해하는 데
중요한 국가유산입니다.
""")

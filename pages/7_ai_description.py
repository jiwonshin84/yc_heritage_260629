import streamlit as st
import pandas as pd

st.title("🤖 AI 문화재 해설")

df = pd.read_csv(
    "data/processed/영천문화재_좌표보완.csv"
)

heritage = st.selectbox(
    "문화재 선택",
    df["문화재명(국문)"]
)

row = df[
    df["문화재명(국문)"] == heritage
].iloc[0]

st.subheader(heritage)

st.write("### 시대")
st.write(row["시대"])

st.write("### 설명")
st.write(row["내용"])

st.write("### AI 해설")

st.info(f"""
{heritage}은(는)
{row["시대"]} 시대의 문화재로
역사적 가치가 높은 국가유산입니다.
""")

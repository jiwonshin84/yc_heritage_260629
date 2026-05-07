import streamlit as st
import pandas as pd

st.set_page_config(page_title="AI 문화재 해설", layout="wide")

st.markdown("<h1 style='font-size:40px; text-align:center; margin-bottom:30px;'>🤖 AI 문화재 해설</h1>", unsafe_allow_html=True)

@st.cache_data
def load_data():
    return pd.read_csv("data/processed/yc_heritage_detail_enriched.csv")

def clean(val):
    if pd.isna(val):
        return "-"
    s = str(val).strip()
    return s if s != "" else "-"

try:
    df = load_data()

    col_select1, col_select2 = st.columns(2)

    with col_select1:
        if "종목" in df.columns:
            category_col = "종목"
        else:
            category_col = "국가유산종목"
        category = st.selectbox("📂 문화재 품목 선택", sorted(df[category_col].dropna().unique()))

    filtered_df = df[df[category_col] == category]

    with col_select2:
        heritage = st.selectbox("🏛 문화재 선택", filtered_df["문화재명(국문)"])

    row = filtered_df[filtered_df["문화재명(국문)"] == heritage].iloc[0]

    st.markdown(
        "<div style='background-color:#f8f9fa; padding:20px; border-radius:15px; margin-bottom:30px; border:1px solid #e9ecef;'>"
        "<h2 style='text-align:center; color:#2c3e50; margin:0;'>🏛 " + heritage + "</h2>"
        "</div>",
        unsafe_allow_html=True
    )

    left_col, right_col = st.columns([1, 1.2])

    with left_col:
        image_url = row.get("이미지URL", None)
        if pd.notna(image_url) and str(image_url).strip() != "":
            st.image(image_url, use_container_width=True)
            st.caption("출처: 국가유산청 - " + heritage)
        else:
            st.info("🖼 등록된 이미지가 없습니다.")

    with right_col:
        st.markdown("#### 📋 상세 정보")

        info_data = {
            "종목": clean(row.get(category_col)),
            "분류": clean(row.get("국가유산분류")) + " (" + clean(row.get("국가유산분류2")) + ")",
            "한자명": clean(row.get("문화재명(한자)")),
            "시대": clean(row.get("시대")),
            "소재지": clean(row.get("소재지상세")),
            "소유자/관리자": clean(row.get("소유자")) + " / " + clean(row.get("관리자"))
        }

        for key, value in info_data.items():
            col_a, col_b = st.columns([1, 2])
            with col_a:
                st.markdown("**" + key + "**")
            with col_b:
                st.markdown(value)
            st.divider()

    st.markdown("<br>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["📖 상세 설명", "🤖 AI 스마트 해설"])

    with tab1:
        content = str(row.get("내용", "상세 설명 정보가 없습니다."))
        st.markdown(
            "<div style='line-height:1.8; background-color:#ffffff; padding:20px; border-radius:10px; border:1px solid #eee;'>"
            + content +
            "</div>",
            unsafe_allow_html=True
        )

    with tab2:
        시대 = clean(row.get("시대"))
        소재지 = clean(row.get("소재지상세"))
        종목 = clean(row.get(category_col))
        st.success(
            "### 🤖 AI 도슨트 가이드\n\n"
            "**" + heritage + "**은(는) **" + 시대 + "** 시대의 숨결을 간직한 소중한 유산입니다.\n\n"
            "현재 **" + 소재지 + "**에 보존되어 있으며, "
            "**" + 종목 + "**으로서 학술적 가치가 매우 높습니다.\n\n"
            "특히 이 유산은 영천 지역의 역사적 정체성을 잘 보여주는 중요한 지표가 됩니다."
        )

except Exception as e:
    st.error("데이터를 불러오거나 처리하는 중 오류가 발생했습니다: " + str(e))

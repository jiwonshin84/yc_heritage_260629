import streamlit as st
import pandas as pd

# 페이지 설정
st.set_page_config(page_title="AI 문화재 해설", layout="wide")

st.markdown("""
<h1 style='font-size:40px; text-align:center; margin-bottom: 30px;'>
🤖 AI 문화재 해설
</h1>
""", unsafe_allow_html=True)

# 데이터 불러오기
@st.cache_data
def load_data():
    df = pd.read_csv("data/processed/yc_heritage_detail_enriched.csv")
    return df

df = load_data()

# =========================
# 품목 및 문화재 선택 (사이드바 또는 상단)
# =========================
col1, col2 = st.columns(2)

with col1:
    category = st.selectbox(
        "📂 문화재 품목 선택",
        sorted(df["국가유산종목"].dropna().unique())
    )

filtered_df = df[df["국가유산종목"] == category]

with col2:
    heritage = st.selectbox(
        "🏛 문화재 선택",
        filtered_df["문화재명(국문)"]
    )

row = filtered_df[filtered_df["문화재명(국문)"] == heritage].iloc[0]

# =========================
# 제목 부분
# =========================
st.markdown(f"""
<div style="background-color: #f0f2f6; padding: 20px; border-radius: 10px; margin-bottom: 25px;">
    <h2 style='text-align:center; color: #31333F; margin: 0;'>
        🏛 {heritage}
    </h2>
</div>
""", unsafe_allow_html=True)

# =========================
# 메인 컨텐츠 (좌우 배치)
# =========================
left_col, right_col = st.columns([1, 1.2])

# -------------------------
# 왼쪽 : 이미지
# -------------------------
with left_col:
    # 이미지 URL 확인 (컬럼명이 'imageUrl'인지 데이터프레임 확인 필요)
    image_url = row.get("imageUrl", None)

    if pd.notna(image_url) and str(image_url).startswith('http'):
        st.image(image_url, use_container_width=True, caption=heritage)
    else:
        # 이미지가 없을 때 보여줄 플레이스홀더
        st.info("🖼 등록된 이미지가 없습니다.")
        st.markdown("""
        <div style="width:100%; height:300px; background-color:#f9f9f9; border:1px dashed #ccc; 
        display:flex; align-items:center; justify-content:center; border-radius:10px;">
            <span style="color:#999;">이미지 준비 중</span>
        </div>
        """, unsafe_allow_html=True)

# -------------------------
# 오른쪽 : 상세 정보 (테이블)
# -------------------------
with right_col:
    # NaN 값을 빈 문자열이나 '정보 없음'으로 처리
    def clean_val(val):
        return val if pd.notna(val) and str(val).strip() != "" else "-"

    info_items = {
        "국가유산종목": row.get('국가유산종목'),
        "국가유산분류": f"{clean_val(row.get('국가유산분류'))} > {clean_val(row.get('국가유산분류2'))}",
        "세부분류": f"{clean_val(row.get('국가유산분류3'))} > {clean_val(row.get('국가유산분류4'))}",
        "문화재명(한자)": row.get('문화재명(한자)'),
        "시대": row.get('시대'),
        "소재지": row.get('소재지상세'),
        "관리자(소유자)": f"{clean_val(row.get('관리자'))} ({clean_val(row.get('소유자'))})"
    }

    # HTML 테이블 생성
    table_html = """
    <table style="width:100%; border-collapse:collapse; font-size:15px;">
    """
    for key, value in info_items.items():
        table_html += f"""
        <tr style="border-bottom: 1px solid #eee;">
            <td style="padding: 10px; font-weight: bold; background-color: #fafafa; width: 30%;">{key}</td>
            <td style="padding: 10px;">{clean_val(value)}</td>
        </tr>
        """
    table_html += "</table>"
    
    st.markdown(table_html, unsafe_allow_html=True)

# =========================
# 하단 설명 및 AI 해설
# =========================
st.markdown("<br>", unsafe_allow_html=True)
tab1, tab2 = st.tabs(["📖 문화재 설명", "🤖 AI 스마트 해설"])

with tab1:
    content = str(row.get("내용", "설명 데이터가 없습니다."))
    st.markdown(f"""
    <div style="line-height: 1.8; background-color: #f8f9fa; padding: 20px; border-radius: 10px;">
        {content}
    </div>
    """, unsafe_allow_html=True)

with tab2:
    st.success(f"""
    ### 🤖 AI 도슨트의 한마디
    **{heritage}**은(는) **{clean_val(row.get('시대'))}** 시대에 조성된 유산으로, 
    현재 **{clean_val(row.get('소재지상세'))}** 지역의 역사를 증명하는 중요한 자료입니다.
    
    이 문화재는 **{clean_val(row.get('국가유산분류'))}** 체계에서 학술적/역사적 가치를 인정받고 있으며, 
    당시의 기술력과 시대상을 엿볼 수 있는 소중한 국가유산입니다.
    """)

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
    return pd.read_csv("data/processed/yc_heritage_detail_enriched.csv")

try:
    df = load_data()

    # =========================
    # 품목 및 문화재 선택
    # =========================
    col_select1, col_select2 = st.columns(2)

    with col_select1:
        category = st.selectbox(
            "📂 문화재 품목 선택",
            sorted(df["국가유산종목"].dropna().unique())
        )

    filtered_df = df[df["국가유산종목"] == category]

    with col_select2:
        heritage = st.selectbox(
            "🏛 문화재 선택",
            filtered_df["문화재명(국문)"]
        )

    row = filtered_df[filtered_df["문화재명(국문)"] == heritage].iloc[0]

    # =========================
    # 제목 부분
    # =========================
    st.markdown(f"""
    <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin-bottom: 25px;">
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
    # 왼쪽 : 이미지 표시 (컬럼명: 이미지URL)
    # -------------------------
    with left_col:
        # 알려주신 컬럼명 '이미지URL' 사용
        image_url = row.get("이미지URL", None)

        # URL이 문자열이고 비어있지 않은지 확인
        if pd.notna(image_url) and str(image_url).strip() != "":
            st.image(
                image_url, 
                use_container_width=True, 
                caption=f"출처: 국가유산청 - {heritage}"
            )
        else:
            st.warning("⚠️ 등록된 이미지가 없습니다.")
            # 이미지가 없을 때의 대체 박스
            st.markdown("""
            <div style="width:100%; height:300px; background-color:#f9f9f9; border:1px dashed #ccc; 
            display:flex; align-items:center; justify-content:center; border-radius:10px;">
                <span style="color:#999;">이미지 준비 중</span>
            </div>
            """, unsafe_allow_html=True)

    # -------------------------
    # 오른쪽 : 상세 정보 (테이블 형식)
    # -------------------------
    with right_col:
        def clean_val(val):
            return val if pd.notna(val) and str(val).strip() != "" else "-"

        info_items = {
            "국가유산종목": row.get('국가유산종목'),
            "국가유산분류": f"{clean_val(row.get('국가유산분류'))} ({clean_val(row.get('국가유산분류2'))})",
            "문화재명(한자)": row.get('문화재명(한자)'),
            "시대": row.get('시대'),
            "소재지": row.get('소재지상세'),
            "관리자/소유자": f"{clean_val(row.get('관리자'))} / {clean_val(row.get('소유자'))}"
        }

        # HTML 테이블 렌더링
        table_html = "<table style='width:100%; border-collapse:collapse;'>"
        for key, value in info_items.items():
            table_html += f"""
            <tr style="border-bottom: 1px solid #eee;">
                <td style="padding: 10px; font-weight: bold; background-color: #fafafa; width: 35%;">{key}</td>
                <td style="padding: 10px;">{clean_val(value)}</td>
            </tr>
            """
        table_html += "</table>"
        
        st.markdown(table_html, unsafe_allow_html=True)

    # =========================
    # 하단 탭 (설명 & AI 해설)
    # =========================
    st.markdown("<br>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["📖 문화재 설명", "🤖 AI 스마트 해설"])

    with tab1:
        content = str(row.get("내용", "상세 설명 정보가 없습니다."))
        st.info(content)

    with tab2:
        st.success(f"""
        ### 🤖 AI 도슨트 가이드
        **{heritage}**은(는) **{clean_val(row.get('시대'))}** 시대에 만들어진 소중한 유산입니다.
        
        이 유산은 **{clean_val(row.get('국가유산종목'))}**으로 분류되어 있으며, 
        현재 **{clean_val(row.get('소재지상세'))}**에 위치하여 영천의 유구한 역사를 증명해주고 있습니다.
        
        특히 **{clean_val(row.get('국가유산분류'))}** 측면에서 그 가치가 매우 높게 평가됩니다.
        """)

except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.info("CSV 파일의 컬럼명(이미지URL, 국가유산종목 등)이 정확한지 확인해주세요.")

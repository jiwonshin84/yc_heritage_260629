import streamlit as st
import pandas as pd
import google.generativeai as genai

# =====================================================
# 1. 페이지 및 보안 설정
# =====================================================
st.set_page_config(
    page_title="영천 AI 문화재 해설사",
    page_icon="🤖",
    layout="wide"
)

# [중요] Secrets에서 키를 가져와 Gemini 설정
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-2.5-flash")
else:
    st.error("API 키가 설정되지 않았습니다. Streamlit Cloud의 Settings -> Secrets에 GEMINI_API_KEY를 입력해주세요.")
    st.stop()

# =====================================================
# 2. 데이터 처리 함수
# =====================================================
@st.cache_data
def load_data():
    # 데이터 경로가 현재 환경과 일치하는지 확인하세요.
    return pd.read_csv("data/processed/yc_heritage_detail_enriched.csv")

def clean(val):
    if pd.isna(val) or str(val).strip() == "":
        return "-"
    return str(val).strip()

# =====================================================
# 3. 메인 UI 렌더링
# =====================================================
try:
    df = load_data()
    
    st.title("🤖 AI 문화재 해설 가이드")
    st.markdown("---")

    # [문화재 선택 필터]
    category_col = "종목" if "종목" in df.columns else "국가유산종목"
    col_sel1, col_sel2 = st.columns(2)
    
    with col_sel1:
        category = st.selectbox("📂 문화재 품목 선택", sorted(df[category_col].dropna().unique()))
    
    filtered_df = df[df[category_col] == category]
    
    with col_sel2:
        heritage = st.selectbox("🏛 문화재 선택", filtered_df["문화재명(국문)"])

    row = filtered_df[filtered_df["문화재명(국문)"] == heritage].iloc[0]

    # [상단 타이틀 배너]
    st.markdown(f"""
        <div style="background-color:#f8f9fa; padding:20px; border-radius:15px; text-align:center; margin-bottom:25px; border:1px solid #e9ecef;">
            <h1 style="margin:0; color:#2c3e50; font-size:32px;">🏛 {heritage}</h1>
        </div>
    """, unsafe_allow_html=True)

    # [좌우 분할 콘텐츠]
    left_col, right_col = st.columns([1, 1.2], gap="large")

    with left_col:
        image_url = row.get("이미지URL")
        if pd.notna(image_url) and str(image_url).strip() != "":
            st.image(image_url, use_container_width=True)
            st.caption(f"출처: 국가유산청 - {heritage}")
        else:
            st.info("🖼 등록된 이미지가 없습니다.")

    with right_col:
        st.markdown("<h3 style='margin-top:0; color:#2c3e50;'>📋 상세 정보</h3>", unsafe_allow_html=True)
        
        # ⭐️ HTML 노출 문제 완벽 해결 테이블 (st.markdown 통합)
        st.markdown(f"""
            <style>
                .info-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; border: 1px solid #f0f0f0; }}
                .info-tr {{ border-bottom: 1px solid #eeeeee; }}
                .info-key {{ width: 25%; padding: 12px 10px; font-weight: bold; color: #34495e; background-color: #f8f9fa; font-size: 15px; }}
                .info-val {{ width: 75%; padding: 12px 15px; color: #2c3e50; font-size: 15px; line-height: 1.5; }}
            </style>
            <table class="info-table">
                <tr class="info-tr"><td class="info-key">종목</td><td class="info-val">{clean(row.get(category_col))}</td></tr>
                <tr class="info-tr"><td class="info-key">분류</td><td class="info-val">{clean(row.get('국가유산분류'))} ({clean(row.get('국가유산분류2'))})</td></tr>
                <tr class="info-tr"><td class="info-key">한자명</td><td class="info-val">{clean(row.get('문화재명(한자)'))}</td></tr>
                <tr class="info-tr"><td class="info-key">시대</td><td class="info-val">{clean(row.get('시대'))}</td></tr>
                <tr class="info-tr"><td class="info-key">소재지</td><td class="info-val">{clean(row.get('소재지상세'))}</td></tr>
                <tr class="info-tr"><td class="info-key">소유/관리</td><td class="info-val">{clean(row.get('소유자'))} / {clean(row.get('관리자'))}</td></tr>
            </table>
        """, unsafe_allow_html=True)
        
        with st.expander("📖 원문 설명 보기", expanded=True):
            st.write(clean(row.get("내용")))

    # [AI 스마트 도슨트 기능]
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.divider()
    st.header("🤖 AI 스마트 도슨트")
    
    col_ai1, col_ai2 = st.columns(2)
    
    with col_ai1:
        if st.button("✨ AI 도슨트 해설 생성"):
            with st.spinner("AI 해설사가 원고를 작성 중입니다..."):
                prompt = f"당신은 영천 지역 문화재 전문 도슨트입니다. '{heritage}'에 대해 역사적 배경과 특징을 구어체로 설명해 주세요. 참고 자료: {clean(row.get('내용'))}"
                response = model.generate_content(prompt)
                st.info(response.text)
                
    with col_ai2:
        user_q = st.text_input("💬 궁금한 점을 질문해 보세요.")
        if st.button("질문 전송"):
            if user_q:
                with st.spinner("답변을 생성 중입니다..."):
                    res = model.generate_content(f"{heritage}에 대한 질문: {user_q}\n자료: {clean(row.get('내용'))}")
                    st.success(res.text)

except Exception as e:
    st.error(f"오류가 발생했습니다: {e}")

import streamlit as st
import pandas as pd

# 1. 페이지 설정
st.set_page_config(page_title="AI 문화재 해설", layout="wide")

# 상단 제목
st.markdown("""
<h1 style='font-size:40px; text-align:center; margin-bottom: 30px;'>
🤖 AI 문화재 해설
</h1>
""", unsafe_allow_html=True)

# 2. 데이터 불러오기
@st.cache_data
def load_data():
    # 파일 경로가 실제 환경과 맞는지 확인하세요.
    return pd.read_csv("data/processed/yc_heritage_detail_enriched.csv")

try:
    df = load_data()

    # 3. 품목 및 문화재 선택
    col_select1, col_select2 = st.columns(2)

    with col_select1:
        # 컬럼명이 '종목'인지 '국가유산종목'인지 데이터프레임에 맞춰 확인 필요
        category_col = "종목" if "종목" in df.columns else "국가유산종목"
        category = st.selectbox(
            "📂 문화재 품목 선택",
            sorted(df[category_col].dropna().unique())
        )

    filtered_df = df[df[category_col] == category]

    with col_select2:
        heritage = st.selectbox(
            "🏛 문화재 선택",
            filtered_df["문화재명(국문)"]
        )

    # 선택된 행 데이터
    row = filtered_df[filtered_df["문화재명(국문)"] == heritage].iloc[0]

    # 4. 중앙 제목 섹션
    st.markdown(f"""
    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 15px; margin-bottom: 30px; border: 1px solid #e9ecef;">
        <h2 style='text-align:center; color: #2c3e50; margin: 0;'>
            🏛 {heritage}
        </h2>
    </div>
    """, unsafe_allow_html=True)

    # 5. 메인 컨텐츠 (이미지 + 상세정보 테이블)
    left_col, right_col = st.columns([1, 1.2])

    # --- 왼쪽: 이미지 ---
    with left_col:
        image_url = row.get("이미지URL", None)
        if pd.notna(image_url) and str(image_url).strip() != "":
            st.image(image_url, use_container_width=True)
            st.caption(f"출처: 국가유산청 - {heritage}")
        else:
            st.info("🖼 등록된 이미지가 없습니다.")
            st.markdown("""
            <div style="width:100%; height:350px; background-color:#f1f3f5; border:1px dashed #ced4da; 
            display:flex; align-items:center; justify-content:center; border-radius:10px;">
                <span style="color:#adb5bd;">이미지 준비 중</span>
            </div>
            """, unsafe_allow_html=True)

    # --- 오른쪽: 상세 정보 테이블 ---
    with right_col:
        # 데이터 정제 함수 (NaN 처리)
        def clean(val):
            return str(val) if pd.notna(val) and str(val).strip() != "" else "-"

        # 표시할 항목 정리
        info_data = {
            "종목": clean(row.get(category_col)),
            "분류": f"{clean(row.get('국가유산분류'))} ({clean(row.get('국가유산분류2'))})",
            "한자명": clean(row.get('문화재명(한자)')),
            "시대": clean(row.get('시대')),
            "소재지": clean(row.get('소재지상세')),
            "소유자/관리자": f"{clean(row.get('소유자'))} / {clean(row.get('관리자'))}"
        }

        # HTML 테이블 생성 (문자열 결합 방식이 렌더링 오류가 적습니다)
        rows_html = ""
        for key, value in info_data.items():
            rows_html += f"""
            <tr style="border-bottom: 1px solid #eee;">
                <td style="padding: 12px; font-weight: bold; background-color: #fcfcfc; width: 35%; color: #495057;">{key}</td>
                <td style="padding: 12px; color: #212529;">{value}</td>
            </tr>
            """
        
        table_html = f"""
        <table style="width:100%; border-collapse:collapse; border: 1px solid #eee; font-size: 15px;">
            <tbody>
                {rows_html}
            </tbody>
        </table>
        """
        st.markdown(table_html, unsafe_allow_html=True)

    # 6. 하단 설명 및 AI 해설 (탭 구성)
    st.markdown("<br>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["📖 상세 설명", "🤖 AI 스마트 해설"])

    with tab1:
        content = str(row.get("내용", "상세 설명 정보가 없습니다."))
        st.markdown(f"""
        <div style="line-height: 1.8; background-color: #ffffff; padding: 20px; border-radius: 10px; border: 1px solid #eee;">
            {content}
        </div>
        """, unsafe_allow_html=True)

    with tab2:
        st.success(f"""
        ### 🤖 AI 도슨트 가이드
        **{heritage}**은(는) **{clean(row.get('시대'))}** 시대의 숨결을 간직한 소중한 유산입니다.
        
        현재 **{clean(row.get('소재지상세'))}**에 보존되어 있으며, 
        **{clean(row.get(category_col))}**으로서 학술적 가치가 매우 높습니다.
        
        특히 이 유산은 영천 지역의 역사적 정체성을 잘 보여주는 중요한 지표가 됩니다.
        """)

except Exception as e:
    st.error(f"데이터를 불러오거나 처리하는 중 오류가 발생했습니다: {e}")

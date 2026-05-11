import streamlit as st
import pandas as pd
import folium
import re
from streamlit_folium import st_folium
from folium.plugins import HeatMap, MarkerCluster

# =================================================
# 페이지 설정
# =================================================
st.set_page_config(
    page_title="🛰️ 영천 국가유산 공간 정보",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS를 이용해 목록 스크롤바 및 스타일 보정
st.markdown("""
    <style>
    .heritage-card {
        border-radius: 10px;
        padding: 10px;
        margin-bottom: 10px;
        border: 1px solid #ddd;
    }
    .stButton>button {
        text-align: left;
        display: block;
        border: none;
        padding: 0;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🗺 영천 문화재 공간분석")

# =================================================
# 데이터 로드 및 전처리 (캐싱 적용)
# =================================================
@st.cache_data
def load_data():
    # 데이터 경로를 실제 환경에 맞게 수정하세요.
    df = pd.read_csv("data/processed/yc_heritage_detail_enriched.csv")
    df.columns = df.columns.str.strip()
    df = df.dropna(subset=["위도", "경도"])
    
    # 시대 그룹화 함수 내부 포함
    def simplify_era(text):
        if pd.isna(text): return "기타"
        text = str(text).strip()
        if "청동기" in text: return "청동기"
        elif "통일신라" in text or "신라시대 후기" in text: return "통일신라"
        elif "신라" in text: return "신라"
        elif "고려" in text:
            if "초기" in text: return "고려초기"
            if "말기" in text or "후기" in text: return "고려후기"
            return "고려"
        elif any(king in text for king in ["세종", "태조", "태종", "문종", "단종", "세조", "성종", "연산군", "중종", "인종"]):
            return "조선초기"
        elif any(king in text for king in ["숙종", "영조", "정조", "순조", "철종", "고종", "광해군"]):
            return "조선후기"
        elif "조선" in text:
            if "초기" in text: return "조선초기"
            if "후기" in text: return "조선후기"
            return "조선"
        elif "대한제국" in text: return "대한제국"
        
        # 연도 기반
        year_match = re.search(r"\d{4}", text)
        if year_match:
            year = int(year_match.group())
            if year < 700: return "신라"
            elif year < 1400: return "고려"
            elif year < 1600: return "조선초기"
            elif year < 1910: return "조선후기"
        return "기타"

    df["시대그룹"] = df["시대"].apply(simplify_era)
    df["국가유산종목"] = df.get("국가유산종목", "미상").fillna("미상").astype(str)
    df["소재지상세"] = df.get("소재지상세", "-").fillna("-").astype(str)
    return df

df = load_data()

# =================================================
# 사이드바 필터
# =================================================
st.sidebar.header("🔎 문화재 필터")

era_order = ["청동기", "신라", "통일신라", "고려초기", "고려", "고려후기", "조선초기", "조선", "조선후기", "대한제국", "기타"]
existing_eras = [e for e in era_order if e in df["시대그룹"].unique()]
selected_era = st.sidebar.selectbox("시대 선택", ["전체"] + existing_eras)

type_options = ["전체"] + sorted(df["국가유산종목"].unique().tolist())
selected_type = st.sidebar.selectbox("종목 선택", type_options)

# 필터 적용
filtered_df = df.copy()
if selected_era != "전체":
    filtered_df = filtered_df[filtered_df["시대그룹"] == selected_era]
if selected_type != "전체":
    filtered_df = filtered_df[filtered_df["국가유산종목"] == selected_type]

st.sidebar.info(f"🏛 검색된 문화재: {len(filtered_df)}개")

if filtered_df.empty:
    st.warning("조건에 맞는 문화재가 없습니다.")
    st.stop()

# =================================================
# 세션 상태 관리 (선택된 문화재)
# =================================================
if "selected_heritage" not in st.session_state or \
   st.session_state.selected_heritage not in filtered_df["문화재명(국문)"].values:
    st.session_state.selected_heritage = filtered_df.iloc[0]["문화재명(국문)"]

# 선택된 데이터 추출
selected_row = filtered_df[filtered_df["문화재명(국문)"] == st.session_state.selected_heritage].iloc[0]

# =================================================
# 레이아웃 구성
# =================================================
map_col, list_col = st.columns([3.5, 1.2])

with map_col:
    # 지도 생성
    m = folium.Map(
        location=[selected_row["위도"], selected_row["경도"]],
        zoom_start=15,
        tiles="CartoDB positron"
    )

    marker_cluster = MarkerCluster().add_to(m)
    
    # 히트맵 데이터 준비
    heat_data = filtered_df[["위도", "경도"]].values.tolist()
    HeatMap(heat_data, radius=15, blur=10).add_to(m)

    for _, row in filtered_df.iterrows():
        name = row["문화재명(국문)"]
        is_selected = (name == st.session_state.selected_heritage)
        
        # 이미지 HTML 처리
        img_url = str(row.get("이미지URL", "")).replace("http://", "https://")
        if not img_url or img_url.lower() == "nan":
            img_tag = '<div style="width:100%; height:150px; background:#eee; display:flex; justify-content:center; align-items:center; border-radius:8px;">이미지 없음</div>'
        else:
            img_tag = f'<img src="{img_url}" style="width:100%; height:180px; object-fit:cover; border-radius:8px;">'

        popup_html = f"""
            <div style="width:280px; font-family:sans-serif;">
                <h4 style="margin-top:0;">{name}</h4>
                {img_tag}
                <p style="font-size:13px; margin-top:10px;">
                    <b>시대:</b> {row['시대그룹']}<br>
                    <b>종목:</b> {row['국가유산종목']}<br>
                    <b>주소:</b> {row['소재지상세']}
                </p>
            </div>
        """
        
        folium.Marker(
            location=[row["위도"], row["경도"]],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=name,
            icon=folium.Icon(color="red" if is_selected else "blue", icon="info-sign")
        ).add_to(marker_cluster)

    st_folium(m, width="100%", height=700, key="heritage_map")

with list_col:
    st.subheader("🏛 문화재 목록")
    # 스크롤 가능한 영역 생성
    list_container = st.container(height=650)
    with list_container:
        for idx, row in filtered_df.iterrows():
            name = row["문화재명(국문)"]
            addr = row["소재지상세"]
            is_selected = (name == st.session_state.selected_heritage)
            
            # 스타일 설정
            bg_color = "#FFF0F0" if is_selected else "transparent"
            border_color = "#FF4B4B" if is_selected else "#DDD"
            
            # 목록 카드 구성
            with st.container():
                # 버튼을 클릭하면 세션 상태 업데이트 및 리프레시
                if st.button(f"📍 {name}", key=f"btn_{idx}", use_container_width=True):
                    st.session_state.selected_heritage = name
                    st.rerun()
                
                # 버튼 바로 아래 상세 주소 표시 (HTML 코드 노출 문제 해결)
                st.caption(f"{addr}")
                st.markdown("---")

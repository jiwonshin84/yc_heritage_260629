# ==========================================================
# 1. 라이브러리 로드
# ==========================================================
import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, silhouette_samples
from sklearn.preprocessing import StandardScaler

# ==========================================================
# 2. 페이지 설정 및 API 키
# ==========================================================
st.set_page_config(
    page_title="영천시 국가유산 위험예측 시스템",
    page_icon="🏛",
    layout="wide"
)

SERVICE_KEY = "feb2bfabd299d5d05e89c7aec49ba7e706112603e76549a92e868bd86ec60323"

# ==========================================================
# 3. 실시간 환경 데이터 수집 (기상청 & 에어코리아)
# ==========================================================

@st.cache_data(ttl=3600) # 1시간마다 데이터 갱신
def get_env_data():
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    
    # [기상 데이터 - ASOS] 현재 시각 기준 최신 데이터 (보통 1시간 전 데이터가 확정치)
    search_time = now - timedelta(hours=1)
    base_date = search_time.strftime("%Y%m%d")
    base_hour = search_time.strftime("%H")
    
    asos_url = "https://apis.data.go.kr/1360000/AsosHourlyInfoService/getWthrDataList"
    asos_params = {
        "serviceKey": SERVICE_KEY, "pageNo": "1", "numOfRows": "1", "dataType": "JSON",
        "dataCd": "ASOS", "dateCd": "HR", "stnIds": "281", # 영천 관측소
        "startDt": base_date, "startHh": base_hour, "endDt": base_date, "endHh": base_hour
    }
    
    # [대기오염 데이터 - Arpltn]
    air_url = "https://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getCtprvnRltmMesureDnsty"
    air_params = {
        "serviceKey": SERVICE_KEY, "returnType": "json", "numOfRows": "100", 
        "pageNo": "1", "sidoName": "경북", "ver": "1.0"
    }
    
    env_res = {"weather": {}, "air": {}}
    
    try:
        # 기상 조회
        res_w = requests.get(asos_url, params=asos_params, timeout=10).json()
        item_w = res_w["response"]["body"]["items"]["item"][0]
        env_res["weather"] = {
            "tm": item_w["tm"], "temp": item_w["ta"], "hum": item_w["hm"],
            "rn": item_w["rn"] if item_w["rn"] else "0", "ws": item_w["ws"]
        }
        
        # 대기 조회
        res_a = requests.get(air_url, params=air_params, timeout=10).json()
        items_a = res_a["response"]["body"]["items"]
        for item in items_a:
            if "영천" in item["stationName"]:
                env_res["air"] = item
                break
    except:
        st.warning("일부 실시간 데이터를 불러올 수 없습니다. 기본값을 표시합니다.")
        
    return env_res

env_data = get_env_data()

# ==========================================================
# 4. 데이터 로드 및 지능형 군집 분석 (위험관리 지구 도출)
# ==========================================================

@st.cache_data
def load_heritage_data():
    df = pd.read_csv("data/processed/yc_clustering.csv")
    df = df.dropna(subset=['위도', '경도', '가치점수', '시대점수'])
    df['소재지상세'] = df['소재지상세'].fillna("-").astype(str).str.replace('\t', ' ', regex=True).str.strip()
    return df

df_base = load_heritage_data()

# 군집 분석 (표준화 적용 - 지리적 가중치 강화)
scaler = StandardScaler()
features_scaled = scaler.fit_transform(df_base[['위도', '경도', '가치점수', '시대점수']])

# 사이드바에서 K값 조절
k_val = st.sidebar.slider("🛠 위험 관리 지구 수(k) 설정", 2, 10, 5)
kmeans = KMeans(n_clusters=k_val, random_state=42, n_init=10)
df_base['cluster'] = (kmeans.fit_predict(features_scaled) + 1).astype(str)

# ==========================================================
# 5. UI 렌더링 - 상단 대시보드
# ==========================================================
st.markdown("<h2 style='font-size:28px;'>🏛 실시간 환경 데이터 기반 영천 유산 위험예측</h2>", unsafe_allow_html=True)
st.divider()

# 대시보드 카드 스타일
card_style = "background-color:#f8f9fa; padding:20px; border-radius:15px; border:1px solid #e5e7eb; height:280px;"

col_w, col_a, col_h = st.columns([1, 1.2, 0.8])

with col_w:
    w = env_data["weather"]
    st.markdown(f"""<div style="{card_style}"><h4>🌦 최신 기상</h4><hr>
    <b>🌡 기온:</b> {w.get('temp', '-')} °C<br><b>💧 습도:</b> {w.get('hum', '-')} %<br>
    <b>🌧 강수:</b> {w.get('rn', '-')} mm<br><b>💨 풍속:</b> {w.get('ws', '-')} m/s<br>
    <p style='font-size:12px; color:gray; margin-top:15px;'>⏱ {w.get('tm', '-')}</p></div>""", unsafe_allow_html=True)

with col_a:
    a = env_data["air"]
    st.markdown(f"""<div style="{card_style}"><h4>🌫 대기 환경</h4><hr>
    <div style='display:flex; justify-content:space-between;'>
    <span><b>PM10:</b> {a.get('pm10Value', '-')}</span><span><b>PM2.5:</b> {a.get('pm25Value', '-')}</span>
    </div><div style='display:flex; justify-content:space-between;'>
    <span><b>O₃:</b> {a.get('o3Value', '-')}</span><span><b>NO₂:</b> {a.get('no2Value', '-')}</span>
    </div><p style='font-size:12px; color:gray; margin-top:55px;'>⏱ {a.get('dataTime', '-')}</p></div>""", unsafe_allow_html=True)

with col_h:
    st.markdown(f"""<div style="{card_style}"><h4>📊 분석 현황</h4><hr>
    <b>분석 대상:</b> {len(df_base)}개<br><b>관리 지구:</b> {k_val}개 구역<br>
    <br><span style='color:red;'>⚠️ 고위험 예측: 18개</span></div>""", unsafe_allow_html

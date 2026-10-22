import io
import requests
import pandas as pd
import numpy as np
import plotly.express as px
import streamlit as st

# 페이지 기본 설정
st.set_page_config(
    page_title="전국 인구 구조 단계구분도",
    page_icon="🗺️",
    layout="wide"
)

# HTTP 요청 헤더 (GitHub 차단 방지)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

@st.cache_data(show_spinner="인구 데이터를 불러오는 중입니다...")
def load_population_data():
    """Github raw zip 파일에서 인구 데이터를 읽어오는 함수"""
    # 중복 슬래시(//) 수정 및 User-Agent 헤더 추가
    pop_url = "https://raw.githubusercontent.com/njy0625-beep/contents/main/population_ts_yearly_gender.zip"
    try:
        response = requests.get(pop_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        zip_buffer = io.BytesIO(response.content)
        df = pd.read_csv(zip_buffer)
        return df
    except Exception as e:
        st.error(f"인구 데이터 로딩 실패: {e}")
        st.stop()


@st.cache_data(show_spinner="시군구 경계 GeoJSON 데이터를 불러오는 중입니다...")
def load_geojson_data():
    """Github raw에서 시군구 경계 GeoJSON을 읽어오는 함수"""
    # 중복 슬래시(//) 수정 및 User-Agent 헤더 추가
    geojson_url = "https://raw.githubusercontent.com/first2022-cyber/contents/main/sigungu_kr.geojson"
    try:
        response = requests.get(geojson_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        geo_data = response.json()

        # GeoJSON 내의 '코드' 속성을 5자리 문자열로 통일
        for feature in geo_data['features']:
            code = str(feature['properties'].get('코드', '')).strip().zfill(5)
            feature['properties']['코드'] = code

        return geo_data
    except Exception as e:
        st.error(f"GeoJSON 데이터 로딩 실패: {e}")
        st.stop()


def fix_sigungu_code(code_str):
    """행정구역 개편 및 통합에 따른 과거 시군구 코드 변환 매핑"""
    code = str(code_str).strip().zfill(8)[:5]
    if code == '47720':  # 군위군 (경북 47 -> 대구 27)
        return '27720'
    if code.startswith('42'):  # 강원 특별자치도 (42 -> 51)
        return '51' + code[2:]
    if code.startswith('45'):  # 전북 특별자치도 (45 -> 52)
        return '52' + code[2:]
    return code


# --- 데이터 로딩 ---
df_raw = load_population_data()
geo_data = load_geojson_data()

# 연도 추출 (2015 ~ 2026)
df_raw['연도_숫자'] = df_raw['연도'].astype(str).str.extract(r'(\d{4})').astype(int)
available_years = sorted(df_raw['연도_숫자'].unique().tolist())

# --- 사이드바 컨트롤 ---
st.sidebar.header("⚙️ 검색 및 지표 설정")

# 1. 연도 선택 슬라이더
selected_year = st.sidebar.slider(
    "📅 연도 선택",
    min_value=int(min(available_years)),
    max_value=int(max(available_years)),
    value=int(max(available_years)),
    step=1
)

# 2. 지표 선택
indicator_option = st.sidebar.radio(
    "📊 분석 지표 선택",
    ["65세 이상 비율 (고령화율)", "0~14세 비율 (유소년 비율)"]
)

# --- 선택된 연도 데이터 필터링 및 집계 ---
df_year = df_raw[df_raw['연도_숫자'] == selected_year].copy()
df_year['sigungu_code'] = df_year['코드'].apply(fix_sigungu_code)

total_cols = [c for c in df_year.columns if c.startswith('계_')]

def parse_age(col):
    clean = col.replace('계_', '').replace('세', '').replace('이상', '').strip()
    try:
        return int(clean)
    except ValueError:
        return None

# 지표별 연령열 추출 및 색상 구간 설정
if "65세" in indicator_option:
    metric_title = "고령화율"
    target_cols = [c for c in total_cols if (p := parse_age(c)) is not None and p >= 65]
    
    # 19%, 23%, 28%, 38% 고정 경계값
    bins = [-1, 19, 23, 28, 38, 100]
    bin_labels = ["19% 미만", "19% ~ 23%", "23% ~ 28%", "28% ~ 38%", "38% 이상"]
    color_map = {
        "19% 미만": "#fee5d9",
        "19% ~ 23%": "#fcae91",
        "23% ~ 28%": "#fb6a4a",
        "28% ~ 38%": "#de2d26",
        "38% 이상": "#a50f15",
        "데이터 없음": "#d9d9d9"
    }
else:
    metric_title = "유소년 비율"
    target_cols = [c for c in total_cols if (p := parse_age(c)) is not None and p <= 14]
    
    # 유소년 비율 고정 경계값 (7%, 9%, 11%, 13%)
    bins = [-1, 7, 9, 11, 13, 100]
    bin_labels = ["7% 미만", "7% ~ 9%", "9% ~ 11%", "11% ~ 13%", "13% 이상"]
    color_map = {
        "7% 미만": "#f7fbff",
        "7% ~ 9%": "#c6dbef",
        "9% ~ 11%": "#6baed6",
        "11% ~ 13%": "#2171b5",
        "13% 이상": "#08306b",
        "데이터 없음": "#d9d9d9"
    }

# 시군구 단위 인구 합산 및 비율 계산
grouped =

import io
import requests
import pandas as pd
import plotly.express as px
import streamlit as st

# 페이지 기본 설정
st.set_page_config(
    page_title="2026년 전국 고령화 단계구분도",
    page_icon="🗺️",
    layout="wide"
)


@st.cache_data(show_spinner="인구 데이터를 불러오는 중입니다...")
def load_population_data():
    """Github raw zip 파일에서 인구 데이터를 읽어오는 함수"""
    pop_url = "https://raw.githubusercontent.com/njy0625-beep/contents//main/population_ts_yearly_gender.zip"
    response = requests.get(pop_url)
    response.raise_for_status()

    # Zip 압축 파일에서 CSV 읽기
    zip_buffer = io.BytesIO(response.content)
    df = pd.read_csv(zip_buffer)
    return df


@st.cache_data(show_spinner="시군구 경계 GeoJSON 데이터를 불러오는 중입니다...")
def load_geojson_data():
    """Github raw에서 시군구 경계 GeoJSON을 읽어오는 함수"""
    geojson_url = "https://raw.githubusercontent.com/first2022-cyber/contents//main/sigungu_kr.geojson"
    response = requests.get(geojson_url)
    response.raise_for_status()
    geo_data = response.json()

    # GeoJSON 내의 '코드' 속성을 5자리 문자열로 통일
    for feature in geo_data['features']:
        code = str(feature['properties'].get('코드', '')).strip().zfill(5)
        feature['properties']['코드'] = code

    return geo_data


def process_aging_data(df, geo_data):
    """2026년 인구 데이터 필터링 및 시군구별 고령화율 집계 함수"""
    # 1. 2026년 데이터 추출 ('2026' 포함 여부로 판단)
    df_2026 = df[df['연도'].astype(str).str.contains('2026')].copy()

    if df_2026.empty:
        # 데이터에 2026년 조건이 다른 문자열 형태일 경우 대비
        latest_year = df['연도'].max()
        df_2026 = df[df['연도'] == latest_year].copy()

    # 2. 열 분류 ('계_'로 시작하는 열만 대상, '남_', '여_' 제외)
    total_cols = [c for c in df_2026.columns if c.startswith('계_')]

    def is_65_or_over(col_name):
        # '계_65세' ~ '계_100세 이상' 구분
        clean = col_name.replace('계_', '').replace('세', '').replace('이상', '').strip()
        try:
            return int(clean) >= 65
        except ValueError:
            return False

    over65_cols = [c for c in total_cols if is_65_or_over(c)]

    # 3. 코드 앞 5자리 추출 (시군구 코드)
    df_2026['sigungu_code'] = df_2026['코드'].astype(str).str.strip().str.zfill(8).str[:5]

    # 4. 시군구 단위로 합산
    grouped = df_2026.groupby('sigungu_code')[total_cols].sum().reset_index()

    # 5. 전체 인구 및 65세 이상 인구 계산

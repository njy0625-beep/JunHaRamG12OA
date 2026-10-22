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
    
    # 유소년 비율에 맞춘 7%, 9%, 11%, 13% 고정 경계값
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
grouped = df_year.groupby('sigungu_code')[total_cols].sum().reset_index()
grouped['total_pop'] = grouped[total_cols].sum(axis=1)
grouped['target_pop'] = grouped[target_cols].sum(axis=1)
grouped['ratio'] = (grouped['target_pop'] / grouped['total_pop'].replace(0, np.nan) * 100).fillna(0).round(2)
grouped['구간'] = pd.cut(grouped['ratio'], bins=bins, labels=bin_labels)

# GeoJSON 속성 정보 및 CSV 행정구역명 맵 생성
geo_sido_map = {}
geo_sigungu_map = {}
all_geo_codes = set()

for f in geo_data['features']:
    code = f['properties'].get('코드', '')
    all_geo_codes.add(code)
    geo_sido_map[code] = f['properties'].get('시도', '')
    geo_sigungu_map[code] = f['properties'].get('시군구', '')

csv_names = df_year.groupby('sigungu_code').agg({'시도': 'first', '시군구': 'first'}).reset_index()
csv_sido_map = dict(zip(csv_names['sigungu_code'], csv_names['시도']))
csv_sigungu_map = dict(zip(csv_names['sigungu_code'], csv_names['시군구']))

grouped['시도'] = grouped['sigungu_code'].apply(lambda c: geo_sido_map.get(c) or csv_sido_map.get(c, '기타'))
grouped['시군구'] = grouped['sigungu_code'].apply(lambda c: geo_sigungu_map.get(c) or csv_sigungu_map.get(c, '기타'))
grouped['지역명'] = grouped['시도'] + ' ' + grouped['시군구']

# 3. 시도 선택 드롭다운 (확대용)
sido_options = ["전국"] + sorted([s for s in grouped['시도'].unique() if s and s != '기타'])
selected_sido = st.sidebar.selectbox("🗺️ 시·도 선택 (지역 확대)", sido_options)

# --- 메인화면 레이아웃 ---
st.title(f"🗺️ {selected_year}년 전국 시군구별 {metric_title} 단계구분도")

# 데이터 필터링 (시도 선택 시)
if selected_sido != "전국":
    df_calc = grouped[grouped['시도'] == selected_sido].copy()
else:
    df_calc = grouped.copy()

# --- 지표 카드 3장 나란히 배치 ---
c1, c2, c3 = st.columns(3)

total_target_pop = df_calc['target_pop'].sum()
total_all_pop = df_calc['total_pop'].sum()
overall_ratio = (total_target_pop / total_all_pop * 100) if total_all_pop > 0 else 0

if not df_calc.empty:
    highest_row = df_calc.loc[df_calc['ratio'].idxmax()]
    lowest_row = df_calc.loc[df_calc['ratio'].idxmin()]
    
    high_name, high_val = highest_row['지역명'], f"{highest_row['ratio']:.2f}%"
    low_name, low_val = lowest_row['지역명'], f"{lowest_row['ratio']:.2f}%"
else:
    high_name, high_val = "-", "-"
    low_name, low_val = "-", "-"

sido_prefix = f"[{selected_sido}] " if selected_sido != "전국" else ""
c1.metric(f"{sido_prefix}평균 {metric_title}", f"{overall_ratio:.2f}%")
c2.metric("가장 높은 시군구", high_name, high_val)
c3.metric("가장 낮은 시군구", low_name, low_val)

st.divider()

# --- 지도 시각화 데이터 구성 (경계선 전체 유지 및 회색 처리용) ---
master_df = pd.DataFrame({'sigungu_code': list(all_geo_codes)})
master_df['시도'] = master_df['sigungu_code'].apply(lambda c: geo_sido_map.get(c, '기타'))
master_df['시군구'] = master_df['sigungu_code'].apply(lambda c: geo_sigungu_map.get(c, '기타'))

map_df = pd.merge(
    master_df, 
    df_calc[['sigungu_code', 'target_pop', 'total_pop', 'ratio', '구간', '지역명']], 
    on='sigungu_code', 
    how='left'
)

if selected_sido != "전국":
    map_df = map_df[map_df['시도'] == selected_sido].copy()

map_df['지역명'] = map_df['지역명'].fillna(map_df['시도'] + ' ' + map_df['시군구'])
map_df['구간_str'] = map_df['구간'].astype(str).fillna("데이터 없음")
map_df.loc[map_df['ratio'].isna(), '구간_str'] = "데이터 없음"

# --- Plotly Choropleth 지도 생성 ---
fig = px.choropleth(
    map_df,
    geojson=geo_data,
    locations='sigungu_code',
    featureidkey='properties.코드',
    color='구간_str',
    category_orders={'구간_str': bin_labels + ["데이터 없음"]},
    color_discrete_map=color_map,
    labels={
        'sigungu_code': '지역코드',
        'ratio': f'{metric_title}(%)',
        '구간_str': '구간',
        'total_pop': '전체인구',
        'target_pop': '해당연령인구'
    },
    hover_name='지역명',
    hover_data={
        'sigungu_code': True,
        'ratio': ':.2f',
        'total_pop': ':,',
        'target_pop': ':,'
    }
)

# 배경 타일 제거 및 영역 자동 맞춤
fig.update_geos(
    fitbounds="locations",
    visible=False,
    showcountries=False,
    showcoastlines=False,
    showland=False,
    showframe=False
)

fig.update_layout(
    margin={"r": 0, "t": 10, "l": 0, "b": 0},
    height=650,
    legend_title_text=f"{metric_title} 구간"
)

st.plotly_chart(fig, use_container_width=True)

# --- 미매칭/회색 표시 지역 안내 문구 ---
has_unmatched = map_df['ratio'].isna().any()
if has_unmatched:
    unmatched_list = map_df[map_df['ratio'].isna()]['지역명'].unique().tolist()
    st.info(
        f"ℹ️ **안내**: 행정구역 개편 및 과거 코드 차이로 인해 **{selected_year}년** 데이터가 현행 경계 파일과 일치하지 않는 지역({len(unmatched_list)}곳)은 회색으로 표기됩니다.\n\n"
        f"**회색 표기 지역 예시**: {', '.join(unmatched_list[:6])}{' 등' if len(unmatched_list) > 6 else ''}"
    )

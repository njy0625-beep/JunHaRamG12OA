import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# -----------------------------------------------------------------------------
# 1. 페이지 기본 설정 (제목, 아이콘, 레이아웃)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="동네별 인구 피라미드",
    page_icon="🏡",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 2. 데이터 불러오기 함수 (캐싱 적용으로 속도 향상)
# -----------------------------------------------------------------------------
@st.cache_data
def load_data():
    # GitHub 저장소의 압축 CSV 파일 주소
    url = "https://raw.githubusercontent.com/njy0625-beep/JunHaRamG12OA/main/population_ts_yearly_gender.zip"
    
    # 판다스로 ZIP 압축 파일 직접 읽기
    df = pd.read_csv(url)
    
    # 전체 데이터 중 가장 최신 연도만 추출
    latest_year = int(df['연도'].max())
    df_latest = df[df['연도'] == latest_year].copy()
    
    return df_latest, latest_year

# -----------------------------------------------------------------------------
# 3. 데이터 로드 및 타이틀 표시
# -----------------------------------------------------------------------------
df, latest_year = load_data()

st.title("🏡 우리 동네 인구 피라미드")
st.markdown(f"**기준 연도: {latest_year}년** | 우리 동네의 연령별 인구 구조를 따뜻하고 한눈에 쉽게 확인해 보세요.")
st.write("---")

# -----------------------------------------------------------------------------
# 4. 화면 위쪽 드롭다운 메뉴 (시도 → 시군구 → 동 3단계 연동)
# -----------------------------------------------------------------------------
col1, col2, col3 = st.columns(3)

with col1:
    # 1단계: 시/도 목록 추출 및 선택
    sido_list = sorted(df['시도'].dropna().unique())
    selected_sido = st.selectbox("📍 시·도 선택", sido_list)

with col2:
    # 2단계: 선택한 시/도 내의 시/군/구 목록 추출 및 선택
    sigungu_df = df[df['시도'] == selected_sido]
    sigungu_list = sorted(sigungu_df['시군구'].dropna().unique())
    selected_sigungu = st.selectbox("🏙️ 시·군·구 선택", sigungu_list)

with col3:
    # 3단계: 선택한 시/군/구 내의 읍/면/동 목록 추출 및 선택
    dong_df = sigungu_df[sigungu_df['시군구'] == selected_sigungu]
    dong_list = sorted(dong_df['동'].dropna().unique())
    selected_dong = st.selectbox("🏘️ 읍·면·동 선택", dong_list)

# 선택된 동네의 1개 행(Row) 데이터 추출
selected_row = dong_df[dong_df['동'] == selected_dong].iloc[0]

# -----------------------------------------------------------------------------
# 5. 나이 라벨 순서 구성 및 데이터 정형화
# -----------------------------------------------------------------------------
# 0세부터 99세, 그리고 '100세 이상' 라벨 목록 생성
expected_ages = [f"{i}세" for i in range(100)] + ["100세 이상", "100세이상"]

# 실제 데이터프레임에 존재하는 나이 열만 0세부터 순서대로 수집
age_labels = []
for age in expected_ages:
    if f"남_{age}" in df.columns and f"여_{age}" in df.columns:
        age_labels.append(age)

# 남성/여성 인구수 리스트 생성
# 남성은 피라미드 왼쪽에 배치하기 위해 음수(-) 값으로 변환
male_pop = [int(selected_row[f"남_{age}"]) for age in age_labels]
female_pop = [int(selected_row[f"여_{age}"]) for age in age_labels]
male_pop_neg = [-val for val in male_pop]

# 요약 정보 계산 (총 인구, 남성/여성 인구)
total_m = sum(male_pop)
total_f = sum(female_pop)
total_pop = total_m + total_f

# -----------------------------------------------------------------------------
# 6. 주요 요약 지표 (카드 형태)
# -----------------------------------------------------------------------------
m_col1, m_col2, m_col3 = st.columns(3)
m_col1.metric("총 인구수", f"{total_pop:,} 명")
m_col2.metric("남성 인구", f"{total_m:,} 명")
m_col3.metric("여성 인구", f"{total_f:,} 명")

st.write("")

# -----------------------------------------------------------------------------
# 7. Plotly 인구 피라미드 가로 막대그래프 생성
# -----------------------------------------------------------------------------
fig = go.Figure()

# 남성 막대 그래프 (왼쪽 - 음수 값)
fig.add_trace(go.Bar(
    y=age_labels,
    x=male_pop_neg,
    name='남성',
    orientation='h',
    hoverinfo='text',
    hovertext=[f"<b>{age} 남성</b>: {val:,}명" for age, val in zip(age_labels, male_pop)],
    marker=dict(color='#5B9BD5')  # 따뜻하고 부드러운 블루
))

# 여성 막대 그래프 (오른쪽 - 양수 값)
fig.add_trace(go.Bar(
    y=age_labels,
    x=female_pop,
    name='여성',
    orientation='h',
    hoverinfo='text',
    hovertext=[f"<b>{age} 여성</b>: {val:,}명" for age, val in zip(age_labels, female_pop)],
    marker=dict(color='#ED7D31')  # 따뜻한 핑크/코랄
))

# X축 눈금에 음수가 아닌 절댓값이 표시되도록 설정
max_val = max(max(male_pop), max(female_pop)) if total_pop > 0 else 100
step = max(1, int(max_val / 4))
tick_vals = list(range(-max_val, max_val + step, step))
tick_text = [f"{abs(v):,}" for v in tick_vals]

# 레이아웃 및 세로축 고정 설정
fig.update_layout(
    title=dict(
        text=f"<b>{selected_sido} {selected_sigungu} {selected_dong}</b> 인구 피라미드",
        font=dict(size=20),
        x=0.5
    ),
    barmode='relative',
    bargap=0.1,
    xaxis=dict(
        title="인구수 (명)",
        tickvals=tick_vals,
        ticktext=tick_text,
        gridcolor='#F0F0F0',
        zeroline=True,
        zerolinecolor='#888888',
        zerolinewidth=1
    ),
    # 📌 세로축 순서 고정: 0세가 맨 아래, 100세 이상이 맨 위로 오도록 배열 순서 고정
    yaxis=dict(
        title="나이",
        type='category',
        categoryorder='array',
        categoryarray=age_labels,  # 0세 -> 100세 이상 순서 배열 입력
        showgrid=True,
        gridcolor='#F0F0F0'
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    ),
    height=800,
    template='plotly_white',
    margin=dict(l=60, r=60, t=80, b=60)
)

# 스트림릿 화면에 차트 출력
st.plotly_chart(fig, use_container_width=True)

# -----------------------------------------------------------------------------
# 8. 원본 데이터 확인용 접기/펼치기 영역
# -----------------------------------------------------------------------------
with st.expander("📋 선택한 동네 상세 데이터 보기"):
    st.dataframe(pd.DataFrame({
        '나이': age_labels,
        '남성 인구(명)': male_pop,
        '여성 인구(명)': female_pop
    }))

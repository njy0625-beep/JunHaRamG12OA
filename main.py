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

# 데이터 로드
df, latest_year = load_data()

# -----------------------------------------------------------------------------
# 3. 타이틀 및 안내 문구
# -----------------------------------------------------------------------------
st.title("🏡 우리 동네 인구 피라미드")
st.markdown(f"**기준 연도: {latest_year}년** | 우리 동네의 연령별 인구 구조를 확인해 보세요.")
st.write("---")

# -----------------------------------------------------------------------------
# 4. 화면 위쪽 드롭다운 메뉴 (시도 → 시군구 → 동 3단계 연동)
# -----------------------------------------------------------------------------
col1, col2, col3 = st.columns(3)

with col1:
    sido_list = sorted(df['시도'].dropna().unique())
    selected_sido = st.selectbox("📍 시·도 선택", sido_list)

with col2:
    sigungu_df = df[df['시도'] == selected_sido]
    sigungu_list = sorted(sigungu_df['시군구'].dropna().unique())
    selected_sigungu = st.selectbox("🏙️ 시·군·구 선택", sigungu_list)

with col3:
    dong_df = sigungu_df[sigungu_df['시군구'] == selected_sigungu]
    dong_list = sorted(dong_df['동'].dropna().unique())
    selected_dong = st.selectbox("🏘️ 읍·면·동 선택", dong_list)

# 선택된 동네 데이터 1행 추출
selected_row = dong_df[dong_df['동'] == selected_dong].iloc[0]

# -----------------------------------------------------------------------------
# 5. 나이 라벨 추출 및 통계 지표 계산
# -----------------------------------------------------------------------------
expected_ages = [f"{i}세" for i in range(100)] + ["100세 이상", "100세이상"]

age_labels = []
numeric_ages = []

for age in expected_ages:
    if f"남_{age}" in df.columns and f"여_{age}" in df.columns:
        age_labels.append(age)
        if age in ["100세 이상", "100세이상"]:
            numeric_ages.append(100)
        else:
            numeric_ages.append(int(age.replace("세", "")))

# 남성/여성 인구 데이터 (남성은 피라미드 왼쪽 배치를 위해 음수 변환)
male_pop = [int(selected_row[f"남_{age}"]) for age in age_labels]
female_pop = [int(selected_row[f"여_{age}"]) for age in age_labels]
male_pop_neg = [-val for val in male_pop]

# 통계 지표 계산
total_m = sum(male_pop)
total_f = sum(female_pop)
total_pop = total_m + total_f

if total_pop > 0:
    # 평균연령
    total_age_sum = sum(age_num * (m + f) for age_num, m, f in zip(numeric_ages, male_pop, female_pop))
    avg_age = total_age_sum / total_pop

    # 고령화율 (65세 이상 비율)
    elderly_pop = sum(m + f for age_num, m, f in zip(numeric_ages, male_pop, female_pop) if age_num >= 65)
    aging_rate = (elderly_pop / total_pop) * 100

    # 유소년 비율 (0~14세 비율)
    youth_pop = sum(m + f for age_num, m, f in zip(numeric_ages, male_pop, female_pop) if age_num <= 14)
    youth_rate = (youth_pop / total_pop) * 100
else:
    avg_age = 0.0
    aging_rate = 0.0
    youth_rate = 0.0

# -----------------------------------------------------------------------------
# 6. 상단 요약 지표 카드 3개 (총인구, 평균연령, 고령화율)
# -----------------------------------------------------------------------------
m_col1, m_col2, m_col3 = st.columns(3)

with m_col1:
    st.metric(label="👥 총인구", value=f"{total_pop:,} 명")

with m_col2:
    st.metric(label="🎂 평균연령", value=f"{avg_age:.1f} 세")

with m_col3:
    # 고령화율이 20% 이상인 초고령사회 지역이면 ⚠️/🚨 주의 표시 추가
    if aging_rate >= 20.0:
        st.metric(
            label="👵 고령화율 (65세 이상) ⚠️",
            value=f"{aging_rate:.1f} %",
            delta="초고령사회 (20% 초과) 🚨",
            delta_color="inverse"
        )
    else:
        st.metric(
            label="👵 고령화율 (65세 이상)",
            value=f"{aging_rate:.1f} %"
        )

st.write("")

# -----------------------------------------------------------------------------
# 7. Plotly 인구 피라미드 그래프 생성 (괄호 오류 완벽 방지 구조)
# -----------------------------------------------------------------------------
fig = go.Figure()

# 남성 막대 (왼쪽)
fig.add_trace(go.Bar(
    y=age_labels,
    x=male_pop_neg,
    name='남성',
    orientation='h',
    hoverinfo='text',
    hovertext=[f"<b>{age} 남성</b>: {val:,}명" for age, val in zip(age_labels, male_pop)],
    marker_color='#5B9BD5'
))

# 여성 막대 (오른쪽)
fig.add_trace(go.Bar(
    y=age_labels,
    x=female_pop,
    name='여성',
    orientation='h',
    hoverinfo='text',
    hovertext=[f"<b>{age} 여성</b>: {val:,}명" for age, val in zip(age_labels, female_pop)],
    marker_color='#ED7D31'
))

# X축 눈금 범위 계산
max_val = max(max(male_pop), max(female_pop)) if total_pop > 0 else 100
step = max(1, int(max_val / 4))
tick_vals = list(range(-max_val, max_val + step, step))
tick_text = [f"{abs(v):,}" for v in tick_vals]

# [그래프 레이아웃 설정] - 단일 속성 직접 지정으로 괄호 오류 원천 차단
fig.layout.title.text = f"<b>{selected_sido} {selected_sigungu} {selected_dong}</b> 인구 피라미드"
fig.layout.title.x = 0.5
fig.layout.barmode = 'relative'
fig.layout.bargap = 0.1
fig.layout.height = 800
fig.layout.template = 'plotly_white'

# 범례 위치 설정
fig.layout.legend.orientation = "h"
fig.layout.legend.yanchor = "bottom"
fig.layout.legend.y = 1.02
fig.layout.legend.xanchor = "right"
fig.layout.legend.x = 1

# X축 설정 (절댓값 표시)
fig.layout.xaxis.title.text = "인구수 (명)"
fig.layout.xaxis.tickvals = tick_vals
fig.layout.xaxis.ticktext = tick_text
fig.layout.xaxis.gridcolor = '#F0F0F0'
fig.layout.xaxis.zeroline = True
fig.layout.xaxis.zerolinecolor = '#888888'

# Y축 설정 (📌 세로축 순서 고정: 0세가 맨 아래, 100세 이상이 맨 위)
fig.layout.yaxis.title.text = "나이"
fig.layout.yaxis.type = 'category'
fig.layout.yaxis.categoryorder = 'array'
fig.layout.yaxis.categoryarray = age_labels
fig.layout.yaxis.showgrid = True
fig.layout.yaxis.gridcolor = '#F0F0F0'

# 차트 화면 출력
st.plotly_chart(fig, use_container_width=True)

# -----------------------------------------------------------------------------
# 8. 한 줄 자동 분석 문구
# -----------------------------------------------------------------------------
st.subheader("💡 우리 동네 인구 특징 한눈에 보기")

if youth_rate > aging_rate:
    summary_text = (
        f"**{selected_dong}**은(는) **아이가 상대적으로 많은 동네**입니다! "
        f"(유소년(0~14세) 비율 **{youth_rate:.1f}%** > 어르신(65세 이상) 비율 **{aging_rate:.1f}%**)"
    )
    st.info(summary_text, icon="👶")
elif aging_rate > youth_rate:
    summary_text = (
        f"**{selected_dong}**은(는) **어르신이 상대적으로 많은 동네**입니다. "
        f"(어르신(65세 이상) 비율 **{aging_rate:.1f}%** > 유소년(0~14세) 비율 **{youth_rate:.1f}%**)"
    )
    if aging_rate >= 20.0:
        st.warning(summary_text, icon="👵")
    else:
        st.info(summary_text, icon="👵")
else:
    summary_text = (
        f"**{selected_dong}**은(는) **아이와 어르신의 비율이 비슷한 동네**입니다. "
        f"(유소년 비율 **{youth_rate:.1f}%**, 어르신 비율 **{aging_rate:.1f}%**)"
    )
    st.info(summary_text, icon="🏡")

# -----------------------------------------------------------------------------
# 9. 원본 데이터 상세 표
# -----------------------------------------------------------------------------
with st.expander("📋 선택한 동네 상세 데이터 보기"):
    st.dataframe(pd.DataFrame({
        '나이': age_labels,
        '남성 인구(명)': male_pop,
        '여성 인구(명)': female_pop
    }))

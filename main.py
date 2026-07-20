import streamlit as st


st.set_page_config(
    page_title="대한민국 시가총액 TOP 10",
    page_icon="🇰🇷",
    layout="wide",
)

st.title("🇰🇷 대한민국 주식 시가총액 TOP 10")
st.write(
    "코스피와 코스닥 시가총액 상위 10개 종목을 "
    "최근 거래일 기준으로 분석하는 대시보드입니다."
)

st.info(
    "왼쪽 사이드바에서 분석할 시장을 선택하세요.\n\n"
    "1. 코스피 시가총액 TOP 10\n"
    "2. 코스닥 시가총액 TOP 10"
)

col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 코스피 TOP 10")
    st.write(
        "코스피 시장에서 시가총액이 가장 큰 10개 종목의 "
        "현재가, 등락률, 거래량, PER, PBR 등을 분석합니다."
    )

with col2:
    st.subheader("📊 코스닥 TOP 10")
    st.write(
        "코스닥 시장에서 시가총액이 가장 큰 10개 종목의 "
        "현재가, 등락률, 거래량, PER, PBR 등을 분석합니다."
    )

st.divider()

st.warning(
    "표시되는 정보는 학습 및 정보 제공 목적이며, "
    "투자 권유나 매매 추천이 아닙니다."
)

import streamlit as st

from market_utils import render_market_page


st.set_page_config(
    page_title="코스닥 시가총액 TOP 10",
    page_icon="📊",
    layout="wide",
)

render_market_page(
    market_code="KOSDAQ",
    market_name="코스닥",
    page_icon="📊",
    description=(
        "코스닥 시장 시가총액 상위 10개 종목의 "
        "가격, 등락률, 거래량 및 투자지표를 분석합니다."
    ),
)

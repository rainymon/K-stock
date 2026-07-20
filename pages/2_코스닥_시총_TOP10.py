import streamlit as st

from market_utils import render_market_page


st.set_page_config(
    page_title="코스닥 시가총액 TOP 10",
    page_icon="📊",
    layout="wide",
)

render_market_page(
    market_code=1,
    market_name="코스닥",
    page_icon="📊",
    description=(
        "코스닥 시가총액 상위 10개 종목의 "
        "가격과 등락 현황을 분석합니다."
    ),
)

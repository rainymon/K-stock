from datetime import datetime, timedelta
import time

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from pykrx import stock


@st.cache_data(ttl=3600, show_spinner=False)
def find_latest_trading_date(market):
    """
    오늘부터 과거 방향으로 조회하면서
    데이터가 존재하는 가장 최근 거래일을 찾습니다.
    """

    today = datetime.now()

    for days_ago in range(15):
        target_date = today - timedelta(days=days_ago)
        date_string = target_date.strftime("%Y%m%d")

        try:
            market_cap = stock.get_market_cap_by_ticker(
                date_string,
                market=market,
            )

            if market_cap is not None and not market_cap.empty:
                return date_string

        except Exception:
            continue

    raise RuntimeError(
        "최근 거래일을 찾지 못했습니다. 잠시 후 다시 시도해 주세요."
    )


@st.cache_data(ttl=3600, show_spinner=False)
def get_market_top10(market):
    """
    최근 거래일의 시가총액 상위 10개 종목을 조회합니다.
    """

    latest_date = find_latest_trading_date(market)

    market_cap = stock.get_market_cap_by_ticker(
        latest_date,
        market=market,
    )

    ohlcv = stock.get_market_ohlcv_by_ticker(
        latest_date,
        market=market,
    )

    try:
        fundamentals = stock.get_market_fundamental_by_ticker(
            latest_date,
            market=market,
        )
    except Exception:
        fundamentals = pd.DataFrame()

    if market_cap is None or market_cap.empty:
        raise RuntimeError("시가총액 데이터를 불러오지 못했습니다.")

    market_cap = market_cap.copy()
    market_cap.index = market_cap.index.astype(str)

    ohlcv = ohlcv.copy()
    ohlcv.index = ohlcv.index.astype(str)

    if not fundamentals.empty:
        fundamentals = fundamentals.copy()
        fundamentals.index = fundamentals.index.astype(str)

    # 시가총액이 큰 순서대로 10개 종목 선택
    top10 = market_cap.sort_values(
        by="시가총액",
        ascending=False,
    ).head(10)

    result = pd.DataFrame(index=top10.index)

    result["종목명"] = [
        get_ticker_name(ticker)
        for ticker in result.index
    ]

    result["현재가"] = get_column(
        ohlcv,
        "종가",
        result.index,
    )

    result["전일대비"] = get_column(
        ohlcv,
        "등락률",
        result.index,
    )

    result["시가"] = get_column(
        ohlcv,
        "시가",
        result.index,
    )

    result["고가"] = get_column(
        ohlcv,
        "고가",
        result.index,
    )

    result["저가"] = get_column(
        ohlcv,
        "저가",
        result.index,
    )

    result["거래량"] = get_column(
        ohlcv,
        "거래량",
        result.index,
    )

    result["거래대금"] = get_column(
        ohlcv,
        "거래대금",
        result.index,
    )

    result["시가총액"] = get_column(
        top10,
        "시가총액",
        result.index,
    )

    result["상장주식수"] = get_column(
        top10,
        "상장주식수",
        result.index,
    )

    if not fundamentals.empty:
        result["PER"] = get_column(
            fundamentals,
            "PER",
            result.index,
        )

        result["PBR"] = get_column(
            fundamentals,
            "PBR",
            result.index,
        )

        result["EPS"] = get_column(
            fundamentals,
            "EPS",
            result.index,
        )

        result["BPS"] = get_column(
            fundamentals,
            "BPS",
            result.index,
        )

        result["배당수익률"] = get_column(
            fundamentals,
            "DIV",
            result.index,
        )

    else:
        result["PER"] = None
        result["PBR"] = None
        result["EPS"] = None
        result["BPS"] = None
        result["배당수익률"] = None

    result.index.name = "종목코드"
    result = result.reset_index()

    result["시총순위"] = range(1, len(result) + 1)

    column_order = [
        "시총순위",
        "종목코드",
        "종목명",
        "현재가",
        "전일대비",
        "시가",
        "고가",
        "저가",
        "거래량",
        "거래대금",
        "시가총액",
        "상장주식수",
        "PER",
        "PBR",
        "EPS",
        "BPS",
        "배당수익률",
    ]

    result = result[column_order]

    return latest_date, result


@st.cache_data(ttl=3600, show_spinner=False)
def get_ticker_name(ticker):
    """
    종목코드를 종목명으로 변환합니다.
    """

    try:
        return stock.get_market_ticker_name(ticker)
    except Exception:
        return ticker


def get_column(dataframe, column, index):
    """
    데이터프레임에 특정 열이 없거나 일부 종목이 없는 경우에도
    오류 없이 값을 반환합니다.
    """

    if dataframe is None or dataframe.empty:
        return pd.Series(index=index, dtype=float)

    if column not in dataframe.columns:
        return pd.Series(index=index, dtype=float)

    return dataframe[column].reindex(index)


def format_date(date_string):
    """
    YYYYMMDD 형식을 YYYY-MM-DD 형식으로 변환합니다.
    """

    try:
        return datetime.strptime(
            date_string,
            "%Y%m%d",
        ).strftime("%Y-%m-%d")
    except Exception:
        return date_string


def format_won(value):
    if value is None or pd.isna(value):
        return "-"

    return f"₩{float(value):,.0f}"


def format_percent(value):
    if value is None or pd.isna(value):
        return "-"

    return f"{float(value):+.2f}%"


def format_number(value):
    if value is None or pd.isna(value):
        return "-"

    value = float(value)

    if abs(value) >= 1_000_000_000_000:
        return f"{value / 1_000_000_000_000:.2f}조"

    if abs(value) >= 100_000_000:
        return f"{value / 100_000_000:.2f}억"

    if abs(value) >= 10_000:
        return f"{value / 10_000:.2f}만"

    return f"{value:,.0f}"


def create_change_chart(data, market_name):
    """
    종목별 상승·하락률을 막대그래프로 표시합니다.

    상승: 빨간색
    하락: 파란색
    보합: 회색
    """

    chart_data = data.copy()

    chart_data["전일대비"] = pd.to_numeric(
        chart_data["전일대비"],
        errors="coerce",
    ).fillna(0)

    chart_data = chart_data.sort_values(
        by="전일대비",
        ascending=True,
    )

    bar_colors = []

    for value in chart_data["전일대비"]:
        if value > 0:
            bar_colors.append("#ef4444")
        elif value < 0:
            bar_colors.append("#2563eb")
        else:
            bar_colors.append("#9ca3af")

    text_values = chart_data["전일대비"].map(
        lambda value: f"{value:+.2f}%"
    )

    figure = go.Figure()

    figure.add_trace(
        go.Bar(
            x=chart_data["전일대비"],
            y=chart_data["종목명"],
            orientation="h",
            marker_color=bar_colors,
            text=text_values,
            textposition="outside",
            customdata=chart_data[
                [
                    "시총순위",
                    "종목코드",
                    "현재가",
                    "시가총액",
                ]
            ],
            hovertemplate=(
                "<b>%{y}</b><br>"
                "시총 순위: %{customdata[0]}위<br>"
                "종목코드: %{customdata[1]}<br>"
                "현재가: %{customdata[2]:,.0f}원<br>"
                "등락률: %{x:+.2f}%<br>"
                "시가총액: %{customdata[3]:,.0f}원"
                "<extra></extra>"
            ),
        )
    )

    figure.add_vline(
        x=0,
        line_width=1,
        line_dash="dash",
        line_color="gray",
    )

    figure.update_layout(
        title=f"{market_name} 시가총액 TOP 10 상승·하락",
        height=570,
        xaxis_title="전일 대비 등락률",
        yaxis_title="",
        showlegend=False,
        margin=dict(
            l=20,
            r=80,
            t=70,
            b=30,
        ),
    )

    figure.update_xaxes(
        ticksuffix="%",
        zeroline=True,
    )

    return figure


def create_display_table(data):
    """
    사용자 화면에 표시할 표를 만듭니다.
    """

    display = data.copy()

    money_columns = [
        "현재가",
        "시가",
        "고가",
        "저가",
        "EPS",
        "BPS",
    ]

    for column in money_columns:
        display[column] = display[column].map(format_won)

    display["전일대비"] = display["전일대비"].map(
        format_percent
    )

    display["시가총액"] = display["시가총액"].map(
        format_number
    )

    display["거래대금"] = display["거래대금"].map(
        format_number
    )

    display["거래량"] = display["거래량"].map(
        format_number
    )

    display["상장주식수"] = display["상장주식수"].map(
        format_number
    )

    for column in ["PER", "PBR"]:
        display[column] = display[column].map(
            lambda value: (
                f"{float(value):,.2f}"
                if value is not None and not pd.isna(value)
                else "-"
            )
        )

    display["배당수익률"] = display["배당수익률"].map(
        lambda value: (
            f"{float(value):.2f}%"
            if value is not None and not pd.isna(value)
            else "-"
        )
    )

    return display


def display_summary_metrics(data):
    """
    상승·하락 종목 수와 시장 요약을 표시합니다.
    """

    change = pd.to_numeric(
        data["전일대비"],
        errors="coerce",
    ).fillna(0)

    rising_count = int((change > 0).sum())
    falling_count = int((change < 0).sum())
    unchanged_count = int((change == 0).sum())

    best_index = change.idxmax()
    worst_index = change.idxmin()

    best_stock = data.loc[best_index]
    worst_stock = data.loc[worst_index]

    average_change = change.mean()
    total_market_cap = pd.to_numeric(
        data["시가총액"],
        errors="coerce",
    ).sum()

    columns = st.columns(6)

    columns[0].metric(
        "상승 종목",
        f"{rising_count}개",
    )

    columns[1].metric(
        "하락 종목",
        f"{falling_count}개",
    )

    columns[2].metric(
        "보합 종목",
        f"{unchanged_count}개",
    )

    columns[3].metric(
        "평균 등락률",
        format_percent(average_change),
    )

    columns[4].metric(
        "상승률 1위",
        best_stock["종목명"],
        format_percent(best_stock["전일대비"]),
    )

    columns[5].metric(
        "하락률 1위",
        worst_stock["종목명"],
        format_percent(worst_stock["전일대비"]),
    )

    st.caption(
        f"TOP 10 합산 시가총액: {format_number(total_market_cap)}원"
    )


def render_market_page(
    market_code,
    market_name,
    page_icon,
    description,
):
    """
    코스피와 코스닥 페이지의 공통 화면을 렌더링합니다.
    """

    st.title(f"{page_icon} {market_name} 시가총액 TOP 10")
    st.caption(description)

    left, right = st.columns([3, 1])

    with left:
        st.info(
            "최근 거래일을 기준으로 시가총액 상위 10개 종목을 "
            "자동으로 선정합니다."
        )

    with right:
        refresh_button = st.button(
            "데이터 새로고침",
            type="primary",
            use_container_width=True,
        )

    if refresh_button:
        st.cache_data.clear()

    try:
        with st.spinner(
            f"{market_name} 시가총액 데이터를 불러오는 중입니다..."
        ):
            latest_date, top10_data = get_market_top10(market_code)

    except Exception as error:
        st.error(
            "데이터를 불러오지 못했습니다. "
            "잠시 후 다시 실행해 주세요."
        )

        with st.expander("오류 내용 확인"):
            st.code(str(error))

        st.stop()

    st.subheader(f"데이터 기준일: {format_date(latest_date)}")

    display_summary_metrics(top10_data)

    st.divider()

    # 페이지당 상승·하락 그래픽 하나
    figure = create_change_chart(
        data=top10_data,
        market_name=market_name,
    )

    st.plotly_chart(
        figure,
        use_container_width=True,
        config={
            "displaylogo": False,
            "scrollZoom": False,
        },
    )

    st.caption(
        "그래프에서 빨간색은 상승, 파란색은 하락, "
        "회색은 보합을 의미합니다."
    )

    st.divider()

    st.subheader("📋 시가총액 상위 10종목 상세 분석")

    display_table = create_display_table(top10_data)

    st.dataframe(
        display_table,
        use_container_width=True,
        hide_index=True,
    )

    csv_data = top10_data.to_csv(
        index=False,
        encoding="utf-8-sig",
    ).encode("utf-8-sig")

    st.download_button(
        label=f"{market_name} TOP 10 CSV 다운로드",
        data=csv_data,
        file_name=(
            f"{market_code.lower()}_market_cap_top10_"
            f"{latest_date}.csv"
        ),
        mime="text/csv",
        use_container_width=True,
    )

    st.divider()

    with st.expander("분석 지표 설명"):
        st.write(
            """
            **시가총액**
            
            현재 주가에 상장주식 수를 곱한 값입니다.

            **전일대비**

            직전 거래일 종가와 비교한 등락률입니다.

            **PER**

            주가를 주당순이익으로 나눈 값입니다. 기업의 이익 대비
            주가 수준을 확인할 때 사용합니다.

            **PBR**

            주가를 주당순자산으로 나눈 값입니다. 기업의 순자산 대비
            주가 수준을 확인할 때 사용합니다.

            **EPS**

            기업의 순이익을 발행주식 수로 나눈 주당순이익입니다.

            **BPS**

            기업의 순자산을 발행주식 수로 나눈 주당순자산입니다.
            """
        )

    st.warning(
        "본 대시보드는 교육 및 정보 제공 목적입니다. "
        "데이터는 실제 거래소 데이터와 차이가 있거나 지연될 수 있으며, "
        "투자 판단은 이용자 본인의 책임입니다."
    )

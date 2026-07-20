from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from bs4 import BeautifulSoup


# ---------------------------------------------------------
# 네이버 금융 설정
# ---------------------------------------------------------
NAVER_MARKET_URL = (
    "https://finance.naver.com/sise/"
    "sise_market_sum.naver?sosok={market_code}&page=1"
)

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0.0.0 Safari/537.36"
    ),
    "Referer": "https://finance.naver.com/",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
}


# ---------------------------------------------------------
# 숫자 변환 함수
# ---------------------------------------------------------
def parse_number(value):
    """
    쉼표와 퍼센트 기호가 포함된 문자열을 숫자로 변환합니다.
    """

    if value is None:
        return 0.0

    text = str(value).strip()

    text = text.replace(",", "")
    text = text.replace("%", "")
    text = text.replace("+", "")

    if text in ["", "-", "N/A", "nan"]:
        return 0.0

    try:
        return float(text)
    except ValueError:
        return 0.0


def get_text(element):
    """
    BeautifulSoup 요소의 텍스트를 안전하게 가져옵니다.
    """

    if element is None:
        return ""

    return element.get_text(strip=True)


# ---------------------------------------------------------
# 시가총액 TOP 10 조회
# ---------------------------------------------------------
@st.cache_data(ttl=1800, show_spinner=False)
def get_market_top10(market_code):
    """
    네이버 금융에서 코스피 또는 코스닥 시가총액
    상위 10개 종목을 가져옵니다.

    market_code
    0: 코스피
    1: 코스닥
    """

    url = NAVER_MARKET_URL.format(market_code=market_code)

    response = requests.get(
        url,
        headers=REQUEST_HEADERS,
        timeout=20,
    )

    response.raise_for_status()

    # 네이버 금융 국내 주식 페이지 인코딩
    response.encoding = "euc-kr"

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    table = soup.select_one("table.type_2")

    if table is None:
        raise RuntimeError(
            "시가총액 순위 표를 찾지 못했습니다."
        )

    rows = table.select("tr")

    result_rows = []

    for row in rows:
        cells = row.select("td")

        # 실제 종목 행은 일반적으로 13개 열을 가지고 있습니다.
        if len(cells) < 10:
            continue

        name_element = row.select_one("a.tltle")

        if name_element is None:
            continue

        rank_text = get_text(cells[0])
        stock_name = get_text(name_element)

        href = name_element.get("href", "")
        stock_code = ""

        if "code=" in href:
            stock_code = href.split("code=")[-1].split("&")[0]

        current_price = parse_number(
            get_text(cells[2])
        )

        change_text = get_text(cells[3])
        change_amount = parse_number(change_text)

        change_rate_text = get_text(cells[4])
        change_rate = parse_number(change_rate_text)

        # 네이버 금융은 상승·하락 상태를 CSS 클래스로 제공합니다.
        change_cell_classes = cells[3].get(
            "class",
            [],
        )

        class_text = " ".join(change_cell_classes)

        if (
            "nv01" in class_text
            or "tah p11 nv01" in class_text
        ):
            change_amount = -abs(change_amount)
            change_rate = -abs(change_rate)

        elif (
            "red01" in class_text
            or "tah p11 red01" in class_text
        ):
            change_amount = abs(change_amount)
            change_rate = abs(change_rate)

        else:
            # CSS를 찾지 못한 경우 표시 문자열과 이미지로 판단
            blind_text = get_text(cells[3])

            down_image = cells[3].select_one(
                "img[alt='하락']"
            )

            up_image = cells[3].select_one(
                "img[alt='상승']"
            )

            if down_image is not None or "하락" in blind_text:
                change_amount = -abs(change_amount)
                change_rate = -abs(change_rate)

            elif up_image is not None or "상승" in blind_text:
                change_amount = abs(change_amount)
                change_rate = abs(change_rate)

        face_value = parse_number(
            get_text(cells[5])
        )

        market_cap = parse_number(
            get_text(cells[6])
        )

        listed_shares = parse_number(
            get_text(cells[7])
        )

        foreign_ratio = parse_number(
            get_text(cells[8])
        )

        volume = parse_number(
            get_text(cells[9])
        )

        per = (
            parse_number(get_text(cells[10]))
            if len(cells) > 10
            else 0
        )

        roe = (
            parse_number(get_text(cells[11]))
            if len(cells) > 11
            else 0
        )

        result_rows.append(
            {
                "시총순위": int(parse_number(rank_text)),
                "종목코드": stock_code,
                "종목명": stock_name,
                "현재가": current_price,
                "전일대비금액": change_amount,
                "등락률": change_rate,
                "액면가": face_value,
                "시가총액": market_cap,
                "상장주식수": listed_shares,
                "외국인비율": foreign_ratio,
                "거래량": volume,
                "PER": per,
                "ROE": roe,
            }
        )

        if len(result_rows) >= 10:
            break

    if len(result_rows) == 0:
        raise RuntimeError(
            "종목 데이터를 가져오지 못했습니다. "
            "네이버 금융 페이지 구조가 변경되었을 수 있습니다."
        )

    result = pd.DataFrame(result_rows)

    result = result.sort_values(
        "시총순위",
        ascending=True,
    ).reset_index(drop=True)

    return datetime.now().strftime("%Y-%m-%d"), result


# ---------------------------------------------------------
# 표시 형식
# ---------------------------------------------------------
def format_won(value):
    if value is None or pd.isna(value):
        return "-"

    return f"{float(value):,.0f}원"


def format_percent(value):
    if value is None or pd.isna(value):
        return "-"

    return f"{float(value):+.2f}%"


def format_market_cap(value):
    """
    네이버 금융 시가총액 단위는 억 원입니다.
    """

    if value is None or pd.isna(value):
        return "-"

    value = float(value)

    if value >= 10_000:
        trillion = value / 10_000
        return f"{trillion:,.2f}조원"

    return f"{value:,.0f}억원"


def format_number(value):
    if value is None or pd.isna(value):
        return "-"

    value = float(value)

    if abs(value) >= 100_000_000:
        return f"{value / 100_000_000:,.2f}억"

    if abs(value) >= 10_000:
        return f"{value / 10_000:,.2f}만"

    return f"{value:,.0f}"


def format_ratio(value):
    if value is None or pd.isna(value):
        return "-"

    if float(value) == 0:
        return "-"

    return f"{float(value):,.2f}"


# ---------------------------------------------------------
# 상승·하락 그래프
# ---------------------------------------------------------
def create_change_chart(data, market_name):
    """
    각 시장 시가총액 TOP 10 종목의 상승·하락을
    하나의 가로 막대그래프로 표시합니다.
    """

    chart_data = data.copy()

    chart_data["등락률"] = pd.to_numeric(
        chart_data["등락률"],
        errors="coerce",
    ).fillna(0)

    chart_data = chart_data.sort_values(
        "등락률",
        ascending=True,
    )

    colors = []

    for value in chart_data["등락률"]:
        if value > 0:
            colors.append("#ef4444")
        elif value < 0:
            colors.append("#2563eb")
        else:
            colors.append("#9ca3af")

    text_values = chart_data["등락률"].map(
        lambda value: f"{value:+.2f}%"
    )

    custom_data = chart_data[
        [
            "시총순위",
            "종목코드",
            "현재가",
            "시가총액",
            "거래량",
        ]
    ].to_numpy()

    figure = go.Figure()

    figure.add_trace(
        go.Bar(
            x=chart_data["등락률"],
            y=chart_data["종목명"],
            orientation="h",
            marker_color=colors,
            text=text_values,
            textposition="outside",
            customdata=custom_data,
            hovertemplate=(
                "<b>%{y}</b><br>"
                "시총 순위: %{customdata[0]}위<br>"
                "종목코드: %{customdata[1]}<br>"
                "현재가: %{customdata[2]:,.0f}원<br>"
                "등락률: %{x:+.2f}%<br>"
                "시가총액: %{customdata[3]:,.0f}억원<br>"
                "거래량: %{customdata[4]:,.0f}주"
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
        title={
            "text": (
                f"{market_name} 시가총액 TOP 10 "
                "상승·하락 현황"
            ),
            "x": 0.5,
            "xanchor": "center",
        },
        height=590,
        xaxis_title="등락률",
        yaxis_title="",
        showlegend=False,
        margin={
            "l": 20,
            "r": 90,
            "t": 80,
            "b": 40,
        },
    )

    figure.update_xaxes(
        ticksuffix="%",
        zeroline=True,
        zerolinewidth=1,
        zerolinecolor="gray",
    )

    return figure


# ---------------------------------------------------------
# 요약 지표
# ---------------------------------------------------------
def display_summary_metrics(data):
    change = pd.to_numeric(
        data["등락률"],
        errors="coerce",
    ).fillna(0)

    rising_count = int(
        (change > 0).sum()
    )

    falling_count = int(
        (change < 0).sum()
    )

    unchanged_count = int(
        (change == 0).sum()
    )

    average_change = float(
        change.mean()
    )

    best_row = data.loc[
        change.idxmax()
    ]

    worst_row = data.loc[
        change.idxmin()
    ]

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
        best_row["종목명"],
        format_percent(
            best_row["등락률"]
        ),
    )

    columns[5].metric(
        "하락률 1위",
        worst_row["종목명"],
        format_percent(
            worst_row["등락률"]
        ),
    )

    st.caption(
        "TOP 10 합산 시가총액: "
        f"{format_market_cap(total_market_cap)}"
    )


# ---------------------------------------------------------
# 화면용 표
# ---------------------------------------------------------
def create_display_table(data):
    display = data.copy()

    display["현재가"] = display[
        "현재가"
    ].map(format_won)

    display["전일대비금액"] = display[
        "전일대비금액"
    ].map(
        lambda value: (
            f"{float(value):+,.0f}원"
            if not pd.isna(value)
            else "-"
        )
    )

    display["등락률"] = display[
        "등락률"
    ].map(format_percent)

    display["시가총액"] = display[
        "시가총액"
    ].map(format_market_cap)

    display["상장주식수"] = display[
        "상장주식수"
    ].map(format_number)

    display["거래량"] = display[
        "거래량"
    ].map(format_number)

    display["외국인비율"] = display[
        "외국인비율"
    ].map(
        lambda value: (
            f"{float(value):.2f}%"
            if not pd.isna(value)
            else "-"
        )
    )

    display["PER"] = display[
        "PER"
    ].map(format_ratio)

    display["ROE"] = display[
        "ROE"
    ].map(
        lambda value: (
            f"{float(value):.2f}%"
            if not pd.isna(value)
            and float(value) != 0
            else "-"
        )
    )

    selected_columns = [
        "시총순위",
        "종목코드",
        "종목명",
        "현재가",
        "전일대비금액",
        "등락률",
        "시가총액",
        "거래량",
        "외국인비율",
        "PER",
        "ROE",
    ]

    return display[selected_columns]


# ---------------------------------------------------------
# 공통 페이지 출력
# ---------------------------------------------------------
def render_market_page(
    market_code,
    market_name,
    page_icon,
    description,
):
    st.title(
        f"{page_icon} {market_name} 시가총액 TOP 10"
    )

    st.caption(description)

    info_column, button_column = st.columns(
        [4, 1]
    )

    with info_column:
        st.info(
            "최근 네이버 금융 시가총액 순위를 기준으로 "
            "상위 10개 종목을 분석합니다."
        )

    with button_column:
        refresh_button = st.button(
            "데이터 새로고침",
            type="primary",
            use_container_width=True,
        )

    if refresh_button:
        st.cache_data.clear()
        st.rerun()

    try:
        with st.spinner(
            f"{market_name} 데이터를 불러오는 중입니다..."
        ):
            data_date, top10_data = get_market_top10(
                market_code
            )

    except requests.exceptions.Timeout:
        st.error(
            "데이터 서버의 응답이 늦어 조회에 실패했습니다."
        )
        st.stop()

    except requests.exceptions.HTTPError as error:
        st.error(
            "네이버 금융 서버가 요청을 거부했습니다."
        )

        with st.expander("오류 내용"):
            st.code(str(error))

        st.stop()

    except Exception as error:
        st.error(
            "시가총액 데이터를 불러오지 못했습니다."
        )

        with st.expander("오류 내용 확인"):
            st.code(str(error))

        st.stop()

    st.subheader(
        f"조회 기준: {data_date}"
    )

    display_summary_metrics(top10_data)

    st.divider()

    # 각 페이지에 상승·하락 그래픽 하나만 표시
    change_figure = create_change_chart(
        data=top10_data,
        market_name=market_name,
    )

    st.plotly_chart(
        change_figure,
        use_container_width=True,
        config={
            "displaylogo": False,
            "scrollZoom": False,
        },
    )

    st.caption(
        "🔴 빨간색은 상승, 🔵 파란색은 하락, "
        "회색은 보합을 의미합니다."
    )

    st.divider()

    st.subheader(
        "📋 시가총액 TOP 10 상세 정보"
    )

    display_table = create_display_table(
        top10_data
    )

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
        label=(
            f"{market_name} TOP 10 "
            "CSV 다운로드"
        ),
        data=csv_data,
        file_name=(
            f"{market_name}_시가총액_TOP10_"
            f"{data_date}.csv"
        ),
        mime="text/csv",
        use_container_width=True,
    )

    st.divider()

    with st.expander(
        "지표 설명"
    ):
        st.markdown(
            """
            **현재가**  
            조회 시점의 종목 가격입니다.

            **등락률**  
            직전 거래일 종가 대비 현재 가격의 변동률입니다.

            **시가총액**  
            현재 주가에 상장주식 수를 곱한 값입니다.

            **외국인비율**  
            전체 상장주식 중 외국인이 보유한 비율입니다.

            **PER**  
            주가를 주당순이익으로 나눈 값입니다.

            **ROE**  
            기업이 자기자본을 이용해 어느 정도의 이익을
            창출했는지 나타내는 지표입니다.
            """
        )

    st.warning(
        "본 대시보드는 교육 및 정보 제공 목적입니다. "
        "표시된 데이터는 실시간 거래소 데이터와 차이가 있을 수 있으며 "
        "투자 권유가 아닙니다."
    )

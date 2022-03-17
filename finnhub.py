#!/usr/bin/env python

"""
    Author: Iain Muir, iam9ez@virginia.edu
    Date:
    Project:
"""


from plotly.subplots import make_subplots
import plotly.graph_objects as go
import datapane as dp
import pandas as pd
import requests
import datetime
import math
import time


# -------------------- QUOTE --------------------
def quote(key, ticker):
    """
    Real-time quote data for United States equities
    ---> includes high, low, open, close, change, etc.

    :param key
    :param ticker
    :return:
    """

    q = f'https://finnhub.io/api/v1/quote?symbol={ticker}&token={key}'
    with requests.get(q) as r:
        resp = r.json()
    return list(resp.values())


def big_number(key, ticker):
    """

    """
    close, delta, delta_pct, high, low, open_, p_close, _ = quote(key, ticker)

    return dp.BigNumber(
        heading=ticker,
        value=f"${round(close, 2)}",
        change=f"{round(delta_pct, 2)}%",
        is_upward_change=True if delta_pct > 0 else False
    )


# -------------------- CANDLES --------------------
def candles(key, ticker, years=1, resolution='D', type_='stock'):
    """
    Get candlestick data (OHLCV) for stocks.
    ---> daily data will be adjusted for splits; intraday data will remain unadjusted.

    :param key
    :param ticker
    :param years
    :param resolution
    :param type_
    :return:
    """

    if isinstance(years, int) or isinstance(years, float):
        days = math.ceil(years * 365)
        today = datetime.date.today()
        f = int(time.mktime((today - datetime.timedelta(days)).timetuple()))
        t = int(time.mktime(today.timetuple()))
    else:
        f, t = years
        f = int(time.mktime(f.timetuple()))
        t = int(time.mktime(t.timetuple()))

    candle = f'https://finnhub.io/' \
             f'api/v1/{type_}/candle?symbol={ticker}&resolution={resolution}&from={f}&to={t}&token={key}'
    with requests.get(candle) as r:
        resp = r.json()

    try:
        return pd.DataFrame(resp)
    except ValueError:
        return None


def candlestick(df, ticker, label=None):
    """

    :param df
    :param ticker
    :param label
    :return:
    """

    try:
        df['t'] = pd.to_datetime(
            df['t'],
            unit='s'
        )
    except TypeError:
        return None

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Candlestick(
            x=df.t,
            open=df.o,
            high=df.h,
            low=df.l,
            close=df.c
        ),
        secondary_y=True
    )

    fig.add_trace(
        go.Bar(
            x=df.t,
            y=df.v
        ),
        secondary_y=False
    )

    fig.update_layout(
        title={
            'text': f"<b>{ticker if label is None else label} Stock Price over Time</b>",
            'y': 0.9,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        xaxis_title="<b>Date</b>",
        xaxis=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=1,
                         label="1m",
                         step="month",
                         stepmode="backward"),
                    dict(count=3,
                         label="3m",
                         step="month",
                         stepmode="backward"),
                    dict(count=6,
                         label="6m",
                         step="month",
                         stepmode="backward"),
                    dict(count=1,
                         label="YTD",
                         step="year",
                         stepmode="todate"),
                    dict(count=1,
                         label="1y",
                         step="year",
                         stepmode="backward"),
                    dict(step="all")
                ])
            ),
            rangeslider=dict(
                visible=True
            ),
            type="date"
        )
    )

    fig.update_xaxes(
        dtick="M1",
        tickformat="%b\n%Y"
    )
    fig.update_yaxes(title_text="<b>Trade Volume</b> (M)", secondary_y=False)
    fig.update_yaxes(title_text="<b>Share Price</b> ($)", secondary_y=True)
    fig.layout.yaxis2.showgrid=False

    return dp.Plot(
        fig,
        label=ticker if label is None else label
    )


# -------------------- PROFILE --------------------
def name_search(key, ticker):
    """

    :param key
    :param ticker
    :return:
    """

    prof = f'https://finnhub.io/api/v1/stock/profile2?symbol={ticker}&token={key}'
    with requests.get(prof) as r:
        resp = r.json()

    try:
        name = resp['name']
    except KeyError:
        return None

    return f'{name} ({ticker})'


def profile(client, ticker):
    """
    General information of a company
    ---> mainly qualitative data
    """

    country, curr, exc, ipo, mkt_cap, name, _, shares, _, url, logo, industry = client.company_profile2(
        symbol=ticker
    ).values()
    return [
        country, curr, exc, ipo, mkt_cap, name, shares, url, logo, industry
    ]

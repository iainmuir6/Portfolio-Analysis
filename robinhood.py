#!/usr/bin/env python

"""
    Author: Iain Muir, iam9ez@virginia.edu
    Date:
    Project:
"""

import robin_stocks.robinhood as r
from datetime import timedelta
from finnhub import big_number
from functools import partial
import datapane as dp
import pandas as pd
import datetime


# ----------------- AUTHENTICATION PROCEDURE -----------------
def authenticate_(username, password):
    """

    :param username:
    :param password:
    :return:
    """

    r.login(
        username=username,
        password=password,
        expiresIn=30,
        scope='r',
        store_session=True
    )
    return r


# ---------------------- BUILD HOLDINGS ----------------------
def load_portfolio(client):
    """

    :return:
    """
    # TODO Error Handling for Tickers

    # ----- Build Holdings -----
    equities = client.account.build_holdings()
    equities = pd.DataFrame(equities).T
    equities = equities.reset_index()

    stock = equities.loc[equities['type'] == 'stock']
    stock_tickers = stock['index'].tolist()
    etf = equities.loc[equities['type'] == 'etp']
    etf_tickers = etf['index'].tolist()

    crypto = client.crypto.get_crypto_positions()
    crypto = {
        curr['currency']['code']: curr for curr in crypto if float(curr['quantity']) != 0.0
    }
    crypto_tickers = list(crypto.keys())
    crypto = pd.DataFrame(crypto).T
    crypto = crypto.reset_index()

    # ----- Portfolio Value -----
    portfolio = client.profiles.load_portfolio_profile()

    return [stock_tickers, etf_tickers, crypto_tickers], [stock, etf, crypto], portfolio


# ----------------- ROBINHOOD NEWS FUNCTIONS -----------------
def robinhood_news(client, ticker):
    """

    :param: client
    :param: ticker
    :return:
    """
    news = client.stocks.get_news(ticker)
    news = pd.DataFrame(news)
    news['published_at'] = pd.to_datetime(news['published_at'])
    news['published'] = news['published_at'].dt.date

    yesterday = datetime.date.today() - timedelta(days=1)
    recent_news = news.loc[
        news['published'] >= yesterday
        ]
    recent_news['preview_text'] = recent_news['preview_text'].apply(clean_summary)

    article_groups = list(
        recent_news.apply(
            lambda row: format_article(row),
            axis=1
        ).values
    )

    related_htmls = recent_news.related_instruments.apply(
        lambda i: related_instruments(client, i)
    )

    article_groups = list(map(
        lambda article, html: dp.Group(
            article,
            html
        ),
        article_groups,
        related_htmls
    ))

    return article_groups


def format_article(article):
    """

    :param article
    :param source
    :return:
    """

    _, byline, _, img, date, _, source, _, title, _, url, _, _, abstract, _, _ = article
    if byline is None or byline == "":
        byline = source
    date = datetime.datetime.strptime(str(date)[:-6], '%Y-%m-%d %H:%M:%S').strftime('%m/%d/%y %I:%M:%S %p')

    media = dp.HTML(f"""
        <img src="{img}" width="200"/>
    """.strip())
    html = dp.HTML(
        """
        <html>
            <style type='text/css'>
                h4 {
                    text-align:left;
                }
                a {
                    text-decoration:none;
                    color:#000000;
                }
                p {
                    text-align:left;
                    font-size:14px;
                    color=#000000;
                }
                .info span {
                    font-size:12px;
                    color=#808080;
                }
            </style>
            
            <h4><a href='""" + url + """' target="_blank">""" + title + """</a></h4>
            <p class='info'>
                <span><i>""" + byline + '<br>' + date + """</i></span><br><br>
                """ + abstract + """
            </p>
        </html>
        """.strip()
    )

    return dp.Group(
        media,
        html,
        columns=2
    )


def format_related(client, id_):
    """

    :param: client
    :param: id_
    :return:
    """
    q = client.stocks.get_stock_quote_by_id(id_)
    symbol, price, p_close = q['symbol'], q['last_trade_price'], q['previous_close']
    delta = (float(price) / float(p_close) - 1) * 100
    arrow = 'up' if delta >= 0 else 'down'

    return f"""
        <b>{symbol}</b>&nbsp;<div class="triangle-{arrow}"></div>&nbsp;{round(delta, 2)}%
    """.strip()


def related_instruments(client, id_list):
    """

    :param: client
    :param: id_list
    :return:
    """
    instruments = list(map(
        lambda id_: format_related(client, id_), id_list
    ))
    html = """
        <html>
            <style type='text/css'>
                .related {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                .triangle-up {
                    width: 0;
                    height: 0;
                    border-left: 8px solid transparent;
                    border-right: 8px solid transparent;
                    border-bottom: 15px solid #00FF00;
                }
                .triangle-down {
                    width: 0;
                    height: 0;
                    border-top: 15px solid #FF0000;
                    border-left: 8px solid transparent;
                    border-right: 8px solid transparent;
                }
            </style>
            <div class="related">
                """ + "&nbsp;|&nbsp;".join(instruments) + """
            </div>
        </html>
        """.strip()
    return dp.HTML(html)


def clean_summary(summary):
    """

    :param: summary
    :return:
    """
    return summary.replace('Text size\n\n', "").replace('Summary\n\nSummary Related documents ', "").strip()


# ----------------- MISCELLANEOUS HELPERS -----------------
def get_scroll_objects(row):
    """

    :param row
    :return:
    """
    current, p_close, symbol = row
    delta = float(current) / float(p_close) - 1
    delta = f'<span class="{"up" if delta >= 0 else "down"}">{round(delta * 100, 2)}%</span>'

    return f"""
    <a href="#"><b>{symbol}</b>&nbsp;<span class="price">${round(float(current), 2)}</span>&nbsp;{delta}</a>&nbsp;&nbsp;
    """.strip()


def ticker_toggle(key, tickers, label):
    """

    :param key
    :param tickers
    :param label
    :return:
    """

    bn = list(map(
        partial(big_number, key), tickers
    ))
    return dp.Toggle(
        dp.Group(
            *bn,
            columns=4
        ),
        label=label
    )


def make_header(header):
    """

    """

    return dp.HTML(
        """
        <html>
            <style type='text/css'>
                @keyframes cycle {
                    0%   {color: #89CFF0;}
                    25%  {color: #6495ED;}
                    50%  {color: #0096FF;}
                    100% {color: #0047AB;}
                }
                p {
                    text-align: center;
                }
                #container {
                    background: #ADD8E6;
                    padding: 5px 5px 5px 5px;
                    animation-name: cycle;
                    animation-duration: 4s;
                    animation-iteration-count: infinite;
                }
            </style>
            
            <div id="container">
                <p> 
                    <b>""" + header + """</b>
                </p>
            </div>
        </html>
        """
    )

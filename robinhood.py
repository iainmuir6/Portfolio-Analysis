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
from constants import ROOT
import datapane as dp
import pandas as pd
import datetime
import pickle
import os


# ----------------- AUTHENTICATION PROCEDURE -----------------
def login(username, password, expiresIn=86400, scope="internal", by_sms=True, store_session=True):
    """This function will effectivly log the user into robinhood by getting an
    authentication token and saving it to the session header. By default, it will store the authentication
    token in a pickle file and load that value on subsequent logins.
    :param username: The username for your robinhood account. Usually your email.
    :type username: str
    :param password: The password for your robinhood account.
    :type password: str
    :param expiresIn: The time until your login session expires. This is in seconds.
    :type expiresIn: Optional[int]
    :param scope: Specifies the scope of the authentication.
    :type scope: Optional[str]
    :param by_sms: Specifies whether to send an email(False) or an sms(True)
    :type by_sms: Optional[boolean]
    :param store_session: Specifies whether to save the log in authorization for future log ins.
    :type store_session: Optional[boolean]
    :returns:  A dictionary with log in information. The 'access_token' keyword contains the access token, and the 'detail' keyword \
    contains information on whether the access token was generated or loaded from pickle file.
    """

    pickle_ = username[:username.find('@')]
    device_token = r.authentication.generate_device_token()
    dir_path = os.path.dirname(os.path.realpath(__file__))
    pickle_path = os.path.join(dir_path, "Input", f"robinhood_{pickle_}.pickle")

    # Challenge type is used if not logging in with two-factor authentication.
    challenge_type = "sms" if by_sms else "email"

    url = r.urls.login_url()
    payload = {
        "client_id": "c82SH0WZOsabOXGP2sxqcj34FxkvfnWRZBKlBjFS",
        "expires_in": expiresIn,
        "grant_type": "password",
        "password": password,
        "scope": scope,
        "username": username,
        "challenge_type": challenge_type,
        "device_token": device_token,
    }
    # If authentication has been stored in pickle file then load it. Stops login server from being pinged so much.
    if os.path.isfile(pickle_path):
        # If store_session has been set to false then delete the pickle file, otherwise try to load it.
        # Loading pickle file will fail if the acess_token has expired.
        if store_session:
            try:
                with open(pickle_path, "rb") as f:
                    pickle_data = pickle.load(f)
                    access_token = pickle_data["access_token"]
                    token_type = pickle_data["token_type"]
                    refresh_token = pickle_data["refresh_token"]
                    # Set device_token to be the original device token when first logged in.
                    pickle_device_token = pickle_data["device_token"]
                    payload["device_token"] = pickle_device_token
                    # Set login status to True in order to try and get account info.
                    r.helper.set_login_state(True)
                    r.helper.update_session(
                        "Authorization", "{0} {1}".format(token_type, access_token)
                    )
                    # Try to load account profile to check that authorization token is still valid.
                    res = r.helper.request_get(
                        r.urls.portfolio_profile(), "regular", payload, jsonify_data=False
                    )
                    # Raises exception is response code is not 200.
                    res.raise_for_status()
                    return {
                        "access_token": access_token,
                        "token_type": token_type,
                        "expires_in": expiresIn,
                        "scope": scope,
                        "detail": "logged in using authentication in data.pickle",
                        "backup_code": None,
                        "refresh_token": refresh_token,
                    }
            except:
                print(
                    "ERROR: There was an issue loading pickle file. Authentication may be expired - logging in normally."
                )
                r.helper.set_login_state(False)
                r.helper.update_session("Authorization", None)
        else:
            os.remove(pickle_path)
    # Try to log in normally.
    data = r.helper.request_post(
        url,
        payload
    )

    # Handle case where mfa or challenge is required.
    if "mfa_required" in data:
        mfa_token = input("Please type in the MFA code: ")
        payload["mfa_code"] = mfa_token
        res = r.helper.request_post(
            url,
            payload,
            jsonify_data=False
        )

        while res.status_code != 200:
            mfa_token = input("Please type in the MFA code: ")
            payload["mfa_code"] = mfa_token
            res = r.helper.request_post(
                url,
                payload,
                jsonify_data=False
            )
        data = res.json()

    elif "challenge" in data:
        challenge_id = data["challenge"]["id"]
        sms_code = input("Enter Robinhood code for validation: ")
        res = r.authentication.respond_to_challenge(challenge_id, sms_code)
        while "challenge" in res and res["challenge"]["remaining_attempts"] > 0:
            sms_code = input("WRONG! Enter Robinhood code for validation: ")
            res = r.authentication.respond_to_challenge(challenge_id, sms_code)

        r.helper.update_session("X-ROBINHOOD-CHALLENGE-RESPONSE-ID", challenge_id)
        data = r.helper.request_post(
            url,
            payload
        )

    # Update Session data with authorization or raise exception with the information present in data.
    if "access_token" in data:
        token = "{0} {1}".format(data["token_type"], data["access_token"])
        r.helper.update_session("Authorization", token)
        r.helper.set_login_state(True)
        data["detail"] = "logged in with brand new authentication code."
        if store_session:
            with open(pickle_path, "wb") as f:
                pickle.dump(
                    {
                        "token_type": data["token_type"],
                        "access_token": data["access_token"],
                        "refresh_token": data["refresh_token"],
                        "device_token": device_token,
                    },
                    f,
                )
    else:
        raise Exception(data["detail"])

    return data


def authenticate_(username, password):
    """

    :param username:
    :param password:
    :return:
    """

    pickle_ = username[:username.find('@')]
    pickle_name = f'{ROOT}/Input/robinhood_{pickle_}.pickle'

    r.login(
        username=username,
        password=password,
        expiresIn=30,
        scope='r',
        pickle_name=pickle_name,
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

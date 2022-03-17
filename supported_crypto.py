#!/usr/bin/env python

"""
    Author: Iain Muir, iam9ez@virginia.edu
    Date:
    Project:
"""

from constants import ROOT
import pandas as pd
import requests
import json

with open('secrets.json') as s:
    secrets = json.loads(s.read())
FINNHUB_KEY = secrets['finnhub']

with requests.get(f'https://finnhub.io/api/v1/crypto/exchange?token={FINNHUB_KEY}') as r:
    exchanges = json.loads(r.content)

supported = []
for exchange in exchanges:
    with requests.get(f'https://finnhub.io/api/v1/crypto/symbol?exchange=binance&token={FINNHUB_KEY}') as r:
        symbols = json.loads(r.content)
        for s in symbols:
            desc, display, symbol = s.values()
            supported.append([exchange, symbol, display, desc])

df = pd.DataFrame(
    supported,
    columns=['exchange', 'symbol', 'displaySymbol', 'description']
)
df.to_csv(f'{ROOT}/Input/supported_crypto.csv')

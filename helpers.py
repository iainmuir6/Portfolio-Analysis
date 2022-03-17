#!/usr/bin/env python

"""
    Author: Iain Muir, iam9ez@virginia.edu
    Date:
    Project:
"""

from constants import ROOT
import pandas as pd
import os


def get_market_opens(client, start, present):
    """

    :param client:
    :param start:
    :param present:
    :return:
    """
    market_open = [
        [
            date.date(),
            client.markets.get_market_hours('XNYS', date.date())['is_open']
        ]
        for date in pd.date_range(start, present)
    ]
    market_open = pd.DataFrame(
        market_open,
        columns=['date', 'is_open']
    )

    if os.path.exists(f'{ROOT}/Input/market_open.csv'):
        is_open = pd.read_csv(f'{ROOT}/Input/market_open.csv')
        market_open = pd.concat(
            [market_open, is_open]
        )
        market_open = market_open.drop_duplicates(
            subset='date'
        ).sort_values(
            by='date',
            ascending=True
        ).reset_index()

    market_open.to_csv(f'{ROOT}/Input/market_open.csv')

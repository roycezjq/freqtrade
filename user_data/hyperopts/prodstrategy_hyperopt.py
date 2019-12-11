# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement

from functools import reduce
from math import exp
from typing import Any, Callable, Dict, List
from datetime import datetime

import numpy as np# noqa F401
import talib.abstract as ta
from pandas import DataFrame
from skopt.space import Categorical, Dimension, Integer, Real

import freqtrade.vendor.qtpylib.indicators as qtpylib
from freqtrade.optimize.hyperopt_interface import IHyperOpt

def normalise(dataval, minval, maxval):
        return (dataval - minval) / (maxval - minval)

class ProdStrategyHyperOpt(IHyperOpt):
    # tick-interval 5m
    # max-open-trades 3

    EMA_SHORT_TERM = 5
    EMA_MEDIUM_TERM = 20
    EMA_LONG_TERM = 50

    use_sell_signal = True
    sell_profit_only = True
    ignore_roi_if_buy_signal = False

    @staticmethod
    def populate_indicators(dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['rsi'] = ta.RSI(dataframe)
        dataframe['adx'] = ta.ADX(dataframe)

        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=40, stds=2)

        dataframe['ema_short'] = ta.EMA(dataframe, timeperiod=ProdStrategyHyperOpt.EMA_SHORT_TERM)
        dataframe['ema_medium'] = ta.EMA(dataframe, timeperiod=ProdStrategyHyperOpt.EMA_MEDIUM_TERM)
        dataframe['ema_long'] = ta.EMA(dataframe, timeperiod=ProdStrategyHyperOpt.EMA_LONG_TERM)

        dataframe['rolling_volume_std'] = dataframe['volume'].rolling(window=120).std().shift(1)
        dataframe['rolling_volume_mean'] = dataframe['volume'].rolling(window=120).mean().shift(1)

        dataframe['volume_plus_one'] = dataframe['rolling_volume_mean'] + (3 * dataframe['rolling_volume_std'])
        dataframe['volume_minus_one'] = dataframe['rolling_volume_mean'] - (3 * dataframe['rolling_volume_std'])

        dataframe['rolling_close_std'] = dataframe['close'].rolling(window=120).std().shift(1)
        dataframe['rolling_close_mean'] = dataframe['close'].rolling(window=120).mean().shift(1)

        dataframe['rolling_close_plus_one'] = dataframe['rolling_close_mean'] + (3 * dataframe['rolling_close_std'])
        dataframe['rolling_close_minus_one'] = dataframe['rolling_close_mean'] - (3 * dataframe['rolling_close_std'])

        dataframe['roc_120'] = dataframe['close'].pct_change(periods=120)

        dataframe['lower'] = np.nan_to_num(bollinger['lower'])
        dataframe['mid'] = np.nan_to_num(bollinger['mid'])
        dataframe['upper'] = np.nan_to_num(bollinger['upper'])
        dataframe['bbdelta'] = (dataframe['mid'] - dataframe['lower']).abs()
        dataframe['pricedelta'] = (dataframe['open'] - dataframe['close']).abs()
        dataframe['closedelta'] = (dataframe['close'] - dataframe['close'].shift()).abs()
        dataframe['tail'] = (dataframe['close'] - dataframe['low']).abs()

        return dataframe

    @staticmethod
    def buy_strategy_generator(params: Dict[str, Any]) -> Callable:
        """
        Define the buy strategy parameters to be used by hyperopt
        """
        def populate_buy_trend(dataframe: DataFrame, metadata: dict) -> DataFrame:
            bbdelta = 0.013
            closedelta = 0.004
            tailval = 0.45

            shouldBuy = (
                (dataframe['lower'].shift().gt(0)) &
                (dataframe['bbdelta'].gt(dataframe['close'] * bbdelta)) &
                (dataframe['closedelta'].gt(dataframe['close'] * closedelta)) &
                (dataframe['tail'].lt(dataframe['bbdelta'] * tailval)) &
                (dataframe['close'].lt(dataframe['lower'].shift())) &
                (dataframe['close'].le(dataframe['close'].shift())) &
                (dataframe['volume'] < dataframe['volume_plus_one']) &
                (dataframe['close'] < dataframe['rolling_close_plus_one']) &                
                (dataframe['roc_120'] < 0.06) &
                (dataframe['rsi'] <= 40)
            )

            print(dataframe['roc_120'])

            dataframe.loc[shouldBuy, 'buy'] = 1

            return dataframe

        return populate_buy_trend

    @staticmethod
    def indicator_space() -> List[Dimension]:
        """
        Define your Hyperopt space for searching strategy parameters
        """
        return [
            #Integer(10, 500, name="stdperiod"),
            #Real(-0.3, 3, name="stddev")

        #    Integer(25, 100, name='ema1'),
        #    Integer(6, 100, name='ema2'),
        #    Integer(6, 100, name='emavar'),
        #    Integer(10, 100, name="wndsize")
        #    Real(0.5, 1.0, name="testparam")
        #    Real(0.0, 0.05, name="bbdelta"),
        #    Real(0.0, 0.05, name="closedelta")
        #    Integer(10, 25, name='mfi-value'),
        #    Integer(15, 45, name='fastd-value'),
        #    Integer(20, 50, name='adx-value'),
        #    Integer(20, 40, name='rsi-value'),
        #    Categorical([True, False], name='mfi-enabled'),
        #    Categorical([True, False], name='fastd-enabled'),
        #    Categorical([True, False], name='adx-enabled'),
        #    Categorical([True, False], name='rsi-enabled'),
        #    Categorical(['bb_lower', 'macd_cross_signal', 'sar_reversal'], name='trigger')
        ]

    @staticmethod
    def sell_strategy_generator(params: Dict[str, Any]) -> Callable:
        """
        Define the sell strategy parameters to be used by hyperopt
        """
        def populate_sell_trend(dataframe: DataFrame, metadata: dict) -> DataFrame:
            shouldBuy = (
                (dataframe['close'] > dataframe['ema_medium']) &
                (dataframe['close'] > dataframe['ema_long']) &
                (dataframe['ema_medium'] > dataframe['ema_long']) &
                (dataframe['close'] > dataframe['upper']*0.95) &
                (dataframe['adx'] > 45) &
                (dataframe['rsi'] >= 80)
            )

            dataframe.loc[shouldBuy, 'sell'] = 1

        return populate_sell_trend

    @staticmethod
    def sell_indicator_space() -> List[Dimension]:
        """
        Define your Hyperopt space for searching sell strategy parameters
        """
        return [
        #    Real(0.5, 1.0, name="upperval")
        #    Integer(75, 100, name='sell-mfi-value'),
        #    Integer(50, 100, name='sell-fastd-value'),
        #    Integer(50, 100, name='sell-adx-value'),
        #    Integer(60, 100, name='sell-rsi-value'),
        #    Categorical([True, False], name='sell-mfi-enabled'),
        #    Categorical([True, False], name='sell-fastd-enabled'),
        #    Categorical([True, False], name='sell-adx-enabled'),
        #    Categorical([True, False], name='sell-rsi-enabled'),
        #    Categorical(['sell-bb_upper',
        #                 'sell-macd_cross_signal',
        #                 'sell-sar_reversal'], name='sell-trigger')
        ]



    @staticmethod
    def stoploss_space() -> List[Dimension]:
        """
        Stoploss Value to search

        Override it if you need some different range for the parameter in the
        'stoploss' optimization hyperspace.
        """
        return [
            Real(-0.5, -0.01, name='stoploss'),
        ]

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        bbdelta = 0.013
        closedelta = 0.004
        tailval = 0.45

        shouldBuy = (
            (dataframe['lower'].shift().gt(0)) &
            (dataframe['bbdelta'].gt(dataframe['close'] * bbdelta)) &
            (dataframe['closedelta'].gt(dataframe['close'] * closedelta)) &
            (dataframe['tail'].lt(dataframe['bbdelta'] * tailval)) &
            (dataframe['close'].lt(dataframe['lower'].shift())) &
            (dataframe['close'].le(dataframe['close'].shift())) &
            (dataframe['volume'] < dataframe['volume_plus_one']) &
            (dataframe['close'] < dataframe['rolling_close_plus_one']) &                
            (dataframe['roc_120'] < -0.01) &
            (dataframe['rsi'] <= 40)
        )

        dataframe.loc[shouldBuy, 'buy'] = 1

        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        shouldBuy = (
            (dataframe['close'] > dataframe['ema_medium']) &
            (dataframe['close'] > dataframe['ema_long']) &
            (dataframe['ema_medium'] > dataframe['ema_long']) &
            (dataframe['close'] > dataframe['upper']*0.95) &
            (dataframe['adx'] > 45) &
            (dataframe['rsi'] >= 80)
        )

        dataframe.loc[shouldBuy, 'sell'] = 1
        return dataframe

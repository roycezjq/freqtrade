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

    EMA_SHORT_TERM = 22
    EMA_MEDIUM_TERM = 50
    EMA_LONG_TERM = 99

    use_sell_signal = True
    sell_profit_only = True
    ignore_roi_if_buy_signal = False

    @staticmethod
    def populate_indicators(dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['rsi'] = ta.RSI(dataframe)

        # Bollinger bands
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=40, stds=2)

        dataframe['ema_{}'.format(ProdStrategyHyperOpt.EMA_SHORT_TERM)] = ta.EMA(
            dataframe, timeperiod=ProdStrategyHyperOpt.EMA_SHORT_TERM
        )
        dataframe['ema_{}'.format(ProdStrategyHyperOpt.EMA_MEDIUM_TERM)] = ta.EMA(
            dataframe, timeperiod=ProdStrategyHyperOpt.EMA_MEDIUM_TERM
        )
        dataframe['ema_{}'.format(ProdStrategyHyperOpt.EMA_LONG_TERM)] = ta.EMA(
            dataframe, timeperiod=ProdStrategyHyperOpt.EMA_LONG_TERM
        )

        dataframe['min'] = ta.MIN(dataframe, timeperiod=ProdStrategyHyperOpt.EMA_MEDIUM_TERM)
        dataframe['max'] = ta.MAX(dataframe, timeperiod=ProdStrategyHyperOpt.EMA_MEDIUM_TERM)

        dataframe['rolling_volume'] = dataframe['volume'].rolling(window=30).mean().shift(1) * 20

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
            condition1 = (
                dataframe['lower'].shift().gt(0) &
                dataframe['bbdelta'].gt(dataframe['close'] * 0.022) &
                dataframe['closedelta'].gt(dataframe['close'] * 0.008) &
                dataframe['tail'].lt(dataframe['bbdelta'] * 0.25) &
                dataframe['close'].lt(dataframe['lower'].shift()) &
                dataframe['close'].le(dataframe['close'].shift())
            )

            condition2 = (
                (dataframe['volume'] < dataframe['rolling_volume']) &
                (dataframe['close'] < dataframe['ema_{}'.format(self.EMA_MEDIUM_TERM)]) &
                (dataframe['close'] <= 0.985 * dataframe['lower']) &
                (dataframe['rsi'] <= 30)
            )

            condition = (condition1|condition2)
            #condition = condition2

            dataframe.loc[condition, 'buy'] = 1

            return dataframe

        return populate_buy_trend

    @staticmethod
    def indicator_space() -> List[Dimension]:
        """
        Define your Hyperopt space for searching strategy parameters
        """
        return [
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
            dataframe['sell'] = 0
        
            return dataframe

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
        condition1 = (
            dataframe['lower'].shift().gt(0) &
            dataframe['bbdelta'].gt(dataframe['close'] * 0.022) &
            dataframe['closedelta'].gt(dataframe['close'] * 0.008) &
            dataframe['tail'].lt(dataframe['bbdelta'] * 0.25) &
            dataframe['close'].lt(dataframe['lower'].shift()) &
            dataframe['close'].le(dataframe['close'].shift())
        )

        condition2 = (
            (dataframe['volume'] < dataframe['rolling_volume']) &
            (dataframe['close'] < dataframe['ema_{}'.format(ProdStrategyHyperOpt.EMA_SHORT_TERM)]) &
            (dataframe['close'] < dataframe['ema_{}'.format(ProdStrategyHyperOpt.EMA_MEDIUM_TERM)]) &
            (dataframe['close'] == dataframe['min']) &
            (dataframe['close'] <= dataframe['lower'])
        )

        condition = (condition1|condition2)

        dataframe.loc[condition, 'buy'] = 1

        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['sell'] = 0
        
        return dataframe

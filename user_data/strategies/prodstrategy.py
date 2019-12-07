# --- Do not remove these libs ---
import freqtrade.vendor.qtpylib.indicators as qtpylib
import numpy as np
from functools import reduce

# --------------------------------
import talib.abstract as ta
from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame

def normalise(dataval, minval, maxval):
        return (dataval - minval) / (maxval - minval)


class ProdStrategy(IStrategy):
    # tick-interval 5m
    # max-open-trades 3
    EMA_SHORT_TERM = 22
    EMA_MEDIUM_TERM = 50
    EMA_LONG_TERM = 99

    use_sell_signal = True
    sell_profit_only = True
    ignore_roi_if_buy_signal = False

    ticker_interval = '5m'

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['rsi'] = ta.RSI(dataframe)

        # ADX
        dataframe['adx'] = ta.ADX(dataframe)

        # Bollinger bands
        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=40, stds=2)

        dataframe['ema_{}'.format(self.EMA_SHORT_TERM)] = ta.EMA(
            dataframe, timeperiod=self.EMA_SHORT_TERM
        )
        dataframe['ema_{}'.format(self.EMA_MEDIUM_TERM)] = ta.EMA(
            dataframe, timeperiod=self.EMA_MEDIUM_TERM
        )
        dataframe['ema_{}'.format(self.EMA_LONG_TERM)] = ta.EMA(
            dataframe, timeperiod=self.EMA_LONG_TERM
        )

        dataframe['min'] = ta.MIN(dataframe, timeperiod=self.EMA_MEDIUM_TERM)
        dataframe['max'] = ta.MAX(dataframe, timeperiod=self.EMA_MEDIUM_TERM)

        dataframe['rolling_volume'] = dataframe['volume'].rolling(window=30).mean().shift(1) * 20

        dataframe['lower'] = np.nan_to_num(bollinger['lower'])
        dataframe['mid'] = np.nan_to_num(bollinger['mid'])
        dataframe['upper'] = np.nan_to_num(bollinger['upper'])
        dataframe['bbdelta'] = (dataframe['mid'] - dataframe['lower']).abs()
        dataframe['pricedelta'] = (dataframe['open'] - dataframe['close']).abs()
        dataframe['closedelta'] = (dataframe['close'] - dataframe['close'].shift()).abs()
        dataframe['tail'] = (dataframe['close'] - dataframe['low']).abs()

        return dataframe

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
            (dataframe['close'] < dataframe['ema_{}'.format(self.EMA_SHORT_TERM)]) &
            (dataframe['close'] < dataframe['ema_{}'.format(self.EMA_MEDIUM_TERM)]) &
            (dataframe['close'] == dataframe['min']) &
            (dataframe['close'] <= 0.985 * dataframe['lower'])
        )
        #condition = (condition1|condition2)
        condition = condition2

        dataframe.loc[condition, 'buy'] = 1
        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        dataframe['sell'] = 0
        
        return dataframe
# --- Do not remove these libs ---
import freqtrade.vendor.qtpylib.indicators as qtpylib
import numpy as np
from functools import reduce
from freqtrade.state import RunMode
# --------------------------------
import talib.abstract as ta
from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame
from freqtrade.persistence import Trade
from datetime import timedelta, datetime, timezone

class ProdStrategy(IStrategy):
    # tick-interval 5m
    # max-open-trades 3

    minimal_roi = {
        "0": 0.02,
        "55": 0.01,
        "144": 0.005,
        "233": 0.0
    }

    EMA_SHORT_TERM = 5
    EMA_MEDIUM_TERM = 20
    EMA_LONG_TERM = 50

    use_sell_signal = True
    sell_profit_only = True
    ignore_roi_if_buy_signal = False

    ticker_interval = '5m'

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['rsi'] = ta.RSI(dataframe)
        dataframe['adx'] = ta.ADX(dataframe)

        bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(dataframe), window=40, stds=2)

        dataframe['ema_short'] = ta.EMA(dataframe, timeperiod=ProdStrategy.EMA_SHORT_TERM)
        dataframe['ema_medium'] = ta.EMA(dataframe, timeperiod=ProdStrategy.EMA_MEDIUM_TERM)
        dataframe['ema_long'] = ta.EMA(dataframe, timeperiod=ProdStrategy.EMA_LONG_TERM)

        dataframe['rolling_volume_std'] = dataframe['volume'].rolling(window=120).std().shift(1)
        dataframe['rolling_volume_mean'] = dataframe['volume'].rolling(window=120).mean().shift(1)

        dataframe['rolling_volume_plus_one'] = dataframe['rolling_volume_mean'] + (3 * dataframe['rolling_volume_std'])
        dataframe['rolling_volume_minus_one'] = dataframe['rolling_volume_mean'] - (3 * dataframe['rolling_volume_std'])

        dataframe['rolling_close_std'] = dataframe['close'].rolling(window=120).std().shift(1)
        dataframe['rolling_close_mean'] = dataframe['close'].rolling(window=120).mean().shift(1)

        dataframe['rolling_close_plus_one'] = dataframe['rolling_close_mean'] + (3 * dataframe['rolling_close_std'])
        dataframe['rolling_close_minus_one'] = dataframe['rolling_close_mean'] - (3 * dataframe['rolling_close_std'])

        dataframe['pntchg'] = dataframe['close'].pct_change(periods=120)

        dataframe['pntchg_std'] = dataframe['pntchg'].rolling(window=120).std().shift(1)
        dataframe['pntchg_mean'] = dataframe['pntchg'].rolling(window=120).mean().shift(1)

        dataframe['rolling_pntchg_plus_one'] = dataframe['pntchg_mean'] + (3 * dataframe['pntchg_std'])
        dataframe['rolling_pntchg_minus_one'] = dataframe['pntchg_mean'] - (3 * dataframe['pntchg_std'])

        dataframe['lower'] = np.nan_to_num(bollinger['lower'])
        dataframe['mid'] = np.nan_to_num(bollinger['mid'])
        dataframe['upper'] = np.nan_to_num(bollinger['upper'])
        dataframe['bbdelta'] = (dataframe['mid'] - dataframe['lower']).abs()
        dataframe['pricedelta'] = (dataframe['open'] - dataframe['close']).abs()
        dataframe['closedelta'] = (dataframe['close'] - dataframe['close'].shift()).abs()
        dataframe['tail'] = (dataframe['close'] - dataframe['low']).abs()

        #Within populate indicators (or populate_buy):
        if self.config['runmode'] in (RunMode.LIVE, RunMode.DRY_RUN):
            # fetch trades for the last 2 days
            trades = Trade.get_trades([Trade.pair == metadata['pair'],
                                    Trade.open_date > datetime.utcnow() - timedelta(days=2),
                                    Trade.is_open == False,
                        ]).all()
            # Analyze the conditions you'd like to lock the pair .... will probably be different for every strategy
            sumprofit = sum(trade.close_profit for trade in trades)
            if sumprofit < 0:
                # Lock pair for 2 days
                self.lock_pair(metadata['pair'], until=datetime.now(timezone.utc) + timedelta(days=2))

        return dataframe

    def populate_buy_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        bbdelta = 0.02042
        closedelta = 0.00025
        tailval = 0.25

        mainQuery = (
            (dataframe['lower'].shift().gt(0)) &
            (dataframe['ema_medium'] < dataframe['ema_long']) &
            (dataframe['bbdelta'].gt(dataframe['close'] * bbdelta)) &
            (dataframe['closedelta'].gt(dataframe['close'] * closedelta)) &
            (dataframe['tail'].lt(dataframe['bbdelta'] * tailval)) &
            (dataframe['close'].lt(dataframe['lower'].shift())) &
            (dataframe['close'].le(dataframe['close'].shift()))
        )


        # Is volume closer to less than 3 stddevs than more than 3 stddevs
        closerToVolumeMinus3 = (
            (dataframe['volume']-dataframe['rolling_volume_minus_one']) < (dataframe['rolling_volume_plus_one']-dataframe['close'])
        )

        # Is close price less than 1 standard deviation
        closePriceLessThan1StdDev = (
            (dataframe['close'] < dataframe['rolling_close_plus_one'])
        )

        volumeLessThanOneStdDev = (dataframe['volume'] < dataframe['rolling_volume_plus_one'])
        
        rocChange = (dataframe['pntchg'] > -0.2)

        rsiBelowThreshold = (dataframe['rsi'] <= 40)

        shouldBuy = (mainQuery & volumeLessThanOneStdDev & closePriceLessThan1StdDev & rsiBelowThreshold & rocChange)

        dataframe.loc[shouldBuy, 'buy'] = 1
        return dataframe

    def populate_sell_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        dataframe['sell'] = 0
        
        return dataframe

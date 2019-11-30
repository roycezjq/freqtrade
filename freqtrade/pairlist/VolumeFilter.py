import logging
import json
from copy import deepcopy
from typing import Dict, List

from freqtrade.pairlist.IPairList import IPairList

logger = logging.getLogger(__name__)


class VolumeFilter(IPairList):

    def __init__(self, exchange, pairlistmanager, config, pairlistconfig: dict,
                 pairlist_pos: int) -> None:
        super().__init__(exchange, pairlistmanager, config, pairlistconfig, pairlist_pos)

        self._low_volume = pairlistconfig.get('min_volume', 0)

    @property
    def needstickers(self) -> bool:
        """
        Boolean property defining if tickers are necessary.
        If no Pairlist requries tickers, an empty List is passed
        as tickers argument to filter_pairlist
        """
        return True

    def short_desc(self) -> str:
        """
        Short whitelist method description - used for startup-messages
        """
        return f"{self.name} - Filtering pairs with volume below {self._low_volume}."

    def _validate_ticker_volume(self, ticker) -> bool:
        """
        Check if the volume is below the threshold
        :param ticker: ticker dict as returned from ccxt.load_markets()
        :param precision: Precision
        :return: True if the pair can stay, false if it should be removed
        """

        qv = float(ticker['quoteVolume'])
        minv = self._low_volume

        if qv <= minv:
            logger.info(f"Removed {ticker['symbol']} from whitelist, "
            f"because quoteVolume {qv:10.10} would be <= threshold {minv}")
            return False

        return True

    def filter_pairlist(self, pairlist: List[str], tickers: Dict) -> List[str]:

        """
        Filters and sorts pairlist and returns the whitelist again.
        Called on each bot iteration - please use internal caching if necessary
        :param pairlist: pairlist to filter or sort
        :param tickers: Tickers (from exchange.get_tickers()). May be cached.
        :return: new whitelist
        """
        # Copy list since we're modifying this list
        for p in deepcopy(pairlist):
            ticker = tickers.get(p)
            if not ticker:
                pairlist.remove(p)

            # Filter out assets which would not allow setting a stoploss
            if self._low_volume and not self._validate_ticker_volume(ticker):
                pairlist.remove(p)

        return pairlist

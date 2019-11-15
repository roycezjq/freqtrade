install:
	./setup.sh --install

run:
	./.env/bin/freqtrade trade --strategy Strategy

train:
	./.env/bin/freqtrade -c config.json hyperopt \
	--customhyperopt StrategyHyperOpt \
	-e 8000 \
	--spaces buy \
	--ticker-interval 5m \
	--print-all \
	--min-trades 50

backtest:
	./.env/bin/freqtrade backtesting \
	--strategy-list Strategy  \
	--ticker-interval 5m \
	--timerange 20191101- \
	--export trades

backtest2:
	./.env/bin/freqtrade backtesting \
	--strategy-list Strategy  \
	--ticker-interval 5m \
	--timerange 20191001- \
	--export trades

data:
	./.env/bin/freqtrade download-data --exchange binance --days 120 --timeframes 5m
install:
	./setup.sh --install

run:
	./.env/bin/freqtrade trade --strategy Strategy

train:
	./.env/bin/freqtrade hyperopt \
	-c config.json \
	--hyperopt StrategyHyperOpt \
	--strategy Strategy \
	-e 8000 \
	--spaces buy \
	--ticker-interval 1m \
	--print-all \
	--timerange 20191008- \
	--min-trades 50

backtest:
	./.env/bin/freqtrade backtesting \
	--strategy-list Strategy  \
	--ticker-interval 5m \
	--timerange 20191001- \
	--export trades

backtest2:
	./.env/bin/freqtrade backtesting \
	--strategy-list Strategy  \
	--ticker-interval 5m \
	--timerange 20191001- \
	--export trades

data:
	./.env/bin/freqtrade download-data --exchange binance --days 120 --timeframes 5m 1m


stop-svc:
	systemctl --user stop freqtrade.service

disable-svc:
	systemctl --user disable freqtrade.service

enable-svc:
	systemctl --user enable freqtrade.service

start-svc:
	systemctl --user start freqtrade.service

show-logs:
	tail -f -n 100 /var/log/syslog
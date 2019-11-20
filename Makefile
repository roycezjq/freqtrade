install:
	./setup.sh --install

run:
	./.env/bin/freqtrade trade --strategy Strategy1M

refresh-and-train: data train

train:
	./.env/bin/freqtrade hyperopt \
	-c config.json \
	--hyperopt StrategyHyperOpt \
	--strategy Strategy1M \
	-e 8000 \
	-j 10 \
	--spaces stoploss \
	--ticker-interval 1m \
	--timerange 20191111- \
	--print-all \
	--min-trades 50

backtest:
	./.env/bin/freqtrade backtesting \
	--strategy-list Strategy1M  \
	--ticker-interval 1m \
	--export trades

backtest-14day:
	./.env/bin/freqtrade backtesting \
	--strategy-list Strategy  \
	--ticker-interval 1m \
	--timerange 20191104- \
	--export trades


backtest-7day:
	./.env/bin/freqtrade backtesting \
	--strategy-list Strategy  \
	--ticker-interval 1m \
	--timerange 20191111- \
	--export trades

backtest-1day:
	./.env/bin/freqtrade backtesting \
	--strategy-list Strategy  \
	--ticker-interval 1m \
	--timerange 20191117- \
	--export trades

data:
	./.env/bin/freqtrade download-data --exchange binance --days 60 --timeframes 1m


stop-svc:
	systemctl --user stop freqtrade.service

disable-svc:
	systemctl --user disable freqtrade.service

enable-svc:
	systemctl --user enable freqtrade.service

start-svc:
	systemctl --user start freqtrade.service

restart: stop-svc start-svc

show-logs:
	tail -f -n 100 /var/log/syslog

install:
	./setup.sh --install

run:
	./.env/bin/freqtrade trade --strategy Strategy1M

refresh-and-train: data train

train:
	./.env/bin/freqtrade hyperopt \
	-c config.json \
	--hyperopt-loss CalmarHyperOptLoss \
	--hyperopt ProdStrategyHyperOpt \
	--strategy ProdStrategy \
	-e 8000 \
	-j 10 \
	--spaces roi \
	--ticker-interval 5m \
	--timerange 20191111- \
	--print-all \
	--min-trades 2 \
	--max-duration 450

backtest:
	./.env/bin/freqtrade backtesting \
	--strategy-list ProdStrategy  \
	--ticker-interval 5m \
	--export trades

backtest-14day:
	./.env/bin/freqtrade backtesting \
	--strategy-list ProdStrategy  \
	--ticker-interval 5m \
	--timerange 20191104- \
	--autosuggest_pairlist \
	--export trades


backtest-7day:
	./.env/bin/freqtrade backtesting \
	--strategy-list ProdStrategy  \
	--ticker-interval 5m \
	--timerange 20191125- \
	--export trades

backtest-1day:
	./.env/bin/freqtrade backtesting \
	--strategy-list ProdStrategy  \
	--ticker-interval 5m \
	--timerange 20191117- \
	--export trades

data:
	./.env/bin/freqtrade download-data --exchange binance --days 60 --timeframes 1m 5m


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

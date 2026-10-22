# Weather Bot (paper trading)

Compares Kalshi's daily high-temperature markets with professional weather
forecast ensembles (GFS, ECMWF, ICON) and logs "paper" trades wherever the
forecast says a contract is mispriced after fees. **No real money. No Kalshi
account needed.** Everything uses free, public data.

## Run it

Open **Terminal** and paste:

    cd ~/Desktop/"Trading Bots"/weather-bot
    python3 scan.py

Or double-click **Scan.command** in this folder. (The first time, macOS may
block it: right-click > Open > Open.)

- `python3 scan.py Austin` scans one city.
- `python3 report.py` settles finished trades and shows the scorecard.
  Double-click **Report.command** does the same.

## Dashboard

Double-click **Dashboard.command** (or open `dashboard.html`) to see results,
open trades, and a visual board of forecast vs. market price. It rebuilds
every time the bot runs.

## What the files do

| File | Purpose |
|---|---|
| `config.py` | All settings: cities, edge threshold, trade size, model spread |
| `botlib.py` | Talks to Kalshi + Open-Meteo, turns forecasts into probabilities |
| `scan.py` | Prints every bracket: model % vs Kalshi price, logs signals |
| `report.py` | Grades settled paper trades, P&L, per-city forecast error |
| `paper_trades.csv` | Your paper-trade log (opens in Numbers/Excel) |
| `dashboard.py` | Builds `dashboard.html` from the log files |
| `forecasts.csv` | Every forecast the bot made, for calibration |

## Routine for the next few weeks

1. Run `scan.py` 2-3 times a day. Good times are just after the big model
   updates land: roughly 6am, 11am and 6pm Central.
2. Run `report.py` each morning. Kalshi settles each day's markets the next morning.
3. After about 2 weeks, look at the forecast-error section and set `BIAS_F`
   in `config.py` for each city.
4. Go live only after 100+ settled paper trades that show a real ROI and a
   win rate close to what the model expected.

## How it decides

For each forecast member's predicted high, it draws a small bell curve
(`SPREAD_F` wide) and adds up how much of each curve lands in each bracket.
That gives the probability. A trade is logged only when
`probability - price - fee >= MIN_EDGE`.

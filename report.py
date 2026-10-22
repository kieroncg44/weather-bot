"""Settle paper trades whose markets have finished, then print the scorecard.

Run:  python3 report.py
"""

import csv
import os
import sys
from collections import defaultdict

import botlib
import config
from scan import TRADES, FORECASTS, TRADE_COLS

if len(sys.argv) > 1:          # e.g. python3 report.py paper_trades_v1.csv
    TRADES = os.path.join(os.path.dirname(os.path.abspath(__file__)), sys.argv[1])

SETTLED = ("settled", "finalized", "determined")
ACTUALS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "actuals.csv")


def save_actuals(actual):
    """Remember what the thermometer actually said, for forecast-error tracking."""
    known = {}
    if os.path.exists(ACTUALS):
        with open(ACTUALS, newline="") as f:
            for r in csv.DictReader(f):
                known[(r["city"], r["date"])] = r["actual"]
    for k, v in actual.items():
        known[k] = v
    with open(ACTUALS, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["city", "date", "actual"])
        for (c, d), v in sorted(known.items()):
            w.writerow([c, d, v])


def settle():
    if not os.path.exists(TRADES):
        print("No paper trades yet. Run scan.py first.")
        return [], {}
    with open(TRADES, newline="") as f:
        rows = list(csv.DictReader(f))

    actual = {}  # (city, date) -> actual high, from Kalshi's settlement value
    cache = {}
    changed = False
    for r in rows:
        if r["status"] != "open":
            continue
        try:
            m = cache.get(r["ticker"]) or botlib.market(r["ticker"])
            cache[r["ticker"]] = m
        except Exception as e:
            print("  could not check %s: %s" % (r["ticker"], e))
            continue
        if m.get("status") not in SETTLED or m.get("result") not in ("yes", "no"):
            continue
        won = (m["result"] == "yes") == (r["side"] == "YES")
        price = int(r["price_cents"]) / 100.0
        n = int(r["contracts"])
        fee = float(r["fee_per_contract"])
        pnl = n * ((1 - price) if won else -price) - n * fee
        r.update(status="settled", result="win" if won else "loss", pnl=round(pnl, 2))
        changed = True
        ev = m.get("expiration_value")
        if ev not in (None, ""):
            try:
                actual[(r["city"], r["date"])] = float(ev)
            except ValueError:
                pass

    if changed:
        with open(TRADES, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=TRADE_COLS)
            w.writeheader()
            w.writerows(rows)
    return rows, actual


def scorecard(rows):
    done = [r for r in rows if r["status"] == "settled"]
    open_n = sum(1 for r in rows if r["status"] == "open")
    print("\nPAPER TRADING SCORECARD")
    print("=" * 60)
    print("Settled trades: %d    Still open: %d" % (len(done), open_n))
    if not done:
        print("Nothing settled yet. Markets settle the morning after each day.")
        return
    pnl = sum(float(r["pnl"]) for r in done)
    risked = sum(int(r["contracts"]) * int(r["price_cents"]) / 100.0 for r in done)
    wins = sum(1 for r in done if r["result"] == "win")
    exp_wins = sum(float(r["model_prob_win"]) for r in done)
    print("Total P&L:      $%+.2f   on $%.2f risked  (ROI %+.1f%%)" % (pnl, risked, 100 * pnl / risked))
    print("Win rate:       %d/%d = %.0f%%   (model expected %.0f%%)" % (
        wins, len(done), 100.0 * wins / len(done), 100.0 * exp_wins / len(done)))

    by_city = defaultdict(lambda: [0, 0.0])
    for r in done:
        by_city[r["city"]][0] += 1
        by_city[r["city"]][1] += float(r["pnl"])
    print("\nBy city:")
    for c, (n, p) in sorted(by_city.items(), key=lambda x: -x[1][1]):
        print("  %-14s %3d trades   $%+8.2f" % (c, n, p))

    if len(done) < 100:
        print("\nNote: under ~100 settled trades, results are mostly luck. Keep paper trading.")


def bias_check(actual):
    """Compare the forecast we logged to what actually happened, per city."""
    if not actual or not os.path.exists(FORECASTS):
        return
    last = {}
    with open(FORECASTS, newline="") as f:
        for r in csv.DictReader(f):
            last[(r["city"], r["date"])] = float(r["mean_high"])
    errs = defaultdict(list)
    for key, act in actual.items():
        if key in last:
            errs[key[0]].append(act - last[key])
    if not errs:
        return
    print("\nForecast error (actual minus our forecast, °F):")
    for c, e in sorted(errs.items()):
        print("  %-14s avg %+.1f over %d day(s)" % (c, sum(e) / len(e), len(e)))
    print("Once a city has 10+ days, put its average into BIAS_F in config.py.")


if __name__ == "__main__":
    rows, actual = settle()
    if actual and len(sys.argv) == 1:
        save_actuals(actual)
    if rows:
        scorecard(rows)
        bias_check(actual)
    if len(sys.argv) == 1:
        try:
            import dashboard
            dashboard.build()
            print("\nDashboard updated: open dashboard.html")
        except Exception as e:
            print("(dashboard not updated: %s)" % e)

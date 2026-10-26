"""Scan Kalshi weather markets, compare to the forecast model, and log paper trades.

Run:  python3 scan.py            (all cities)
      python3 scan.py Austin     (just one city, by name)
"""

import csv
import json
import os
import sys
from datetime import datetime, timezone

import botlib
import config

HERE = os.path.dirname(os.path.abspath(__file__))
TRADES = os.path.join(HERE, "paper_trades.csv")
FORECASTS = os.path.join(HERE, "forecasts.csv")
LATEST = os.path.join(HERE, "latest_scan.json")
BOARD = []  # everything the last scan saw, for the dashboard

TRADE_COLS = ["logged_at", "city", "date", "ticker", "bracket", "side", "price_cents",
              "contracts", "fee_per_contract", "model_prob_win", "edge",
              "status", "result", "pnl"]
OPPS = os.path.join(HERE, "opportunities.csv")
OPP_COLS = ["logged_at", "city", "date", "ticker", "bracket", "model_prob_yes",
            "yes_ask", "no_ask", "signal_side", "signal_edge"]
FC_COLS = ["logged_at", "city", "date", "members", "mean_high", "min_high", "max_high",
           "raw_ensemble_mean", "anchor_high"]


def _append(path, cols, row):
    new = not os.path.exists(path) or os.path.getsize(path) == 0
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        if new:
            w.writeheader()
        w.writerow(row)


def _already_logged():
    """Tickers already traded, plus city-days already traded since the freeze began
    (at most one trade per city per day)."""
    seen, days = set(), set()
    if os.path.exists(TRADES) and os.path.getsize(TRADES) > 0:
        with open(TRADES, newline="") as f:
            for r in csv.DictReader(f):
                seen.add((r["ticker"], r["side"]))
                if r["logged_at"] >= config.FREEZE_START:
                    days.add((r["city"], r["date"]))
    return seen, days


def _too_late(d, tz, kind="high"):
    if botlib.ZoneInfo is None:
        return False
    now_local = datetime.now(botlib.ZoneInfo(tz))
    if d < now_local.date():
        return True
    if kind == "low":
        return d <= now_local.date()
    return d == now_local.date() and now_local.hour >= config.SAME_DAY_CUTOFF_HOUR


def scan_city(series, city, seen, days_traded, now, kind="high"):
    name = city["name"] + (" low" if kind == "low" else "")
    try:
        markets = botlib.open_markets(series)
    except Exception as e:
        print("  %-14s skipped (Kalshi: %s)" % (name, e))
        return []
    markets = [m for m in markets if m["date"] and not _too_late(m["date"], city["tz"], kind)]
    if not markets:
        return []

    days = sorted({m["date"] for m in markets})
    try:
        highs_by_day = botlib.ensemble_highs(city, days, kind)
        anchors = botlib.anchor_high(city, days, kind)
    except Exception as e:
        print("  %-14s skipped (forecast: %s)" % (name, e))
        return []

    bias = config.BIAS_F.get(series, config.HIGH_BIAS_F if kind == "high" else 0.0)
    signals = []
    for d in days:
        raw = highs_by_day.get(d, [])
        highs = botlib.centered(raw, anchors.get(d))
        if len(highs) < config.MIN_MEMBERS:
            print("  %-14s %s  not enough forecast members (%d)" % (name, d, len(highs)))
            continue
        mean = sum(highs) / len(highs) + bias
        _append(FORECASTS, FC_COLS, {
            "logged_at": now, "city": name, "date": d, "members": len(highs),
            "mean_high": round(mean, 1), "min_high": round(min(highs) + bias, 1),
            "max_high": round(max(highs) + bias, 1),
            "raw_ensemble_mean": round(sum(raw) / len(raw), 1) if raw else "",
            "anchor_high": anchors.get(d, "")})
        print("\n  %s  %s   forecast %s %.1f°F  (range %.0f-%.0f, %s)" % (
            name, d.strftime("%a %b %d"), kind, mean,
            min(highs) + bias, max(highs) + bias,
            "anchored" if d in anchors else "ensemble only"))
        print("    %-14s %7s %7s %7s   %s" % ("bracket", "model", "yes ask", "no ask", "signal"))
        card = {"city": city["name"], "kind": kind, "date": str(d), "forecast": round(mean, 1),
                "low": round(min(highs) + bias, 1), "high": round(max(highs) + bias, 1),
                "anchored": d in anchors, "rows": []}
        BOARD.append(card)
        candidates = []

        for m in sorted(markets, key=lambda x: (x["bracket"][0] if x["bracket"][0] is not None else -999)):
            if m["date"] != d:
                continue
            p = botlib.bracket_probability(highs, m["bracket"], bias)
            t = botlib.best_trade(p, m, config.PAPER_CONTRACTS)
            no_ask = m["no_ask"] or (100 - m["yes_bid"] if m["yes_bid"] else None)
            sig = ""
            if t:
                sig = "BUY %s @ %d¢  edge %+.0f¢" % (t["side"], t["price"], t["edge"] * 100)
            print("    %-14s %6.0f%% %6s %6s    %s" % (
                botlib.bracket_label(m["bracket"]), p * 100,
                "%d¢" % m["yes_ask"] if m["yes_ask"] else "-",
                "%d¢" % no_ask if no_ask else "-", sig))
            card["rows"].append({
                "label": botlib.bracket_label(m["bracket"]), "model": round(p, 3),
                "yes_ask": m["yes_ask"], "no_ask": no_ask,
                "side": t["side"] if t else None, "price": t["price"] if t else None,
                "edge": round(t["edge"], 3) if t else None})
            _append(OPPS, OPP_COLS, {
                "logged_at": now, "city": name, "date": d, "ticker": m["ticker"],
                "bracket": botlib.bracket_label(m["bracket"]), "model_prob_yes": round(p, 4),
                "yes_ask": m["yes_ask"], "no_ask": no_ask,
                "signal_side": t["side"] if t else "", "signal_edge": round(t["edge"], 3) if t else ""})
            if t and (m["ticker"], t["side"]) not in seen:
                candidates.append((t, m))

        # Sit out unsettled days (fronts, storms): forecast runs disagree too much.
        if max(highs) - min(highs) > config.MAX_FORECAST_RANGE_F:
            print("    (no trade: forecast runs too spread out, %.0f-%.0f)" % (min(highs) + bias, max(highs) + bias))
            candidates = []

        # Only the single best trade per city per day.
        if candidates and (name, str(d)) not in days_traded:
            t, m = max(candidates, key=lambda c: c[0]["edge"])
            seen.add((m["ticker"], t["side"]))
            days_traded.add((name, str(d)))
            row = {"logged_at": now, "city": name, "date": d,
                   "ticker": m["ticker"], "bracket": botlib.bracket_label(m["bracket"]),
                   "side": t["side"], "price_cents": t["price"],
                   "contracts": config.PAPER_CONTRACTS,
                   "fee_per_contract": round(t["fee"], 4),
                   "model_prob_win": round(t["p_win"], 3),
                   "edge": round(t["edge"], 3), "status": "open",
                   "result": "", "pnl": ""}
            _append(TRADES, TRADE_COLS, row)
            signals.append(row)
    return signals


def main():
    only = " ".join(sys.argv[1:]).lower()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print("Weather bot scan  %s   (paper trading only)" % now)
    seen, days_traded = _already_logged()
    new = []
    for series, city in config.CITIES.items():
        if only and only not in city["name"].lower():
            continue
        new += scan_city(series, city, seen, days_traded, now)
        if config.TRADE_LOWS and city.get("low"):
            new += scan_city(city["low"], city, seen, days_traded, now, kind="low")

    print("\n" + "=" * 60)
    if new:
        print("%d new paper trade(s) logged to paper_trades.csv:" % len(new))
        for r in new:
            print("  %-14s %s  %-12s BUY %-3s @ %s¢  edge %+.0f¢" % (
                r["city"], r["date"], r["bracket"], r["side"], r["price_cents"],
                r["edge"] * 100))
    else:
        print("No new paper trades this scan.")
    print("Run  python3 report.py  after markets settle to see results.")
    if not only:
        with open(LATEST, "w") as f:
            json.dump({"scanned_at": now, "new_trades": len(new), "board": BOARD}, f)
    try:
        import dashboard
        dashboard.build()
        print("Dashboard updated: open dashboard.html")
    except Exception as e:
        print("(dashboard not updated: %s)" % e)


if __name__ == "__main__":
    main()

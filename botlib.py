"""Shared code: talking to Kalshi and Open-Meteo, and the probability model."""

import json
import math
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

import config

try:
    from zoneinfo import ZoneInfo
except ImportError:  # very old Python
    ZoneInfo = None


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------

_CACHE = {}


def get_json(url, params=None, tries=4):
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    if "open-meteo" in url and url in _CACHE:   # highs and lows share forecasts
        return _CACHE[url]
    req = urllib.request.Request(url, headers={"User-Agent": config.USER_AGENT,
                                               "Accept": "application/json"})
    last = None
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=12) as r:
                data = json.loads(r.read().decode("utf-8"))
            if "open-meteo" in url:
                _CACHE[url] = data
            return data
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 404:
                raise
            time.sleep(1.5 * (attempt + 1))
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise last


# --------------------------------------------------------------------------
# Kalshi (public market data, no account needed)
# --------------------------------------------------------------------------

def _cents(market, name):
    """Price in cents, whichever format the API uses (cents int or dollar string)."""
    v = market.get(name + "_dollars")
    if v not in (None, ""):
        try:
            return round(float(v) * 100)
        except ValueError:
            pass
    v = market.get(name)
    if v in (None, ""):
        return None
    try:
        return round(float(v))
    except ValueError:
        return None


_MONTHS = {m: i for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], 1)}


def event_date(event_ticker):
    """KXHIGHNY-26OCT22 -> date(2026, 10, 22)."""
    m = re.search(r"-(\d{2})([A-Z]{3})(\d{2})$", event_ticker or "")
    if not m or m.group(2) not in _MONTHS:
        return None
    return date(2000 + int(m.group(1)), _MONTHS[m.group(2)], int(m.group(3)))


def bracket(market):
    """Return (low, high) whole-degree range that pays YES. None = open-ended."""
    st = market.get("strike_type")
    lo, hi = market.get("floor_strike"), market.get("cap_strike")
    if st == "between":
        return (int(round(lo)), int(round(hi)))
    if st == "greater":            # YES if temp > floor
        return (int(math.floor(lo)) + 1, None)
    if st == "less":               # YES if temp < cap
        return (None, int(math.ceil(hi)) - 1)
    return None


def bracket_label(b):
    lo, hi = b
    if lo is None:
        return "%d° or below" % hi
    if hi is None:
        return "%d° or above" % lo
    if lo == hi:
        return "%d°" % lo
    return "%d-%d°" % (lo, hi)


def open_markets(series):
    data = get_json(config.KALSHI_API + "/markets",
                    {"series_ticker": series, "status": "open", "limit": 200})
    out = []
    for m in data.get("markets", []):
        b = bracket(m)
        if b is None:
            continue
        out.append({
            "ticker": m["ticker"],
            "event_ticker": m.get("event_ticker", ""),
            "date": event_date(m.get("event_ticker", "")),
            "bracket": b,
            "yes_bid": _cents(m, "yes_bid"),
            "yes_ask": _cents(m, "yes_ask"),
            "no_bid": _cents(m, "no_bid"),
            "no_ask": _cents(m, "no_ask"),
            "volume": m.get("volume") or m.get("volume_fp") or 0,
            "close_time": m.get("close_time", ""),
        })
    return out


def market(ticker):
    return get_json(config.KALSHI_API + "/markets/" + ticker).get("market", {})


def fee_per_contract(price_cents, contracts):
    p = price_cents / 100.0
    total = math.ceil(config.FEE_RATE * contracts * p * (1 - p) * 100) / 100.0
    return total / contracts


# --------------------------------------------------------------------------
# Forecast: ensemble members' daily high at the station
# --------------------------------------------------------------------------

def _climate_day_bounds(day, tz_name):
    """NWS climate days run midnight-to-midnight LOCAL STANDARD time, so during
    daylight saving the day is 1am-1am on the clock. Returns UTC bounds."""
    if ZoneInfo is None:
        start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
        return start, start + timedelta(days=1)
    tz = ZoneInfo(tz_name)
    noon = datetime(day.year, day.month, day.day, 12, tzinfo=tz)
    dst = noon.dst() or timedelta(0)
    std_offset = noon.utcoffset() - dst
    start_local_std = datetime(day.year, day.month, day.day)
    start_utc = (start_local_std - std_offset).replace(tzinfo=timezone.utc)
    return start_utc, start_utc + timedelta(days=1)


def ensemble_highs(city, days, kind="high"):
    """Return {date: [member daily highs (or lows) in F]} for the requested dates."""
    pick = max if kind == "high" else min
    params = {
        "latitude": city["lat"], "longitude": city["lon"],
        "hourly": "temperature_2m",
        "models": ",".join(config.ENSEMBLE_MODELS),
        "temperature_unit": "fahrenheit",
        "timezone": "GMT",
        "past_days": 1, "forecast_days": 4,
    }
    data = get_json(config.OPEN_METEO_ENSEMBLE, params)
    hourly = data.get("hourly", {})
    times = [datetime.strptime(t, "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
             for t in hourly.get("time", [])]
    members = [k for k in hourly if k.startswith("temperature_2m")]

    out = {}
    for d in days:
        start, end = _climate_day_bounds(d, city["tz"])
        idx = [i for i, t in enumerate(times) if start <= t < end]
        highs = []
        for k in members:
            vals = [hourly[k][i] for i in idx if hourly[k][i] is not None]
            # need most of the afternoon covered to trust a member's max
            if len(vals) >= 6:
                highs.append(pick(vals))
        out[d] = highs
    return out


def _hourly_extreme(city, days, pick, model):
    """Daily high (or low) per day from one hourly forecast model."""
    params = {"latitude": city["lat"], "longitude": city["lon"],
              "hourly": "temperature_2m", "temperature_unit": "fahrenheit",
              "timezone": "GMT", "past_days": 1, "forecast_days": 4}
    if model:
        params["models"] = model
    try:
        data = get_json(config.OPEN_METEO_FORECAST, params)
    except Exception:
        return {}
    hourly = data.get("hourly", {})
    key = next((k for k in hourly if k.startswith("temperature_2m")), None)
    if not key:
        return {}
    times = [datetime.strptime(t, "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
             for t in hourly.get("time", [])]
    out = {}
    for d in days:
        start, end = _climate_day_bounds(d, city["tz"])
        vals = [hourly[key][i] for i, t in enumerate(times)
                if start <= t < end and hourly[key][i] is not None]
        if len(vals) >= 18:
            out[d] = pick(vals)
    return out


def anchor_high(city, days, kind="high"):
    """Best single estimate of the day's high (or low) at the station.
    Blends Open-Meteo's best US model mix (HRRR for the next day or two, then GFS)
    with the National Blend of Models. On day one NBM ran 4-10F too cold in a few
    cities (Phoenix, Boston, DC), so when the two disagree by more than
    ANCHOR_MAX_GAP_F we trust the best-match mix alone."""
    pick = max if kind == "high" else min
    best = _hourly_extreme(city, days, pick, None)
    nbm = _hourly_extreme(city, days, pick, config.ANCHOR_MODEL)
    out = {}
    for d in days:
        b, n = best.get(d), nbm.get(d)
        if b is not None and n is not None:
            out[d] = (b + n) / 2 if abs(b - n) <= config.ANCHOR_MAX_GAP_F else b
        elif b is not None or n is not None:
            out[d] = b if b is not None else n
    return out


def centered(highs, center):
    """Keep the ensemble's spread (uncertainty) but move its middle to `center`.
    Raw ensembles sample every 3 hours and miss the afternoon peak, so they run cold."""
    if center is None or not highs:
        return highs
    shift = center - sum(highs) / len(highs)
    return [h + shift for h in highs]


# --------------------------------------------------------------------------
# Probability model
# --------------------------------------------------------------------------

def _phi(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def bracket_probability(highs, b, bias=0.0, spread=None):
    """Chance the official (whole-degree) high lands in bracket b.
    Each member is treated as a bell curve of width `spread` around its value."""
    if not highs:
        return None
    s = spread if spread is not None else config.SPREAD_F
    lo, hi = b
    lo_edge = -1e9 if lo is None else lo - 0.5
    hi_edge = 1e9 if hi is None else hi + 0.5
    total = 0.0
    for h in highs:
        m = h + bias
        total += _phi((hi_edge - m) / s) - _phi((lo_edge - m) / s)
    p = total / len(highs)
    return min(max(p, 0.001), 0.999)


def best_trade(prob, mkt, contracts):
    """Pick the better of buying YES or buying NO, after fees.
    Returns dict or None if neither clears the edge threshold."""
    options = []
    if mkt["yes_ask"]:
        options.append(("YES", mkt["yes_ask"], prob))
    no_ask = mkt["no_ask"]
    if not no_ask and mkt["yes_bid"]:
        no_ask = 100 - mkt["yes_bid"]
    if no_ask:
        options.append(("NO", no_ask, 1 - prob))
    best = None
    for side, price, p_win in options:
        if not (config.MIN_PRICE <= price <= config.MAX_PRICE):
            continue
        fee = fee_per_contract(price, contracts)
        edge = p_win - price / 100.0 - fee
        if edge > config.MAX_EDGE:
            continue  # too good to be true: almost always our model, not the market
        if edge >= config.MIN_EDGE and (best is None or edge > best["edge"]):
            best = {"side": side, "price": price, "p_win": p_win,
                    "fee": fee, "edge": edge}
    return best

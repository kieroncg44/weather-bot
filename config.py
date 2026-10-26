# =====================================================================
# SETTINGS FROZEN from Oct 26 to Nov 9, 2026. Judge this version only on
# trades logged after FREEZE_START. Change only to fix something broken.
# =====================================================================
FREEZE_START = "2026-10-26 19:00"   # UTC, matches the logged_at format

"""Settings for the weather bot. Edit these, not the other files."""

# Each Kalshi "highest temperature" series (and its matching "low" series), and the exact weather station it
# settles on (NWS Daily Climate Report). Lat/lon are the station itself.
CITIES = {
    "KXHIGHNY":    {"name": "New York", "low": "KXLOWTNYC",      "station": "KNYC", "lat": 40.7790, "lon": -73.9692,  "tz": "America/New_York"},
    "KXHIGHCHI":   {"name": "Chicago", "low": "KXLOWTCHI",       "station": "KMDW", "lat": 41.7868, "lon": -87.7522,  "tz": "America/Chicago"},
    "KXHIGHMIA":   {"name": "Miami", "low": "KXLOWTMIA",         "station": "KMIA", "lat": 25.7959, "lon": -80.2870,  "tz": "America/New_York"},
    "KXHIGHAUS":   {"name": "Austin", "low": "KXLOWTAUS",        "station": "KAUS", "lat": 30.1945, "lon": -97.6699,  "tz": "America/Chicago"},
    "KXHIGHLAX":   {"name": "Los Angeles", "low": "KXLOWTLAX",   "station": "KLAX", "lat": 33.9382, "lon": -118.3866, "tz": "America/Los_Angeles"},
    "KXHIGHDEN":   {"name": "Denver", "low": "KXLOWTDEN",        "station": "KDEN", "lat": 39.8466, "lon": -104.6562, "tz": "America/Denver"},
    "KXHIGHPHIL":  {"name": "Philadelphia", "low": "KXLOWTPHIL",  "station": "KPHL", "lat": 39.8721, "lon": -75.2407,  "tz": "America/New_York"},
    "KXHIGHTPHX":  {"name": "Phoenix", "low": "KXLOWTPHX",       "station": "KPHX", "lat": 33.4343, "lon": -112.0116, "tz": "America/Phoenix"},
    "KXHIGHTHOU":  {"name": "Houston", "low": "KXLOWTHOU",       "station": "KHOU", "lat": 29.6454, "lon": -95.2789,  "tz": "America/Chicago"},
    "KXHIGHTDAL":  {"name": "Dallas", "low": "KXLOWTDAL",        "station": "KDFW", "lat": 32.8998, "lon": -97.0403,  "tz": "America/Chicago"},
    "KXHIGHTSATX": {"name": "San Antonio", "low": "KXLOWTSATX",   "station": "KSAT", "lat": 29.5337, "lon": -98.4698,  "tz": "America/Chicago"},
    "KXHIGHTMIN":  {"name": "Minneapolis", "low": "KXLOWTMIN",   "station": "KMSP", "lat": 44.8848, "lon": -93.2223,  "tz": "America/Chicago"},
    "KXHIGHTOKC":  {"name": "Oklahoma City", "low": "KXLOWTOKC", "station": "KOKC", "lat": 35.3931, "lon": -97.6007,  "tz": "America/Chicago"},
    "KXHIGHTSFO":  {"name": "San Francisco", "low": "KXLOWTSFO", "station": "KSFO", "lat": 37.6190, "lon": -122.3749, "tz": "America/Los_Angeles"},
    "KXHIGHTDC":   {"name": "Washington DC", "low": "KXLOWTDC", "station": "KDCA", "lat": 38.8512, "lon": -77.0402,  "tz": "America/New_York"},
    "KXHIGHTBOS":  {"name": "Boston", "low": "KXLOWTBOS",        "station": "KBOS", "lat": 42.3656, "lon": -71.0096,  "tz": "America/New_York"},
    "KXHIGHTSEA":  {"name": "Seattle", "low": "KXLOWTSEA",       "station": "KSEA", "lat": 47.4502, "lon": -122.3088, "tz": "America/Los_Angeles"},
    "KXHIGHTLV":   {"name": "Las Vegas", "low": "KXLOWTLV",     "station": "KLAS", "lat": 36.0840, "lon": -115.1537, "tz": "America/Los_Angeles"},
    "KXHIGHTATL":  {"name": "Atlanta", "low": "KXLOWTATL",       "station": "KATL", "lat": 33.6407, "lon": -84.4277,  "tz": "America/New_York"},
    "KXHIGHTNOLA": {"name": "New Orleans", "low": "KXLOWTNOLA",   "station": "KMSY", "lat": 29.9934, "lon": -90.2580,  "tz": "America/Chicago"},
}

# Forecast models pulled from Open-Meteo's free ensemble API (no key needed).
# Each model gives 30-50 slightly different runs ("members") of the weather.
ENSEMBLE_MODELS = ["gfs_seamless", "ecmwf_ifs025", "icon_seamless"]

# Ensembles are known to be over-confident. Each member is blurred by this
# many degrees F before counting. Bigger = more humble. Tune later from results.
SPREAD_F = 0.8   # was 1.8: capped any bracket at 42%, far wider than real errors (~2.1F)

# Per-city warm/cold correction in degrees F (+ means the model runs cold).
# Leave at 0 until report.py has enough settled days to estimate it.
BIAS_F = {}

# Default warm correction for daily HIGHS (forecasts ran ~1F cold Oct 22-25;
# we correct half of that until there's more data).
HIGH_BIAS_F = 0.5

# Only paper-trade when our probability beats the price by at least this much
# AFTER fees. 0.06 = 6 cents per $1 contract.
MIN_EDGE = 0.06

# How much to lean on the market's own price (0 = ignore market, 1 = copy it).
# 0.5 means a trade needs the model to disagree with the crowd by a wide margin.
MARKET_WEIGHT = 0.5

# Ignore "edges" bigger than this. A 30-cent edge on a busy market almost
# always means our model is off, not that traders are leaving free money.
MAX_EDGE = 0.20

# Single best hourly forecast used to set the CENTER of the forecast.
# The ensemble then only supplies the uncertainty around it.
ANCHOR_MODEL = "ncep_nbm_conus"

# If NBM and the best-match model disagree by more than this, ignore NBM.
ANCHOR_MAX_GAP_F = 3.0

# Skip contracts priced outside this range (cents). Very cheap/expensive ones
# are where models are least reliable and fees bite hardest relative to profit.
MIN_PRICE = 5
MAX_PRICE = 92

# Paper trade size: contracts per signal (each pays $1 if right).
PAPER_CONTRACTS = 10

# Kalshi taker fee: ceil(rate * contracts * price * (1 - price)) dollars.
FEE_RATE = 0.07

KALSHI_API = "https://api.elections.kalshi.com/trade-api/v2"
OPEN_METEO_FORECAST = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_ENSEMBLE = "https://ensemble-api.open-meteo.com/v1/ensemble"
USER_AGENT = "kieron-weather-bot/0.1"

# After this local hour, skip TODAY's markets. Late in the day the market can
# see actual thermometer readings and our forecast-only model can't, so any
# "edge" it finds then is probably fake.
SAME_DAY_CUTOFF_HOUR = 11

# Daily LOW markets: only trade future days. The low is usually set around
# dawn, so by morning traders can already see today's answer.
TRADE_LOWS = False   # off Oct 24: lows won 30% vs 68% expected

# Sit out a city-day when the forecast runs span more than this many degrees
# (usually a front or storm whose timing the models can't agree on).
MAX_FORECAST_RANGE_F = 12

# Need at least this many ensemble members to trust a probability.
MIN_MEMBERS = 20

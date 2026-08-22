import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo


# =========================================================
# BEÁLLÍTÁSOK
# =========================================================

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]

SYMBOL = "SOLUSDT"

BINANCE_FUTURES = "https://fapi.binance.com"
BINANCE_SPOT = "https://api.binance.com"


# =========================================================
# SEGÉDFÜGGVÉNYEK
# =========================================================

def get_json(url, params=None, timeout=15):
    response = requests.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()


def ema(values, period):
    """
    Exponential Moving Average
    """
    if len(values) < period:
        return None

    multiplier = 2 / (period + 1)
    result = sum(values[:period]) / period

    for price in values[period:]:
        result = (price - result) * multiplier + result

    return result


def ema_series(values, period):
    if len(values) < period:
        return []

    multiplier = 2 / (period + 1)
    current = sum(values[:period]) / period

    results = [current]

    for price in values[period:]:
        current = (price - current) * multiplier + current
        results.append(current)

    return results


def calculate_rsi(values, period=14):
    """
    RSI Wilder-módszerrel
    """
    if len(values) <= period:
        return None

    changes = [
        values[i] - values[i - 1]
        for i in range(1, len(values))
    ]

    gains = [max(x, 0) for x in changes]
    losses = [abs(min(x, 0)) for x in changes]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(changes)):
        avg_gain = (
            (avg_gain * (period - 1)) + gains[i]
        ) / period

        avg_loss = (
            (avg_loss * (period - 1)) + losses[i]
        ) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss

    return 100 - (100 / (1 + rs))


def calculate_macd(values):
    """
    MACD 12 / 26 / 9
    """

    ema12 = ema_series(values, 12)
    ema26 = ema_series(values, 26)

    if not ema12 or not ema26:
        return None, None, None

    # A két EMA sor hosszának összehangolása
    difference = len(ema12) - len(ema26)
    ema12 = ema12[difference:]

    macd_line = [
        a - b
        for a, b in zip(ema12, ema26)
    ]

    signal_series = ema_series(macd_line, 9)

    if not signal_series:
        return None, None, None

    macd_value = macd_line[-1]
    signal_value = signal_series[-1]
    histogram = macd_value - signal_value

    return macd_value, signal_value, histogram


def pct_change(old, new):
    if old == 0:
        return None

    return ((new - old) / old) * 100


def fmt(value, decimals=2):
    if value is None:
        return "nincs adat"

    return f"{value:.{decimals}f}"


# =========================================================
# 1. SOL 24H PIACI ADAT
# =========================================================

ticker = get_json(
    f"{BINANCE_SPOT}/api/v3/ticker/24hr",
    {"symbol": SYMBOL}
)

sol_price = float(ticker["lastPrice"])
sol_change_24h = float(ticker["priceChangePercent"])
sol_high_24h = float(ticker["highPrice"])
sol_low_24h = float(ticker["lowPrice"])
sol_volume = float(ticker["quoteVolume"])


# =========================================================
# 2. 4H GYERTYÁK
# =========================================================

klines = get_json(
    f"{BINANCE_FUTURES}/fapi/v1/klines",
    {
        "symbol": SYMBOL,
        "interval": "4h",
        "limit": 220
    }
)

# Az utolsó gyertya még nyitott lehet,
# ezért nem használjuk az indikátorokhoz.
closed_klines = klines[:-1]

opens = [float(x[1]) for x in closed_klines]
highs = [float(x[2]) for x in closed_klines]
lows = [float(x[3]) for x in closed_klines]
closes = [float(x[4]) for x in closed_klines]
volumes = [float(x[5]) for x in closed_klines]


# =========================================================
# 3. TECHNIKAI INDIKÁTOROK
# =========================================================

rsi14 = calculate_rsi(closes, 14)

ema20 = ema(closes, 20)
ema50 = ema(closes, 50)
ema200 = ema(closes, 200)

macd, macd_signal, macd_histogram = calculate_macd(closes)


# =========================================================
# 4. TÁMASZ / ELLENÁLLÁS
# =========================================================

# Utolsó 20 lezárt 4h gyertya = kb. 3,3 nap

recent_highs = highs[-20:]
recent_lows = lows[-20:]

resistance = max(recent_highs)
support = min(recent_lows)


# =========================================================
# 5. VOLUMEN MOMENTUM
# =========================================================

recent_volume = sum(volumes[-6:]) / 6
previous_volume = sum(volumes[-12:-6]) / 6

volume_change = pct_change(
    previous_volume,
    recent_volume
)


# =========================================================
# 6. FUNDING RATE
# =========================================================

try:
    premium = get_json(
        f"{BINANCE_FUTURES}/fapi/v1/premiumIndex",
        {"symbol": SYMBOL}
    )

    funding_rate = (
        float(premium["lastFundingRate"]) * 100
    )

except Exception as e:
    print("Funding rate hiba:", e)
    funding_rate = None


# =========================================================
# 7. OPEN INTEREST
# =========================================================

try:
    oi_history = get_json(
        f"{BINANCE_FUTURES}/futures/data/openInterestHist",
        {
            "symbol": SYMBOL,
            "period": "1d",
            "limit": 2
        }
    )

    if len(oi_history) >= 2:

        old_oi = float(
            oi_history[-2]["sumOpenInterestValue"]
        )

        new_oi = float(
            oi_history[-1]["sumOpenInterestValue"]
        )

        oi_change = pct_change(
            old_oi,
            new_oi
        )

    else:
        oi_change = None

except Exception as e:
    print("Open interest hiba:", e)
    oi_change = None


# =========================================================
# 8. FEAR & GREED
# =========================================================

try:
    fear_data = get_json(
        "https://api.alternative.me/fng/",
        {"limit": 1}
    )

    fear_greed = int(
        fear_data["data"][0]["value"]
    )

    fear_class = fear_data["data"][0][
        "value_classification"
    ]

except Exception as e:
    print("Fear & Greed hiba:", e)

    fear_greed = None
    fear_class = "nincs adat"


# =========================================================
# 9. BTC DOMINANCIA
# =========================================================

try:
    global_data = get_json(
        "https://api.alternative.me/v2/global/"
    )

    btc_dominance = float(
        global_data["data"][
            "bitcoin_percentage_of_market_cap"
        ]
    )

except Exception as e:
    print("BTC dominance hiba:", e)
    btc_dominance = None


# =========================================================
# 10. BTC 24H MOZGÁS
# =========================================================

try:
    btc_ticker = get_json(
        f"{BINANCE_SPOT}/api/v3/ticker/24hr",
        {"symbol": "BTCUSDT"}
    )

    btc_change = float(
        btc_ticker["priceChangePercent"]
    )

except Exception as e:
    print("BTC hiba:", e)
    btc_change = None


# =========================================================
# 11. TREND OBJEKTÍV BESOROLÁSA
# =========================================================

if (
    ema20
    and ema50
    and ema200
    and sol_price > ema20 > ema50 > ema200
):

    technical_trend = "BULLISH"

elif (
    ema20
    and ema50
    and ema200
    and sol_price < ema20 < ema50 < ema200
):

    technical_trend = "BEARISH"

else:

    technical_trend = "MIXED / SIDEWAYS"


# =========================================================
# 12. ADATCSOMAG AZ AI-NAK
# =========================================================

budapest_time = datetime.now(
    ZoneInfo("Europe/Budapest")
)

date_string = budapest_time.strftime(
    "%Y-%m-%d %H:%M"
)


prompt = f"""
Te professzionális kriptopiaci elemző és swing trader vagy.

Az alábbi adatok VALÓS API adatok.

TILOS olyan számot, hírt vagy eseményt kitalálnod,
amely nincs az adatok között.

Dátum:
{date_string}

SOLANA PIACI ADATOK

Ár:
{sol_price:.2f} USD

24h változás:
{sol_change_24h:.2f} %

24h maximum:
{sol_high_24h:.2f} USD

24h minimum:
{sol_low_24h:.2f} USD

24h volumen:
{sol_volume:,.0f} USD


TECHNIKAI ADATOK – 4H

Trend:
{technical_trend}

RSI 14:
{fmt(rsi14)}

EMA20:
{fmt(ema20)}

EMA50:
{fmt(ema50)}

EMA200:
{fmt(ema200)}

MACD:
{fmt(macd, 4)}

MACD signal:
{fmt(macd_signal, 4)}

MACD histogram:
{fmt(macd_histogram, 4)}

Támasz:
{support:.2f} USD

Ellenállás:
{resistance:.2f} USD

4H volumen változás:
{fmt(volume_change)} %


DERIVATÍV ADATOK

Funding rate:
{fmt(funding_rate, 4)} %

Open Interest 24h változás:
{fmt(oi_change)} %


PIACI KÖRNYEZET

BTC 24h:
{fmt(btc_change)} %

BTC dominancia:
{fmt(btc_dominance)} %

Fear & Greed:
{fear_greed if fear_greed is not None else "nincs adat"}
({fear_class})


Készíts maximum 2600 karakteres magyar elemzést.

Pontosan ezt a struktúrát használd:

📊 PIACI HELYZET
Maximum 3 rövid sor.

📈 TECHNIKAI KÉP
RSI, EMA-k, MACD, momentum.
Maximum 5 rövid sor.

🎯 KULCSSZINTEK
Támasz és ellenállás.
Írd le röviden, mi történne kitörés vagy letörés esetén.

🌍 PIACI HANGULAT
BTC, BTC dominancia, Fear & Greed,
funding és OI alapján maximum 4 sor.

🔮 FORGATÓKÖNYVEK
🟢 Bullish: 2 rövid mondat.
🔴 Bearish: 2 rövid mondat.

⚠️ KOCKÁZAT
Maximum 3 rövid pont.

🧭 NAPI BIAS
Csak egy ezek közül:

ERŐSEN BULLISH
BULLISH
SEMLEGES
BEARISH
ERŐSEN BEARISH

Utána egyetlen rövid mondat:
"Ma ezt figyelném: ..."

Ne használj hosszú bevezetést.
Ne ismételd az adatokat feleslegesen.
Ne találj ki híreket.
"""


# =========================================================
# 13. GROQ GPT-OSS
# =========================================================

response = requests.post(
    "https://api.groq.com/openai/v1/chat/completions",
    headers={
        "Authorization":
            f"Bearer {GROQ_API_KEY}",

        "Content-Type":
            "application/json"
    },
    json={
        "model": "openai/gpt-oss-120b",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    },
    timeout=60
)

print("GROQ STATUS:", response.status_code)

response.raise_for_status()

data = response.json()

analysis = (
    data["choices"][0]
    ["message"]["content"]
)


# =========================================================
# 14. TELEGRAM ÜZENET
# =========================================================

message = f"""📈 SOL DAILY

🕒 {date_string}

💰 {sol_price:.2f} USD
24h: {sol_change_24h:+.2f}%

High: {sol_high_24h:.2f}
Low: {sol_low_24h:.2f}

{analysis}
"""


# =========================================================
# TELEGRAM 4096 LIMIT
# =========================================================

TELEGRAM_LIMIT = 4096

if len(message) > 4000:

    print(
        "FIGYELEM: Telegram üzenet túl hosszú:",
        len(message)
    )

    message = (
        message[:3950]
        + "\n\n⚠️ Riport automatikusan rövidítve."
    )


# =========================================================
# 15. TELEGRAM KÜLDÉS
# =========================================================

telegram_response = requests.post(
    f"https://api.telegram.org/"
    f"bot{TELEGRAM_TOKEN}/sendMessage",

    json={
        "chat_id":
            TELEGRAM_CHAT_ID,

        "text":
            message
    },

    timeout=30
)

telegram_response.raise_for_status()

print(
    "Telegram karakter:",
    len(message)
)

print(
    "TELEGRAM RESPONSE:",
    telegram_response.text
)

print("KÉSZ")

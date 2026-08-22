import os
import time
import requests
from datetime import datetime
from zoneinfo import ZoneInfo


# =========================================================
# BEÁLLÍTÁSOK
# =========================================================

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]

COINGECKO = "https://api.coingecko.com/api/v3"

HEADERS = {
    "User-Agent": "SOL-Daily-Market-Analysis/1.0"
}


# =========================================================
# BIZTONSÁGOS API LEKÉRÉS
# =========================================================

def get_json(url, params=None, retries=3, timeout=30):
    last_error = None

    for attempt in range(retries):
        try:
            response = requests.get(
                url,
                params=params,
                headers=HEADERS,
                timeout=timeout
            )

            print(
                f"GET {response.url} -> "
                f"{response.status_code}"
            )

            response.raise_for_status()
            return response.json()

        except Exception as e:
            last_error = e
            print(
                f"API hiba, próbálkozás "
                f"{attempt + 1}/{retries}: {e}"
            )

            if attempt < retries - 1:
                time.sleep(5)

    raise last_error


# =========================================================
# SEGÉDFÜGGVÉNYEK
# =========================================================

def pct_change(old, new):
    if old is None or old == 0:
        return None

    return ((new - old) / old) * 100


def fmt(value, decimals=2):
    if value is None:
        return "nincs adat"

    return f"{value:.{decimals}f}"


def ema(values, period):
    if len(values) < period:
        return None

    multiplier = 2 / (period + 1)

    current = sum(values[:period]) / period

    for price in values[period:]:
        current = (
            (price - current) * multiplier
            + current
        )

    return current


def ema_series(values, period):
    if len(values) < period:
        return []

    multiplier = 2 / (period + 1)

    current = sum(values[:period]) / period

    results = [current]

    for price in values[period:]:
        current = (
            (price - current) * multiplier
            + current
        )

        results.append(current)

    return results


def calculate_rsi(values, period=14):
    if len(values) <= period:
        return None

    changes = [
        values[i] - values[i - 1]
        for i in range(1, len(values))
    ]

    gains = [
        max(change, 0)
        for change in changes
    ]

    losses = [
        abs(min(change, 0))
        for change in changes
    ]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(changes)):
        avg_gain = (
            avg_gain * (period - 1)
            + gains[i]
        ) / period

        avg_loss = (
            avg_loss * (period - 1)
            + losses[i]
        ) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss

    return 100 - (100 / (1 + rs))


def calculate_macd(values):
    ema12 = ema_series(values, 12)
    ema26 = ema_series(values, 26)

    if not ema12 or not ema26:
        return None, None, None

    difference = len(ema12) - len(ema26)

    if difference > 0:
        ema12 = ema12[difference:]

    macd_line = [
        fast - slow
        for fast, slow in zip(ema12, ema26)
    ]

    signal_series = ema_series(macd_line, 9)

    if not signal_series:
        return None, None, None

    macd_value = macd_line[-1]
    signal_value = signal_series[-1]

    histogram = macd_value - signal_value

    return (
        macd_value,
        signal_value,
        histogram
    )


# =========================================================
# COINGECKO HISTORIKUS ADAT
# =========================================================

def get_market_chart(coin_id, days):
    return get_json(
        f"{COINGECKO}/coins/{coin_id}/market_chart",
        {
            "vs_currency": "usd",
            "days": days
        }
    )


print("SOL piaci adatok lekérése...")

sol_data = get_market_chart(
    "solana",
    60
)


# =========================================================
# SOL ÓRÁS ADATOK
# =========================================================

price_points = sol_data["prices"]
volume_points = sol_data["total_volumes"]

hourly_prices = [
    float(point[1])
    for point in price_points
]

hourly_volumes = [
    float(point[1])
    for point in volume_points
]


if len(hourly_prices) < 250:
    raise RuntimeError(
        "Nincs elegendő CoinGecko történelmi adat."
    )


# =========================================================
# AKTUÁLIS SOL ADAT
# =========================================================

sol_price = hourly_prices[-1]

# kb. 24 órával ezelőtti adat
price_24h_ago = hourly_prices[-25]

sol_change_24h = pct_change(
    price_24h_ago,
    sol_price
)

last_24_prices = hourly_prices[-24:]

sol_high_24h = max(last_24_prices)
sol_low_24h = min(last_24_prices)

sol_volume_24h = hourly_volumes[-1]


# =========================================================
# VOLUMEN VÁLTOZÁS
# =========================================================

recent_volumes = hourly_volumes[-24:]
previous_volumes = hourly_volumes[-48:-24]

if recent_volumes and previous_volumes:

    recent_volume_avg = (
        sum(recent_volumes)
        / len(recent_volumes)
    )

    previous_volume_avg = (
        sum(previous_volumes)
        / len(previous_volumes)
    )

    volume_change = pct_change(
        previous_volume_avg,
        recent_volume_avg
    )

else:
    volume_change = None


# =========================================================
# KB. 4 ÓRÁS PRICE SERIES
#
# CoinGecko órás adatából minden 4. pontot használunk.
# Ez NEM exchange OHLC gyertya,
# hanem 4 óránként mintavett piaci ár.
# =========================================================

prices_4h = hourly_prices[::4]


if len(prices_4h) < 205:
    raise RuntimeError(
        "Nincs elég 4 órás adat EMA200 számításhoz."
    )


# =========================================================
# TECHNIKAI INDIKÁTOROK
# =========================================================

rsi14 = calculate_rsi(
    prices_4h,
    14
)

ema20 = ema(
    prices_4h,
    20
)

ema50 = ema(
    prices_4h,
    50
)

ema200 = ema(
    prices_4h,
    200
)

macd_value, macd_signal, macd_hist = (
    calculate_macd(prices_4h)
)


# =========================================================
# TÁMASZ / ELLENÁLLÁS
#
# Utolsó 30 db 4h adatpont ~= 5 nap
# =========================================================

recent_prices = prices_4h[-30:]

support = min(recent_prices)
resistance = max(recent_prices)


# =========================================================
# TREND
# =========================================================

if (
    ema20 is not None
    and ema50 is not None
    and ema200 is not None
    and sol_price > ema20 > ema50 > ema200
):
    technical_trend = "BULLISH"

elif (
    ema20 is not None
    and ema50 is not None
    and ema200 is not None
    and sol_price < ema20 < ema50 < ema200
):
    technical_trend = "BEARISH"

else:
    technical_trend = "MIXED / SIDEWAYS"


# =========================================================
# BTC
# =========================================================

print("BTC adatok lekérése...")

try:
    btc_data = get_market_chart(
        "bitcoin",
        2
    )

    btc_prices = [
        float(point[1])
        for point in btc_data["prices"]
    ]

    btc_price = btc_prices[-1]

    btc_24h_ago = btc_prices[-25]

    btc_change_24h = pct_change(
        btc_24h_ago,
        btc_price
    )

except Exception as e:
    print("BTC adat hiba:", e)

    btc_price = None
    btc_change_24h = None


# =========================================================
# FEAR & GREED
# =========================================================

print("Fear & Greed lekérése...")

try:
    fear_data = get_json(
        "https://api.alternative.me/fng/",
        {
            "limit": 1,
            "format": "json"
        }
    )

    fear_greed = int(
        fear_data["data"][0]["value"]
    )

    fear_class = (
        fear_data["data"][0]
        ["value_classification"]
    )

except Exception as e:
    print("Fear & Greed hiba:", e)

    fear_greed = None
    fear_class = "nincs adat"


# =========================================================
# BTC DOMINANCIA
# =========================================================

print("BTC dominancia lekérése...")

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
# DÁTUM
# =========================================================

local_time = datetime.now(
    ZoneInfo("Europe/Budapest")
)

date_string = local_time.strftime(
    "%Y-%m-%d %H:%M"
)


# =========================================================
# GROQ PROMPT
# =========================================================

prompt = f"""
Te professzionális kriptovaluta-piaci elemző és
swing trader vagy.

Az alábbi adatok külső API-kból származó
valós piaci adatok.

FONTOS:
TILOS olyan számot, hírt, whale aktivitást,
funding rate-et vagy open interest adatot
kitalálnod, amely nincs megadva.

Dátum:
{date_string}

SOLANA

Aktuális ár:
{sol_price:.2f} USD

24h változás:
{fmt(sol_change_24h)} %

24h maximum:
{sol_high_24h:.2f} USD

24h minimum:
{sol_low_24h:.2f} USD

24h volumen:
{sol_volume_24h:,.0f} USD

Volumen trend:
{fmt(volume_change)} %


TECHNIKAI ADATOK

Idősík:
kb. 4H mintavételezett CoinGecko árfolyam

Trend:
{technical_trend}

RSI14:
{fmt(rsi14)}

EMA20:
{fmt(ema20)}

EMA50:
{fmt(ema50)}

EMA200:
{fmt(ema200)}

MACD:
{fmt(macd_value, 4)}

MACD signal:
{fmt(macd_signal, 4)}

MACD histogram:
{fmt(macd_hist, 4)}

Közeli támasz:
{support:.2f} USD

Közeli ellenállás:
{resistance:.2f} USD


PIACI KÖRNYEZET

BTC ár:
{fmt(btc_price)} USD

BTC 24h változás:
{fmt(btc_change_24h)} %

BTC dominancia:
{fmt(btc_dominance)} %

Fear & Greed:
{fear_greed if fear_greed is not None else "nincs adat"}

Besorolás:
{fear_class}


Készíts maximum 2600 karakteres,
tömör magyar piaci elemzést.

Pontosan ezt a szerkezetet használd:

📊 PIACI HELYZET
Maximum 3 rövid sor.
Értékeld az árat, 24h mozgást és volument.

📈 TECHNIKAI KÉP
Maximum 5 rövid sor.
Értékeld RSI, EMA20/50/200 és MACD alapján
a trendet és momentumot.

🎯 KULCSSZINTEK
Írd le a támaszt és ellenállást.
Maximum 3 rövid sor.
Mondd meg, mit jelentene egy kitörés vagy letörés.

🌍 PIACI HANGULAT
Maximum 4 rövid sor.
BTC mozgás, BTC dominancia és
Fear & Greed alapján.

🔮 FORGATÓKÖNYVEK
🟢 Bullish:
maximum 2 rövid mondat.

🔴 Bearish:
maximum 2 rövid mondat.

24-48h:
1 rövid mondat.

1 hét:
1 rövid mondat.

⚠️ KOCKÁZAT
Maximum 3 rövid pont.

🧭 NAPI BIAS
Pontosan egyet válassz:

ERŐSEN BULLISH
BULLISH
SEMLEGES
BEARISH
ERŐSEN BEARISH

Végül:
Ma ezt figyelném: ...

Ne ismételd feleslegesen ugyanazokat a számokat.
Ne találj ki híreket.
Ne találj ki derivatív adatokat.
Legyél objektív.
"""


# =========================================================
# GROQ
# =========================================================

print("GPT-OSS elemzés indítása...")

groq_response = requests.post(
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
    timeout=90
)

print(
    "GROQ STATUS:",
    groq_response.status_code
)

if not groq_response.ok:
    print(
        "GROQ ERROR:",
        groq_response.text
    )

groq_response.raise_for_status()

groq_data = groq_response.json()

analysis = (
    groq_data["choices"][0]
    ["message"]["content"]
)


# =========================================================
# TELEGRAM ÜZENET
# =========================================================

message = f"""📈 SOL DAILY

🕒 {date_string}

💰 SOL: {sol_price:.2f} USD
📊 24h: {sol_change_24h:+.2f}%

⬆️ High: {sol_high_24h:.2f}
⬇️ Low: {sol_low_24h:.2f}

{analysis}
"""


# =========================================================
# TELEGRAM LIMIT
# =========================================================

TELEGRAM_SAFE_LIMIT = 4000

if len(message) > TELEGRAM_SAFE_LIMIT:

    print(
        "FIGYELEM: túl hosszú Telegram üzenet:",
        len(message)
    )

    message = (
        message[:3920]
        + "\n\n⚠️ Riport rövidítve."
    )


# =========================================================
# TELEGRAM KÜLDÉS
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

print(
    "TELEGRAM STATUS:",
    telegram_response.status_code
)

if not telegram_response.ok:
    print(
        "TELEGRAM ERROR:",
        telegram_response.text
    )

telegram_response.raise_for_status()

print(
    "Telegram karakter:",
    len(message)
)

print("✅ KÉSZ – Telegram elküldve")

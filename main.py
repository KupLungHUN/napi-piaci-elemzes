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
    "User-Agent": "SOL-Daily-Market-Analysis/3.0"
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

    return macd_value, signal_value, histogram


# =========================================================
# COINGECKO HISTORIKUS SOL ADAT
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

if len(hourly_prices) < 800:
    raise RuntimeError(
        "Nincs elegendő CoinGecko történelmi SOL adat."
    )


# =========================================================
# AKTUÁLIS SOL ADAT
# =========================================================

sol_price = hourly_prices[-1]

price_24h_ago = hourly_prices[-25]
price_7d_ago = hourly_prices[-(24 * 7 + 1)]
price_30d_ago = hourly_prices[-(24 * 30 + 1)]

sol_change_24h = pct_change(
    price_24h_ago,
    sol_price
)

sol_change_7d = pct_change(
    price_7d_ago,
    sol_price
)

sol_change_30d = pct_change(
    price_30d_ago,
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
# KB. 4H TECHNIKAI ADATSOR
# =========================================================

prices_4h = hourly_prices[::4]

if len(prices_4h) < 205:
    raise RuntimeError(
        "Nincs elegendő 4H adat EMA200 számításhoz."
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
# SUPPORT / RESISTANCE
# =========================================================

recent_prices = prices_4h[-30:]

support = min(recent_prices)
resistance = max(recent_prices)

support_distance = (
    ((sol_price - support) / sol_price) * 100
)

resistance_distance = (
    ((resistance - sol_price) / sol_price) * 100
)


# =========================================================
# TECHNIKAI TREND
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
# BTC ADAT
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
# SOL / BTC RELATÍV ERŐ
# =========================================================

sol_vs_btc_24h = None

if btc_change_24h is not None:
    sol_vs_btc_24h = (
        sol_change_24h
        - btc_change_24h
    )


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
# MARKET SCORE 0-100
# =========================================================

score = 50


# --- ÁR EMA20 FELETT / ALATT ---

if (
    ema20 is not None
    and sol_price > ema20
):
    score += 5
else:
    score -= 5


# --- EMA20 / EMA50 ---

if (
    ema20 is not None
    and ema50 is not None
):
    if ema20 > ema50:
        score += 7
    else:
        score -= 7


# --- EMA50 / EMA200 ---

if (
    ema50 is not None
    and ema200 is not None
):
    if ema50 > ema200:
        score += 8
    else:
        score -= 8


# --- RSI ---

if rsi14 is not None:

    if 50 <= rsi14 <= 65:
        score += 7

    elif 40 <= rsi14 < 50:
        score += 1

    elif 65 < rsi14 <= 70:
        score += 3

    elif rsi14 > 70:
        score -= 3

    elif rsi14 < 40:
        score -= 7


# --- MACD ---

if macd_hist is not None:

    if macd_hist > 0:
        score += 7
    else:
        score -= 7


# --- VOLUMEN ---

if volume_change is not None:

    if volume_change > 10:
        score += 5

    elif volume_change < -10:
        score -= 5


# --- SOL/BTC RELATÍV ERŐ ---

if sol_vs_btc_24h is not None:

    if sol_vs_btc_24h > 1:
        score += 6

    elif sol_vs_btc_24h < -1:
        score -= 6


# --- 7 NAPOS MOMENTUM ---

if sol_change_7d is not None:

    if sol_change_7d > 5:
        score += 5

    elif sol_change_7d < -5:
        score -= 5


# --- 30 NAPOS TREND ---

if sol_change_30d is not None:

    if sol_change_30d > 10:
        score += 5

    elif sol_change_30d < -10:
        score -= 5


# --- FEAR & GREED ---

if fear_greed is not None:

    if 45 <= fear_greed <= 70:
        score += 3

    elif fear_greed >= 80:
        score -= 3

    elif fear_greed <= 20:
        score -= 3


# --- SCORE 0-100 KÖZÉ SZORÍTÁSA ---

score = max(
    0,
    min(100, score)
)


# =========================================================
# OBJEKTÍV BIAS
# =========================================================

if score >= 75:
    calculated_bias = "ERŐSEN BULLISH"

elif score >= 60:
    calculated_bias = "BULLISH"

elif score >= 40:
    calculated_bias = "SEMLEGES"

elif score >= 25:
    calculated_bias = "BEARISH"

else:
    calculated_bias = "ERŐSEN BEARISH"


print("SOL 24h:", fmt(sol_change_24h), "%")
print("SOL 7d:", fmt(sol_change_7d), "%")
print("SOL 30d:", fmt(sol_change_30d), "%")
print("SOL vs BTC:", fmt(sol_vs_btc_24h), "%")
print("RSI:", fmt(rsi14))
print("MARKET SCORE:", score)
print("CALCULATED BIAS:", calculated_bias)


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
Te professzionális kriptovaluta-piaci elemző,
swing trader és kockázatelemző vagy.

Az alábbi adatok külső API-kból származó
valós piaci adatok.

TILOS:
- hírt kitalálni
- whale aktivitást kitalálni
- funding rate-et kitalálni
- open interestet kitalálni
- hiányzó indikátort kitalálni
- nem létező eseményt tényként közölni

Az elemzés célja nem a biztos jóslás,
hanem a jelenlegi piaci struktúra
objektív értékelése.

DÁTUM
{date_string}


SOLANA PIACI ADATOK

Aktuális ár:
{sol_price:.2f} USD

24h:
{fmt(sol_change_24h)} %

7 nap:
{fmt(sol_change_7d)} %

30 nap:
{fmt(sol_change_30d)} %

24h maximum:
{sol_high_24h:.2f} USD

24h minimum:
{sol_low_24h:.2f} USD

24h volumen:
{sol_volume_24h:,.0f} USD

Volumen változás:
{fmt(volume_change)} %


TECHNIKAI ADATOK

Technikai trend:
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

Támasz:
{support:.2f} USD

Támasz távolsága:
{support_distance:.2f} %

Ellenállás:
{resistance:.2f} USD

Ellenállás távolsága:
{resistance_distance:.2f} %


PIACI KÖRNYEZET

BTC ár:
{fmt(btc_price)} USD

BTC 24h:
{fmt(btc_change_24h)} %

SOL relatív erő BTC-hez képest:
{fmt(sol_vs_btc_24h)} %

BTC dominancia:
{fmt(btc_dominance)} %

Fear & Greed:
{fear_greed if fear_greed is not None else "nincs adat"}

Fear & Greed besorolás:
{fear_class}


OBJEKTÍV MODELL

Market score:
{score}/100

Python által számított bias:
{calculated_bias}


Készíts maximum 3200 karakteres,
professzionális magyar napi SOL elemzést.

Ne ismételd feleslegesen ugyanazokat a számokat.

Pontosan ezt a struktúrát használd:


📊 PIACI HELYZET

Maximum 4 rövid sor.

Értékeld:
- 24h mozgás
- 7 napos momentum
- 30 napos trend
- volumen


📈 TECHNIKAI KÉP

Maximum 6 rövid sor.

Értékeld:
- RSI
- EMA20 / EMA50 / EMA200 struktúra
- MACD
- momentum
- trend minősége

Ne csak felsorold az indikátorokat,
hanem mondd el röviden, mit jelentenek együtt.


⚖️ RELATÍV ERŐ

Maximum 3 rövid sor.

Értékeld:
SOL mennyire teljesít jobban vagy rosszabbul,
mint BTC.

Írd le, hogy ez támogatja vagy gyengíti-e
a SOL setupot.


🎯 KULCSSZINTEK

Írd le:
- legfontosabb támasz
- legfontosabb ellenállás

Majd:

Kitörési feltétel:
maximum 1 rövid mondat.

Letörési feltétel:
maximum 1 rövid mondat.


🌍 PIACI HANGULAT

Maximum 4 rövid sor.

Értékeld:
- BTC mozgását
- BTC dominanciát
- Fear & Greed állapotát
- ezek altcoinokra gyakorolt hatását


🔮 24–48H OUTLOOK

🟢 BULL CASE
Maximum 3 rövid sor.
Írd le:
- milyen feltétel aktiválja
- melyik szint áttörése fontos
- mi erősítené meg

⚪ BASE CASE
Maximum 3 rövid sor.
Ez legyen az adatok alapján
leginkább valószínű alappálya.

🔴 BEAR CASE
Maximum 3 rövid sor.
Írd le:
- mi aktiválja
- melyik támasz elvesztése kritikus
- mi erősítené meg


📅 1 HETES OUTLOOK

Maximum 5 rövid sor.

Vedd figyelembe:
- 7 napos teljesítmény
- 30 napos teljesítmény
- EMA struktúra
- momentum
- SOL/BTC relatív erő


🎯 INVALIDATION

Adj egy konkrét technikai feltételt,
amely esetén a jelenlegi bias
már nem tekinthető érvényesnek.

Maximum 2 sor.


⚠️ FŐ KOCKÁZATOK

Maximum 3 rövid pont.

Csak az adatokból indokolható
kockázatokat említsd.


📊 CONFIDENCE

Objektív market score:
{score}/100

Ezt használd confidence értékként.

Ne találj ki saját százalékot.

Egy rövid mondatban magyarázd meg,
mi növeli vagy csökkenti a confidence-et.


🧭 NAPI BIAS

Elsődlegesen ezt használd:

{calculated_bias}

Csak akkor térj el tőle,
ha konkrét technikai ellentmondást találsz.

Ha eltérsz,
egy mondatban indokold.


👀 MA EZT FIGYELNÉM

Egyetlen rövid,
konkrét kereskedői szempont.
"""


# =========================================================
# GROQ GPT-OSS
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
        "model":
            "openai/gpt-oss-120b",

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
24h: {sol_change_24h:+.2f}%
7d: {sol_change_7d:+.2f}%
30d: {sol_change_30d:+.2f}%

⚖️ SOL vs BTC: {fmt(sol_vs_btc_24h)}%
📊 Score: {score}/100
🧭 Bias: {calculated_bias}

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
        + "\n\n⚠️ Riport automatikusan rövidítve."
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

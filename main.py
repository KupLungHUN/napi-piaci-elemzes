import os
import requests
from datetime import datetime

# --- SECRETS ---
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]

# --- SOLANA ÁR (CoinGecko) ---
sol = requests.get(
    "https://api.coingecko.com/api/v3/simple/price",
    params={
        "ids": "solana",
        "vs_currencies": "usd",
        "include_24hr_change": "true"
    }
).json()["solana"]

# --- PROMPT ---
prompt = f"""
Dátum: {datetime.now().strftime('%Y-%m-%d')}

Solana (SOL):
Ár: {sol['usd']} USD
24h változás: {sol['usd_24h_change']:.2f} %

"Viselkedj professzionális kriptovaluta piaci elemzőként és swing/day traderként.

Készíts teljes napi elemzést a Solana (SOL) coinról az aktuális piaci adatok alapján.

Az elemzés legyen részletes, logikus és kereskedői szemléletű.

Elemezd a következőket:

1. Aktuális ár és napi teljesítmény
- Jelenlegi SOL ár
- 24 órás változás (%)
- Napi minimum és maximum
- Volumen változás
- Piaci kapitalizáció
- BTC és ETH viszonyított teljesítmény

2. Technikai elemzés
Vizsgáld meg:
- Trend irány (bullish / bearish / sideway)
- RSI
- MACD
- EMA 20 / 50 / 200
- Bollinger Bands
- Támasz és ellenállás szintek
- Likviditási zónák
- Kitörési vagy visszafordulási lehetőségek
- Gyertyaalakzatok
- Momentum

3. Idősík elemzés
Külön elemezd:
- 15m
- 1H
- 4H
- 1D

Minden idősíknál:
- trend
- várható mozgás
- fontos szintek
- belépési lehetőség

4. Piaci hangulat
Elemezd:
- Fear & Greed hatását
- Kripto piac általános állapotát
- Bitcoin dominanciát
- Solana ökoszisztéma híreket
- Whale aktivitást
- Funding rate-eket
- Open interest változásokat

5. Előrejelzés
Adj:
- rövid távú (24-48h)
- középtávú (1 hét)
- bullish és bearish szcenáriót
- valószínűségi becslést

6. Kereskedési ötletek
Adj konkrét példákat:
- scalp setup
- intraday setup
- swing setup

Mindennél:
- belépési zóna
- stop loss
- take profit
- risk/reward arány

7. Kockázatok
Sorold fel:
- milyen esemény törheti meg az elemzést
- makrogazdasági kockázatok
- BTC mozgás hatása
- manipulációs veszélyek

8. Összegzés
A végén adj:
- egy rövid, profi összefoglalót
- napi bias-t:
  - erősen bullish
  - bullish
  - semleges
  - bearish
  - erősen bearish

Az elemzés legyen objektív, adat-alapú és ne túl optimista.

Használj táblázatokat és jól elkülönített szekciókat.
"

# --- GROQ API ---
response = requests.post(
    "https://api.groq.com/openai/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    },
    json={
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
)

data = response.json()
print("GROQ RESPONSE:", data)

if "choices" in data and len(data["choices"]) > 0:
    analysis = data["choices"][0]["message"]["content"]
else:
    change = sol["usd_24h_change"]

    if change > 2:
        trend = "erőteljes emelkedés"
        sentiment = "pozitív"
    elif change > 0:
        trend = "enyhe emelkedés"
        sentiment = "óvatosan pozitív"
    elif change > -2:
        trend = "oldalazás / enyhe gyengülés"
        sentiment = "bizonytalan"
    else:
        trend = "jelentős esés"
        sentiment = "negatív"

    analysis = f"""
Automatikus piaci összefoglaló:

A Solana árfolyam {trend} jeleit mutatja.
A piaci hangulat jelenleg {sentiment}.
"""

# --- TELEGRAM ÜZENET ---
message = f"""
📈 Napi piaci elemzés – Solana

💰 Ár: {sol['usd']} USD
📊 24h változás: {sol['usd_24h_change']:.2f} %

🧠 Elemzés:
{analysis}
"""

telegram_response = requests.post(
    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
    json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
)

print("TELEGRAM RESPONSE:", telegram_response.text)
print("KÉSZ – üzenet elküldve")

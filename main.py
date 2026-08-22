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

Viselkedj professzionális kriptovaluta-piaci elemzőként és swing/day traderként.

Készíts TÖMÖR, adatközpontú napi SOL elemzést magyarul.

FONTOS:
- A teljes válasz legfeljebb 2800 karakter legyen.
- Ne ismételd ugyanazt több pontban.
- Minden rész csak a legfontosabb információkat tartalmazza.
- Ha egy adathoz nem kaptál valós adatot, NE találj ki számot vagy hírt. Írd: "nincs adat".
- Ne állíts olyan hírt, whale aktivitást, funding rate-et, open interestet, RSI-t, MACD-t vagy EMA-t tényként, amelyet a bemenet nem tartalmaz.

Használd pontosan ezt a szerkezetet:

1. 📊 PIACI HELYZET
- SOL ár és 24h változás
- Trend: bullish / bearish / sideway
- Momentum röviden

2. 🎯 TECHNIKAI KÉP
- Legfontosabb támasz
- Legfontosabb ellenállás
- RSI / MACD / EMA csak akkor, ha rendelkezésre áll valódi adat
- Kitörési vagy visszafordulási feltétel

3. 🌍 PIACI HANGULAT
Maximum 3 rövid pont.
BTC/piaci környezet, hírek, funding, OI stb. csak akkor, ha erre tényleges adat áll rendelkezésre.

4. 🔮 FORGATÓKÖNYVEK
🟢 Bullish: maximum 2 mondat
🔴 Bearish: maximum 2 mondat
24-48h várakozás: 1 mondat
1 hetes kilátás: 1 mondat

5. ⚠️ KOCKÁZAT
Maximum 3 rövid kockázat.

6. 🧭 NAPI BIAS
Pontosan egy:
ERŐSEN BULLISH / BULLISH / SEMLEGES / BEARISH / ERŐSEN BEARISH

Zárásként adj egyetlen rövid mondatot arról, hogy mit érdemes ma figyelni.

Ne írj hosszú bevezetést vagy általános magyarázatokat.
"""

# --- GROQ API ---
response = requests.post(
    "https://api.groq.com/openai/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    },
    json={
        "model": "openai/gpt-oss-120b",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
)

# Hibakeresés
print(response.status_code)
print(response.text)
response.raise_for_status()

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
message = f"""📈 Napi piaci elemzés – Solana

💰 Ár: {sol['usd']} USD
📊 24h változás: {sol['usd_24h_change']:.2f} %

🧠 Elemzés:
{analysis}
"""

# Telegram maximum: 4096 karakter.
# Hagyunk egy kis biztonsági tartalékot.
TELEGRAM_MAX = 4000

if len(message) > TELEGRAM_MAX:
    message = message[:TELEGRAM_MAX - 50] + "\n\n⚠️ Riport rövidítve."

telegram_response = requests.post(
    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
    json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
)

telegram_response.raise_for_status()

print("TELEGRAM RESPONSE:", telegram_response.text)
print("KÉSZ – üzenet elküldve")

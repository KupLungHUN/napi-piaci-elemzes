import os
import requests
from datetime import datetime

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]

# --- SOLANA ÁR ---
sol = requests.get(
    "https://api.coingecko.com/api/v3/simple/price",
    params={
        "ids": "solana",
        "vs_currencies": "usd",
        "include_24hr_change": "true"
    }
).json()["solana"]

prompt = f"""
Dátum: {datetime.now().strftime('%Y-%m-%d')}

Solana (SOL):
Ár: {sol['usd']} USD
24h változás: {sol['usd_24h_change']:.2f} %

Elemezze a tőzsde jelenlegi trendjeit, különös tekintettel a sol. Azonosítsa a felmerülő mintákat, és javasoljon potenciális befektetési lehetőségeket. Az elemzés során vegye figyelembe a legfrissebb eredményjelentéseket és az iparági híreket, elüre látható mozgásokat
"""

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

# DEBUG – ezt MOST hagyd bent
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
Automatikus piaci összefoglaló (AI fallback):

A Solana árfolyam {trend} jeleit mutatja.
A rövid távú piaci hangulat {sentiment}.
A jelenlegi mozgás fokozott figyelmet igényel a volatilitás miatt.
"""

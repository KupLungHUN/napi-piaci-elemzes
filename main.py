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
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
)

data = response.json()

if "choices" not in data:
    analysis = "⚠️ Az AI válasza nem érhető el jelenleg (limit vagy hiba)."
else:
    analysis = data["choices"][0]["message"]["content"]


message = f"""
📈 *Napi piaci elemzés – Solana*

💰 Ár: {sol['usd']} USD
📊 24h változás: {sol['usd_24h_change']:.2f} %

🧠 Elemzés:
{analysis}
"""

requests.post(
    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
    json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
)

print("Telegram üzenet elküldve (GROQ)")

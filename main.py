import os
import requests
from datetime import datetime
from openai import OpenAI

# --- SECRET-EK ---
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

# --- SOLANA ÁR (CoinGecko) ---
sol = requests.get(
    "https://api.coingecko.com/api/v3/simple/price",
    params={
        "ids": "solana",
        "vs_currencies": "usd",
        "include_24hr_change": "true"
    }
).json()["solana"]

# --- CHATGPT ---
client = OpenAI(api_key=OPENAI_API_KEY)

prompt = f"""
Dátum: {datetime.now().strftime('%Y-%m-%d')}

Solana (SOL):
- Ár: {sol['usd']} USD
- 24 órás változás: {sol['usd_24h_change']:.2f} %

Készíts rövid, tömör napi piaci elemzést magyar nyelven:
Elemezze a tőzsde jelenlegi trendjeit, különös tekintettel a sol. Azonosítsa a felmerülő mintákat, és javasoljon potenciális befektetési lehetőségeket. Az elemzés során vegye figyelembe a legfrissebb eredményjelentéseket és az iparági híreket, észlelhető mozgásokat
"""

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": prompt}]
)

elemzes = response.choices[0].message.content

# --- TELEGRAM ÜZENET ---
uzenet = f"""
📈 *Napi piaci elemzés – Solana*

💰 Ár: {sol['usd']} USD
📊 24h változás: {sol['usd_24h_change']:.2f} %

🧠 Elemzés:
{elemzes}
"""

url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

requests.post(url, json={
    "chat_id": TELEGRAM_CHAT_ID,
    "text": uzenet,
    "parse_mode": "Markdown"
})

print("Telegram üzenet elküldve!")

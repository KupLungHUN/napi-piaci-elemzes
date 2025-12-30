import os
import requests
from datetime import datetime
from openai import OpenAI

SENDGRID_API_KEY = os.environ["SENDGRID_API_KEY"]
EMAIL_TO = os.environ["EMAIL_TO"]
EMAIL_FROM = os.environ["EMAIL_FROM"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

# --- SOLANA ADAT ---
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
Mai dátum: {datetime.now().strftime('%Y-%m-%d')}

Solana (SOL):
- Ár: {sol['usd']} USD
- 24 órás változás: {sol['usd_24h_change']:.2f} %

Készíts rövid, tömör napi piaci elemzést magyarul:
- általános piaci hangulat
- Solana trendek
- kockázatok és lehetőségek
Ne adj befektetési tanácsot.
"""

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": prompt}]
)

elemzes = response.choices[0].message.content

# --- EMAIL SENDGRID ---
email_data = {
    "personalizations": [{"to": [{"email": EMAIL_TO}]}],
    "from": {"email": EMAIL_FROM},
    "subject": "📈 Napi piaci elemzés – Solana",
    "content": [{"type": "text/plain", "value": elemzes}]
}

headers = {
    "Authorization": f"Bearer {SENDGRID_API_KEY}",
    "Content-Type": "application/json"
}

requests.post(
    "https://api.sendgrid.com/v3/mail/send",
    headers=headers,
    json=email_data
)

print("Napi elemzés elküldve!")

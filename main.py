import smtplib
from email.mime.text import MIMEText

EMAIL = "IDE_A_SAJAT_EMAIL_CIMED"
APP_JELSZO = "IDE_GMAIL_APP_JELSZO"

szoveg = """
Ez egy TESZT email.

Ha ezt megkaptad, akkor
a GitHub automatikus futtatás működik.
"""

uzenet = MIMEText(szoveg)
uzenet["Subject"] = "📈 Napi piaci elemzés – GitHub TESZT"
uzenet["From"] = EMAIL
uzenet["To"] = EMAIL

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
    server.login(EMAIL, APP_JELSZO)
    server.send_message(uzenet)

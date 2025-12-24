# utils/email.py
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from config.email_config import SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, SENDER_PASSWORD

def enviar_correo(asunto: str, cuerpo: str, destinatario: str):
    try:
        mensaje = MimeMultipart()
        mensaje["From"] = SENDER_EMAIL
        mensaje["To"] = destinatario
        mensaje["Subject"] = asunto

        mensaje.attach(MimeText(cuerpo, "html"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, destinatario, mensaje.as_string())
        return True
    except Exception as e:
        print(f"Error al enviar correo: {e}")
        return False
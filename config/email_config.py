# config/email_config.py
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "rlayam@gmail.com"
SENDER_PASSWORD = "otpf jtbc hrjh gmpn"  # App Password
DEFAULT_RECEIVER = "rlayam@gmail.com"
```

### Usa en `models/factura.py` (al cancelar)

```python
# En cancelar_factura_con_anulacion, al final del try:
from utils.email import enviar_correo
from config.email_config import DEFAULT_RECEIVER

# ... después de conn.commit()
enviar_correo(
    asunto=f"Factura {id_factura} cancelada",
    cuerpo=f"""
    <h3>Cancelación de factura</h3>
    <p>La factura <strong>{id_factura}</strong> ha sido cancelada.</p>
    <p>Asiento de anulación: {id_asiento_anul}</p>
    <p>Usuario: {id_usuario}</p>
    """,
    destinatario=DEFAULT_RECEIVER
)
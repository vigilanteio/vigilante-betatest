import sendgrid
from sendgrid.helpers.mail import Mail
import os

def enviar_email(destinatario, asunto, cuerpo, remitente):
    api_key = os.environ.get("SENDGRID_API_KEY")
    if not api_key:
        print("Error: La variable de entorno SENDGRID_API_KEY no está configurada.")
        return None
    sg = sendgrid.SendGridAPIClient(api_key=api_key)
    message = Mail(
        from_email=remitente,
        to_emails=destinatario,
        subject=asunto,
        plain_text_content=cuerpo
    )
    try:
        response = sg.send(message)
        return response.status_code
    except Exception as e:
        print(f"Error al enviar email: {e}")
        return None

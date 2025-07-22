import sendgrid
from sendgrid.helpers.mail import Mail

SENDGRID_API_KEY = "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"

def enviar_email(destinatario, asunto, cuerpo, remitente):
    sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
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

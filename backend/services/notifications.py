from ..config import (
    SMS_PROVIDER_API_KEY,
    EMAIL_PROVIDER_API_KEY,
    VOICE_PROVIDER_API_KEY,
)


def send_sms(to: str, message: str) -> None:
    """
    Envío de SMS – placeholder.
    Aquí puedes integrar Twilio u otro proveedor.
    """
    # ej. si tuvieras un cliente real:
    # client = TwilioClient(SMS_PROVIDER_API_KEY)
    # client.send_sms(to=to, body=message)
    print(f"[SMS] To: {to} | Message: {message}")


def send_email(to: str, subject: str, body: str) -> None:
    """
    Envío de email – placeholder.
    """
    print(f"[EMAIL] To: {to} | Subject: {subject} | Body: {body}")


def send_voice_call(to: str, script_text: str) -> None:
    """
    Llamada de voz – placeholder.
    Aquí integrarías un proveedor tipo Twilio Voice o similar.
    """
    print(f"[VOICE] To: {to} | Script: {script_text}")

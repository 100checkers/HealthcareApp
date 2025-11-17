import uuid

from ..config import PAYMENTS_BASE_URL, PAYMENTS_API_KEY


def generate_payment_link(appointment_id: int, amount_eur: float) -> str:
    """
    Devuelve un enlace de pago "fake" para el hackatón.
    En producción aquí llamarías a Juspay u otro proveedor.

    Usamos PAYMENTS_BASE_URL si está configurado, si no, generamos algo local.
    """
    # ID de sesión de pago simulado
    session_id = uuid.uuid4().hex[:16]

    if PAYMENTS_BASE_URL:
        base = PAYMENTS_BASE_URL.rstrip("/")
    else:
        # URL dummy para demo
        base = "https://pay.example.com"

    # En un proveedor real usarías la API, amount, currency, etc.
    return f"{base}/session/{session_id}?appointment_id={appointment_id}&amount={amount_eur:.2f}&currency=EUR"

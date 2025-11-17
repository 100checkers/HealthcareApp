import httpx
from ..config import APARAVI_API_URL, APARAVI_API_KEY


def redact_text_with_aparavi(text: str) -> str:
    """
    Envía texto a Aparavi para que elimine PII/PHI.
    Esta es una implementación genérica: ajusta el payload/respuesta
    a la API real cuando la tengas.

    Si no hay config, devuelve el texto tal cual (modo desarrollo).
    """
    if not APARAVI_API_URL or not APARAVI_API_KEY:
        return text

    try:
        headers = {
            "Authorization": f"Bearer {APARAVI_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {"text": text}
        resp = httpx.post(APARAVI_API_URL, json=payload, headers=headers, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
        # Ajusta la clave según el formato real
        return data.get("redacted_text", text)
    except Exception:
        # En caso de error, por seguridad podrías devolver
        # una versión muy neutral, pero para desarrollo dejamos tal cual.
        return text

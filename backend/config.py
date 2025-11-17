import os
from dotenv import load_dotenv

load_dotenv()

# SQLite local
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./healthcare.db")

# Aparavi (PII/PHI redaction)
APARAVI_API_URL = os.getenv("APARAVI_API_URL", "")
APARAVI_API_KEY = os.getenv("APARAVI_API_KEY", "")

# Notifications (ej. Twilio, SendGrid, etc.) – de momento usamos print(),
# pero dejamos las variables preparadas.
SMS_PROVIDER_API_KEY = os.getenv("SMS_PROVIDER_API_KEY", "")
EMAIL_PROVIDER_API_KEY = os.getenv("EMAIL_PROVIDER_API_KEY", "")
VOICE_PROVIDER_API_KEY = os.getenv("VOICE_PROVIDER_API_KEY", "")

# Payments (Juspay o similar)
PAYMENTS_BASE_URL = os.getenv("PAYMENTS_BASE_URL", "")
PAYMENTS_API_KEY = os.getenv("PAYMENTS_API_KEY", "")

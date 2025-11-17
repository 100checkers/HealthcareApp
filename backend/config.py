import os
from dotenv import load_dotenv

load_dotenv()

# SQLite local
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./healthcare.db")

# Aquí luego puedes añadir claves para LLM, notificaciones, etc.

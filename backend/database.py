from sqlmodel import SQLModel, create_engine, Session
from .config import DATABASE_URL  # import relativo dentro de backend

engine = create_engine(
    DATABASE_URL,
    echo=False,
)

def init_db() -> None:
    """
    Crear tablas en la base de datos.
    """
    from . import models  # importa modelos dentro del paquete backend
    SQLModel.metadata.create_all(engine)

def get_session():
    """
    Dependencia de FastAPI que devuelve una sesión de BD.
    """
    with Session(engine) as session:
        yield session

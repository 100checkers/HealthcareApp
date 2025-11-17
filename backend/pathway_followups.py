import sqlite3
import time
from datetime import datetime
from typing import Set

import pathway as pw

from .config import DATABASE_URL
from .services.notifications import send_sms, send_email, send_voice_call


# ---------- Resolver ruta del archivo SQLite a partir de DATABASE_URL ----------

if DATABASE_URL.startswith("sqlite:///"):
    DB_PATH = DATABASE_URL.replace("sqlite:///", "", 1)
else:
    # Fallback simple
    DB_PATH = "healthcare.db"


# ---------- Esquema Pathway para FollowUpTask ----------


class FollowUpSchema(pw.Schema):
    id: int = pw.column_definition(primary_key=True)
    appointment_id: int
    type: str
    channel: str
    scheduled_time: datetime
    message: str


# ---------- Conector de entrada: lee follow-ups desde SQLite ----------


class FollowUpSubject(pw.io.python.ConnectorSubject):
    """
    Conector personalizado de Pathway que:
    - Conecta a la base de datos SQLite (healthcare.db)
    - Busca FollowUpTask pendientes (executed = 0) cuya hora ya ha llegado
    - Va haciendo self.next(...) para enviar filas a Pathway
    """

    def __init__(self, db_path: str) -> None:
        super().__init__()
        self.db_path = db_path
        # Para no reenviar las mismas tareas continuamente
        self._seen_ids: Set[int] = set()

    def run(self) -> None:
        """
        Bucle infinito que:
        - cada X segundos consulta la BD
        - envía a Pathway los follow-ups listos para ejecutarse
        """
        while True:
            now = datetime.utcnow()

            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            # Importante: la tabla se llama followuptask (por defecto de SQLModel)
            cur.execute(
                """
                SELECT id, appointment_id, type, channel, scheduled_time, message
                FROM followuptask
                WHERE executed = 0
            """
            )
            rows = cur.fetchall()
            conn.close()

            for row in rows:
                fid = row["id"]
                if fid in self._seen_ids:
                    continue

                # scheduled_time vendrá como string ISO o datetime; lo normalizamos
                s_time = row["scheduled_time"]
                if isinstance(s_time, str):
                    scheduled_dt = datetime.fromisoformat(s_time)
                else:
                    scheduled_dt = s_time

                # Solo emitimos si ya toca (hora <= ahora)
                if scheduled_dt <= now:
                    self.next(
                        id=fid,
                        appointment_id=row["appointment_id"],
                        type=row["type"],
                        channel=row["channel"],
                        scheduled_time=scheduled_dt,
                        message=row["message"],
                    )
                    self._seen_ids.add(fid)

            # Enviamos un commit para que Pathway procese el mini-batch
            self.commit()

            # Dormimos unos segundos antes de la siguiente ronda
            time.sleep(5)


# ---------- Observador de salida: ejecuta notificaciones y marca ejecutado ----------


class FollowUpObserver(pw.io.python.ConnectorObserver):
    """
    Recibe cambios desde la tabla Pathway y:
    - envía notificación por SMS/EMAIL/VOICE
    - marca el follow-up como ejecutado en SQLite
    """

    def __init__(self, db_path: str) -> None:
        super().__init__()
        self.db_path = db_path

    def on_change(self, key: pw.Pointer, row: dict, time_: int, is_addition: bool):
        # Sólo actuamos en adiciones (diff = +1)
        if not is_addition:
            return

        followup_id = row["id"]
        appointment_id = row["appointment_id"]
        channel = row["channel"]
        message = row["message"]

        # Recuperamos info básica del paciente para logging / destino
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute(
            "SELECT patient_id FROM appointment WHERE id = ?",
            (appointment_id,),
        )
        app_row = cur.fetchone()

        if app_row is not None:
            patient_id = app_row["patient_id"]
            # En una versión más avanzada aquí usarías teléfono/email reales
            destination = f"patient-{patient_id}"
        else:
            destination = "unknown-patient"

        # Enviar notificación según canal
        if channel.lower() == "sms":
            send_sms(destination, message)
        elif channel.lower() == "email":
            send_email(destination, "Appointment follow-up", message)
        elif channel.lower() == "voice":
            send_voice_call(destination, message)
        else:
            # Canal desconocido, hacemos log
            print(f"[FOLLOWUP] Unknown channel '{channel}' for followup {followup_id}")

        # Marcar follow-up como ejecutado
        now_iso = datetime.utcnow().isoformat()

        cur.execute(
            """
            UPDATE followuptask
            SET executed = 1,
                executed_at = ?
            WHERE id = ?
            """,
            (now_iso, followup_id),
        )
        conn.commit()
        conn.close()

        print(f"[FOLLOWUP] executed followup_id={followup_id} via {channel} to {destination}")

    def on_end(self):
        print("[FOLLOWUP] Pathway stream ended.")


# ---------- Construcción del pipeline y arranque ----------


def build_pipeline():
    """
    Construye el pipeline Pathway:
    - Entrada: FollowUpSubject (SQLite -> Pathway)
    - Salida: FollowUpObserver (Pathway -> notificaciones + update BD)
    """
    subject = FollowUpSubject(DB_PATH)
    table = pw.io.python.read(
        subject,
        schema=FollowUpSchema,
        autocommit_duration_ms=1_000,
    )

    pw.io.python.write(table, FollowUpObserver(DB_PATH))
    return table


if __name__ == "__main__":
    build_pipeline()
    pw.run()

from datetime import datetime
from ..models import Appointment, Doctor, Patient


def add_appointment_to_calendar(appointment: Appointment, doctor: Doctor, patient: Patient) -> str:
    """
    Stub de integración calendario.
    En producción aquí llamarías a Google Calendar API u otro proveedor.

    Devuelve un event_id "fake" que podrías guardar en Appointment (campo nuevo).
    """
    event_id = f"evt_{appointment.id}"

    start_dt = datetime.combine(appointment.date, appointment.scheduled_time)
    end_dt = datetime.combine(appointment.date, appointment.current_time)

    # Para el hackatón, basta con un log bien explicado.
    print(
        f"[CALENDAR] Adding event for doctor={doctor.name}, patient={patient.display_name}, "
        f"start={start_dt.isoformat()}, end={end_dt.isoformat()}, event_id={event_id}"
    )

    return event_id

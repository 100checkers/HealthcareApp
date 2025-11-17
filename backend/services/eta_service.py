from datetime import datetime, date, time, timedelta
from typing import List

from sqlmodel import Session, select

from ..models import Appointment, AppointmentStatus, Doctor

def to_datetime(d: date, t: time) -> datetime:
    return datetime.combine(d, t)


def compute_doctor_delay_for_day(session: Session, doctor: Doctor, day: date) -> int:
    """
    Devuelve el retraso actual estimado del doctor en minutos.
    Algoritmo simplificado:
    - Si no hay visitas empezadas, asumimos retraso 0.
    - Si hay visitas en curso o completadas, calculamos cuánto se ha ido desplazando.
    """
    stmt = (
        select(Appointment)
        .where(Appointment.doctor_id == doctor.id)
        .where(Appointment.date == day)
        .order_by(Appointment.scheduled_time)
    )
    appointments = session.exec(stmt).all()

    if not appointments:
        return 0

    # si hay visitas ya completadas, miramos la última
    last_done = None
    for app in appointments:
        if app.status in (AppointmentStatus.IN_PROGRESS, AppointmentStatus.COMPLETED):
            last_done = app

    if not last_done or not last_done.visit_start_time:
        # no sabemos aún, devolvemos 0
        return 0

    # hora real de inicio vs hora programada -> retraso
    scheduled_dt = to_datetime(last_done.date, last_done.scheduled_time)
    actual_dt = last_done.visit_start_time
    delay = int((actual_dt - scheduled_dt).total_seconds() // 60)
    return max(delay, 0)


def compute_eta_for_appointment(
    session: Session,
    appointment: Appointment,
) -> dict:
    """
    Calcula ETA para una cita:
    - Ordena citas del día por current_time.
    - Aplica slot_minutes.
    - Devuelve:
      - original_time
      - current_delay_minutes
      - eta_time
      - queue_position
    """
    stmt = (
        select(Appointment)
        .where(Appointment.doctor_id == appointment.doctor_id)
        .where(Appointment.date == appointment.date)
        .order_by(Appointment.current_time)
    )
    same_day = session.exec(stmt).all()

    # posición en cola
    position = 1
    current_time_pointer = to_datetime(appointment.date, same_day[0].current_time)

    eta_dt = None
    for app in same_day:
        slot_duration = timedelta(minutes=app.slot_minutes)
        if app.id == appointment.id:
            eta_dt = current_time_pointer
            break
        # visitas completadas pueden adelantar la cola
        if app.status == AppointmentStatus.COMPLETED:
            current_time_pointer = current_time_pointer  # sin cambio
        else:
            current_time_pointer += slot_duration
            position += 1

    if eta_dt is None:
        eta_dt = to_datetime(appointment.date, appointment.current_time)

    original_dt = to_datetime(appointment.date, appointment.scheduled_time)
    delay_minutes = int((eta_dt - original_dt).total_seconds() // 60)

    return {
        "original_time": appointment.scheduled_time.strftime("%H:%M"),
        "eta_time": eta_dt.strftime("%H:%M"),
        "current_delay_minutes": max(delay_minutes, 0),
        "queue_position": position,
    }


def recommend_time_slots(
    session: Session,
    doctor: Doctor,
    day: date,
    start_hour: int = 9,
    end_hour: int = 13,
    slot_minutes: int = 20,
) -> dict:
    """
    Genera slots posibles y estima la espera basada en las citas ya programadas.
    Devuelve:
    - recommended: lista con 2–3 mejores opciones
    - all_slots: todos los slots con waiting_time_mins
    Esto encaja con la pantalla 2 del PDF: Recommended Times + All Available Times. :contentReference[oaicite:5]{index=5}
    """
    # sacar citas del día
    stmt = (
        select(Appointment)
        .where(Appointment.doctor_id == doctor.id)
        .where(Appointment.date == day)
        .order_by(Appointment.current_time)
    )
    appointments = session.exec(stmt).all()

    # mapa de hora -> cuántos pacientes hay antes
    base_time = time(hour=start_hour, minute=0)
    end_time = time(hour=end_hour, minute=0)

    slot_list = []
    current_t = base_time
    while current_t < end_time:
        slot_list.append(current_t)
        dt = datetime.combine(day, current_t) + timedelta(minutes=slot_minutes)
        current_t = dt.time()

    all_slots = []
    for slot in slot_list:
        # contamos cuántas citas hay antes de esa hora
        before_count = 0
        for app in appointments:
            if app.current_time <= slot and app.status != AppointmentStatus.COMPLETED:
                before_count += 1
        estimated_wait = before_count * slot_minutes  # muy simplificado
        all_slots.append(
            {
                "time": slot.strftime("%H:%M"),
                "estimated_wait_minutes": estimated_wait,
            }
        )

    # recomendadas: las de menor tiempo de espera
    sorted_slots = sorted(all_slots, key=lambda s: s["estimated_wait_minutes"])
    recommended = sorted_slots[:3]

    return {
        "recommended": recommended,
        "all_slots": all_slots,
    }

from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..database import get_session
from ..models import (
    Appointment,
    Patient,
    FollowUpTask,
    FollowUpType,
    FollowUpChannel,
    Escalation,
)
from ..services.llm_client import (
    generate_followup_message,
    classify_patient_reply,
)
from ..services.notifications import send_sms, send_email, send_voice_call

router = APIRouter()


# ---------- Schemas ----------

class ScheduleFollowUpsRequest(BaseModel):
    appointment_id: int
    # canal preferido para el paciente (para el demo usamos uno solo)
    channel: FollowUpChannel = FollowUpChannel.SMS


class PatientReplyRequest(BaseModel):
    appointment_id: int
    message: str


class FollowUpTaskResponse(BaseModel):
    id: int
    appointment_id: int
    type: FollowUpType
    channel: FollowUpChannel
    scheduled_time: datetime
    executed: bool
    executed_at: datetime | None


# ---------- Utilidades internas ----------

def _schedule_default_followups(
    session: Session,
    appointment: Appointment,
    patient: Patient,
    channel: FollowUpChannel,
) -> List[FollowUpTask]:
    """
    Crea:
    - 1 recordatorio antes de la cita (ej. 2h antes)
    - 1 check-in después de la cita (ej. 4h después de visit_end_time)
    """
    tasks: List[FollowUpTask] = []

    # Recordatorio 2h antes de la hora programada
    scheduled_dt = datetime.combine(appointment.date, appointment.scheduled_time)
    reminder_time = scheduled_dt - timedelta(hours=2)
    reminder_msg = generate_followup_message(appointment, patient, FollowUpType.REMINDER)

    reminder_task = FollowUpTask(
        appointment_id=appointment.id,
        type=FollowUpType.REMINDER,
        channel=channel,
        scheduled_time=reminder_time,
        message=reminder_msg,
    )
    session.add(reminder_task)
    tasks.append(reminder_task)

    # Check-in 4h después de visit_end_time (si ya se ha finalizado),
    # si no, lo dejamos para más tarde (puedes adaptar esta lógica).
    if appointment.visit_end_time:
        checkin_time = appointment.visit_end_time + timedelta(hours=4)
    else:
        checkin_time = scheduled_dt + timedelta(hours=4)

    checkin_msg = generate_followup_message(appointment, patient, FollowUpType.CHECKIN)

    checkin_task = FollowUpTask(
        appointment_id=appointment.id,
        type=FollowUpType.CHECKIN,
        channel=channel,
        scheduled_time=checkin_time,
        message=checkin_msg,
    )
    session.add(checkin_task)
    tasks.append(checkin_task)

    session.commit()
    for t in tasks:
        session.refresh(t)

    return tasks


# ---------- Endpoints ----------

@router.post("/schedule", response_model=list[FollowUpTaskResponse])
def schedule_followups(
    body: ScheduleFollowUpsRequest,
    session: Session = Depends(get_session),
):
    """
    Programa follow-ups por defecto para una cita:
    - recordatorio 2h antes
    - check-in 4h después

    Lo puedes llamar cuando se crea la cita o cuando el doctor termina la visita.
    """
    appointment = session.get(Appointment, body.appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    patient = session.get(Patient, appointment.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    tasks = _schedule_default_followups(session, appointment, patient, body.channel)

    return [
        FollowUpTaskResponse(
            id=t.id,
            appointment_id=t.appointment_id,
            type=t.type,
            channel=t.channel,
            scheduled_time=t.scheduled_time,
            executed=t.executed,
            executed_at=t.executed_at,
        )
        for t in tasks
    ]


@router.post("/run_once")
def run_followup_worker_once(session: Session = Depends(get_session)):
    """
    Worker simple:
    - Busca follow-ups pendientes cuya hora ya ha llegado.
    - Envía el mensaje por SMS/email/voz.
    - Marca como ejecutados.

    En un entorno real esto sería un cron job o un Pathway pipeline.
    """
    now = datetime.utcnow()

    stmt = select(FollowUpTask).where(
        (FollowUpTask.executed == False)  # noqa: E712
        & (FollowUpTask.scheduled_time <= now)
    )
    tasks = session.exec(stmt).all()

    processed = 0

    for task in tasks:
        app = session.get(Appointment, task.appointment_id)
        if not app:
            continue

        patient = session.get(Patient, app.patient_id)
        if not patient:
            continue

        # Para el demo no guardamos teléfono/email reales.
        # Supón que aquí tienes patient.contact_xxx y úsalo.
        destination = f"patient-{patient.id}"

        if task.channel == FollowUpChannel.SMS:
            send_sms(destination, task.message)
        elif task.channel == FollowUpChannel.EMAIL:
            send_email(destination, "Appointment follow-up", task.message)
        elif task.channel == FollowUpChannel.VOICE:
            send_voice_call(destination, task.message)

        task.executed = True
        task.executed_at = now
        session.add(task)
        processed += 1

    session.commit()
    return {"processed": processed}


@router.post("/reply")
def process_patient_reply(
    body: PatientReplyRequest,
    session: Session = Depends(get_session),
):
    """
    Recibe una respuesta de un paciente a un follow-up:
    - Clasifica con reglas + Aparavi.
    - Si parece grave => crea una Escalation para humano.
    - Si es reprogramación => devuelve NEED_RESCHEDULE.
    - Si todo OK => 'ok'.
    """
    appointment = session.get(Appointment, body.appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    label = classify_patient_reply(body.message)

    if label == "NEED_HUMAN_REVIEW":
        esc = Escalation(
            appointment_id=appointment.id,
            status="open",
            notes="Auto-created from patient reply classified as NEED_HUMAN_REVIEW",
        )
        session.add(esc)
        session.commit()
        session.refresh(esc)
        return {"status": "escalated", "escalation_id": esc.id}

    if label == "NEED_RESCHEDULE":
        return {"status": "needs_reschedule"}

    return {"status": "ok"}

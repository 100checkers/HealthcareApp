from datetime import date, time, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..database import get_session
from ..models import Appointment, Patient, Doctor
from ..services.eta_service import recommend_time_slots, compute_eta_for_appointment

router = APIRouter()


class AgentMessageRequest(BaseModel):
    patient_id: int
    message: str


class AgentResponse(BaseModel):
    intent: str
    data: dict


def _find_doctor_for_patient(session: Session, patient_id: int) -> Doctor | None:
    """
    Para simplificar: asumimos que el paciente suele ver al mismo doctor:
    cogemos el último doctor con el que tuvo cita.
    """
    stmt = (
        select(Appointment)
        .where(Appointment.patient_id == patient_id)
        .order_by(Appointment.date.desc())
    )
    last_app = session.exec(stmt).first()
    if not last_app:
        return None
    return session.get(Doctor, last_app.doctor_id)


@router.post("/message", response_model=AgentResponse)
def handle_agent_message(
    body: AgentMessageRequest,
    session: Session = Depends(get_session),
):
    """
    Agente muy simple basado en reglas, que:
    - detecta intenciones básicas (book / reschedule / eta),
    - llama a la lógica ya existente del backend.
    """
    patient = session.get(Patient, body.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    text = body.message.lower()

    # Intent: preguntar por la cita de hoy / ETA
    if any(word in text for word in ["when", "what time", "hour", "time"]) and "appointment" in text:
        today = date.today()
        stmt = (
            select(Appointment)
            .where(Appointment.patient_id == patient.id)
            .where(Appointment.date == today)
        )
        app = session.exec(stmt).first()
        if not app:
            return AgentResponse(
                intent="GET_TODAY_APPOINTMENT",
                data={"message": "You don't seem to have an appointment today."},
            )

        eta = compute_eta_for_appointment(session, app)

        return AgentResponse(
            intent="GET_TODAY_APPOINTMENT",
            data={
                "scheduled_time": app.scheduled_time.strftime("%H:%M"),
                "eta": eta,
            },
        )

    # Intent: buscar horas para una nueva cita (ej. "book", "schedule", "appointment tomorrow")
    if any(word in text for word in ["book", "schedule", "appointment"]):
        doctor = _find_doctor_for_patient(session, patient.id)
        if not doctor:
            # si no tiene doctor, elegimos uno cualquiera
            doc_stmt = select(Doctor)
            doctor = session.exec(doc_stmt).first()
            if not doctor:
                raise HTTPException(status_code=400, detail="No doctors configured")

        # Muy simplificado: asumimos que quiere cita mañana
        target_day = date.today().replace(day=date.today().day + 1)
        slots = recommend_time_slots(session, doctor, target_day)

        return AgentResponse(
            intent="RECOMMEND_SLOTS",
            data={
                "doctor_id": doctor.id,
                "doctor_name": doctor.name,
                "day": target_day.isoformat(),
                "recommended": slots["recommended"],
                "all_slots": slots["all_slots"],
            },
        )

    # Intent: reprogramar – lo dejamos como mensaje “needs manual”
    if any(word in text for word in ["change", "reschedule", "another time", "different time"]):
        return AgentResponse(
            intent="RESCHEDULE",
            data={
                "message": (
                    "It looks like you want to reschedule. "
                    "A human assistant will review your request."
                )
            },
        )

    # Fallback
    return AgentResponse(
        intent="UNKNOWN",
        data={"message": "I'm not sure how to help with that yet."},
    )

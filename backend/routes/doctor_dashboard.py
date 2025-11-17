from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..database import get_session
from ..models import (
    Appointment,
    AppointmentStatus,
    ArrivalStatus,
    Doctor,
    Patient,
)
from ..services.eta_service import compute_eta_for_appointment

router = APIRouter()


class DoctorScheduleRow(BaseModel):
    appointment_id: int
    patient_name: str
    time: str
    status: str
    arrival_status: str
    eta: dict


class DoctorScheduleResponse(BaseModel):
    doctor_id: int
    date: date
    rows: list[DoctorScheduleRow]


class ActionRequest(BaseModel):
    appointment_id: int


@router.get("/schedule", response_model=DoctorScheduleResponse)
def get_today_schedule(
    doctor_id: int,
    day: date,
    session: Session = Depends(get_session),
):
    doctor = session.get(Doctor, doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    stmt = (
        select(Appointment)
        .where(Appointment.doctor_id == doctor_id)
        .where(Appointment.date == day)
        .order_by(Appointment.current_time)
    )
    appointments = session.exec(stmt).all()

    rows: list[DoctorScheduleRow] = []
    for app in appointments:
        patient = session.get(Patient, app.patient_id)
        eta = compute_eta_for_appointment(session, app)
        rows.append(
            DoctorScheduleRow(
                appointment_id=app.id,
                patient_name=patient.display_name if patient else "Unknown",
                time=app.current_time.strftime("%H:%M"),
                status=app.status.value,
                arrival_status=app.arrival_status.value,
                eta=eta,
            )
        )

    return DoctorScheduleResponse(doctor_id=doctor_id, date=day, rows=rows)


@router.post("/mark_arrived")
def doctor_mark_arrived(
    body: ActionRequest,
    session: Session = Depends(get_session),
):
    app = session.get(Appointment, body.appointment_id)
    if not app:
        raise HTTPException(status_code=404, detail="Appointment not found")

    app.arrival_status = ArrivalStatus.ARRIVED
    app.patient_arrival_time = datetime.utcnow()
    session.add(app)
    session.commit()
    return {"status": "ok"}


@router.post("/start_visit")
def start_visit(
    body: ActionRequest,
    session: Session = Depends(get_session),
):
    app = session.get(Appointment, body.appointment_id)
    if not app:
        raise HTTPException(status_code=404, detail="Appointment not found")

    app.status = AppointmentStatus.IN_PROGRESS
    app.visit_start_time = datetime.utcnow()
    session.add(app)
    session.commit()
    return {"status": "ok"}


@router.post("/end_visit")
def end_visit(
    body: ActionRequest,
    session: Session = Depends(get_session),
):
    app = session.get(Appointment, body.appointment_id)
    if not app:
        raise HTTPException(status_code=404, detail="Appointment not found")

    app.status = AppointmentStatus.COMPLETED
    app.visit_end_time = datetime.utcnow()
    session.add(app)
    session.commit()

    # Opcional: podrías llamar aquí a la programación de follow-ups por defecto.
    # Para evitar imports circulares, simplemente lo dejas a decisión del front:
    # el front puede llamar a POST /followups/schedule después de esta acción.

    return {"status": "ok"}

@router.post("/skip")
def skip_patient(
    body: ActionRequest,
    session: Session = Depends(get_session),
):
    app = session.get(Appointment, body.appointment_id)
    if not app:
        raise HTTPException(status_code=404, detail="Appointment not found")

    app.status = AppointmentStatus.SKIPPED
    app.arrival_status = ArrivalStatus.SKIPPED

    stmt = (
        select(Appointment)
        .where(Appointment.doctor_id == app.doctor_id)
        .where(Appointment.date == app.date)
        .order_by(Appointment.current_time)
    )
    appointments = session.exec(stmt).all()
    last_time = appointments[-1].current_time if appointments else app.current_time

    last_dt = datetime.combine(app.date, last_time)
    new_dt = last_dt + timedelta(minutes=app.slot_minutes)
    app.current_time = new_dt.time()

    session.add(app)
    session.commit()
    return {"status": "ok", "new_time": app.current_time.strftime("%H:%M")}

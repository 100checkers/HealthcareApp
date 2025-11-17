from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..database import get_session
from ..models import Appointment, Doctor, Patient, AppointmentStatus, ArrivalStatus
from ..services.eta_service import recommend_time_slots, compute_eta_for_appointment
from ..services.payments import generate_payment_link


router = APIRouter()


class SlotsResponse(BaseModel):
    recommended: list[dict]
    all_slots: list[dict]


class BookAppointmentRequest(BaseModel):
    doctor_id: int
    patient_id: int
    date: date
    time: time
    slot_minutes: int = 20


class AppointmentDetailResponse(BaseModel):
    id: int
    doctor_id: int
    patient_id: int
    date: date
    scheduled_time: str
    current_time: str
    status: str
    arrival_status: str
    eta: dict


class CheckInRequest(BaseModel):
    arrived: bool


@router.get("/slots", response_model=SlotsResponse)
def get_slots(
    doctor_id: int,
    day: date,
    session: Session = Depends(get_session),
):
    doctor = session.get(Doctor, doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    result = recommend_time_slots(session, doctor, day)
    return SlotsResponse(
        recommended=result["recommended"],
        all_slots=result["all_slots"],
    )


@router.post("/", response_model=AppointmentDetailResponse)
def book_appointment(
    payload: BookAppointmentRequest,
    session: Session = Depends(get_session),
):
    doctor = session.get(Doctor, payload.doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    patient = session.get(Patient, payload.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    appointment = Appointment(
        doctor_id=doctor.id,
        patient_id=patient.id,
        date=payload.date,
        scheduled_time=payload.time,
        current_time=payload.time,
        slot_minutes=payload.slot_minutes,
        status=AppointmentStatus.SCHEDULED,
        arrival_status=ArrivalStatus.NOT_ARRIVED,
    )

    session.add(appointment)
    session.commit()
    session.refresh(appointment)

    # 💳 Generar payment link
    # Para el demo, asumimos una tarifa plana de 50€ por cita.
    payment_link = generate_payment_link(appointment.id, amount_eur=50.0)
    appointment.payment_link = payment_link
    session.add(appointment)
    session.commit()
    session.refresh(appointment)

    eta = compute_eta_for_appointment(session, appointment)

    return AppointmentDetailResponse(
        id=appointment.id,
        doctor_id=appointment.doctor_id,
        patient_id=appointment.patient_id,
        date=appointment.date,
        scheduled_time=appointment.scheduled_time.strftime("%H:%M"),
        current_time=appointment.current_time.strftime("%H:%M"),
        status=appointment.status.value,
        arrival_status=appointment.arrival_status.value,
        eta=eta,
    )


@router.get("/{appointment_id}", response_model=AppointmentDetailResponse)
def get_appointment_detail(
    appointment_id: int,
    session: Session = Depends(get_session),
):
    appointment = session.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    eta = compute_eta_for_appointment(session, appointment)

    return AppointmentDetailResponse(
        id=appointment.id,
        doctor_id=appointment.doctor_id,
        patient_id=appointment.patient_id,
        date=appointment.date,
        scheduled_time=appointment.scheduled_time.strftime("%H:%M"),
        current_time=appointment.current_time.strftime("%H:%M"),
        status=appointment.status.value,
        arrival_status=appointment.arrival_status.value,
        eta=eta,
    )


@router.post("/{appointment_id}/checkin", response_model=AppointmentDetailResponse)
def check_in_appointment(
    appointment_id: int,
    body: CheckInRequest,
    session: Session = Depends(get_session),
):
    appointment = session.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if body.arrived:
        appointment.arrival_status = ArrivalStatus.ARRIVED
        appointment.patient_arrival_time = datetime.utcnow()
    else:
        appointment.arrival_status = ArrivalStatus.NOT_ARRIVED

    session.add(appointment)
    session.commit()
    session.refresh(appointment)

    eta = compute_eta_for_appointment(session, appointment)

    return AppointmentDetailResponse(
        id=appointment.id,
        doctor_id=appointment.doctor_id,
        patient_id=appointment.patient_id,
        date=appointment.date,
        scheduled_time=appointment.scheduled_time.strftime("%H:%M"),
        current_time=appointment.current_time.strftime("%H:%M"),
        status=appointment.status.value,
        arrival_status=appointment.arrival_status.value,
        eta=eta,
    )

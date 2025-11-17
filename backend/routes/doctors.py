from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..database import get_session
from ..models import Doctor, DoctorPreferences

router = APIRouter()


@router.get("/", response_model=list[Doctor])
def list_doctors(session: Session = Depends(get_session)):
    return session.exec(select(Doctor)).all()


@router.post("/", response_model=Doctor)
def create_doctor(doctor: Doctor, session: Session = Depends(get_session)):
    session.add(doctor)
    session.commit()
    session.refresh(doctor)
    return doctor


@router.get("/{doctor_id}", response_model=Doctor)
def get_doctor(doctor_id: int, session: Session = Depends(get_session)):
    doctor = session.get(Doctor, doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doctor


@router.get("/{doctor_id}/preferences", response_model=DoctorPreferences)
def get_preferences(doctor_id: int, session: Session = Depends(get_session)):
    statement = select(DoctorPreferences).where(DoctorPreferences.doctor_id == doctor_id)
    prefs = session.exec(statement).first()
    if not prefs:
        raise HTTPException(status_code=404, detail="Preferences not found")
    return prefs


@router.put("/{doctor_id}/preferences", response_model=DoctorPreferences)
def upsert_preferences(
    doctor_id: int,
    prefs_in: DoctorPreferences,
    session: Session = Depends(get_session),
):
    doctor = session.get(Doctor, doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    statement = select(DoctorPreferences).where(DoctorPreferences.doctor_id == doctor_id)
    prefs = session.exec(statement).first()

    if prefs:
        prefs.workday_start = prefs_in.workday_start
        prefs.workday_end = prefs_in.workday_end
        prefs.appointment_duration_minutes = prefs_in.appointment_duration_minutes
        prefs.max_consecutive_appointments = prefs_in.max_consecutive_appointments
        prefs.lunch_start = prefs_in.lunch_start
        prefs.lunch_end = prefs_in.lunch_end
    else:
        prefs = DoctorPreferences(
            doctor_id=doctor_id,
            workday_start=prefs_in.workday_start,
            workday_end=prefs_in.workday_end,
            appointment_duration_minutes=prefs_in.appointment_duration_minutes,
            max_consecutive_appointments=prefs_in.max_consecutive_appointments,
            lunch_start=prefs_in.lunch_start,
            lunch_end=prefs_in.lunch_end,
        )
        session.add(prefs)

    session.commit()
    session.refresh(prefs)
    return prefs


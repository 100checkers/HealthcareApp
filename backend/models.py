from datetime import datetime, date, time
from enum import Enum
from typing import Optional

from sqlmodel import SQLModel, Field


class AppointmentStatus(str, Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class ArrivalStatus(str, Enum):
    NOT_ARRIVED = "not_arrived"
    ARRIVED = "arrived"
    SKIPPED = "skipped"


class Doctor(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    specialty: str


class DoctorPreferences(SQLModel, table=True):
    """
    Preferencias del doctor: horario, duración típica de cita, etc.
    Las usa el router de doctors (GET/PUT /doctors/{id}/preferences).
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    doctor_id: int = Field(foreign_key="doctor.id")
    workday_start: time
    workday_end: time
    slot_minutes: int = 20  # duración típica de un slot en minutos
    lunch_start: Optional[time] = None
    lunch_end: Optional[time] = None


class Patient(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    display_name: str  # nombre que verá el doctor en el dashboard


class Appointment(SQLModel, table=True):
    """
    Una cita entre doctor y paciente para un día concreto.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    doctor_id: int = Field(foreign_key="doctor.id")
    patient_id: int = Field(foreign_key="patient.id")

    date: date
    scheduled_time: time   # hora original (p.ej. 10:30)
    current_time: time     # hora actual estimada (puede cambiar al hacer skip)

    status: AppointmentStatus = Field(default=AppointmentStatus.SCHEDULED)
    arrival_status: ArrivalStatus = Field(default=ArrivalStatus.NOT_ARRIVED)

    # tiempos reales
    doctor_arrival_time: Optional[datetime] = None
    patient_arrival_time: Optional[datetime] = None
    visit_start_time: Optional[datetime] = None
    visit_end_time: Optional[datetime] = None

    # cuánto dura esta visita (para ETA y saltos)
    slot_minutes: int = 20

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
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    doctor_id: int = Field(foreign_key="doctor.id")
    workday_start: time
    workday_end: time
    slot_minutes: int = 20
    lunch_start: Optional[time] = None
    lunch_end: Optional[time] = None


class Patient(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    display_name: str  # nombre visible en dashboard del doctor


class Appointment(SQLModel, table=True):
    """
    Cita entre doctor y paciente para un día concreto.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    doctor_id: int = Field(foreign_key="doctor.id")
    patient_id: int = Field(foreign_key="patient.id")

    date: date
    scheduled_time: time   # hora original
    current_time: time     # hora actual estimada (cambia al hacer skip, etc.)

    status: AppointmentStatus = Field(default=AppointmentStatus.SCHEDULED)
    arrival_status: ArrivalStatus = Field(default=ArrivalStatus.NOT_ARRIVED)

    # tiempos reales
    doctor_arrival_time: Optional[datetime] = None
    patient_arrival_time: Optional[datetime] = None
    visit_start_time: Optional[datetime] = None
    visit_end_time: Optional[datetime] = None

    # duración de la visita (min)
    slot_minutes: int = 20

    # enlace de pago opcional
    payment_link: Optional[str] = None

    event_id: Optional[str] = None



# ---- Follow-ups & Action Items ----

class FollowUpType(str, Enum):
    REMINDER = "reminder"
    CHECKIN = "checkin"


class FollowUpChannel(str, Enum):
    SMS = "sms"
    EMAIL = "email"
    VOICE = "voice"


class FollowUpTask(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    appointment_id: int = Field(foreign_key="appointment.id")
    type: FollowUpType
    channel: FollowUpChannel
    scheduled_time: datetime
    message: str

    executed: bool = False
    executed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ActionItemStatus(str, Enum):
    PENDING = "pending"
    DONE = "done"


class ActionItem(SQLModel, table=True):
    """
    Para la pantalla "After Your Visit" – tareas tipo:
    - 'Do blood test'
    - 'Take medication 3x per day'
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    appointment_id: int = Field(foreign_key="appointment.id")
    title: str
    description: str
    status: ActionItemStatus = Field(default=ActionItemStatus.PENDING)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    due_date: Optional[datetime] = None


class Escalation(SQLModel, table=True):
    """
    Escalados a humano cuando una respuesta del paciente parece preocupante.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    appointment_id: int = Field(foreign_key="appointment.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "open"  # open | in_progress | resolved
    notes: Optional[str] = None

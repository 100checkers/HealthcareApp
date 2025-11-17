import uuid
from fastapi import APIRouter, Depends
from sqlmodel import Session

from ..database import get_session
from ..models import Patient

router = APIRouter()


@router.post("/", response_model=Patient)
def create_patient(
    display_name: str,
    session: Session = Depends(get_session),
):
    patient = Patient(display_name=display_name)
    session.add(patient)
    session.commit()
    session.refresh(patient)
    return patient


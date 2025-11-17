from ..models import Appointment, Patient, FollowUpType
from .aparavi_client import redact_text_with_aparavi


def generate_followup_message(
    appointment: Appointment,
    patient: Patient,
    followup_type: FollowUpType,
) -> str:
    """
    Genera mensajes de recordatorio / check-in con tono empático.
    De momento son plantillas estáticas (sin PII).
    """
    if followup_type == FollowUpType.REMINDER:
        return (
            "Hi! This is a gentle reminder about your upcoming appointment. "
            "If you feel unwell or need to reschedule, please contact the clinic."
        )

    if followup_type == FollowUpType.CHECKIN:
        return (
            "Hi! We hope you are feeling okay after your recent visit. "
            "If your symptoms get worse or you feel worried, please contact your doctor or local emergency services."
        )

    return "Hi! This is a follow-up message from your clinic."


def classify_patient_reply(raw_message: str) -> str:
    """
    Clasifica una respuesta libre del paciente en:
    - OK
    - NEED_RESCHEDULE
    - NEED_HUMAN_REVIEW

    1) Redaccionamos con Aparavi para eliminar PII/PHI.
    2) Aplicamos reglas simples (puedes cambiarlo por LLM/Pathway).
    """
    safe_text = redact_text_with_aparavi(raw_message)
    text = safe_text.lower()

    if any(word in text for word in ["change", "reschedule", "another time", "different time"]):
        return "NEED_RESCHEDULE"

    if any(word in text for word in ["worse", "worst", "pain", "bleeding", "fever", "emergency"]):
        return "NEED_HUMAN_REVIEW"

    return "OK"

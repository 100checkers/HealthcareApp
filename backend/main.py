from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .routes import doctors, patients, appointments, doctor_dashboard, followups, agent


app = FastAPI(
    title="HealthcareApp API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en producción, restringir
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(doctors.router, prefix="/doctors", tags=["doctors"])
app.include_router(patients.router, prefix="/patients", tags=["patients"])
app.include_router(appointments.router, prefix="/appointments", tags=["appointments"])
app.include_router(doctor_dashboard.router, prefix="/doctor", tags=["doctor_dashboard"])
app.include_router(followups.router, prefix="/followups", tags=["followups"])
app.include_router(agent.router, prefix="/agent", tags=["agent"])




@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def read_root():
    return {"status": "ok", "message": "HealthcareApp backend running"}

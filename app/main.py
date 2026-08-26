from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session
from typing import List
from datetime import datetime, date, timedelta

from .database import init_db, get_session
from . import models, schemas, crud

app = FastAPI(title="Clinic Booking API")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/")
def read_index():
    return FileResponse("app/static/index.html")


@app.get("/doctors", response_model=List[schemas.DoctorRead])
def list_doctors(session: Session = Depends(get_session)):
    doctors = session.query(models.Doctor).all()
    return doctors


@app.post("/doctors", response_model=schemas.DoctorRead)
def create_doctor(req: schemas.DoctorCreate, session: Session = Depends(get_session)):
    doctor = models.Doctor(name=req.name, specialty=req.specialty)
    session.add(doctor)
    session.commit()
    session.refresh(doctor)
    return doctor


@app.get("/patients", response_model=List[schemas.PatientRead])
def list_patients(session: Session = Depends(get_session)):
    patients = session.query(models.Patient).all()
    return patients


@app.post("/patients", response_model=schemas.PatientRead)
def create_patient(req: schemas.PatientCreate, session: Session = Depends(get_session)):
    patient = models.Patient(name=req.name, email=req.email, phone=req.phone)
    session.add(patient)
    session.commit()
    session.refresh(patient)
    return patient


@app.post("/seed-demo")
def seed_demo(session: Session = Depends(get_session)):
    doctor = session.query(models.Doctor).filter(models.Doctor.name == "Dr. Alice Carter").first()
    if not doctor:
        doctor = models.Doctor(name="Dr. Alice Carter", specialty="Primary Care")
        session.add(doctor)
        session.commit()
        session.refresh(doctor)

    today = datetime.utcnow().date()
    weekday = today.weekday()
    existing_hours = session.query(models.WorkingHours).filter(models.WorkingHours.doctor_id == doctor.id).filter(models.WorkingHours.weekday == weekday).first()
    if not existing_hours:
        session.add(models.WorkingHours(
            doctor_id=doctor.id,
            weekday=weekday,
            start_time=datetime.strptime("09:00", "%H:%M").time(),
            end_time=datetime.strptime("17:00", "%H:%M").time(),
        ))
        session.commit()

    patient = session.query(models.Patient).filter(models.Patient.name == "Jane Smith").first()
    if not patient:
        patient = models.Patient(name="Jane Smith", email="jane@example.com", phone="555-0100")
        session.add(patient)
        session.commit()
        session.refresh(patient)

    return {"doctor": {"id": doctor.id, "name": doctor.name}, "patient": {"id": patient.id, "name": patient.name}}


@app.get("/doctors/{doctor_id}/availability")
def get_availability(doctor_id: int, date: date, session: Session = Depends(get_session)):
    weekday = date.weekday()
    whs = crud.get_doctor_working_hours(session, doctor_id, weekday)
    if not whs:
        return {"slots": []}
    all_slots = []
    for wh in whs:
        for start, end in crud.slots_for_working_hours(wh, date):
            all_slots.append({"start": start.isoformat(), "end": end.isoformat()})

    booked = crud.get_booked_slots(session, doctor_id, date)
    booked_starts = {b.start_at for b in booked}
    now = datetime.utcnow()
    available = [s for s in all_slots if datetime.fromisoformat(s["start"]) not in booked_starts and datetime.fromisoformat(s["start"]) >= now]
    return {"slots": available}


@app.post("/appointments", response_model=schemas.AppointmentResponse)
def book_appointment(req: schemas.AppointmentCreate, session: Session = Depends(get_session)):
    if req.start_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Cannot book in the past")
    exists = session.query(models.Appointment).filter(models.Appointment.doctor_id == req.doctor_id).filter(models.Appointment.start_at == req.start_at).first()
    if exists and exists.status == "booked":
        raise HTTPException(status_code=400, detail="Slot already taken")
    end_at = req.start_at + timedelta(minutes=30)
    appt = models.Appointment(doctor_id=req.doctor_id, patient_id=req.patient_id, start_at=req.start_at, end_at=end_at)
    session.add(appt)
    session.commit()
    session.refresh(appt)
    return appt


@app.patch("/appointments/{appointment_id}/cancel")
def cancel_appointment(appointment_id: int, req: schemas.CancelRequest, session: Session = Depends(get_session)):
    appt = session.get(models.Appointment, appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appt.status == "cancelled":
        raise HTTPException(status_code=400, detail="Appointment already cancelled")
    appt.status = "cancelled"
    appt.cancel_reason = req.reason
    session.add(appt)
    session.commit()
    session.refresh(appt)
    return {"status": "cancelled"}


@app.patch("/appointments/{appointment_id}/reschedule")
def reschedule_appointment(appointment_id: int, req: schemas.RescheduleRequest, session: Session = Depends(get_session)):
    appt = session.get(models.Appointment, appointment_id)
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appt.status == "cancelled":
        raise HTTPException(status_code=400, detail="Cannot reschedule cancelled appointment")
    exists = session.query(models.Appointment).filter(models.Appointment.doctor_id == appt.doctor_id).filter(models.Appointment.start_at == req.new_start_at).first()
    if exists and exists.id != appt.id and exists.status == "booked":
        raise HTTPException(status_code=400, detail="Desired slot already taken")
    appt.start_at = req.new_start_at
    appt.end_at = req.new_start_at + timedelta(minutes=30)
    session.add(appt)
    session.commit()
    session.refresh(appt)
    return appt

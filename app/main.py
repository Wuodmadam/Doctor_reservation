from fastapi import FastAPI, HTTPException, Depends
from sqlmodel import Session
from typing import List
from datetime import datetime, date, timedelta

from .database import init_db, get_session
from . import models, schemas, crud

app = FastAPI(title="Clinic Booking API")


@app.on_event("startup")
def on_startup():
    init_db()


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
    # exclude slots in the past
    available = [s for s in all_slots if datetime.fromisoformat(s["start"]) not in booked_starts and datetime.fromisoformat(s["start"]) >= now]
    return {"slots": available}


@app.post("/appointments", response_model=schemas.AppointmentResponse)
def book_appointment(req: schemas.AppointmentCreate, session: Session = Depends(get_session)):
    # Validate not in past
    if req.start_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Cannot book in the past")
    # simple check: uniqueness
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
    # check new slot availability
    exists = session.query(models.Appointment).filter(models.Appointment.doctor_id == appt.doctor_id).filter(models.Appointment.start_at == req.new_start_at).first()
    if exists and exists.id != appt.id and exists.status == "booked":
        raise HTTPException(status_code=400, detail="Desired slot already taken")
    appt.start_at = req.new_start_at
    appt.end_at = req.new_start_at + timedelta(minutes=30)
    session.add(appt)
    session.commit()
    session.refresh(appt)
    return appt

from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db
from app import models
from sqlmodel import Session
import pytest
from datetime import date, datetime, time, timedelta


client = TestClient(app)


def setup_module(module):
    init_db()


def test_slot_generation_and_booking():
    # create doctor, patient, working hours via DB session
    from app.database import engine
    with Session(engine) as session:
        d = models.Doctor(name="Dr Test")
        session.add(d)
        session.commit()
        session.refresh(d)
        p = models.Patient(name="Alice")
        session.add(p)
        session.commit()
        session.refresh(p)
        # choose a future date to avoid filtering out same-day past slots
        target_date = date.today() + timedelta(days=1)
        wh = models.WorkingHours(doctor_id=d.id, weekday=target_date.weekday(), start_time=time(9,0), end_time=time(17,0))
        session.add(wh)
        session.commit()
        
        resp = client.get(f"/doctors/{d.id}/availability", params={"date": target_date.isoformat()})
        assert resp.status_code == 200
        data = resp.json()
        assert "slots" in data

        # book a slot
        # pick first slot start
        first_slot = data["slots"][0]["start"]
        start_dt = datetime.fromisoformat(first_slot)
        book_resp = client.post("/appointments", json={"doctor_id": d.id, "patient_id": p.id, "start_at": start_dt.isoformat()})
        assert book_resp.status_code == 200 or book_resp.status_code == 201

from datetime import datetime, timedelta, date, time
from zoneinfo import ZoneInfo
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import Session
from .models import Doctor, WorkingHours, Appointment
from .database import engine

Nairobi = ZoneInfo("Africa/Nairobi")

SLOT_MINUTES = 30

def slots_for_working_hours(wh: WorkingHours, for_date: date):
    # produce list of (start_datetime, end_datetime) in UTC
    local_start = datetime.combine(for_date, wh.start_time, tzinfo=Nairobi)
    local_end = datetime.combine(for_date, wh.end_time, tzinfo=Nairobi)
    slots = []
    cur = local_start
    from zoneinfo import ZoneInfo
    UTC = ZoneInfo("UTC")
    while cur + timedelta(minutes=SLOT_MINUTES) <= local_end:
        start_utc = cur.astimezone(UTC)
        end_utc = (cur + timedelta(minutes=SLOT_MINUTES)).astimezone(UTC)
        # return naive UTC datetimes for storage/compatibility
        slots.append((start_utc.replace(tzinfo=None), end_utc.replace(tzinfo=None)))
        cur += timedelta(minutes=SLOT_MINUTES)
    return slots

def get_doctor_working_hours(session: Session, doctor_id: int, weekday: int):
    stmt = select(WorkingHours).where(WorkingHours.doctor_id == doctor_id).where(WorkingHours.weekday == weekday)
    return session.exec(stmt).all()

def get_booked_slots(session: Session, doctor_id: int, for_date: date):
    start_day = datetime.combine(for_date, time.min)
    end_day = datetime.combine(for_date, time.max)
    stmt = select(Appointment).where(Appointment.doctor_id == doctor_id).where(Appointment.status == "booked").where(Appointment.start_at >= start_day).where(Appointment.start_at <= end_day)
    return session.exec(stmt).all()

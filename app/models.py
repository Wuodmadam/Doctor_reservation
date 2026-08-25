from typing import Optional
from datetime import datetime, time
from sqlmodel import SQLModel, Field, Relationship, Column, UniqueConstraint
from sqlalchemy import String


class Doctor(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    specialty: Optional[str] = None
    working_hours: list["WorkingHours"] = Relationship(back_populates="doctor")


class WorkingHours(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    doctor_id: int = Field(foreign_key="doctor.id")
    weekday: int  # 0=Mon..6=Sun
    start_time: time
    end_time: time
    doctor: Optional[Doctor] = Relationship(back_populates="working_hours")


class Patient(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: Optional[str] = Field(default=None, sa_column=Column(String(255)))
    phone: Optional[str] = None


class Appointment(SQLModel, table=True):
    __table_args__ = (UniqueConstraint('doctor_id', 'start_at', name='uix_doctor_start'),)

    id: Optional[int] = Field(default=None, primary_key=True)
    doctor_id: int = Field(foreign_key="doctor.id")
    patient_id: int = Field(foreign_key="patient.id")
    start_at: datetime
    end_at: datetime
    status: str = Field(default="booked")
    cancel_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

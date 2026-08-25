from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import Optional


class AppointmentCreate(BaseModel):
    doctor_id: int
    patient_id: int
    start_at: datetime


class AppointmentResponse(BaseModel):
    id: int
    doctor_id: int
    patient_id: int
    start_at: datetime
    end_at: datetime
    status: str


class CancelRequest(BaseModel):
    reason: str


class RescheduleRequest(BaseModel):
    new_start_at: datetime

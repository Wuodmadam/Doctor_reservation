from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import Optional


class DoctorCreate(BaseModel):
    name: str
    specialty: Optional[str] = None


class DoctorRead(BaseModel):
    id: int
    name: str
    specialty: Optional[str] = None


class PatientCreate(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None


class PatientRead(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None


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

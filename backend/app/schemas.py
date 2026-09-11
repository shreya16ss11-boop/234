from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


AppointmentStatus = Literal["Booked", "Confirmed", "Completed", "Cancelled", "No-show"]


class ServiceIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    category: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=8, max_length=400)
    duration_minutes: int = Field(ge=15, le=240)
    price: float = Field(ge=0, le=5000)
    active: bool = True
    color: str = Field(min_length=3, max_length=40)


class StaffIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    role: str = Field(min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(min_length=6, max_length=32)
    active: bool = True
    bio: str = Field(min_length=5, max_length=400)
    service_ids: list[int] = Field(default_factory=list)


class AppointmentIn(BaseModel):
    customer_name: str = Field(min_length=2, max_length=100)
    customer_email: EmailStr
    customer_phone: str = Field(min_length=6, max_length=32)
    service_id: int = Field(gt=0)
    staff_id: int = Field(gt=0)
    appointment_date: date
    start_time: str = Field(min_length=5, max_length=5)
    notes: str | None = Field(default=None, max_length=400)

    @field_validator("start_time")
    @classmethod
    def validate_time(cls, value: str) -> str:
        parts = value.split(":")
        if len(parts) != 2:
            raise ValueError("Time must use HH:MM format")
        hour, minute = (int(parts[0]), int(parts[1]))
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            raise ValueError("Invalid time")
        return f"{hour:02d}:{minute:02d}"


class AppointmentUpdate(BaseModel):
    customer_name: str | None = Field(default=None, min_length=2, max_length=100)
    customer_email: EmailStr | None = None
    customer_phone: str | None = Field(default=None, min_length=6, max_length=32)
    appointment_date: date | None = None
    start_time: str | None = Field(default=None, min_length=5, max_length=5)
    staff_id: int | None = Field(default=None, gt=0)
    service_id: int | None = Field(default=None, gt=0)
    status: AppointmentStatus | None = None
    notes: str | None = Field(default=None, max_length=400)

    @field_validator("start_time")
    @classmethod
    def validate_optional_time(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return AppointmentIn.validate_time(value)


class StatusIn(BaseModel):
    status: AppointmentStatus

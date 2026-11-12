from datetime import date, datetime, time, timedelta
from threading import Lock
from uuid import uuid4
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI(
    title="CarePoint Pharmacy Test Scheduling API",
    version="1.0.0",
    description="A test-only appointment API for Rafiki AI Custom Scheduling."
)

_lock = Lock()
_bookings = []

class BookingRequest(BaseModel):
    customer_name: str = Field(..., min_length=1)
    customer_phone: str = Field(..., min_length=5)
    appointment_date: date
    appointment_time: str
    reason: Optional[str] = None
    duration_minutes: int = Field(default=30, ge=10, le=180)

def _parse_time(value: str) -> time:
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError:
        raise HTTPException(status_code=400, detail="appointment_time must use HH:MM format")

def _working_hours(day: date):
    # Monday-Friday 08:00-18:00; Saturday 09:00-15:00; Sunday closed.
    if day.weekday() <= 4:
        return time(8, 0), time(18, 0)
    if day.weekday() == 5:
        return time(9, 0), time(15, 0)
    return None

def _slots_for(day: date):
    hours = _working_hours(day)
    if not hours:
        return []
    start, end = hours
    slots = []
    cursor = datetime.combine(day, start)
    closing = datetime.combine(day, end)
    while cursor + timedelta(minutes=30) <= closing:
        # Lunch break weekdays 13:00-14:00
        if not (day.weekday() <= 4 and time(13, 0) <= cursor.time() < time(14, 0)):
            slots.append(cursor.strftime("%H:%M"))
        cursor += timedelta(minutes=30)
    return slots

@app.get("/")
def root():
    return {
        "service": "CarePoint Pharmacy Test Scheduling API",
        "status": "ok",
        "test_only": True,
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
def health():
    return {"status": "ok", "service": "carepoint-scheduling-test"}

@app.get("/availability")
def lookup_availability(
    appointment_date: date = Query(..., description="Date in YYYY-MM-DD format"),
    duration_minutes: int = Query(30, ge=10, le=180)
):
    """Return available appointment start times for a date."""
    if appointment_date < date.today():
        raise HTTPException(status_code=400, detail="Cannot check availability for a past date")
    available = []
    with _lock:
        booked = [
            b for b in _bookings
            if b["appointment_date"] == appointment_date.isoformat()
        ]
        for slot in _slots_for(appointment_date):
            start = datetime.combine(appointment_date, _parse_time(slot))
            end = start + timedelta(minutes=duration_minutes)
            conflict = False
            for booking in booked:
                bstart = datetime.combine(appointment_date, _parse_time(booking["appointment_time"]))
                bend = bstart + timedelta(minutes=booking["duration_minutes"])
                if start < bend and bstart < end:
                    conflict = True
                    break
            if not conflict:
                available.append(slot)
    return {
        "date": appointment_date.isoformat(),
        "timezone": "Africa/Nairobi",
        "duration_minutes": duration_minutes,
        "available_slots": available
    }

@app.post("/appointments", status_code=201)
def book_appointment(payload: BookingRequest):
    """Create a booking if the requested time is open."""
    if payload.appointment_date < date.today():
        raise HTTPException(status_code=400, detail="Cannot book an appointment in the past")
    requested_time = _parse_time(payload.appointment_time)
    if payload.appointment_time not in _slots_for(payload.appointment_date):
        raise HTTPException(status_code=400, detail="Requested time is outside clinic hours or during the lunch break")
    start = datetime.combine(payload.appointment_date, requested_time)
    end = start + timedelta(minutes=payload.duration_minutes)
    with _lock:
        for booking in _bookings:
            if booking["appointment_date"] != payload.appointment_date.isoformat():
                continue
            bstart = datetime.combine(payload.appointment_date, _parse_time(booking["appointment_time"]))
            bend = bstart + timedelta(minutes=booking["duration_minutes"])
            if start < bend and bstart < end:
                raise HTTPException(status_code=409, detail="That appointment slot is already booked")
        booking = {
            "booking_id": "CP-" + uuid4().hex[:8].upper(),
            "customer_name": payload.customer_name,
            "customer_phone": payload.customer_phone,
            "appointment_date": payload.appointment_date.isoformat(),
            "appointment_time": payload.appointment_time,
            "duration_minutes": payload.duration_minutes,
            "reason": payload.reason,
            "status": "confirmed"
        }
        _bookings.append(booking)
    return {
        "success": True,
        "message": "Appointment booked successfully",
        "booking": booking
    }

@app.get("/appointments/{booking_id}")
def lookup_booking(booking_id: str):
    with _lock:
        for booking in _bookings:
            if booking["booking_id"] == booking_id:
                return {"found": True, "booking": booking}
    raise HTTPException(status_code=404, detail="Booking not found")

@app.get("/appointments")
def list_appointments():
    # Test/admin endpoint; returns only bookings in this in-memory test instance.
    with _lock:
        return {"appointments": list(_bookings), "count": len(_bookings)}

@app.delete("/appointments/{booking_id}")
def cancel_booking(booking_id: str):
    with _lock:
        for booking in _bookings:
            if booking["booking_id"] == booking_id:
                booking["status"] = "cancelled"
                return {"success": True, "message": "Appointment cancelled", "booking": booking}
    raise HTTPException(status_code=404, detail="Booking not found")

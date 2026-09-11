from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from app.database import get_db, init_db
from app.main import app
from app.seed import seed_sample_data


client = TestClient(app)


def setup_function():
    db = Path(os.environ["RESERVEHUB_DB_PATH"])
    if db.exists():
        db.unlink()
    with get_db() as conn:
        init_db(conn)
        seed_sample_data(conn)


def future_date(days: int = 5) -> str:
    return (datetime.now(timezone.utc).date() + timedelta(days=days)).isoformat()


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_services_and_staff_are_available():
    services = client.get("/services?active=true").json()
    staff = client.get("/staff?active=true").json()
    assert len(services) >= 5
    assert any(person["services"] for person in staff)


def test_slots_respect_availability():
    response = client.get(f"/slots?service_id=1&staff_id=1&appointment_date={future_date(7)}")
    assert response.status_code == 200
    data = response.json()
    assert "09:00" in data["slots"]
    assert "17:00" not in data["slots"]


def test_create_appointment():
    response = client.post(
        "/appointments",
        json={
            "customer_name": "Booking Customer",
            "customer_email": "booking@example.com",
            "customer_phone": "+995555303030",
            "service_id": 1,
            "staff_id": 1,
            "appointment_date": future_date(8),
            "start_time": "09:00",
            "notes": "Needs a focused strategy session",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "Booked"
    assert data["end_time"] == "10:00"
    assert data["service_name"] == "Strategy Consultation"


def test_double_booking_is_rejected():
    payload = {
        "customer_name": "First Booking",
        "customer_email": "first@example.com",
        "customer_phone": "+995555303031",
        "service_id": 1,
        "staff_id": 1,
        "appointment_date": future_date(9),
        "start_time": "09:00",
    }
    assert client.post("/appointments", json=payload).status_code == 201
    payload["customer_name"] = "Second Booking"
    payload["customer_email"] = "second@example.com"
    conflict = client.post("/appointments", json=payload)
    assert conflict.status_code == 409


def test_unqualified_staff_is_rejected():
    response = client.post(
        "/appointments",
        json={
            "customer_name": "Bad Match",
            "customer_email": "badmatch@example.com",
            "customer_phone": "+995555303032",
            "service_id": 2,
            "staff_id": 1,
            "appointment_date": future_date(10),
            "start_time": "10:00",
        },
    )
    assert response.status_code == 422


def test_update_appointment_status_records_activity():
    created = client.post(
        "/appointments",
        json={
            "customer_name": "Status Customer",
            "customer_email": "status@example.com",
            "customer_phone": "+995555303033",
            "service_id": 3,
            "staff_id": 2,
            "appointment_date": future_date(12),
            "start_time": "13:00",
        },
    ).json()
    moved = client.patch(f"/appointments/{created['id']}/status", json={"status": "Confirmed"})
    assert moved.status_code == 200
    assert moved.json()["status"] == "Confirmed"
    assert any(item["event_type"] == "Status changed" for item in moved.json()["activity"])


def test_search_and_filter_appointments():
    response = client.get("/appointments?search=Giorgi&status=Booked")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["customer_name"] == "Giorgi T."


def test_dashboard_uses_backend_data():
    data = client.get("/dashboard").json()
    assert data["upcoming_appointments"] >= 1
    assert data["completed_revenue"] > 0
    assert data["service_mix"]


def test_delete_appointment():
    created = client.post(
        "/appointments",
        json={
            "customer_name": "Delete Customer",
            "customer_email": "delete@example.com",
            "customer_phone": "+995555303034",
            "service_id": 5,
            "staff_id": 2,
            "appointment_date": future_date(12),
            "start_time": "10:00",
        },
    ).json()
    response = client.delete(f"/appointments/{created['id']}")
    assert response.status_code == 204
    assert client.get(f"/appointments/{created['id']}").status_code == 404


def test_restore_sample_records():
    client.delete("/appointments/1")
    assert len(client.get("/appointments").json()) == 4
    response = client.post("/admin/restore-sample-records")
    assert response.status_code == 200
    assert len(client.get("/appointments").json()) == 5

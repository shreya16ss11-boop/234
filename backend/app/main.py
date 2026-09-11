from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import get_db, init_db, row_to_dict, rows_to_dicts
from .schemas import AppointmentIn, AppointmentUpdate, ServiceIn, StaffIn, StatusIn
from .seed import now_iso, record, seed_sample_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    with get_db() as conn:
        init_db(conn)
        count = conn.execute("SELECT COUNT(*) FROM services").fetchone()[0]
        if count == 0:
            seed_sample_data(conn)
    yield


app = FastAPI(title="ReserveHub API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def parse_time(value: str) -> time:
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid time: {value}") from exc


def minutes(value: str) -> int:
    parsed = parse_time(value)
    return parsed.hour * 60 + parsed.minute


def from_minutes(value: int) -> str:
    return f"{value // 60:02d}:{value % 60:02d}"


def add_minutes(start: str, amount: int) -> str:
    return from_minutes(minutes(start) + amount)


def row(conn, sql: str, params: tuple = ()) -> dict:
    item = row_to_dict(conn.execute(sql, params).fetchone())
    if item is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return item


def validate_service_staff(conn, service_id: int, staff_id: int) -> tuple[dict, dict]:
    service = row_to_dict(conn.execute("SELECT * FROM services WHERE id = ? AND active = 1", (service_id,)).fetchone())
    if service is None:
        raise HTTPException(status_code=422, detail="Service is unavailable")
    staff = row_to_dict(conn.execute("SELECT * FROM staff WHERE id = ? AND active = 1", (staff_id,)).fetchone())
    if staff is None:
        raise HTTPException(status_code=422, detail="Staff member is unavailable")
    linked = conn.execute(
        "SELECT 1 FROM staff_services WHERE staff_id = ? AND service_id = ?",
        (staff_id, service_id),
    ).fetchone()
    if linked is None:
        raise HTTPException(status_code=422, detail="Selected staff member does not provide this service")
    return service, staff


def is_within_availability(conn, staff_id: int, appointment_date: str, start_time: str, end_time: str) -> bool:
    day = datetime.fromisoformat(appointment_date).weekday()
    windows = conn.execute(
        "SELECT * FROM availability WHERE staff_id = ? AND weekday = ?",
        (staff_id, day),
    ).fetchall()
    start, end = minutes(start_time), minutes(end_time)
    return any(minutes(window["start_time"]) <= start and end <= minutes(window["end_time"]) for window in windows)


def has_overlap(conn, staff_id: int, appointment_date: str, start_time: str, end_time: str, exclude_id: int | None = None) -> bool:
    start, end = minutes(start_time), minutes(end_time)
    rows = conn.execute(
        """
        SELECT id, start_time, end_time FROM appointments
        WHERE staff_id = ? AND appointment_date = ? AND status NOT IN ('Cancelled', 'No-show')
        """,
        (staff_id, appointment_date),
    ).fetchall()
    for item in rows:
        if exclude_id is not None and item["id"] == exclude_id:
            continue
        if start < minutes(item["end_time"]) and end > minutes(item["start_time"]):
            return True
    blocks = conn.execute(
        "SELECT start_time, end_time FROM blocked_times WHERE staff_id = ? AND block_date = ?",
        (staff_id, appointment_date),
    ).fetchall()
    return any(start < minutes(block["end_time"]) and end > minutes(block["start_time"]) for block in blocks)


def appointment_detail(conn, appointment_id: int) -> dict:
    appointment = row(
        conn,
        """
        SELECT appointments.*, services.name AS service_name, services.price, services.duration_minutes,
               staff.name AS staff_name, staff.role AS staff_role
        FROM appointments
        JOIN services ON services.id = appointments.service_id
        JOIN staff ON staff.id = appointments.staff_id
        WHERE appointments.id = ?
        """,
        (appointment_id,),
    )
    appointment["activity"] = rows_to_dicts(
        conn.execute("SELECT * FROM activity WHERE appointment_id = ? ORDER BY id DESC", (appointment_id,)).fetchall()
    )
    return appointment


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "ReserveHub API"}


@app.get("/settings")
def settings_view() -> dict:
    with get_db() as conn:
        return row(conn, "SELECT * FROM business_settings WHERE id = 1")


@app.get("/services")
def list_services(active: bool | None = None) -> list[dict]:
    where = "" if active is None else "WHERE active = ?"
    params = () if active is None else (1 if active else 0,)
    with get_db() as conn:
        return rows_to_dicts(conn.execute(f"SELECT * FROM services {where} ORDER BY category, name", params).fetchall())


@app.post("/services", status_code=201)
def create_service(payload: ServiceIn) -> dict:
    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO services (name, category, description, duration_minutes, price, active, color)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (payload.name, payload.category, payload.description, payload.duration_minutes, payload.price, int(payload.active), payload.color),
        )
        return row(conn, "SELECT * FROM services WHERE id = ?", (cursor.lastrowid,))


@app.put("/services/{service_id}")
def update_service(service_id: int, payload: ServiceIn) -> dict:
    with get_db() as conn:
        row(conn, "SELECT * FROM services WHERE id = ?", (service_id,))
        conn.execute(
            """
            UPDATE services SET name = ?, category = ?, description = ?, duration_minutes = ?, price = ?, active = ?, color = ?
            WHERE id = ?
            """,
            (payload.name, payload.category, payload.description, payload.duration_minutes, payload.price, int(payload.active), payload.color, service_id),
        )
        return row(conn, "SELECT * FROM services WHERE id = ?", (service_id,))


@app.get("/staff")
def list_staff(service_id: int | None = None, active: bool | None = None) -> list[dict]:
    params: list[Any] = []
    joins = ""
    filters = []
    if service_id:
        joins = "JOIN staff_services ON staff_services.staff_id = staff.id"
        filters.append("staff_services.service_id = ?")
        params.append(service_id)
    if active is not None:
        filters.append("staff.active = ?")
        params.append(1 if active else 0)
    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    with get_db() as conn:
        staff = rows_to_dicts(conn.execute(f"SELECT DISTINCT staff.* FROM staff {joins} {where} ORDER BY staff.name", params).fetchall())
        for person in staff:
            person["services"] = rows_to_dicts(
                conn.execute(
                    """
                    SELECT services.* FROM services
                    JOIN staff_services ON staff_services.service_id = services.id
                    WHERE staff_services.staff_id = ?
                    ORDER BY services.name
                    """,
                    (person["id"],),
                ).fetchall()
            )
        return staff


@app.post("/staff", status_code=201)
def create_staff(payload: StaffIn) -> dict:
    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO staff (name, role, email, phone, active, bio) VALUES (?, ?, ?, ?, ?, ?)",
            (payload.name, payload.role, str(payload.email), payload.phone, int(payload.active), payload.bio),
        )
        staff_id = cursor.lastrowid
        for service_id in payload.service_ids:
            row(conn, "SELECT * FROM services WHERE id = ?", (service_id,))
            conn.execute("INSERT INTO staff_services (staff_id, service_id) VALUES (?, ?)", (staff_id, service_id))
        return row(conn, "SELECT * FROM staff WHERE id = ?", (staff_id,))


@app.get("/slots")
def available_slots(service_id: int, staff_id: int, appointment_date: date) -> dict:
    with get_db() as conn:
        service, staff = validate_service_staff(conn, service_id, staff_id)
        day = appointment_date.weekday()
        windows = conn.execute(
            "SELECT * FROM availability WHERE staff_id = ? AND weekday = ? ORDER BY start_time",
            (staff_id, day),
        ).fetchall()
        slots = []
        for window in windows:
            cursor = minutes(window["start_time"])
            end_limit = minutes(window["end_time"]) - service["duration_minutes"]
            while cursor <= end_limit:
                start = from_minutes(cursor)
                end = from_minutes(cursor + service["duration_minutes"])
                if not has_overlap(conn, staff_id, appointment_date.isoformat(), start, end):
                    slots.append(start)
                cursor += 15
    return {"service": service, "staff": staff, "date": appointment_date.isoformat(), "slots": slots}


@app.get("/appointments")
def list_appointments(
    status: str | None = None,
    staff_id: int | None = None,
    service_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
) -> list[dict]:
    filters = []
    params: list[Any] = []
    if status:
        filters.append("appointments.status = ?")
        params.append(status)
    if staff_id:
        filters.append("appointments.staff_id = ?")
        params.append(staff_id)
    if service_id:
        filters.append("appointments.service_id = ?")
        params.append(service_id)
    if date_from:
        filters.append("appointments.appointment_date >= ?")
        params.append(date_from.isoformat())
    if date_to:
        filters.append("appointments.appointment_date <= ?")
        params.append(date_to.isoformat())
    if search:
        filters.append("(appointments.customer_name LIKE ? OR appointments.customer_email LIKE ? OR services.name LIKE ? OR staff.name LIKE ?)")
        term = f"%{search}%"
        params.extend([term, term, term, term])
    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    with get_db() as conn:
        return rows_to_dicts(
            conn.execute(
                f"""
                SELECT appointments.*, services.name AS service_name, services.price, services.duration_minutes,
                       staff.name AS staff_name, staff.role AS staff_role
                FROM appointments
                JOIN services ON services.id = appointments.service_id
                JOIN staff ON staff.id = appointments.staff_id
                {where}
                ORDER BY appointments.appointment_date, appointments.start_time
                """,
                params,
            ).fetchall()
        )


@app.get("/appointments/{appointment_id}")
def get_appointment(appointment_id: int) -> dict:
    with get_db() as conn:
        return appointment_detail(conn, appointment_id)


@app.post("/appointments", status_code=201)
def create_appointment(payload: AppointmentIn) -> dict:
    if payload.appointment_date < datetime.now(timezone.utc).date():
        raise HTTPException(status_code=422, detail="Appointment date cannot be in the past")
    with get_db() as conn:
        service, _ = validate_service_staff(conn, payload.service_id, payload.staff_id)
        appointment_date = payload.appointment_date.isoformat()
        end_time = add_minutes(payload.start_time, service["duration_minutes"])
        if not is_within_availability(conn, payload.staff_id, appointment_date, payload.start_time, end_time):
            raise HTTPException(status_code=422, detail="Selected time is outside staff availability")
        if has_overlap(conn, payload.staff_id, appointment_date, payload.start_time, end_time):
            raise HTTPException(status_code=409, detail="Selected time is already booked")
        now = now_iso()
        cursor = conn.execute(
            """
            INSERT INTO appointments (
                customer_name, customer_email, customer_phone, service_id, staff_id,
                appointment_date, start_time, end_time, status, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.customer_name,
                str(payload.customer_email),
                payload.customer_phone,
                payload.service_id,
                payload.staff_id,
                appointment_date,
                payload.start_time,
                end_time,
                "Booked",
                payload.notes,
                now,
                now,
            ),
        )
        appointment_id = cursor.lastrowid
        record(conn, "Appointment booked", f"{payload.customer_name} booked a {service['name']} appointment.", appointment_id=appointment_id)
        return appointment_detail(conn, appointment_id)


@app.put("/appointments/{appointment_id}")
def update_appointment(appointment_id: int, payload: AppointmentUpdate) -> dict:
    with get_db() as conn:
        current = appointment_detail(conn, appointment_id)
        service_id = payload.service_id or current["service_id"]
        staff_id = payload.staff_id or current["staff_id"]
        appointment_date = payload.appointment_date.isoformat() if payload.appointment_date else current["appointment_date"]
        start_time = payload.start_time or current["start_time"]
        service, _ = validate_service_staff(conn, service_id, staff_id)
        end_time = add_minutes(start_time, service["duration_minutes"])
        if not is_within_availability(conn, staff_id, appointment_date, start_time, end_time):
            raise HTTPException(status_code=422, detail="Selected time is outside staff availability")
        if has_overlap(conn, staff_id, appointment_date, start_time, end_time, exclude_id=appointment_id):
            raise HTTPException(status_code=409, detail="Selected time is already booked")
        conn.execute(
            """
            UPDATE appointments
            SET customer_name = ?, customer_email = ?, customer_phone = ?, service_id = ?, staff_id = ?,
                appointment_date = ?, start_time = ?, end_time = ?, status = ?, notes = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                payload.customer_name or current["customer_name"],
                str(payload.customer_email) if payload.customer_email else current["customer_email"],
                payload.customer_phone or current["customer_phone"],
                service_id,
                staff_id,
                appointment_date,
                start_time,
                end_time,
                payload.status or current["status"],
                payload.notes if payload.notes is not None else current["notes"],
                now_iso(),
                appointment_id,
            ),
        )
        record(conn, "Appointment updated", f"Appointment #{appointment_id} was updated.", appointment_id=appointment_id)
        return appointment_detail(conn, appointment_id)


@app.patch("/appointments/{appointment_id}/status")
def update_status(appointment_id: int, payload: StatusIn) -> dict:
    with get_db() as conn:
        current = appointment_detail(conn, appointment_id)
        conn.execute(
            "UPDATE appointments SET status = ?, updated_at = ? WHERE id = ?",
            (payload.status, now_iso(), appointment_id),
        )
        record(conn, "Status changed", f"Appointment #{appointment_id} moved from {current['status']} to {payload.status}.", appointment_id=appointment_id)
        return appointment_detail(conn, appointment_id)


@app.delete("/appointments/{appointment_id}", status_code=204)
def delete_appointment(appointment_id: int) -> Response:
    with get_db() as conn:
        current = row(conn, "SELECT * FROM appointments WHERE id = ?", (appointment_id,))
        conn.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
        record(conn, "Appointment deleted", f"Appointment for {current['customer_name']} was deleted.")
    return Response(status_code=204)


@app.get("/dashboard")
def dashboard() -> dict:
    today = datetime.now(timezone.utc).date().isoformat()
    with get_db() as conn:
        one = lambda sql, params=(): conn.execute(sql, params).fetchone()[0]
        today_count = one("SELECT COUNT(*) FROM appointments WHERE appointment_date = ?", (today,))
        upcoming = one("SELECT COUNT(*) FROM appointments WHERE appointment_date >= ? AND status IN ('Booked','Confirmed')", (today,))
        completed = one("SELECT COUNT(*) FROM appointments WHERE status = 'Completed'")
        cancelled = one("SELECT COUNT(*) FROM appointments WHERE status = 'Cancelled'")
        revenue = one(
            """
            SELECT COALESCE(SUM(services.price), 0)
            FROM appointments JOIN services ON services.id = appointments.service_id
            WHERE appointments.status = 'Completed'
            """
        )
        status_counts = rows_to_dicts(conn.execute("SELECT status, COUNT(*) AS count FROM appointments GROUP BY status").fetchall())
        service_mix = rows_to_dicts(
            conn.execute(
                """
                SELECT services.name, COUNT(*) AS count
                FROM appointments JOIN services ON services.id = appointments.service_id
                GROUP BY services.name
                ORDER BY count DESC
                """
            ).fetchall()
        )
        activity = rows_to_dicts(conn.execute("SELECT * FROM activity ORDER BY id DESC LIMIT 10").fetchall())
    return {
        "today_appointments": today_count,
        "upcoming_appointments": upcoming,
        "completed_appointments": completed,
        "cancelled_appointments": cancelled,
        "completed_revenue": round(revenue, 2),
        "status_counts": status_counts,
        "service_mix": service_mix,
        "recent_activity": activity,
    }


@app.get("/activity")
def list_activity() -> list[dict]:
    with get_db() as conn:
        return rows_to_dicts(conn.execute("SELECT * FROM activity ORDER BY id DESC LIMIT 100").fetchall())


@app.post("/admin/restore-sample-records")
def restore_sample_records() -> dict:
    if not settings.sample_mode:
        raise HTTPException(status_code=403, detail="Sample record restore is disabled")
    with get_db() as conn:
        seed_sample_data(conn)
    return {"message": "ReserveHub sample records restored."}

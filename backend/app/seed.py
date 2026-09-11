from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def record(conn: sqlite3.Connection, event_type: str, description: str, appointment_id: int | None = None) -> None:
    conn.execute(
        "INSERT INTO activity (event_type, description, appointment_id, created_at) VALUES (?, ?, ?, ?)",
        (event_type, description, appointment_id, now_iso()),
    )


def seed_sample_data(conn: sqlite3.Connection) -> None:
    for table in [
        "activity",
        "appointments",
        "blocked_times",
        "availability",
        "staff_services",
        "staff",
        "services",
        "business_settings",
    ]:
        conn.execute(f"DELETE FROM {table}")
    conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('activity','appointments','blocked_times','availability','staff_services','staff','services')")

    conn.execute(
        """
        INSERT INTO business_settings (id, business_name, phone, email, address, timezone, booking_notice, slot_interval)
        VALUES (1, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "ReserveHub Studio",
            "+1 555 014 2086",
            "hello@reservehub.local",
            "24 Rustaveli Avenue, Tbilisi",
            "Asia/Tbilisi",
            "Appointments are confirmed by the service team after review.",
            15,
        ),
    )

    services = [
        ("Strategy Consultation", "Consulting", "A focused planning session for founders and operators who need a clear execution roadmap.", 60, 120.0, 1, "coral"),
        ("Brand Design Review", "Creative", "A practical review of brand assets, website visuals, and conversion points.", 45, 95.0, 1, "violet"),
        ("Technical Discovery Call", "Software", "Requirements discovery for web apps, automations, API integrations, and internal tools.", 60, 150.0, 1, "blue"),
        ("Operations Audit", "Business", "Workflow review for scheduling, client handoffs, reporting, and admin bottlenecks.", 90, 180.0, 1, "green"),
        ("Website Launch Session", "Software", "Pre-launch review covering content, analytics, accessibility, QA, and deployment readiness.", 75, 165.0, 1, "amber"),
    ]
    conn.executemany(
        """
        INSERT INTO services (name, category, description, duration_minutes, price, active, color)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        services,
    )

    staff = [
        ("Mariam Kapanadze", "Business Consultant", "mariam@reservehub.local", "+995 555 100 101", 1, "Helps service teams clarify their client workflows and improve scheduling operations."),
        ("Daniel Stone", "Product Strategist", "daniel@reservehub.local", "+995 555 100 102", 1, "Works with founders on product scope, launch plans, and customer-facing workflows."),
        ("Nino Beridze", "Design Lead", "nino@reservehub.local", "+995 555 100 103", 1, "Reviews brand, visual hierarchy, user experience, and customer booking journeys."),
    ]
    conn.executemany(
        "INSERT INTO staff (name, role, email, phone, active, bio) VALUES (?, ?, ?, ?, ?, ?)",
        staff,
    )

    staff_services = [
        (1, 1), (1, 4),
        (2, 1), (2, 3), (2, 5),
        (3, 2), (3, 5),
    ]
    conn.executemany("INSERT INTO staff_services (staff_id, service_id) VALUES (?, ?)", staff_services)

    availability_rows = []
    for staff_id in [1, 2, 3]:
        for weekday in range(0, 5):
            availability_rows.append((staff_id, weekday, "09:00", "17:00"))
    conn.executemany(
        "INSERT INTO availability (staff_id, weekday, start_time, end_time) VALUES (?, ?, ?, ?)",
        availability_rows,
    )

    today = datetime.now(timezone.utc).date()
    conn.execute(
        "INSERT INTO blocked_times (staff_id, block_date, start_time, end_time, reason) VALUES (?, ?, ?, ?, ?)",
        (2, (today + timedelta(days=2)).isoformat(), "12:00", "13:00", "Lunch meeting"),
    )

    appointments = [
        ("Ana Roberts", "ana@example.com", "+995 555 221 101", 1, 1, today.isoformat(), "10:00", "11:00", "Confirmed", "Bring Q3 growth targets."),
        ("Giorgi T.", "giorgi.t@example.com", "+995 555 221 102", 3, 2, today.isoformat(), "14:00", "15:00", "Booked", "Discuss API integration scope."),
        ("Sofia Klein", "sofia@example.com", "+995 555 221 103", 2, 3, (today + timedelta(days=1)).isoformat(), "11:30", "12:15", "Confirmed", "Website refresh review."),
        ("Luka Martin", "luka@example.com", "+995 555 221 104", 4, 1, (today + timedelta(days=2)).isoformat(), "09:30", "11:00", "Booked", "Operations workflow mapping."),
        ("Nina Patel", "nina@example.com", "+995 555 221 105", 5, 2, (today - timedelta(days=1)).isoformat(), "15:00", "16:15", "Completed", "Launch checklist completed."),
    ]
    base = datetime.now(timezone.utc).replace(microsecond=0)
    for index, appointment in enumerate(appointments):
        created = (base - timedelta(hours=8 - index)).isoformat()
        cursor = conn.execute(
            """
            INSERT INTO appointments (
                customer_name, customer_email, customer_phone, service_id, staff_id,
                appointment_date, start_time, end_time, status, notes, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (*appointment, created, created),
        )
        record(conn, "Appointment imported", f"Seeded appointment for {appointment[0]}.", appointment_id=cursor.lastrowid)
    record(conn, "Sample records restored", "ReserveHub services, staff, availability, bookings, and activity were restored.")

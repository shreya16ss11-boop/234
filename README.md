# ReserveHub

ReserveHub is a full-stack appointment booking platform for service businesses. It includes a public booking experience, service catalog, staff coverage, availability-based time slots, appointment management, status updates, dashboard metrics, activity history, and sample-record restoration for local review.

The application is built as a real frontend/backend project with working API validation and double-booking protection.

## Screenshots

![ReserveHub booking page](assets/screenshots/booking.png)

![ReserveHub admin schedule](assets/screenshots/schedule.png)

Additional verified screenshots are available in `assets/screenshots/` for booking details, services, and mobile layout.

## Features

- Public appointment booking page
- Service catalog with duration and price
- Staff members connected to the services they provide
- Availability-based slot generation
- Double-booking prevention
- Appointment create, update, delete, search, and filters
- Appointment statuses: Booked, Confirmed, Completed, Cancelled, No-show
- Admin schedule view
- Dashboard metrics from backend data
- Recent activity history
- Sample-record restoration endpoint
- Responsive light business interface
- Backend and frontend tests

## Tech Stack

- React
- TypeScript
- Vite
- Python
- FastAPI
- SQLite
- REST API
- Pydantic validation
- Pytest
- Vitest
- Responsive CSS

## Project Structure

```text
reservehub/
|-- frontend/
|-- backend/
|-- assets/
|   `-- screenshots/
|-- README.md
|-- .env.example
|-- .gitignore
|-- requirements.txt
`-- LICENSE
```

## Local Setup

Install backend dependencies:

```bash
python -m pip install -r requirements.txt
```

Install frontend dependencies:

```bash
cd frontend
npm install
```

## Run Backend

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8006
```

Backend:

```text
http://127.0.0.1:8006
```

API documentation:

```text
http://127.0.0.1:8006/docs
```

## Run Frontend

```bash
cd frontend
npm run dev -- --port 5179
```

Frontend:

```text
http://127.0.0.1:5179
```

## Testing

Backend:

```bash
python -m pytest
```

Frontend:

```bash
cd frontend
npm run test
npm run build
```

## Development Evidence

- Real source code
- FastAPI backend with SQLite persistence
- Pydantic request validation
- Service, staff, slot, appointment, dashboard, activity, and restore endpoints
- Backend double-booking protection
- Backend tests: `11 passed`
- Frontend tests: `4 passed`
- Production frontend build verified
- Real screenshots captured from the running app

## Sample Records Notice

ReserveHub includes seeded services, staff members, availability, appointments, and activity records for local development and portfolio review. These records can be restored from the admin schedule view or through the API.

## Deployment Notes

The project is structured for later deployment as two services:

- Static React frontend
- FastAPI backend with a persistent database

For production, move SQLite to a managed database, configure production CORS origins, add authentication for admin routes, and disable public sample-record restoration.

## Future Improvements

- Admin authentication
- Email confirmations
- Calendar export
- Staff-specific booking links
- Recurring availability editor
- Payment deposits
- Multi-location support
- Deployment pipeline and test badges

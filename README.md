# Doctor_reservation

Project: Clinic booking system — backend take-home assessment

**Overview**
This project implements a small clinic booking API: patients can view a doctor's
available 30-minute slots, book an appointment, cancel, and reschedule. The
implementation uses FastAPI and SQLite (chosen for simplicity during the
exercise).

**Tech stack (chosen)**
- FastAPI for the web API
- SQLite for the database (dev / simple deploy)
- SQLModel / SQLAlchemy + Pydantic for models and validation
- Pytest for tests

**Section 1 — System design**

**Models**
- Doctor: `id`, `name`, (optional `specialty`), contact info.
- WorkingHours: `id`, `doctor_id`, `weekday` (0=Mon..6=Sun), `start_time`, `end_time`.
	- Represents recurring weekly working hours. Times are stored as local times.
- Patient: `id`, `name`, `email`, `phone`.
- Appointment: `id`, `doctor_id`, `patient_id`, `start_at` (datetime, UTC),
	`end_at` (datetime, UTC), `status` (`booked` | `cancelled`), `cancel_reason`,
	timestamps `created_at` / `updated_at`.

Notes: appointments are always 30-minute slots; `end_at` = `start_at` + 30m.

**Key components**
- Availability service: given `doctor_id` and date, compute all 30-minute slots
	within the doctor's working hours for that weekday, filter out slots already
	taken (appointments with `status=booked`) and slots in the past.
- Booking endpoint: validates requested slot falls within working hours, is not
	in the past, and is not already taken. Creates an `Appointment` with
	`status=booked`.
- Cancellation endpoint: sets `status=cancelled`, stores `cancel_reason`, and
	frees the slot for others.
- Reschedule endpoint: validates the new slot like a fresh booking; if valid,
	updates the appointment's `start_at`/`end_at` and frees the old slot.

**Slot generation logic**
- Read doctor's `WorkingHours` for the given weekday.
- Build contiguous 30-minute slots between `start_time` and `end_time`.
- Convert slot times to UTC-localized datetimes for the requested date.
- Exclude slots that are already booked (existing `Appointment` with
	overlapping `start_at` and `status=booked`).

**Validation rules**
- Slot must be fully inside declared working hours.
- Cannot book in the past.
- (Bonus) Prevent bookings within 1 hour of now.
- Cannot reschedule a cancelled appointment.
- Cancelling an already-cancelled appointment returns an error.

**Concurrency & consistency**
- Enforce a DB-level uniqueness constraint on `(doctor_id, start_at)` for
	active/booked appointments where possible, or use a transaction to check-and-insert.
- Use transactions when creating or rescheduling appointments to avoid race
	conditions where two clients attempt to book the same slot.

**Trade-offs & assumptions**
- Using recurring `WorkingHours` (weekday-based) is simple and fits the
	requirement; it doesn't support ad-hoc exceptions (vacations / days off). For
	real production, we'd add an `OffDay` or `Override` model.
- Times: to keep the implementation simple, times are stored/handled in UTC in
	the DB; working hours are defined in the clinic's local timezone (documented
	in the README). Clients should send/receive ISO 8601 datetimes in UTC.
- SQLite chosen for speed of iteration and easy deployment; migrating to
	Postgres later is straightforward.

**APIs (high-level)**
- `POST /appointments` — Book a slot.
- `GET /doctors/{id}/availability?date=YYYY-MM-DD` — List available 30-min slots.
- `PATCH /appointments/{id}/cancel` — Cancel with a reason.
- `PATCH /appointments/{id}/reschedule` — Move to a new slot.
- Bonus: `GET /patients/{id}/appointments` — upcoming appointments.

**Testing**
- Focus on booking logic: validation, slot generation, race conditions (as far
	as unit tests allow), cancellation, reschedule flows.

**Next steps**
1. Scaffold FastAPI project structure and database models.
2. Implement endpoints and validations, plus tests for booking logic.
3. Add CI (GitHub Actions) to run tests and deploy on merge (e.g., to Render).

If you'd like, I can now scaffold the FastAPI app, models, and initial
endpoints using SQLite. Which timezone should I assume for working hours (UTC
or a specific zone)?

**CI/CD & Deployment (how to deploy)**
- I added a GitHub Actions workflow at `.github/workflows/ci.yml` that:
	- Runs `pytest` on pull requests and pushes to `main`.
	- On push to `main`, if the repository has the secrets `RENDER_API_KEY` and
		`RENDER_SERVICE_ID` set, the workflow triggers a deploy on Render via the
		Render API.

To enable auto-deploy on merge to `main` (Render):
1. Create a service on Render and note its `SERVICE_ID`.
2. In your GitHub repo, go to Settings → Secrets and create `RENDER_API_KEY` (a
	 Render API key) and `RENDER_SERVICE_ID` with the service id.
3. Merge PRs into `main` — the workflow will run tests and trigger a deploy.

If you prefer another provider (Railway, Fly.io, etc.) I can adapt the
workflow or provide a deploy script.

Local run:
```bash
source .venv/bin/activate
python -m uvicorn app.main:app --reload
```

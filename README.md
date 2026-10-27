# Webservices: Students & Reports API

Two small Flask REST APIs for managing students and their reports, packaged with Docker.

| Version | File | Port (Docker) | Description |
|---|---|---|---|
| **Mine** | `app.py` | `5000` | Students and reports as separate resources, JWT authentication, input validation |
| **Class (teacher)** | `classwork.py` | `5001` | Class version: students with nested reports, file logging |

Both versions keep their data **in memory**: everything resets when the container restarts.

## Project structure

```
.
├── app.py               # My API (JWT, students, reports)
├── classwork.py         # Teacher's class API (students with nested reports)
├── Dockerfile           # Python 3.12-slim image, runs either app via APP_MODULE
├── docker-compose.yml   # Two services: mine (5000) and teacher (5001)
├── requirements.txt     # Flask, PyJWT and dependencies
├── .env.example         # Example environment variables
├── .dockerignore
├── .gitignore
├── postman/             # Postman collection(s) for testing
└── logs/                # Created at runtime (ignored by git)
```

## Quick start with Docker

Requirements: [Docker](https://docs.docker.com/get-docker/) with Docker Compose.

```bash
# Build and start both APIs
docker compose up --build

# Or start only one of them
docker compose up --build mine
docker compose up --build teacher
```

| Service | URL |
|---|---|
| `mine` (`app.py`) | http://localhost:5000 |
| `teacher` (`classwork.py`) | http://localhost:5001 |

Stop everything with `docker compose down`.

### Environment variables

Copy `.env.example` to `.env` to set values for Compose (for example `FLASK_DEBUG`).

| Variable | Default | Used by | Purpose |
|---|---|---|---|
| `APP_MODULE` | `app` | Docker | Which file to run (`app` or `classwork`); set per service in `docker-compose.yml` |
| `PORT` | `5000` | Docker / `classwork.py` | Port inside the container |
| `FLASK_DEBUG` | `0` | both | Set to `1` to enable debug mode |
| `LOG_DIR` | `/app/logs` (Docker), `logs` (local) | `classwork.py` | Folder for `app.log` |
| `SECRET_KEY` | `change-this-secret` | `app.py` | Key used to sign JWT tokens |
| `ACCESS_MINUTES` | `2` | `app.py` | Access token lifetime |
| `REFRESH_MINUTES` | `10` | `app.py` | Refresh token lifetime |

> **Note:** `docker-compose.yml` only passes `APP_MODULE` and `FLASK_DEBUG` to the containers. `SECRET_KEY`, `ACCESS_MINUTES` and `REFRESH_MINUTES` keep their defaults unless you add them to the `environment:` section (or an `env_file:`) of the `mine` service.

## Logs

Logs are written to files so errors can be checked after the fact. Each service mounts its own folder on your machine:

| Service | Host folder | Files |
|---|---|---|
| `mine` | `./logs/mine/` | `server.log` (all server output, including the `[ERROR ...]` messages printed by `app.py`) |
| `teacher` | `./logs/classwork/` | `server.log` (server output) and `app.log` (one line per request plus unhandled errors, rotating: 1 MB, 3 backups) |

```bash
# Follow a log live
tail -f logs/mine/server.log
tail -f logs/classwork/app.log
```

## Run locally without Docker

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt

python app.py                   # http://127.0.0.1:5000
python classwork.py             # http://0.0.0.0:5000
```

---

## API 1: `app.py` (my version)

All request bodies are **JSON lists**, not objects. Empty values are rejected with `400`.

### Authentication

Access tokens are short-lived JWTs (HS256). Send them as `Authorization: Bearer <token>`.

| Method | Route | Body | Response |
|---|---|---|---|
| POST | `/login` | `["username", "password"]` | `[access_token, refresh_token]` |
| POST | `/refresh` | none; send the **refresh** token in the `Authorization` header | `[new_access_token]` |

Demo account: `rahma` / `1234` (hard-coded in `app.py`, for testing only).

### Students

| Method | Route | Auth | Body | Description |
|---|---|---|---|---|
| GET | `/students` | access token | n/a | List all students |
| GET | `/students/<id_s>` | access token | n/a | Get one student |
| POST | `/students` | none | `[fn, ln, level, id_r]` or `[fn, ln, level, degree, id_r]` | Add a student (`id_r` is always last) |

A student is returned as `[id_s, fn, ln, degree, level, id_r]`. `degree` is optional and may be `null`.

Rules for `POST /students`:
- `id_r` must be a number and the report must exist (`404` otherwise)
- A report has at most **2 students** (`400` when full)

### Reports

| Method | Route | Auth | Body | Description |
|---|---|---|---|---|
| GET | `/reports` | none | n/a | List all reports |
| GET | `/reports/<id_r>` | none | n/a | Get one report |
| POST | `/reports` | none | `[title, type, k1, k2, k3, report_date]` | Add a report |

A report is returned as `[id_r, title, type, k1, k2, k3, report_date]`.

Rules for `POST /reports`:
- `type` must be one of: `Mini Senior Project`, `PhD Thesis`, `Internship`, `Master's Thesis`
- `report_date` must use the format `YYYY-MM-DD`

### Example

```bash
# 1. Log in
curl -X POST http://localhost:5000/login \
  -H "Content-Type: application/json" \
  -d '["rahma", "1234"]'
# -> ["<access_token>", "<refresh_token>"]

# 2. List students (token required)
curl http://localhost:5000/students \
  -H "Authorization: Bearer <access_token>"

# 3. Add a report
curl -X POST http://localhost:5000/reports \
  -H "Content-Type: application/json" \
  -d '["Sales Forecasting", "Internship", "sales", "forecast", "python", "2026-10-20"]'

# 4. Add a student to report 2 (reports hold at most 2 students)
curl -X POST http://localhost:5000/students \
  -H "Content-Type: application/json" \
  -d '["Amine", "Khelifi", "Senior", "Bachelor", 2]'
```

On Windows PowerShell, use `curl.exe` instead of `curl`, or use the Postman collection.

### Error responses

Errors are returned as a JSON list with one message, for example `["Token expired"]`, with the matching HTTP status (`400`, `401`, `404`).

---

## API 2: `classwork.py` (class version)

No authentication. Students are objects with their reports nested inside.

| Method | Route | Body | Description |
|---|---|---|---|
| GET | `/students/` | n/a | List all students |
| POST | `/students/` | `{"FN": "...", "LN": "...", "reports": []}` | Add a student (`reports` is optional) |
| GET | `/student/<id>` | n/a | Get one student |
| GET | `/student/<id>/report` | n/a | List a student's reports |
| POST | `/student/<id>/report` | `{"title": "...", "type": "..."}` | Add a report to a student |

Note the routes: the list and create routes use `/students/` (with a trailing slash), while the single-student routes use `/student/<id>`.

### Example

```bash
curl http://localhost:5001/students/

curl -X POST http://localhost:5001/students/ \
  -H "Content-Type: application/json" \
  -d '{"FN": "Sara", "LN": "Trabelsi"}'

curl -X POST http://localhost:5001/student/1/report \
  -H "Content-Type: application/json" \
  -d '{"title": "Network Audit", "type": "Internship"}'
```

Unknown students return `404` with `{"message": "Student not found"}`. Unexpected errors return `500` with `{"message": "Internal server error"}` and the full traceback is written to `app.log`.

---

## Testing with Postman

Import the collection from the `postman/` folder. For `app.py`, call `/login` first, then paste the access token as a Bearer token for the protected routes.

## Tech stack

- Python 3.12
- Flask 3.1
- PyJWT
- Docker and Docker Compose

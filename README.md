# HRMS — Human Resource Management System

A full-stack Human Resource Management System built with **React + Vite**, **FastAPI**, **SQLAlchemy**, **Alembic**, and **PostgreSQL**.

## Main features

- JWT-based authentication and role-based permissions for Admin, HR, and Employee roles.
- Employee onboarding, profile management, department/designation assignments, and employee deactivation.
- Employee document uploads with file type/signature checks and a 5 MB size limit.
- Employee check-in/check-out, working-time calculation, attendance history, monthly summaries, and authorized attendance correction.
- Leave types, leave applications, leave balances, and HR/Admin approval or rejection workflow.
- Monthly payroll generation, adjustments, payroll finalization/locking, and simulated salary credit.
- Salary-slip PDF generation and authorized downloads.
- In-app notifications, email delivery logs, and retry support for failed/skipped email delivery.
- Dashboard metrics, attendance/leave/payroll reports, CSV/PDF exports, and audit logs.

## Technology stack

| Layer | Technology |
|---|---|
| Frontend | React, Vite, React Router, Axios |
| Backend | Python 3.11, FastAPI, Pydantic |
| Data access | SQLAlchemy |
| Database migrations | Alembic |
| Database | PostgreSQL |
| Authentication | JWT bearer access tokens, password hashing, RBAC permissions |
| Documents/reports | Secure file validation, ReportLab PDF generation, CSV export |
| Automated testing | Pytest, FastAPI TestClient |

## Project layout

```text
HRMS/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/   # API routes
│   │   ├── core/               # configuration, security, permissions, audit middleware
│   │   ├── db/                 # SQLAlchemy database setup and initialization
│   │   ├── models/             # database models
│   │   ├── schemas/             # request/response validation
│   │   ├── services/            # business logic
│   │   └── templates/emails/    # email templates
│   ├── alembic/                 # database migrations
│   ├── tests/                   # unit, integration, and security tests
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── src/api/                 # Axios clients and API functions
│   ├── src/features/            # authentication, dashboard, employees, attendance, leave, payroll, etc.
│   ├── src/components/          # shared UI components
│   └── src/app/router.jsx       # application routes
├── postman/
│   ├── HRMS.postman_collection.json
│   └── HRMS.local.postman_environment.json
├── docs/
│   └── postman-guide.md
└── README.md
```

## Prerequisites

- Python 3.11 recommended for the backend virtual environment.
- Node.js and npm for the React/Vite frontend.
- PostgreSQL running locally or a configured PostgreSQL instance.
- Git and Postman (Postman is optional but recommended for API verification).

## Backend setup (Windows PowerShell)

Run the commands from the repository root. Preserve your existing working `.env`; do not overwrite it with example credentials.

```powershell
Set-Location .\backend

# Activate the existing virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies if not already installed
python -m pip install -r .\requirements.txt

# Apply database migrations
python -m alembic upgrade head

# Start the API
python -m uvicorn app.main:app --reload
```

The API should be available at `http://127.0.0.1:8000`. Open `http://127.0.0.1:8000/docs` for the authoritative list of available routes and schemas.

### Configuration

- Configure database connection, JWT secret, CORS/frontend origin, upload settings, and optional SMTP values in `backend/.env`.
- Use `backend/.env.example` as a reference only. Do not paste real secrets into source control or this README.
- For a brand-new database, run the project's existing initialization/seed procedure after migrations so the required roles, permissions, and administrator account are present. Do not rerun seeding blindly against an existing database.

## Frontend setup (second PowerShell terminal)

```powershell
Set-Location .\frontend
npm install
npm run dev
```

Use the URL printed by Vite in the terminal. The frontend API client defaults to `http://127.0.0.1:8000/api/v1`; set `VITE_API_BASE_URL` only if your backend address is different.

## Automated verification

Run backend tests from the `backend` folder:

```powershell
python -m pytest -q
```

The latest test run reported **190 passed, 0 failed**. It also reported deprecation warnings from the installed Starlette/httpx combination and older HTTP status constants; these warnings did not fail the suite.

Run a frontend production build from the `frontend` folder:

```powershell
npm run build
```

The latest build completed successfully. Vite emitted a bundle-size advisory for a JavaScript chunk over 500 kB; this is an optimisation warning, not a build failure.

## Postman API testing

1. Open Postman and import `postman/HRMS.postman_collection.json`.
2. Import and select `postman/HRMS.local.postman_environment.json` as the active environment.
3. Set the `email` and `password` variables to a valid **local test account**. Do not store production credentials in the environment file.
4. Run **Authentication → Login** first. The collection saves the returned access token in the environment's `accessToken` variable.
5. Run authorized requests using an account with the required role/permissions. Fill in resource ID variables such as `employeeId`, `leaveId`, or `runId` using IDs returned by earlier requests.
6. Consult `docs/postman-guide.md` and `http://127.0.0.1:8000/docs` for payload schemas and query parameters.

**Important:** Payroll simulation, payroll locking, document deletion, and email retry are state-changing operations. Use a local/test database and test accounts. `simulate-credit` is a simulation, not a bank transfer; it may queue real emails if SMTP is configured. Email retry can send an email again.

## Security and repository hygiene

- Never commit `.env`, passwords, JWT secrets, real employee data, uploaded documents, generated salary slips, local databases, `.venv`, `node_modules`, or build output.
- The root `.gitignore` template in this package excludes these local/private artifacts while keeping `.env.example`, source files, Alembic migrations, docs, tests, and the sanitised Postman collection/environment.
- Before pushing, inspect `git status --short` and verify no secrets or private files are staged.

## Current verification status

- Backend automated suite: 190 passed in the latest reported run.
- Frontend production build: successful in the latest reported run.
- Employee attendance workflow and Attendance Days/Present Days were manually checked in the browser by the developer.
- Audit Logs View/Hide details were confirmed to appear lower on the page after scrolling; no code change was required for that behavior.
- Import the Postman collection and run the smoke tests against the local server before submission.

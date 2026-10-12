Certify — Bulk Certificate Generator

A backend API (FastAPI + SQLite) that accepts a list of recipients, generates a PDF certificate for each one from a single predefined template, tracks the status of the job, and lets you download the results. It also ships with a small web dashboard, served by the same server.

Features
Bulk generation: one request can contain many recipients.
Validation of event name, date, issuer, recipient names and email addresses.
PDF certificates generated with ReportLab from one predefined template (logo and signature images included).
Job and per-certificate status stored in a relational database (SQLite via SQLAlchemy).
A failure on one certificate does not stop the others in the same job.
Download a single certificate as PDF, or all certificates of a job as a ZIP.
Web dashboard for uploading a CSV/Excel recipient list, previewing, generating and downloading.
Tech stack

Python 3.12 · FastAPI · Pydantic · SQLAlchemy · SQLite · ReportLab · Pytest · uv

Project structure
text
Bulk_Certificate_Generator/
├── src/bulk_certificate_generator/
│   ├── main.py                  # FastAPI app and API endpoints
│   ├── schemas.py               # Request validation (Pydantic)
│   ├── models.py                # Database tables: Job, Certificate
│   ├── database.py              # SQLite engine and session
│   ├── certificate_generator.py # PDF generation (ReportLab)
│   └── templates/               # Logo and signature images used in the certificate
├── frontend/                    # Web dashboard (index.html, logo files)
├── tests/test_main.py
├── run.py                       # Starts the server and opens the browser
├── start_app.bat                # Windows double-click launcher
├── pyproject.toml
└── uv.lock
Setup

You need Python 3.12+ and uv.

bash
cd Bulk_Certificate_Generator
uv sync
Run the application

Option 1 — one command (opens the dashboard in your browser):

bash
uv run python run.py

Option 2 — Windows: double-click start_app.bat. If Windows blocks it, right-click the file → Properties → tick Unblock → OK.

Option 3 — plain uvicorn:

bash
uv run uvicorn --app-dir src bulk_certificate_generator.main:app --reload

Then open:

URL	What it is
http://127.0.0.1:8000/app/	Web dashboard
http://127.0.0.1:8000/docs	Interactive API docs (Swagger UI)
Run the tests
bash
uv run pytest

Currently covered: the health endpoint and rejection of an invalid generation request (HTTP 422).

API
Method	Endpoint	Description
GET	/	Health check
POST	/jobs	Create a bulk generation job
GET	/jobs/{job_id}	Job status and per-certificate results
GET	/certificates/{certificate_id}/download	Download one certificate (PDF)
GET	/jobs/{job_id}/download-zip	Download all successful certificates of a job (ZIP)
Submit a certificate generation request

Save this as request.json:

json
{
  "event_name": "Python Workshop",
  "event_date": "2026-10-08",
  "issuer": "ABC Organization",
  "recipients": [
    { "name": "Shaline Pattabi", "email": "shaline@example.com" },
    { "name": "John Doe", "email": "john@example.com" }
  ]
}

Send it:

bash
curl -X POST http://127.0.0.1:8000/jobs \
  -H "Content-Type: application/json" \
  -d @request.json

Response:

json
{ "job_id": 1, "status": "completed", "total": 2, "successful": 2, "failed": 0 }

You can also paste the same JSON into POST /jobs in the Swagger UI at /docs.

Check job status
bash
curl http://127.0.0.1:8000/jobs/1
json
{
  "job_id": 1,
  "status": "completed",
  "total": 2,
  "successful": 2,
  "failed": 0,
  "certificates": [
    { "certificate_id": 1, "recipient_name": "Shaline Pattabi", "status": "completed" },
    { "certificate_id": 2, "recipient_name": "John Doe", "status": "completed" }
  ]
}

Job status is one of completed, completed_with_errors (some succeeded, some failed) or failed (all failed). Each certificate is completed or failed.

Retrieve generated certificates
bash
# One certificate (use a certificate_id from the job status)
curl -o certificate.pdf http://127.0.0.1:8000/certificates/1/download

# All successful certificates of a job as a ZIP
curl -o certificates.zip http://127.0.0.1:8000/jobs/1/download-zip

Generated PDFs are saved in generated_certificates/, and job data is stored in certificates.db. Both are created automatically and are excluded from Git.

Design decisions
FastAPI + Pydantic. Request validation happens before any work starts. An empty event name, bad date, empty recipient list, blank recipient name or invalid email returns HTTP 422, and no job is created.
SQLite with SQLAlchemy. A relational database with zero setup, which keeps the project easy to run. Two tables: jobs (status and success/failure counts) and certificates (recipient, status, file path, error message), linked by job_id.
Synchronous processing. Each job is processed inside the POST /jobs request, and the response already contains the final result. I chose this because generating a single PDF locally is quick, it keeps the system simple, and it needs no queue or worker infrastructure. The trade-off is that a very large batch holds the request open. For heavy production use, I would move generation to a background worker (for example Celery with Redis) and let clients poll GET /jobs/{job_id}, which already exists.
Failure isolation. Every certificate is generated inside its own try/except. If one fails, it is marked failed with an error message, the others continue, and the job ends as completed_with_errors (or failed if every certificate failed).
One template. A single predefined certificate layout drawn with ReportLab. Long names or event titles are shrunk to fit.
Safe, unique filenames. Recipient names are sanitised for file names, and a counter is added when two recipients have the same name, so no file is overwritten.
Dashboard served by the API. The frontend is mounted at /app, so it shares the same origin as the API and needs no separate server.
Known limitations
Generation is synchronous (see above).
There is no authentication.
The error message of a failed certificate is stored in the database but is not yet returned by GET /jobs/{job_id}.
The test suite is small and can be extended (job creation, certificate generation, status, individual failure and download).
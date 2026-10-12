from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from pathlib import Path
import io
import zipfile
import logging

from .database import Base, engine, get_db
from . import models
from .models import Job, Certificate
from .schemas import CertificateRequest
from .certificate_generator import generate_certificate


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Bulk Certificate Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


# Serve the frontend from the API itself: http://127.0.0.1:8000/app/
# (same origin, so no CORS issues and it works without Live Server).
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_DIR.is_dir():
    app.mount(
        "/app",
        StaticFiles(directory=FRONTEND_DIR, html=True),
        name="frontend"
    )


@app.get("/")
def home():
    return {"message": "Bulk Certificate Generator API"}


@app.post("/jobs")
def create_job(
    request: CertificateRequest,
    db: Session = Depends(get_db)
):
    logger.info(
        "POST /jobs received: %s recipients",
        len(request.recipients)
    )

    job = Job(
        status="processing",
        total=len(request.recipients),
        successful=0,
        failed=0
    )

    try:
        # Save the job first
        db.add(job)
        db.flush()

        logger.info("Job created with ID %s", job.id)

        # Save recipient records
        for recipient in request.recipients:
            certificate = Certificate(
                job_id=job.id,
                recipient_name=recipient.name,
                recipient_email=str(recipient.email),
                status="pending"
            )
            db.add(certificate)

        db.flush()

        logger.info("Recipient records saved for job %s", job.id)

        # Retrieve the certificates
        certificates = (
            db.query(Certificate)
            .filter(Certificate.job_id == job.id)
            .all()
        )

        logger.info(
            "Found %s certificates for job %s",
            len(certificates),
            job.id
        )

        # Generate each PDF
        for certificate in certificates:
            try:
                logger.info(
                    "Generating PDF for certificate %s: %s",
                    certificate.id,
                    certificate.recipient_name
                )

                file_path = generate_certificate(
                    recipient_name=certificate.recipient_name,
                    event_name=request.event_name,
                    event_date=str(request.event_date),
                    issuer=request.issuer,
                    certificate_id=certificate.id
                )

                certificate.file_path = str(file_path)
                certificate.status = "completed"
                job.successful += 1

                logger.info(
                    "PDF generated successfully: %s",
                    file_path
                )

            except Exception as error:
                logger.exception(
                    "Failed to generate PDF for %s",
                    certificate.recipient_name
                )

                certificate.status = "failed"
                certificate.error_message = str(error)
                job.failed += 1

        # Update the final job status
        if job.failed == 0:
            job.status = "completed"
        elif job.successful == 0:
            job.status = "failed"
        else:
            job.status = "completed_with_errors"

        logger.info(
            "Saving job %s: successful=%s, failed=%s",
            job.id,
            job.successful,
            job.failed
        )

        db.commit()
        db.refresh(job)

        result = {
            "job_id": job.id,
            "status": job.status,
            "total": job.total,
            "successful": job.successful,
            "failed": job.failed
        }

        logger.info("POST /jobs completed: %s", result)

        return result

    except HTTPException:
        db.rollback()
        raise

    except Exception as error:
        db.rollback()

        logger.exception("Failed to process certificate job")

        raise HTTPException(
            status_code=500,
            detail=f"Failed to process certificate job: {str(error)}"
        ) from error


@app.get("/jobs/{job_id}")
def get_job_status(
    job_id: int,
    db: Session = Depends(get_db)
):
    logger.info("Fetching job %s", job_id)

    job = db.query(Job).filter(Job.id == job_id).first()

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    return {
        "job_id": job.id,
        "status": job.status,
        "total": job.total,
        "successful": job.successful,
        "failed": job.failed,
        "certificates": [
            {
                "certificate_id": cert.id,
                "recipient_name": cert.recipient_name,
                "status": cert.status
            }
            for cert in job.certificates
        ]
    }


@app.get("/certificates/{certificate_id}/download")
def download_certificate(
    certificate_id: int,
    db: Session = Depends(get_db)
):
    certificate = (
        db.query(Certificate)
        .filter(Certificate.id == certificate_id)
        .first()
    )

    if certificate is None:
        raise HTTPException(
            status_code=404,
            detail="Certificate not found"
        )

    if not certificate.file_path:
        raise HTTPException(
            status_code=404,
            detail="Certificate file not available"
        )

    file_path = Path(certificate.file_path)

    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Certificate PDF file not found"
        )

    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=file_path.name
    )


@app.get("/jobs/{job_id}/download-zip")
def download_certificates_zip(
    job_id: int,
    db: Session = Depends(get_db)
):
    logger.info("Preparing ZIP for job %s", job_id)

    job = db.query(Job).filter(Job.id == job_id).first()

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    certificates = (
        db.query(Certificate)
        .filter(
            Certificate.job_id == job_id,
            Certificate.status == "completed"
        )
        .all()
    )

    # Keep only generated PDFs that exist
    pdf_files = []

    for certificate in certificates:
        if certificate.file_path:
            file_path = Path(certificate.file_path)

            if file_path.is_file():
                pdf_files.append(file_path)

    if not pdf_files:
        raise HTTPException(
            status_code=404,
            detail="No generated certificate PDFs found for this job"
        )

    # Build the ZIP in memory
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(
        zip_buffer,
        mode="w",
        compression=zipfile.ZIP_DEFLATED
    ) as zip_file:
        for index, file_path in enumerate(pdf_files, start=1):
            # Prefix filenames to avoid duplicate names in the ZIP
            archive_name = f"{index}_{file_path.name}"

            zip_file.write(
                file_path,
                arcname=archive_name
            )

    logger.info(
        "ZIP prepared for job %s with %s PDFs",
        job_id,
        len(pdf_files)
    )

    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition":
                f'attachment; filename="certificates_job_{job_id}.zip"'
        }
    )
from datetime import date

from pydantic import BaseModel, EmailStr, Field


class Recipient(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr


class CertificateRequest(BaseModel):
    event_name: str = Field(min_length=1)
    event_date: date
    issuer: str = Field(min_length=1)
    recipients: list[Recipient] = Field(min_length=1)
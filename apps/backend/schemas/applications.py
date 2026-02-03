from pydantic import BaseModel, Field


class CreateApplicationRequest(BaseModel):
    username: str = Field(..., min_length=1)
    job_offer_id: str = Field(..., min_length=1)


class CreateApplicationResponse(BaseModel):
    application_id: str

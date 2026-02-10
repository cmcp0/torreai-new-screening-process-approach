from typing import Optional

from pydantic import BaseModel, Field, StrictStr


class CreateApplicationRequest(BaseModel):
    username: Optional[StrictStr] = Field(default=None)
    job_offer_id: Optional[StrictStr] = Field(default=None)


class CreateApplicationResponse(BaseModel):
    application_id: str

from pydantic import BaseModel, Field


class AnalysisResponse(BaseModel):
    fit_score: int = Field(..., ge=0, le=100)
    skills: list = Field(default_factory=list)

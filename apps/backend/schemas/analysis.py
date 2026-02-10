from pydantic import BaseModel, Field


class AnalysisResponse(BaseModel):
    fit_score: int = Field(..., ge=0, le=100)
    skills: list[str] = Field(default_factory=list)
    failed: bool = Field(default=False, description="True when analysis could not be completed")

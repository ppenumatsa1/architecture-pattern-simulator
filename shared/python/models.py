from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

RiskLevel = Literal["LOW", "MEDIUM", "HIGH"]


class Submission(BaseModel):
    id: str = Field(..., min_length=1, description="Unique submission identifier")
    payload: dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "forbid"


class RiskResult(BaseModel):
    submission_id: str = Field(..., min_length=1)
    score: int = Field(..., ge=0)
    risk_level: RiskLevel
    reasons: list[str] = Field(default_factory=list)

    class Config:
        extra = "forbid"


class TimelineEvent(BaseModel):
    id: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1)
    timestamp: datetime
    data: dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "forbid"

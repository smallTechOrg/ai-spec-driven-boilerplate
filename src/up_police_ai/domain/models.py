from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Officer(BaseModel):
    id: str
    name: str
    badge_number: str
    created_at: datetime

    model_config = {"from_attributes": True}


class Assessment(BaseModel):
    id: str
    officer_id: str
    score_a1: float
    score_a2: float
    score_a3: float
    score_a4: float
    score_a5: float
    score_b1: float
    score_b2: float
    score_b3: float
    score_b4: float
    score_b5: float
    score_c1: float
    score_c2: float
    score_c3: float
    score_c4: float
    score_c5: float
    score_d1: float
    score_d2: float
    score_d3: float
    score_d4: float
    score_d5: float
    avg_a: float
    avg_b: float
    avg_c: float
    avg_d: float
    avg_overall: float
    completed_at: datetime

    model_config = {"from_attributes": True}


class PlanDay(BaseModel):
    id: str
    plan_id: str
    day_number: int
    focus_area: str
    level: str
    task_key: str
    status: str
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class LearningPlan(BaseModel):
    id: str
    officer_id: str
    assessment_id: str
    created_at: datetime
    days: list[PlanDay] = []

    model_config = {"from_attributes": True}

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from schema import CustomerInput, PredictionOutput


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class EmployeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str
    role: str


class EmployeeCreate(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    full_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=128)
    role: Literal["employee", "admin"] = "employee"


class SignupRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    full_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class PredictionHistory(PredictionOutput):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_input: CustomerInput
    created_at: datetime
    employee: EmployeeResponse | None = None


class BatchPredictionRecord(PredictionOutput):
    row_number: int
    customer_input: CustomerInput


class BatchPredictionResponse(BaseModel):
    predictions: list[BatchPredictionRecord]


class PredictionInsight(BaseModel):
    feature_key: str
    feature_label: str
    current_value: str
    contribution_percent: float
    estimated_probability_reduction: float
    reason: str
    recommendation: str


class PredictionExplanation(BaseModel):
    headline: str
    summary: str
    drivers: list[PredictionInsight]


class SinglePredictionResponse(PredictionOutput):
    explanation: PredictionExplanation

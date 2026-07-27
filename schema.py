"""
Pydantic schema for a single customer's input data.

IMPORTANT: These field names and value options are based on the standard
"Telco Customer Churn" dataset structure. Open your notebook and check:
  1. Are these EXACTLY your column names? (rename here if not)
  2. Are the categorical value strings identical to what your LabelEncoder
     was fit on? (e.g. "Yes"/"No" vs "yes"/"no" — case matters!)
"""

from pydantic import BaseModel
from typing import Literal


class CustomerInput(BaseModel):
    gender: Literal["Male", "Female"]
    SeniorCitizen: int  # 0 or 1
    Partner: Literal["Yes", "No"]
    Dependents: Literal["Yes", "No"]
    tenure: int  # months with the company
    PhoneService: Literal["Yes", "No"]
    MultipleLines: Literal["Yes", "No", "No phone service"]
    InternetService: Literal["DSL", "Fiber optic", "No"]
    OnlineSecurity: Literal["Yes", "No", "No internet service"]
    OnlineBackup: Literal["Yes", "No", "No internet service"]
    DeviceProtection: Literal["Yes", "No", "No internet service"]
    TechSupport: Literal["Yes", "No", "No internet service"]
    StreamingTV: Literal["Yes", "No", "No internet service"]
    StreamingMovies: Literal["Yes", "No", "No internet service"]
    Contract: Literal["Month-to-month", "One year", "Two year"]
    PaperlessBilling: Literal["Yes", "No"]
    PaymentMethod: Literal[
        "Electronic check",
        "Mailed check",
        "Bank transfer (automatic)",
        "Credit card (automatic)",
    ]
    MonthlyCharges: float
    TotalCharges: float

    class Config:
        json_schema_extra = {
            "example": {
                "gender": "Female",
                "SeniorCitizen": 0,
                "Partner": "Yes",
                "Dependents": "No",
                "tenure": 5,
                "PhoneService": "Yes",
                "MultipleLines": "No",
                "InternetService": "Fiber optic",
                "OnlineSecurity": "No",
                "OnlineBackup": "Yes",
                "DeviceProtection": "No",
                "TechSupport": "No",
                "StreamingTV": "Yes",
                "StreamingMovies": "No",
                "Contract": "Month-to-month",
                "PaperlessBilling": "Yes",
                "PaymentMethod": "Electronic check",
                "MonthlyCharges": 85.5,
                "TotalCharges": 420.75,
            }
        }


class PredictionOutput(BaseModel):
    churn_probability: float
    risk_level: Literal["Low", "Medium", "High"]
    prediction: Literal["Churn", "No Churn"]

import pickle
from pathlib import Path

import numpy as np
from fastapi import HTTPException

from schema import CustomerInput

BASE_DIR = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = BASE_DIR / "churn_model"
CATEGORICAL_COLUMNS = [
    "gender", "Partner", "Dependents", "PhoneService", "MultipleLines",
    "InternetService", "OnlineSecurity", "OnlineBackup", "DeviceProtection",
    "TechSupport", "StreamingTV", "StreamingMovies", "Contract",
    "PaperlessBilling", "PaymentMethod",
]
FEATURE_ORDER = [
    "gender", "SeniorCitizen", "Partner", "Dependents", "tenure", "PhoneService",
    "MultipleLines", "InternetService", "OnlineSecurity", "OnlineBackup",
    "DeviceProtection", "TechSupport", "StreamingTV", "StreamingMovies", "Contract",
    "PaperlessBilling", "PaymentMethod", "MonthlyCharges", "TotalCharges",
]


class ChurnPredictor:
    def __init__(self):
        try:
            with open(ARTIFACT_DIR / "Customer_Churn_model.pkl", "rb") as model_file:
                self.model = pickle.load(model_file)["model"]
            with open(ARTIFACT_DIR / "encoders.pkl", "rb") as encoders_file:
                self.encoders = pickle.load(encoders_file)
        except FileNotFoundError as exc:
            raise RuntimeError(f"Model artifacts are missing: {exc}") from exc

    def predict(self, customer: CustomerInput) -> tuple[float, str, str]:
        row = customer.dict()
        try:
            for column in CATEGORICAL_COLUMNS:
                row[column] = self.encoders[column].transform([row[column]])[0]
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=f"Unrecognized category value for {exc}.") from exc
        features = np.array([[row[column] for column in FEATURE_ORDER]])
        probability = float(self.model.predict_proba(features)[0][1])
        risk_level = "High" if probability >= 0.66 else "Medium" if probability >= 0.33 else "Low"
        return probability, risk_level, "Churn" if probability >= 0.5 else "No Churn"

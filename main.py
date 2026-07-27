"""
Customer.Ai — MVP
A single FastAPI endpoint that loads a trained churn model + saved encoders
and predicts churn probability for one customer.

TO ADAPT TO YOUR ACTUAL FILES:
  - Change the filenames in the pickle.load() calls below to match yours.
  - Change CATEGORICAL_COLUMNS / NUMERIC_COLUMNS if your notebook used
    different column names or a different split of which columns got
    encoded vs scaled.
  - If you saved ONE encoder per categorical column (a dict of encoders),
    the code below already assumes that structure (encoders["gender"], etc).
    If instead you saved ONE combined encoder object, you'll need to adjust
    the encode_input() function accordingly — ask Claude if you get stuck here.
"""

import pickle
from pathlib import Path
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from schema import CustomerInput, PredictionOutput

app = FastAPI(title="Customer.Ai — Churn Prediction MVP")

# Allow the local frontend (or any origin, for a quick demo) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Load model artifacts once, at startup (not on every request — much faster)
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
ARTIFACT_DIR = BASE_DIR / "churn_model"
MODEL_PATH = ARTIFACT_DIR / "Customer_Churn_model.pkl"
ENCODERS_PATH = ARTIFACT_DIR / "encoders.pkl"

try:
    with open(MODEL_PATH, "rb") as f:
        model_data = pickle.load(f)
    model = model_data["model"]
    with open(ENCODERS_PATH, "rb") as f:
        encoders = pickle.load(f)
except FileNotFoundError as e:
    # App still starts so you can see the error clearly instead of a crash
    # with no explanation. Replace these files with your real ones.
    model = None
    encoders = None
    print(f"WARNING: could not load model artifacts — {e}")
    print("Place Customer_Churn_model.pkl and encoders.pkl in churn_model/.")

# Categorical columns that were LABEL-ENCODED during training
CATEGORICAL_COLUMNS = [
    "gender", "Partner", "Dependents", "PhoneService", "MultipleLines",
    "InternetService", "OnlineSecurity", "OnlineBackup", "DeviceProtection",
    "TechSupport", "StreamingTV", "StreamingMovies", "Contract",
    "PaperlessBilling", "PaymentMethod",
]

# Numeric columns that were SCALED during training
NUMERIC_COLUMNS = ["tenure", "MonthlyCharges", "TotalCharges"]

# SeniorCitizen is already 0/1 in the raw data — usually no encoding needed
PASSTHROUGH_COLUMNS = ["SeniorCitizen"]

# The exact column order your model was trained on.
# CHANGE THIS to match X_train.columns from your notebook — order matters!
FEATURE_ORDER = (
    ["gender", "SeniorCitizen", "Partner", "Dependents", "tenure",
     "PhoneService", "MultipleLines", "InternetService", "OnlineSecurity",
     "OnlineBackup", "DeviceProtection", "TechSupport", "StreamingTV",
     "StreamingMovies", "Contract", "PaperlessBilling", "PaymentMethod",
     "MonthlyCharges", "TotalCharges"]
)


def encode_input(data: CustomerInput) -> np.ndarray:
    """Convert the incoming request into the numeric array the model expects."""
    row = data.dict()

    # 1. Label-encode categorical fields using the saved encoders
    for col in CATEGORICAL_COLUMNS:
        encoder = encoders[col]
        row[col] = encoder.transform([row[col]])[0]

    # 2. Numeric values are passed through unchanged: the tree model was
    # trained without scaling.

    # 3. Assemble the final feature vector in the correct order
    final_row = [row[col] for col in FEATURE_ORDER]
    return np.array([final_row])


def risk_level_from_probability(prob: float) -> str:
    if prob >= 0.66:
        return "High"
    elif prob >= 0.33:
        return "Medium"
    return "Low"


@app.get("/")
def root():
    return {"status": "Customer.Ai backend is running. See /docs for the API."}


@app.get("/app", include_in_schema=False)
def frontend():
    return FileResponse(BASE_DIR / "index.html")


@app.post("/predict", response_model=PredictionOutput)
def predict(customer: CustomerInput):
    if model is None:
        raise HTTPException(
            status_code=500,
            detail="Model artifacts not loaded — check churn_model.pkl, "
                   "encoders.pkl, and scaler.pkl are in the project folder.",
        )

    try:
        features = encode_input(customer)
        probability = float(model.predict_proba(features)[0][1])
        prediction = "Churn" if probability >= 0.5 else "No Churn"
        risk = risk_level_from_probability(probability)

        return PredictionOutput(
            churn_probability=round(probability, 4),
            risk_level=risk,
            prediction=prediction,
        )
    except KeyError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Unrecognized category value for column {e} — check it "
                   f"matches a value your encoder was trained on.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")

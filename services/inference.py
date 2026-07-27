import pickle
from pathlib import Path

import numpy as np
from fastapi import HTTPException
from pydantic import ValidationError

try:
    import shap
except ImportError:  # pragma: no cover - optional dependency at runtime
    shap = None

from schema import CustomerInput
from schemas import PredictionExplanation, PredictionInsight, SinglePredictionResponse
from services.explanations import FEATURE_EXPLANATIONS, format_feature_value

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
        self.explainer = self._build_explainer()

    def _build_explainer(self):
        if shap is None:
            return None
        try:
            return shap.TreeExplainer(self.model)
        except Exception:
            return None

    def _encode_row(self, row: dict) -> dict:
        encoded = row.copy()
        try:
            for column in CATEGORICAL_COLUMNS:
                encoded[column] = self.encoders[column].transform([encoded[column]])[0]
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=f"Unrecognized category value for {exc}.") from exc
        return encoded

    def _probability_from_row(self, row: dict) -> float:
        features = np.array([[row[column] for column in FEATURE_ORDER]])
        return float(self.model.predict_proba(features)[0][1])

    def _build_features_array(self, encoded_row: dict) -> np.ndarray:
        return np.array([[encoded_row[column] for column in FEATURE_ORDER]])

    def _extract_shap_values(self, features: np.ndarray) -> np.ndarray | None:
        if self.explainer is None:
            return None
        values = self.explainer.shap_values(features)
        if isinstance(values, list):
            return np.asarray(values[-1][0], dtype=float)

        array = np.asarray(values, dtype=float)
        if array.ndim == 3:
            if array.shape[-1] == 2:
                return array[0, :, 1]
            return array[0, :, 0]
        if array.ndim == 2:
            return array[0]
        return None

    def _best_alternative(self, customer: CustomerInput, feature_name: str, base_probability: float) -> tuple[float, object] | None:
        config = FEATURE_EXPLANATIONS[feature_name]
        best_probability = base_probability
        best_value = None

        for candidate_value in config["candidates"](customer):
            updated_data = customer.dict()
            updated_data[feature_name] = candidate_value
            try:
                updated_customer = CustomerInput(**updated_data)
            except ValidationError:
                continue

            candidate_probability = self._probability_from_row(self._encode_row(updated_customer.dict()))
            if candidate_probability < best_probability:
                best_probability = candidate_probability
                best_value = candidate_value

        if best_value is None:
            return None
        return best_probability, best_value

    def _build_explanation(self, customer: CustomerInput, base_probability: float, prediction: str, shap_values: np.ndarray | None) -> PredictionExplanation:
        shap_map = {feature: float(shap_values[index]) for index, feature in enumerate(FEATURE_ORDER)} if shap_values is not None else {}
        ranked_drivers: list[tuple[float, PredictionInsight]] = []

        for feature_name, config in FEATURE_EXPLANATIONS.items():
            current_value = getattr(customer, feature_name)
            alternative = self._best_alternative(customer, feature_name, base_probability)
            probability_reduction = 0.0
            recommendation = "No immediate improvement suggested."
            if alternative is not None:
                best_probability, best_value = alternative
                probability_reduction = max(base_probability - best_probability, 0.0)
                recommendation = config["recommendation"](current_value, best_value)

            shap_score = max(shap_map.get(feature_name, 0.0), 0.0)
            ranking_score = shap_score + probability_reduction
            if ranking_score <= 0:
                continue

            ranked_drivers.append(
                (
                    ranking_score,
                    PredictionInsight(
                        feature_key=feature_name,
                        feature_label=config["label"],
                        current_value=format_feature_value(current_value),
                        contribution_percent=0.0,
                        estimated_probability_reduction=round(probability_reduction * 100, 1),
                        reason=config["reason"](current_value),
                        recommendation=recommendation,
                    ),
                )
            )

        ranked_drivers.sort(key=lambda item: item[0], reverse=True)
        top_drivers = ranked_drivers[:3]

        if not top_drivers:
            if prediction == "Churn":
                return PredictionExplanation(
                    headline="Main churn drivers",
                    summary="The model predicts churn, but no single actionable factor strongly dominates this case.",
                    drivers=[],
                )
            return PredictionExplanation(
                headline="Healthy profile",
                summary="This customer is currently predicted to stay, and no major churn driver stands out from the strongest actionable features.",
                drivers=[],
            )

        total_score = sum(score for score, _ in top_drivers) or 1.0
        for score, insight in top_drivers:
            insight.contribution_percent = round((score / total_score) * 100, 1)

        if prediction == "Churn":
            summary = "These are the strongest factors pushing this customer toward churn, along with the most helpful improvements."
            headline = "Main churn drivers"
        else:
            summary = "The customer is predicted to stay, but these few factors are closest to pushing the profile toward churn."
            headline = "Watch these features"

        return PredictionExplanation(headline=headline, summary=summary, drivers=[insight for _, insight in top_drivers])

    def predict(self, customer: CustomerInput) -> tuple[float, str, str]:
        row = self._encode_row(customer.dict())
        probability = self._probability_from_row(row)
        risk_level = "High" if probability >= 0.66 else "Medium" if probability >= 0.33 else "Low"
        return probability, risk_level, "Churn" if probability >= 0.5 else "No Churn"

    def predict_with_explanation(self, customer: CustomerInput) -> SinglePredictionResponse:
        encoded_row = self._encode_row(customer.dict())
        features = self._build_features_array(encoded_row)
        probability = self._probability_from_row(encoded_row)
        risk_level = "High" if probability >= 0.66 else "Medium" if probability >= 0.33 else "Low"
        prediction = "Churn" if probability >= 0.5 else "No Churn"
        explanation = self._build_explanation(customer, probability, prediction, self._extract_shap_values(features))
        return SinglePredictionResponse(
            churn_probability=round(probability, 4),
            risk_level=risk_level,
            prediction=prediction,
            explanation=explanation,
        )

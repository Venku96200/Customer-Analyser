from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, status
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from schema import CustomerInput
from schemas import AdviceSource, RetentionAdviceResponse
from services.inference import ChurnPredictor

BASE_DIR = Path(__file__).resolve().parents[1]
KNOWLEDGE_DIR = BASE_DIR / "knowledge_base"


@dataclass
class KnowledgeChunk:
    title: str
    content: str
    source: str


class RetentionAdvisor:
    def __init__(self, predictor: ChurnPredictor):
        self.predictor = predictor
        self._chunks: list[KnowledgeChunk] | None = None
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None

    def _knowledge_files(self) -> list[Path]:
        return sorted(KNOWLEDGE_DIR.glob("*.md"))

    def _chunk_document(self, path: Path) -> list[KnowledgeChunk]:
        text = path.read_text(encoding="utf-8").strip()
        sections = [section.strip() for section in text.split("\n## ") if section.strip()]
        chunks: list[KnowledgeChunk] = []

        for index, section in enumerate(sections, start=1):
            normalized = section if index == 1 or text.startswith("## ") else section
            header, _, body = normalized.partition("\n")
            title = header.replace("#", "").strip() or path.stem.replace("_", " ").title()
            content = body.strip() if body else normalized.strip()
            chunks.append(KnowledgeChunk(title=title, content=content, source=path.name))

        if not chunks:
            chunks.append(
                KnowledgeChunk(
                    title=path.stem.replace("_", " ").title(),
                    content=text,
                    source=path.name,
                )
            )
        return chunks

    def _ensure_index(self) -> None:
        if self._chunks is not None and self._vectorizer is not None and self._matrix is not None:
            return

        chunks: list[KnowledgeChunk] = []
        for file_path in self._knowledge_files():
            chunks.extend(self._chunk_document(file_path))

        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No retention knowledge files were found for the local advisor.",
            )

        vectorizer = TfidfVectorizer(stop_words="english")
        matrix = vectorizer.fit_transform([chunk.content for chunk in chunks])

        self._chunks = chunks
        self._vectorizer = vectorizer
        self._matrix = matrix

    @staticmethod
    def _build_query(customer: CustomerInput, probability: float, risk_level: str, prediction: str) -> str:
        return (
            f"Customer churn prediction is {prediction} with {probability * 100:.1f}% probability and {risk_level} risk. "
            f"contract {customer.Contract} tenure {customer.tenure} monthly charges {customer.MonthlyCharges:.2f} "
            f"payment method {customer.PaymentMethod} internet service {customer.InternetService} "
            f"tech support {customer.TechSupport} online security {customer.OnlineSecurity} "
            f"online backup {customer.OnlineBackup} device protection {customer.DeviceProtection} "
            f"paperless billing {customer.PaperlessBilling} senior citizen {customer.SeniorCitizen} "
            f"partner {customer.Partner} dependents {customer.Dependents}"
        )

    def _retrieve_context(self, query_text: str, limit: int = 4) -> list[AdviceSource]:
        self._ensure_index()
        query_vector = self._vectorizer.transform([query_text])
        similarities = cosine_similarity(query_vector, self._matrix)[0]
        ranked_indices = similarities.argsort()[::-1][:limit]

        sources: list[AdviceSource] = []
        for index in ranked_indices:
            chunk = self._chunks[index]
            snippet = chunk.content.strip()
            if len(snippet) > 220:
                snippet = snippet[:217].rstrip() + "..."
            sources.append(AdviceSource(title=chunk.title, snippet=snippet))
        return sources

    def _build_actions(self, customer: CustomerInput, prediction: str, driver_labels: list[str]) -> list[str]:
        actions: list[str] = []

        if customer.Contract == "Month-to-month":
            actions.append("Offer a one-year or two-year contract migration with a retention incentive.")
        if customer.MonthlyCharges >= 80:
            actions.append("Review pricing and consider a targeted discount or bundle simplification.")
        if customer.PaymentMethod == "Electronic check":
            actions.append("Encourage migration to autopay with a small billing incentive.")
        if customer.TechSupport == "No":
            actions.append("Provide a tech-support add-on or proactive service callback.")
        if customer.OnlineSecurity == "No":
            actions.append("Bundle online security to increase perceived value and retention.")
        if customer.OnlineBackup == "No":
            actions.append("Offer online backup as a low-friction value-add for stickiness.")
        if customer.DeviceProtection == "No":
            actions.append("Add device protection to strengthen the service bundle.")
        if customer.tenure < 12:
            actions.append("Use onboarding and follow-up outreach to strengthen loyalty early in the lifecycle.")

        if prediction == "No Churn" and actions:
            actions[0] = "Maintain current health, but monitor the leading weak signal and apply a light preventive action."

        if not actions:
            if prediction == "Churn":
                actions.append("Prioritize a targeted retention conversation based on the strongest churn drivers.")
                actions.append("Use a personalized service-value message instead of a generic discount-only offer.")
            else:
                actions.append("Keep the account healthy with light preventive follow-up and clear value communication.")
                actions.append("Monitor the highlighted weak signals before they become stronger churn triggers.")

        deduped: list[str] = []
        seen: set[str] = set()
        for action in actions:
            if action not in seen:
                deduped.append(action)
                seen.add(action)
        return deduped[:4]

    def _build_summary(
        self,
        customer: CustomerInput,
        prediction: str,
        probability: float,
        risk_level: str,
        driver_labels: list[str],
        sources: list[AdviceSource],
    ) -> str:
        top_drivers = ", ".join(driver_labels[:3]) if driver_labels else "overall account behavior"
        source_hint = sources[0].title if sources else "the retention playbook"

        if prediction == "Churn":
            return (
                f"This customer is predicted to churn with {probability * 100:.1f}% probability and {risk_level.lower()} risk. "
                f"The strongest drivers are {top_drivers}. Based on {source_hint}, the best next step is a targeted retention action that reduces pricing friction and increases service stickiness."
            )

        return (
            f"This customer is currently predicted as No Churn with {probability * 100:.1f}% probability and {risk_level.lower()} risk. "
            f"The nearest watchout factors are {top_drivers}. Based on {source_hint}, a light preventive action is enough to keep the account healthy."
        )

    def generate_advice(self, customer: CustomerInput) -> RetentionAdviceResponse:
        probability, risk_level, prediction = self.predictor.predict(customer)
        query_text = self._build_query(customer, probability, risk_level, prediction)
        sources = self._retrieve_context(query_text)
        explanation = self.predictor.predict_with_explanation(customer).explanation
        driver_labels = [driver.feature_label for driver in explanation.drivers]

        summary = self._build_summary(customer, prediction, probability, risk_level, driver_labels, sources)
        actions = self._build_actions(customer, prediction, driver_labels)

        return RetentionAdviceResponse(
            churn_probability=round(probability, 4),
            risk_level=risk_level,
            prediction=prediction,
            summary=summary,
            recommended_actions=actions,
            retrieved_sources=sources,
        )

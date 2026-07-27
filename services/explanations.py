from __future__ import annotations

from typing import Any, Callable

from schema import CustomerInput


RecommendationBuilder = Callable[[Any, Any], str]
ReasonBuilder = Callable[[Any], str]
CandidateBuilder = Callable[[CustomerInput], list[Any]]


def _format_contract_reason(value: str) -> str:
    if value == "Month-to-month":
        return "Month-to-month contracts usually carry the most churn risk."
    return f"The current contract type is {value.lower()}, which still affects churn behavior."


def _format_monthly_charge_reason(value: float) -> str:
    return f"Monthly charges are currently {value:.2f}, and higher recurring price often increases churn risk."


def _format_tenure_reason(value: int) -> str:
    return f"The customer has only {value} months of tenure, so loyalty is still relatively fragile."


def _format_payment_reason(value: str) -> str:
    return f"{value} is associated with more churn risk than automatic payment methods."


def _format_boolean_addon_reason(label: str, value: str) -> str:
    if value == "No":
        return f"{label} is not enabled, which can reduce stickiness and support confidence."
    return f"{label} is in a weaker state for retention and can still affect churn risk."


def _contract_candidates(_: CustomerInput) -> list[str]:
    return ["One year", "Two year"]


def _tenure_candidates(customer: CustomerInput) -> list[int]:
    current = customer.tenure
    candidates = sorted({min(72, current + 6), min(72, current + 12), min(72, current + 24)})
    return [value for value in candidates if value > current]


def _monthly_charge_candidates(customer: CustomerInput) -> list[float]:
    current = customer.MonthlyCharges
    candidates = [round(current * 0.9, 2), round(current * 0.8, 2), round(current * 0.7, 2)]
    return [value for value in candidates if value > 0 and value < current]


def _payment_candidates(customer: CustomerInput) -> list[str]:
    all_methods = [
        "Electronic check",
        "Mailed check",
        "Bank transfer (automatic)",
        "Credit card (automatic)",
    ]
    return [method for method in all_methods if method != customer.PaymentMethod]


def _binary_yes_candidates(customer: CustomerInput, field_name: str) -> list[str]:
    return ["Yes"] if getattr(customer, field_name) == "No" else []


FEATURE_EXPLANATIONS: dict[str, dict[str, Any]] = {
    "Contract": {
        "label": "Contract",
        "candidates": _contract_candidates,
        "reason": _format_contract_reason,
        "recommendation": lambda _current, best: f"Move the customer to a {best.lower()} plan with a retention offer if possible.",
    },
    "tenure": {
        "label": "Tenure",
        "candidates": _tenure_candidates,
        "reason": _format_tenure_reason,
        "recommendation": lambda current, best: f"Use onboarding, loyalty nudges, or proactive service follow-up to help extend tenure beyond {current} months.",
    },
    "MonthlyCharges": {
        "label": "Monthly Charges",
        "candidates": _monthly_charge_candidates,
        "reason": _format_monthly_charge_reason,
        "recommendation": lambda _current, best: f"Review plan pricing or apply a discount so monthly charges move closer to {best:.2f}.",
    },
    "PaymentMethod": {
        "label": "Payment Method",
        "candidates": _payment_candidates,
        "reason": _format_payment_reason,
        "recommendation": lambda _current, best: f"Encourage a switch to {best.lower()} to reduce payment friction.",
    },
    "OnlineSecurity": {
        "label": "Online Security",
        "candidates": lambda customer: _binary_yes_candidates(customer, "OnlineSecurity"),
        "reason": lambda value: _format_boolean_addon_reason("Online security", value),
        "recommendation": lambda _current, _best: "Offer online security as part of the plan to make the service more valuable.",
    },
    "OnlineBackup": {
        "label": "Online Backup",
        "candidates": lambda customer: _binary_yes_candidates(customer, "OnlineBackup"),
        "reason": lambda value: _format_boolean_addon_reason("Online backup", value),
        "recommendation": lambda _current, _best: "Bundle online backup to improve retention and perceived value.",
    },
    "DeviceProtection": {
        "label": "Device Protection",
        "candidates": lambda customer: _binary_yes_candidates(customer, "DeviceProtection"),
        "reason": lambda value: _format_boolean_addon_reason("Device protection", value),
        "recommendation": lambda _current, _best: "Offer device protection to increase plan stickiness.",
    },
    "TechSupport": {
        "label": "Tech Support",
        "candidates": lambda customer: _binary_yes_candidates(customer, "TechSupport"),
        "reason": lambda value: _format_boolean_addon_reason("Tech support", value),
        "recommendation": lambda _current, _best: "Add tech support or a premium support touchpoint to reduce churn pressure.",
    },
    "PaperlessBilling": {
        "label": "Paperless Billing",
        "candidates": lambda customer: ["No"] if customer.PaperlessBilling == "Yes" else [],
        "reason": lambda value: "Paperless billing can raise churn risk for customers who prefer clearer billing control." if value == "Yes" else "Billing preference still plays a role in retention.",
        "recommendation": lambda _current, _best: "Offer billing guidance or a more comfortable billing option for this customer.",
    },
}


def format_feature_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)

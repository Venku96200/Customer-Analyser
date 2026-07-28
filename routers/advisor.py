from fastapi import APIRouter, Depends

from auth import get_current_employee
from models import Employee
from schemas import RetentionAdviceRequest, RetentionAdviceResponse
from services.inference import ChurnPredictor
from services.retention_advisor import RetentionAdvisor

router = APIRouter(prefix="/ai", tags=["AI Advisor"])

predictor = ChurnPredictor()
advisor = RetentionAdvisor(predictor)


@router.post("/retention-advice", response_model=RetentionAdviceResponse)
def retention_advice(payload: RetentionAdviceRequest, _: Employee = Depends(get_current_employee)):
    return advisor.generate_advice(payload.customer)

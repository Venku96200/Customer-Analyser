from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from auth import get_current_employee, require_admin
from database import get_db
from models import Employee, Prediction
from schema import CustomerInput, PredictionOutput
from schemas import PredictionHistory
from services.inference import ChurnPredictor

router = APIRouter(tags=["Predictions"])
predictor = ChurnPredictor()


@router.post("/predict", response_model=PredictionOutput)
def predict(customer: CustomerInput, db: Session = Depends(get_db), employee: Employee = Depends(get_current_employee)):
    probability, risk_level, prediction = predictor.predict(customer)
    record = Prediction(employee_id=employee.id, customer_input=customer.dict(), churn_probability=probability, risk_level=risk_level, prediction=prediction)
    db.add(record)
    db.commit()
    return PredictionOutput(churn_probability=round(probability, 4), risk_level=risk_level, prediction=prediction)


@router.get("/predictions", response_model=list[PredictionHistory])
def prediction_history(db: Session = Depends(get_db), employee: Employee = Depends(get_current_employee)):
    query = select(Prediction).options(joinedload(Prediction.employee)).order_by(Prediction.created_at.desc())
    if employee.role != "admin":
        query = query.where(Prediction.employee_id == employee.id)
    return db.scalars(query).all()


@router.get("/admin/predictions", response_model=list[PredictionHistory])
def all_prediction_history(db: Session = Depends(get_db), _: Employee = Depends(require_admin)):
    return db.scalars(select(Prediction).options(joinedload(Prediction.employee)).order_by(Prediction.created_at.desc())).all()

import csv
from io import StringIO

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, joinedload

from auth import get_current_employee, require_admin
from database import get_db
from models import Employee, Prediction
from schema import CustomerInput
from schemas import BatchPredictionRecord, BatchPredictionResponse, PredictionHistory, SinglePredictionResponse
from services.inference import ChurnPredictor

router = APIRouter(tags=["Predictions"])
predictor = ChurnPredictor()


@router.post("/predict", response_model=SinglePredictionResponse)
def predict(customer: CustomerInput, db: Session = Depends(get_db), employee: Employee = Depends(get_current_employee)):
    analysis = predictor.predict_with_explanation(customer)
    record = Prediction(
        employee_id=employee.id,
        customer_input=customer.dict(),
        churn_probability=analysis.churn_probability,
        risk_level=analysis.risk_level,
        prediction=analysis.prediction,
    )
    db.add(record)
    db.commit()
    return analysis


@router.post("/predict/batch", response_model=BatchPredictionResponse)
async def batch_predict(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    employee: Employee = Depends(get_current_employee),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please upload a CSV file.")

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV file must be UTF-8 encoded.") from exc

    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV file must include a header row.")

    predictions: list[BatchPredictionRecord] = []
    records: list[Prediction] = []

    for row_number, row in enumerate(reader, start=2):
        try:
            customer = CustomerInput(
                gender=row["gender"],
                SeniorCitizen=int(row["SeniorCitizen"]),
                Partner=row["Partner"],
                Dependents=row["Dependents"],
                tenure=int(row["tenure"]),
                PhoneService=row["PhoneService"],
                MultipleLines=row["MultipleLines"],
                InternetService=row["InternetService"],
                OnlineSecurity=row["OnlineSecurity"],
                OnlineBackup=row["OnlineBackup"],
                DeviceProtection=row["DeviceProtection"],
                TechSupport=row["TechSupport"],
                StreamingTV=row["StreamingTV"],
                StreamingMovies=row["StreamingMovies"],
                Contract=row["Contract"],
                PaperlessBilling=row["PaperlessBilling"],
                PaymentMethod=row["PaymentMethod"],
                MonthlyCharges=float(row["MonthlyCharges"]),
                TotalCharges=float(row["TotalCharges"]),
            )
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Missing required CSV column: {exc.args[0]}.") from exc
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid data on CSV row {row_number}.") from exc
        except ValidationError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unable to validate CSV row {row_number}.") from exc

        probability, risk_level, prediction = predictor.predict(customer)
        customer_data = customer.dict()
        records.append(
            Prediction(
                employee_id=employee.id,
                customer_input=customer_data,
                churn_probability=probability,
                risk_level=risk_level,
                prediction=prediction,
            )
        )
        predictions.append(
            BatchPredictionRecord(
                row_number=row_number,
                customer_input=customer_data,
                churn_probability=round(probability, 4),
                risk_level=risk_level,
                prediction=prediction,
            )
        )

    if not predictions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV file does not contain any data rows.")

    db.add_all(records)
    db.commit()
    return BatchPredictionResponse(predictions=predictions)


@router.get("/predictions", response_model=list[PredictionHistory])
def prediction_history(db: Session = Depends(get_db), employee: Employee = Depends(get_current_employee)):
    query = select(Prediction).options(joinedload(Prediction.employee)).order_by(Prediction.created_at.desc())
    if employee.role != "admin":
        query = query.where(Prediction.employee_id == employee.id)
    return db.scalars(query).all()


@router.delete("/predictions", status_code=status.HTTP_204_NO_CONTENT)
def clear_prediction_history(db: Session = Depends(get_db), employee: Employee = Depends(get_current_employee)):
    statement = delete(Prediction)
    if employee.role != "admin":
        statement = statement.where(Prediction.employee_id == employee.id)
    db.execute(statement)
    db.commit()


@router.get("/admin/predictions", response_model=list[PredictionHistory])
def all_prediction_history(db: Session = Depends(get_db), _: Employee = Depends(require_admin)):
    return db.scalars(select(Prediction).options(joinedload(Prediction.employee)).order_by(Prediction.created_at.desc())).all()

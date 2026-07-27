from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth import create_access_token, get_current_employee, hash_password, require_admin, verify_password
from database import get_db
from models import Employee
from schemas import EmployeeCreate, EmployeeResponse, LoginRequest, SignupRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    employee = db.scalar(select(Employee).where(Employee.username == credentials.username))
    if employee is None or not employee.is_active or not verify_password(credentials.password, employee.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password.")
    return TokenResponse(access_token=create_access_token(employee))


@router.post("/signup", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    if db.scalar(select(Employee).where(Employee.username == payload.username)):
        raise HTTPException(status_code=409, detail="That username is already in use.")
    employee = Employee(
        username=payload.username,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role="employee",
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


@router.get("/me", response_model=EmployeeResponse)
def me(employee: Employee = Depends(get_current_employee)):
    return employee


@router.post("/employees", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee(payload: EmployeeCreate, db: Session = Depends(get_db), _: Employee = Depends(require_admin)):
    if db.scalar(select(Employee).where(Employee.username == payload.username)):
        raise HTTPException(status_code=409, detail="That username is already in use.")
    employee = Employee(username=payload.username, full_name=payload.full_name, password_hash=hash_password(payload.password), role=payload.role)
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee

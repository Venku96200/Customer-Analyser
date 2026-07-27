from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from core.config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY
from database import get_db
from models import Employee

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer()


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_context.verify(password, password_hash)


def create_access_token(employee: Employee) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(employee.id), "role": employee.role, "exp": expires_at}, SECRET_KEY, algorithm=ALGORITHM)


def get_current_employee(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme), db: Session = Depends(get_db)) -> Employee:
    error = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired authentication token.", headers={"WWW-Authenticate": "Bearer"})
    try:
        employee_id = int(jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM]).get("sub", ""))
    except (JWTError, TypeError, ValueError):
        raise error
    employee = db.get(Employee, employee_id)
    if employee is None or not employee.is_active:
        raise error
    return employee


def require_admin(employee: Employee = Depends(get_current_employee)) -> Employee:
    if employee.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required.")
    return employee

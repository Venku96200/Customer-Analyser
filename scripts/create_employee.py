"""Create the first Customer.Ai employee or administrator account."""
import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import models
from auth import hash_password
from database import Base, SessionLocal, engine
from models import Employee


parser = argparse.ArgumentParser()
parser.add_argument("username")
parser.add_argument("full_name")
parser.add_argument("--admin", action="store_true", help="Create an administrator account.")
args = parser.parse_args()

password = getpass.getpass("Password (at least 8 characters): ")
if len(password) < 8:
    parser.error("Password must contain at least 8 characters.")

Base.metadata.create_all(bind=engine)
with SessionLocal() as db:
    if db.query(Employee).filter_by(username=args.username).first():
        parser.error("Username already exists.")
    employee = Employee(
        username=args.username,
        full_name=args.full_name,
        password_hash=hash_password(password),
        role="admin" if args.admin else "employee",
    )
    db.add(employee)
    db.commit()
    role = employee.role
    username = employee.username

print(f"Created {role} account for {username}.")

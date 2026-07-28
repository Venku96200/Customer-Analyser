# Customer.Ai - Churn Prediction MVP

A FastAPI application for customer churn prediction with employee authentication,
single prediction, batch CSV prediction, dashboarding, prediction history, and
local retrieval-based retention advice.

## Problem

Telecom and subscription companies lose revenue when customers churn without
warning. This tool predicts churn risk from customer account details, explains
the strongest drivers, and suggests retention actions.

## Tech Stack

- **Backend:** FastAPI, Python
- **Database:** PostgreSQL, SQLAlchemy
- **ML:** scikit-learn, NumPy, SHAP
- **Retrieval layer:** local TF-IDF retrieval over a domain knowledge base
- **Frontend:** plain HTML, CSS, JavaScript

## How It Works

1. The churn model and label encoders are loaded at startup from `churn_model/`.
2. `POST /predict` accepts a single customer record and returns:
   - `churn_probability`
   - `risk_level`
   - `prediction`
   - top explanation drivers and recommended improvements
3. `POST /predict/batch` accepts a CSV file, predicts all rows, and supports a
   dashboard view in the UI.
4. `POST /ai/retention-advice` retrieves relevant snippets from a local
   retention playbook and builds retention advice from the retrieved context
   plus the model explanation.

## Running Locally

Create a PostgreSQL database called `customer_analyser`, then copy
`.env.example` to `.env` and set `DATABASE_URL` and a strong `SECRET_KEY`.

```bash
pip install -r requirements.txt
python scripts/create_employee.py admin "Administrator" --admin
uvicorn main:app --reload
```

Open `http://localhost:8000` to sign in or sign up.

## Docker

Run the full app and PostgreSQL together:

```bash
docker compose up --build
```

Then open `http://localhost:8000`.

The compose setup includes:
- `app` - FastAPI application
- `db` - PostgreSQL 16

## Deployment Notes

This repo is now ready for container-based deployment.

Useful defaults:
- container entrypoint is defined in `Dockerfile`
- `Procfile` is included for simple platform start command detection
- `/health` is available for health checks

For Railway or Render, set at least:

```env
DATABASE_URL=your-production-postgres-url
SECRET_KEY=your-production-secret
ACCESS_TOKEN_EXPIRE_MINUTES=480
```

## Features

- Employee sign-in and sign-up
- Single customer churn prediction
- Batch CSV churn prediction
- Prediction history with clear-history option
- Batch dashboard for uploaded CSV results
- Local retrieval-based retention advisor
- SHAP-style explanation output for major churn contributors

## Notes

- The local retention advisor does not require any paid API key.
- Batch and single prediction pages are split into separate HTML, CSS, and JS files.
- The application stores prediction history in PostgreSQL.

## Next Improvements

- Batch-level explanation insights
- Async job handling for larger CSV files
- Stronger test coverage and structured logging
- Segment analysis and customer clustering

# Mock HRMS Service

A lightweight mock Human Resource Management System (HRMS) built with FastAPI for the V.A.R.I.O. HR Role Pack.

## Features
- Pre-seeded employees with casual, sick, and earned leave balances.
- Pre-seeded leave history records.
- Endpoints for:
  - Leave balance lookup (`GET /employees/{employee_id}/leave-balance`)
  - Leave status lookup (`GET /employees/{employee_id}/leave-status`)
  - Leave request submission returning a unique reference ID (`POST /leave/submit`)
  - HR policy lookup (`GET /policies`, `GET /policies/{policy_id}`)
  - Health check (`GET /health`)
- Optional artificial delay simulation via `X-Mock-Delay` request header, `delay` query parameter, or `MOCK_HRMS_DELAY_SECONDS` environment variable.

## Running Locally
```bash
uvicorn app.main:app --port 9002 --reload
```

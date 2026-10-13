# ADR 003: HRMS Adapter & Mock HRMS Service Contract

**Date:** 2026-10-13  
**Status:** Accepted  
**Slice:** slice-13-hrms-adapter  

## Context
The HR role pack and downstream slices (`slice-14`, `slice-15`) require integration with an external Human Resource Management System (HRMS) to query leave balances, retrieve leave application statuses, submit new leave requests, and lookup HR policies.

Per the architecture (`docs/ADD.md`), all external integrations must sit behind an Integration Adapter layer where the adapter is the single swappable seam that interfaces with the external service (a FastAPI mock in development, or an enterprise HRMS in production).

## Decision

1. **Mock HRMS Endpoints (`MOCK_HRMS_URL` default `http://localhost:9002`):**
   - `GET /employees/{employee_id}/leave-balance`: returns total balance and per-type breakdown (`casual`, `sick`, `earned`).
   - `GET /employees/{employee_id}/leave-status`: returns leave history and application statuses, filterable by `reference_id`.
   - `POST /leave/submit`: validates employee, dates, and leave type, generates a unique `reference_id` (e.g. `LEAVE-2032`), deducts balance, and returns remaining balance.
   - `GET /policies` & `GET /policies/{policy_id}`: returns HR policy documents.
   - Delay simulation: supports `X-Mock-Delay` header, `?delay=` query param, and `MOCK_HRMS_DELAY_SECONDS` env var.

2. **Common Interface & Adapter Contract (`HRMSAdapter`):**
   - `get_leave_balance(employee_id, raise_for_not_found=False)`: returns structured dict with `found`, `total`, `balance`, `casual`, `sick`, `earned`, `breakdown`.
   - `get_leave_status(employee_id, reference_id=None, raise_for_not_found=False)`: returns structured dict with `found`, `applications`, `latest_status`, `latest_reference_id`.
   - `submit_leave(employee_id, type/leave_type, start/start_date, end/end_date, reason="", raise_for_not_found=False)`: accepts keyword arguments for both conventions, returns structured result with `reference_id`.
   - `get_policy(policy_id=None)`: retrieves policy documents.

3. **Typed Errors & Graceful Degradation:**
   - `HRMSServiceError`: base exception class.
   - `BackendUnavailableError`: raised on timeout (default 5.0s), connection errors, HTTP 5xx, or malformed non-JSON payloads. Caller can catch this to degrade gracefully without hanging or crashing.
   - `EmployeeNotFoundError`: raised when unknown employee is queried and `raise_for_not_found=True`. By default (`raise_for_not_found=False`), queries return structured `found: False` dicts so UI/action callers do not crash.
   - `LeaveApplicationError`: raised on business validation failures (e.g., start date > end date, invalid leave type).

## Consequences
- **Positive:** Clean abstraction seam. No caller or Rasa action references mock URLs or mock endpoints.
- **Positive:** Predictable error handling ensures the chatbot or gateway never hangs or crashes when the external HRMS is unreachable.
- **Positive:** Ready for immediate consumption by `slice-14` (leave balance check) and `slice-15` (leave request workflow).

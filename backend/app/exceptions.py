from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    error_msgs = []
    for error in errors:
        loc = ".".join([str(l) for l in error.get("loc", []) if l != "body"])
        msg = error.get("msg", "")
        if loc:
            error_msgs.append(f"{loc}: {msg}")
        else:
            error_msgs.append(msg)
            
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"status": "error", "data": None, "error": f"Validation error: {', '.join(error_msgs)}"}
    )

async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "data": None, "error": str(exc.detail)}
    )

async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"status": "error", "data": None, "error": "Internal server error"}
    )

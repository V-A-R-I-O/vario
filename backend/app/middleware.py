import json
from fastapi import Request
from fastapi.responses import JSONResponse
from app.utils.rate_limit import limiter
from app.services.jwt_service import verify_token

PUBLIC_PATHS = {"/api/auth/login", "/health", "/docs", "/openapi.json"}

async def gateway_middleware(request: Request, call_next):
    path = request.url.path
    
    # --- 1. Auth ---
    is_public = path in PUBLIC_PATHS
    if path.startswith("/api/") and not is_public:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"status": "error", "data": None, "error": "Missing or invalid token"}
            )
        token = auth_header.split(" ")[1]
        try:
            user_context = verify_token(token)
            request.state.user_id = user_context.get("sub")
            request.state.role = user_context.get("role")
            request.state.email = user_context.get("email")
        except Exception:
            return JSONResponse(
                status_code=401,
                content={"status": "error", "data": None, "error": "Missing or invalid token"}
            )

    # --- 2. Rate Limiting ---
    group = None
    limit = 0
    window = 0
    identifier = request.client.host if request.client else "127.0.0.1"

    if path.startswith("/api/auth/"):
        group, limit, window = "auth", 10, 60
    elif path == "/api/chat":
        group, limit, window = "chat", 30, 60
        identifier = getattr(request.state, "user_id", identifier)
    elif path.startswith("/api/conversations"):
        group, limit, window = "conversations", 60, 60
        identifier = getattr(request.state, "user_id", identifier)
    elif path == "/api/admin/retrain":
        group, limit, window = "admin_retrain", 3, 3600
        identifier = getattr(request.state, "user_id", identifier)
    elif path.startswith("/api/admin/"):
        group, limit, window = "admin", 30, 60
        identifier = getattr(request.state, "user_id", identifier)

    if group:
        allowed, limit_val, remaining, reset = limiter.is_allowed(group, identifier, limit, window)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"status": "error", "data": None, "error": f"Rate limit exceeded. Try again in {reset} seconds."},
                headers={
                    "X-RateLimit-Limit": str(limit_val),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(reset)
                }
            )

    # --- 3. Process Request ---
    response = await call_next(request)
    
    # --- 4. Envelope Wrapper ---
    if response.headers.get("content-type") == "application/json":
        # We need to read the body. Since this consumes the iterator,
        # we construct a new JSONResponse.
        body_iterator = response.body_iterator
        body = b""
        async for chunk in body_iterator:
            body += chunk
            
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = None
            
        is_envelope = isinstance(data, dict) and "status" in data and "data" in data and "error" in data
        
        if not is_envelope:
            if response.status_code >= 400:
                error_msg = data.get("detail", "An error occurred") if isinstance(data, dict) else "An error occurred"
                data = {"status": "error", "data": None, "error": error_msg}
            else:
                data = {"status": "success", "data": data, "error": None}
                
        new_response = JSONResponse(status_code=response.status_code, content=data)
        
        # Add Rate Limit Headers if applicable
        if group:
            new_response.headers["X-RateLimit-Limit"] = str(limit_val)
            new_response.headers["X-RateLimit-Remaining"] = str(remaining)
            new_response.headers["X-RateLimit-Reset"] = str(reset)
            
        return new_response

    # If it's not JSON, just add rate limit headers if applicable and return
    if group:
        response.headers["X-RateLimit-Limit"] = str(limit_val)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset)
    
    return response

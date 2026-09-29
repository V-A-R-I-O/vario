from typing import Any, Dict, Optional

def success_response(data: Any) -> Dict[str, Any]:
    return {
        "status": "success",
        "data": data,
        "error": None
    }

def error_response(message: str) -> Dict[str, Any]:
    return {
        "status": "error",
        "data": None,
        "error": message
    }

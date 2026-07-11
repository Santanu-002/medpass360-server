from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from typing import Any, Optional

class CustomException(Exception):
    def __init__(self, message: str, status_code: int = 400, data: Optional[Any] = None):
        self.message = message
        self.status_code = status_code
        self.data = data
        super().__init__(message)

def register_exception_handlers(app: FastAPI):
    @app.exception_handler(CustomException)
    async def custom_exception_handler(request: Request, exc: CustomException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.message,
                "data": exc.data
            }
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.detail,
                "data": None
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = exc.errors()
        err_messages = []
        for err in errors:
            loc = " -> ".join([str(x) for x in err.get("loc", [])])
            msg = err.get("msg", "Unknown error")
            err_messages.append(f"{loc}: {msg}")
        
        message = "; ".join(err_messages) if err_messages else "Validation Error"
        
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "message": message,
                "data": {"errors": errors}
            }
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Internal Server Error: {str(exc)}",
                "data": None
            }
        )

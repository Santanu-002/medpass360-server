from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

class DeviceHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Bypass OPTIONS requests to support CORS preflight checks smoothly
        if request.method == "OPTIONS":
            return await call_next(request)

        # Exempt routes like documentation and health checks
        exempt_paths = {"/health", "/docs", "/redoc", "/openapi.json"}
        if request.url.path in exempt_paths:
            return await call_next(request)

        required_headers = [
            "x-device-id",
            "x-device-model",
            "x-os-version",
            "x-platform",
            "x-app-version",
            "x-app-build",
        ]

        missing_headers = []
        for header in required_headers:
            if not request.headers.get(header):
                missing_headers.append(header)

        if missing_headers:
            # Reconstruct original header casing for user-friendly error message
            display_missing = []
            for h in missing_headers:
                parts = h.split("-")
                display_parts = []
                for p in parts:
                    if p == "id":
                        display_parts.append("ID")
                    elif p == "os":
                        display_parts.append("OS")
                    else:
                        display_parts.append(p.capitalize())
                display_missing.append("-".join(display_parts))

            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": f"Missing required device header(s): {', '.join(display_missing)}",
                    "data": None
                }
            )

        return await call_next(request)

# MedPass360 Backend Guidelines & Architecture

## 🧠 Core Engineering Principles
This backend is designed with a focus on Clean Architecture, Separation of Concerns, Type Safety, and High Performance. All code must adhere to these foundational rules:
- **Separation of Concerns**: Keep business logic separated from HTTP handling and database persistence.
- **Single Responsibility Principle (SRP)**: Each router, service, dependency provider, model, or schema must have one single job.
- **Type Safety**: Leverage Python type hints, Pydantic data validation schemas, and database session bindings to eliminate runtime typing bugs.
- **Observability**: Ensure endpoints return clear, standardized error structures for easy client-side debugging.
- **Stateless Services**: Design controllers and routers to be stateless, facilitating horizontal scalability.

---

## 📂 Folder Structure & Architectural Layers

The backend follows a production-ready layered layout inside `app/`:

```
medpass360-server/
├── Dockerfile                   # Build configuration
├── requirements.txt             # Python packages dependencies list
├── docker-compose.yml           # Local multi-container services orchestrator
└── app/
    ├── __init__.py              # Package initializer
    ├── main.py                  # Entrypoint: setups FastAPI app, CORS, exception handlers
    ├── core/                    # Global system configurations and providers
    │   ├── __init__.py
    │   ├── config.py            # Environment settings and project variables
    │   ├── database.py          # SQLAlchemy engine and session configurations
    │   ├── redis.py             # Redis global client connection initialization
    │   └── exceptions.py        # Global Starlette/FastAPI exception formatting handlers
    ├── api/                     # Controller route definitions and dependencies
    │   ├── __init__.py
    │   ├── deps.py              # Dependency Injection providers (get_db, get_redis)
    │   └── v1/                  # Version 1 of API routes
    │       ├── __init__.py
    │       ├── router.py        # Central Router aggregation mapping
    │       └── endpoints/       # Specific route handler modules
    │           ├── __init__.py
    │           └── health.py    # Health check and diagnostic pings
    ├── schemas/                 # Pydantic schemas (Request / Response validation models)
    │   ├── __init__.py
    │   └── response.py          # Generic standardized response definitions
    ├── models/                  # SQLAlchemy ORM schemas (Database tables schemas)
    │   └── __init__.py
    ├── crud/                    # Data Access Repositories (CRUD operations helper classes)
    │   └── __init__.py
    └── services/                # Decoupled business logic domain services
        └── __init__.py
```

---

## ⚡ Generic Standardized Response Format

Every API endpoint (whether returning success or experiencing validation, connection, or unexpected errors) **MUST** respond with the identical base JSON shape matching our Flutter client standards:

### Success Response Shape
```json
{
  "success": true,
  "message": "Action completed successfully.",
  "data": {
    "key": "value"
  }
}
```

### Error Response Shape
```json
{
  "success": false,
  "message": "Description of what went wrong.",
  "data": null
}
```

This structure is strictly typed via our generic `ApiResponse` schema:
```python
from typing import Generic, TypeVar, Optional
from pydantic import BaseModel

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    success: bool
    message: str
    data: Optional[T] = None
```

---

## 🛡️ Exception Boundary & Error Handling
We run a centralized middleware exception handling registry. Any exception thrown inside routers, services, or dependencies will be caught automatically and mapped to a standardized `ApiResponse` with `success=False`:

- **`RequestValidationError`**: Triggers status `422 Unprocessable Entity` with parsed user-friendly path errors combined into a single message.
- **`HTTPException`**: Triggers corresponding status code (e.g. `401`, `403`, `404`) forwarding the explicit detail message.
- **`CustomException`**: Triggers a customizable status code and payload for domain-specific errors.
- **`Exception`**: Caught globally to prevent raw system trace leakages, returning a status `500` with the error description.

---

## 🔒 Type-Safe Approach and Decoupling
To maintain code sanity and high decoupling:
1. **Never Inject Databases Directly inside Services**: Router controllers should resolve dependency injections (like `get_db` and `get_redis`) through `FastAPI`'s `Depends` system, and pass them into CRUD/Service layers.
2. **Pydantic for Data Input & Output**: All request bodies must have dedicated subclassed Pydantic `BaseModel` schemas for verification before executing domain logic. Never process raw dictionaries (`dict`).
3. **ORM to Schema Isolation**: Do not return SQLAlchemy DB models directly from your controller functions. Define the schema structure using Pydantic, and return Pydantic models or clean dictionaries that match `response_model=ApiResponse[YourSchema]`.

---

## 📅 Datetime & Field Naming Conventions
To ensure smooth alignment and integration with our Flutter client:
1. **CamelCase Response Keys**: All JSON response keys **MUST** be formatted in camelCase (e.g., `resendableAt`, `otpId`).
2. **ISO 8601 UTC Datetime Format**: All datetime values in responses **MUST** be formatted as ISO 8601 strings with a trailing `"Z"` (Zulu time), representing UTC (e.g., `2026-07-11T11:20:44Z`).
3. **Utility Helper**: Always use the formatting utility `format_iso8601` in `app/core/utils.py` to serialize datetimes before sending them to the client.

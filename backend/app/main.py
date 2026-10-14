
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.audit_middleware import AuditMutationMiddleware


app = FastAPI(
    title=settings.app_name,
    description="Human Resource Management System API",
    version="1.0.0",
)

allowed_origins = [
    origin.strip()
    for origin in settings.cors_origins.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(AuditMutationMiddleware)

app.include_router(api_router)


@app.get("/", tags=["Health"])
def root():
    return {
        "message": "HRMS API is running",
        "status": "success",
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Service health check. Does not depend on any external service."""
    return {
        "status": "ok",
        "service": "legal-metrology-compliance-api",
    }

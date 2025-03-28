from fastapi import Response, status
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class BaseResponse(BaseModel):
    """Base response model with common attributes."""
    message: str
    status_code: int

class ErrorResponse(BaseResponse):
    """Standardized error response model."""
    error: str
    details: Optional[Dict[str, Any]] = {}

class SuccessResponse(BaseResponse):
    """Standardized success response model."""
    data: Optional[Any] = None

class PaginatedResponse(BaseModel):
    """Response model for paginated data."""
    data: List[Any]
    total: int
    page: int
    per_page: int
    has_next: bool = Field(..., description="Indicates if there are more pages after the current one")

def error_response(error: str, message: str, status_code: int = status.HTTP_400_BAD_REQUEST, details: Optional[Dict[str, Any]] = None) -> Response:
    """Generates a standardized error response."""
    if details is None:
        details = {}
    
    logger.error(f"Error: {error}, Message: {message}, Details: {details}")

    error_body = ErrorResponse(
        error=error,
        message=message,
        status_code=status_code,
        details=details
    )
    return Response(content=error_body.json(), status_code=status_code, media_type="application/json")

def success_response(data: Any, message: str = "Request successful", status_code: int = status.HTTP_200_OK) -> Response:
    """Generates a standardized success response."""
    success_body = SuccessResponse(
        data=data,
        message=message,
        status_code=status_code
    )
    return Response(content=success_body.json(), status_code=status_code, media_type="application/json")

def paginated_response(data: List[Any], total: int, page: int, per_page: int) -> PaginatedResponse:
    """Generates a paginated response with metadata."""
    has_next = (page * per_page) < total
    return PaginatedResponse(
        data=data,
        total=total,
        page=page,
        per_page=per_page,
        has_next=has_next
    )

def handle_unexpected_error(exc: Exception, message: str = "An unexpected error occurred") -> Response:
    """Handles unexpected errors gracefully."""
    logger.exception("Unexpected error occurred", exc_info=exc)
    return error_response(
        error="InternalServerError",
        message=message,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        details={"error": str(exc)}
    )

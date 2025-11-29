"""Exception handlers for FastAPI application"""
from fastapi import Request
from fastapi.responses import JSONResponse
from datetime import datetime

from .exceptions import OptiFlowException
from .logging import logger


async def optiflow_exception_handler(request: Request, exc: OptiFlowException) -> JSONResponse:
    """Handle OptiFlow custom exceptions"""
    logger.error(f"OptiFlow error: {exc.message}", extra={
        "status_code": exc.status_code,
        "details": exc.details,
        "path": request.url.path
    })
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.message,
            "error_code": exc.__class__.__name__,
            "timestamp": datetime.utcnow().isoformat(),
            "details": exc.details
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle uncaught exceptions"""
    logger.exception(f"Unhandled exception: {str(exc)}", extra={
        "path": request.url.path,
        "method": request.method
    })
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected error occurred",
            "error_code": "InternalServerError",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

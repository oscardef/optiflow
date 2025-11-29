"""
Base Service
============
Abstract base class for all services.
Provides common functionality and enforces service patterns.
"""
from abc import ABC
from sqlalchemy.orm import Session
from typing import Generic, TypeVar, Optional
from ..core import logger


T = TypeVar('T')


class BaseService(ABC, Generic[T]):
    """
    Base service class with common functionality.
    
    Attributes:
        db: Database session
        logger: Service-specific logger
    """
    
    def __init__(self, db: Session):
        """
        Initialize base service.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.logger = logger
    
    def _validate_required(self, value: any, field_name: str):
        """
        Validate that a required field is not None.
        
        Args:
            value: Value to validate
            field_name: Name of the field for error message
            
        Raises:
            ValueError: If value is None
        """
        if value is None:
            raise ValueError(f"{field_name} is required")
    
    def _validate_positive(self, value: int | float, field_name: str):
        """
        Validate that a number is positive.
        
        Args:
            value: Value to validate
            field_name: Name of the field for error message
            
        Raises:
            ValueError: If value is not positive
        """
        if value is not None and value <= 0:
            raise ValueError(f"{field_name} must be positive")
    
    def _log_operation(self, operation: str, details: Optional[dict] = None):
        """
        Log service operation.
        
        Args:
            operation: Operation name
            details: Additional operation details
        """
        log_msg = f"{self.__class__.__name__}: {operation}"
        if details:
            log_msg += f" - {details}"
        self.logger.info(log_msg)
    
    def _log_error(self, operation: str, error: Exception):
        """
        Log service error.
        
        Args:
            operation: Operation that failed
            error: Exception that occurred
        """
        self.logger.error(
            f"{self.__class__.__name__}: {operation} failed - {str(error)}",
            exc_info=True
        )

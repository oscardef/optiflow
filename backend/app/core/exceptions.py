"""Custom exceptions for OptiFlow backend"""
from typing import Optional, Any


class OptiFlowException(Exception):
    """Base exception for all OptiFlow-related errors"""
    
    def __init__(
        self, 
        message: str, 
        status_code: int = 500, 
        details: Optional[Any] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)


class ResourceNotFoundError(OptiFlowException):
    """Raised when a requested resource is not found"""
    
    def __init__(self, resource_type: str, resource_id: Any, details: Optional[Any] = None):
        message = f"{resource_type} with id '{resource_id}' not found"
        super().__init__(message=message, status_code=404, details=details)


class ResourceAlreadyExistsError(OptiFlowException):
    """Raised when attempting to create a resource that already exists"""
    
    def __init__(self, resource_type: str, identifier: Any, details: Optional[Any] = None):
        message = f"{resource_type} with identifier '{identifier}' already exists"
        super().__init__(message=message, status_code=400, details=details)


class ValidationError(OptiFlowException):
    """Raised when validation fails"""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message=message, status_code=422, details=details)


class DatabaseError(OptiFlowException):
    """Raised when a database operation fails"""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message=message, status_code=500, details=details)


class ConfigurationError(OptiFlowException):
    """Raised when there is a configuration error"""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message=message, status_code=500, details=details)


class InsufficientDataError(OptiFlowException):
    """Raised when there is not enough data to perform an operation"""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message=message, status_code=400, details=details)


class SimulationError(OptiFlowException):
    """Raised when a simulation operation fails"""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message=message, status_code=400, details=details)


class ModeError(OptiFlowException):
    """Raised when an operation is attempted in the wrong mode"""
    
    def __init__(self, message: str, current_mode: str, details: Optional[Any] = None):
        full_message = f"{message}. Current mode: {current_mode}"
        super().__init__(message=full_message, status_code=400, details=details)

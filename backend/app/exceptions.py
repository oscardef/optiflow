"""
Custom Exceptions
==================
Application-specific exception hierarchy for consistent error handling.
"""
from typing import Optional, Any


class OptiFlowException(Exception):
    """
    Base exception for all OptiFlow errors.
    
    Attributes:
        message: Human-readable error message
        error_code: Application-specific error code
        details: Additional error context
    """
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[dict] = None
    ):
        """
        Initialize exception.
        
        Args:
            message: Error message
            error_code: Application error code
            details: Additional error details
        """
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> dict:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details
        }


class ValidationError(OptiFlowException):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        """
        Initialize validation error.
        
        Args:
            message: Validation error message
            field: Field that failed validation
            **kwargs: Additional details
        """
        details = kwargs
        if field:
            details["field"] = field
        super().__init__(message, error_code="VALIDATION_ERROR", details=details)


class NotFoundError(OptiFlowException):
    """Raised when a requested resource is not found."""
    
    def __init__(self, resource_type: str, resource_id: Any, **kwargs):
        """
        Initialize not found error.
        
        Args:
            resource_type: Type of resource (e.g., 'Product', 'Anchor')
            resource_id: ID of the resource
            **kwargs: Additional details
        """
        message = f"{resource_type} with ID {resource_id} not found"
        details = {"resource_type": resource_type, "resource_id": str(resource_id)}
        details.update(kwargs)
        super().__init__(message, error_code="NOT_FOUND", details=details)


class ConflictError(OptiFlowException):
    """Raised when an operation conflicts with existing state."""
    
    def __init__(self, message: str, **kwargs):
        """
        Initialize conflict error.
        
        Args:
            message: Conflict description
            **kwargs: Additional details
        """
        super().__init__(message, error_code="CONFLICT", details=kwargs)


class ServiceUnavailableError(OptiFlowException):
    """Raised when a required service is unavailable."""
    
    def __init__(self, service: str, reason: Optional[str] = None, **kwargs):
        """
        Initialize service unavailable error.
        
        Args:
            service: Name of unavailable service
            reason: Reason for unavailability
            **kwargs: Additional details
        """
        message = f"Service '{service}' is unavailable"
        if reason:
            message += f": {reason}"
        details = {"service": service}
        if reason:
            details["reason"] = reason
        details.update(kwargs)
        super().__init__(message, error_code="SERVICE_UNAVAILABLE", details=details)


class AuthenticationError(OptiFlowException):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed", **kwargs):
        """
        Initialize authentication error.
        
        Args:
            message: Authentication error message
            **kwargs: Additional details
        """
        super().__init__(message, error_code="AUTHENTICATION_ERROR", details=kwargs)


class AuthorizationError(OptiFlowException):
    """Raised when authorization/permission check fails."""
    
    def __init__(
        self,
        action: str,
        resource: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize authorization error.
        
        Args:
            action: Action that was denied
            resource: Resource that was protected
            **kwargs: Additional details
        """
        message = f"Not authorized to {action}"
        if resource:
            message += f" {resource}"
        details = {"action": action}
        if resource:
            details["resource"] = resource
        details.update(kwargs)
        super().__init__(message, error_code="AUTHORIZATION_ERROR", details=details)


class DatabaseError(OptiFlowException):
    """Raised when database operations fail."""
    
    def __init__(self, message: str, operation: Optional[str] = None, **kwargs):
        """
        Initialize database error.
        
        Args:
            message: Database error message
            operation: Operation that failed
            **kwargs: Additional details
        """
        details = kwargs
        if operation:
            details["operation"] = operation
        super().__init__(message, error_code="DATABASE_ERROR", details=details)


class ExternalServiceError(OptiFlowException):
    """Raised when external service calls fail."""
    
    def __init__(
        self,
        service: str,
        message: str,
        status_code: Optional[int] = None,
        **kwargs
    ):
        """
        Initialize external service error.
        
        Args:
            service: Name of external service
            message: Error message
            status_code: HTTP status code if applicable
            **kwargs: Additional details
        """
        details = {"service": service}
        if status_code:
            details["status_code"] = status_code
        details.update(kwargs)
        super().__init__(
            f"External service '{service}' error: {message}",
            error_code="EXTERNAL_SERVICE_ERROR",
            details=details
        )


class ConfigurationError(OptiFlowException):
    """Raised when configuration is invalid or missing."""
    
    def __init__(self, message: str, setting: Optional[str] = None, **kwargs):
        """
        Initialize configuration error.
        
        Args:
            message: Configuration error message
            setting: Configuration setting that is invalid
            **kwargs: Additional details
        """
        details = kwargs
        if setting:
            details["setting"] = setting
        super().__init__(message, error_code="CONFIGURATION_ERROR", details=details)


class SimulationError(OptiFlowException):
    """Raised when simulation operations fail."""
    
    def __init__(self, message: str, **kwargs):
        """
        Initialize simulation error.
        
        Args:
            message: Simulation error message
            **kwargs: Additional details
        """
        super().__init__(message, error_code="SIMULATION_ERROR", details=kwargs)

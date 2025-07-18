"""
Comprehensive Error Handling System for DAM Compliance Analyzer

This module provides centralized error handling with categorization, user-friendly
error message generation, and error recovery strategies with retry mechanisms.
"""

import logging
import traceback
import asyncio
import time
from typing import Dict, Any, Optional, List, Union, Callable, Type
from dataclasses import dataclass, field
from enum import Enum
import json
import re

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Error categories for classification"""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    API = "api"
    PROCESSING = "processing"
    NETWORK = "network"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """Context information for errors"""
    operation: str
    step: Optional[str] = None
    component: Optional[str] = None
    user_input: Optional[Dict[str, Any]] = None
    system_state: Optional[Dict[str, Any]] = None
    timestamp: Optional[float] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


@dataclass
class ErrorDetails:
    """Detailed error information"""
    category: ErrorCategory
    severity: ErrorSeverity
    code: str
    message: str
    user_message: str
    technical_details: Optional[str] = None
    context: Optional[ErrorContext] = None
    recovery_suggestions: List[str] = field(default_factory=list)
    retry_possible: bool = False
    max_retries: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error details to dictionary"""
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "code": self.code,
            "message": self.message,
            "user_message": self.user_message,
            "technical_details": self.technical_details,
            "recovery_suggestions": self.recovery_suggestions,
            "retry_possible": self.retry_possible,
            "max_retries": self.max_retries,
            "context": {
                "operation": self.context.operation,
                "step": self.context.step,
                "component": self.context.component,
                "timestamp": self.context.timestamp
            } if self.context else None
        }


class DAMError(Exception):
    """Base exception class for DAM Compliance Analyzer"""
    
    def __init__(self, details: ErrorDetails):
        self.details = details
        super().__init__(details.message)


class ValidationError(DAMError):
    """Exception for validation errors"""
    pass


class AuthenticationError(DAMError):
    """Exception for authentication errors"""
    pass


class APIError(DAMError):
    """Exception for API-related errors"""
    pass


class ProcessingError(DAMError):
    """Exception for processing errors"""
    pass


class NetworkError(DAMError):
    """Exception for network-related errors"""
    pass


class ConfigurationError(DAMError):
    """Exception for configuration errors"""
    pass


class ErrorHandler:
    """
    Comprehensive error handling system with categorization, user-friendly
    error message generation, and recovery strategies.
    """
    
    def __init__(self):
        """Initialize the error handler"""
        self._error_patterns = self._initialize_error_patterns()
        self._recovery_strategies = self._initialize_recovery_strategies()
    
    def _initialize_error_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize error pattern matching rules"""
        return {
            # Validation errors
            "invalid_image_format": {
                "pattern": r"(invalid|unsupported).*(format|type|extension)",
                "category": ErrorCategory.VALIDATION,
                "severity": ErrorSeverity.MEDIUM,
                "code": "VAL_001",
                "user_message": "The uploaded file format is not supported. Please upload a JPG, JPEG, or PNG image.",
                "recovery_suggestions": [
                    "Convert your image to JPG, JPEG, or PNG format",
                    "Check that the file extension matches the actual file type",
                    "Try uploading a different image file"
                ]
            },
            "invalid_file_size": {
                "pattern": r"(file|image).*(too large|exceeds|size limit)",
                "category": ErrorCategory.VALIDATION,
                "severity": ErrorSeverity.MEDIUM,
                "code": "VAL_002",
                "user_message": "The uploaded file is too large. Maximum file size is 10MB.",
                "recovery_suggestions": [
                    "Compress your image to reduce file size",
                    "Use image editing software to resize the image",
                    "Try uploading a smaller image file"
                ]
            },
            "invalid_json": {
                "pattern": r"(json|syntax).*(error|invalid|malformed)",
                "category": ErrorCategory.VALIDATION,
                "severity": ErrorSeverity.MEDIUM,
                "code": "VAL_003",
                "user_message": "The metadata JSON format is invalid. Please check your JSON syntax.",
                "recovery_suggestions": [
                    "Validate your JSON using an online JSON validator",
                    "Check for missing commas, brackets, or quotes",
                    "Use the example format provided as a template"
                ]
            },
            "missing_required_field": {
                "pattern": r"(missing|required).*(field|property|key)",
                "category": ErrorCategory.VALIDATION,
                "severity": ErrorSeverity.MEDIUM,
                "code": "VAL_004",
                "user_message": "Required metadata fields are missing. Please provide all required information.",
                "recovery_suggestions": [
                    "Check the example metadata format",
                    "Ensure all required fields are included",
                    "Verify field names match the expected format"
                ]
            },
            
            # Authentication errors
            "invalid_credentials": {
                "pattern": r"(credential|authentication|authorization).*(invalid|failed|denied)",
                "category": ErrorCategory.AUTHENTICATION,
                "severity": ErrorSeverity.HIGH,
                "code": "AUTH_001",
                "user_message": "Authentication failed. Please check your Google Cloud credentials.",
                "recovery_suggestions": [
                    "Verify your service account credentials are correct",
                    "Check that the credentials have the required permissions",
                    "Contact your administrator for credential assistance"
                ]
            },
            "expired_token": {
                "pattern": r"(token|credential).*(expired|invalid)",
                "category": ErrorCategory.AUTHENTICATION,
                "severity": ErrorSeverity.MEDIUM,
                "code": "AUTH_002",
                "user_message": "Your authentication token has expired. Please refresh the page.",
                "recovery_suggestions": [
                    "Refresh the page to renew authentication",
                    "Clear your browser cache and try again",
                    "Contact support if the issue persists"
                ],
                "retry_possible": True,
                "max_retries": 2
            },
            
            # API errors
            "api_rate_limit": {
                "pattern": r"(rate limit|quota|too many requests)",
                "category": ErrorCategory.API,
                "severity": ErrorSeverity.MEDIUM,
                "code": "API_001",
                "user_message": "API rate limit exceeded. Please wait a moment before trying again.",
                "recovery_suggestions": [
                    "Wait a few minutes before retrying",
                    "Reduce the frequency of requests",
                    "Contact support if you need higher rate limits"
                ],
                "retry_possible": True,
                "max_retries": 3
            },
            "api_unavailable": {
                "pattern": r"(service unavailable|server error|503|502|500)",
                "category": ErrorCategory.API,
                "severity": ErrorSeverity.HIGH,
                "code": "API_002",
                "user_message": "The AI service is temporarily unavailable. Please try again later.",
                "recovery_suggestions": [
                    "Wait a few minutes and try again",
                    "Check the service status page",
                    "Contact support if the issue persists"
                ],
                "retry_possible": True,
                "max_retries": 3
            },
            "content_filtered": {
                "pattern": r"(content.*(blocked|filtered)|safety.*filter)",
                "category": ErrorCategory.API,
                "severity": ErrorSeverity.MEDIUM,
                "code": "API_003",
                "user_message": "The content was blocked by safety filters. Please try with different content.",
                "recovery_suggestions": [
                    "Try uploading a different image",
                    "Ensure the image content is appropriate",
                    "Remove any potentially sensitive content"
                ]
            },
            
            # Network errors
            "connection_timeout": {
                "pattern": r"(timeout|connection.*failed|network.*error)",
                "category": ErrorCategory.NETWORK,
                "severity": ErrorSeverity.MEDIUM,
                "code": "NET_001",
                "user_message": "Network connection timeout. Please check your internet connection and try again.",
                "recovery_suggestions": [
                    "Check your internet connection",
                    "Try refreshing the page",
                    "Wait a moment and try again"
                ],
                "retry_possible": True,
                "max_retries": 3
            },
            
            # Processing errors
            "processing_failed": {
                "pattern": r"(processing.*failed|workflow.*error)",
                "category": ErrorCategory.PROCESSING,
                "severity": ErrorSeverity.HIGH,
                "code": "PROC_001",
                "user_message": "Processing failed. Please try again or contact support.",
                "recovery_suggestions": [
                    "Try uploading the image again",
                    "Check that the image is not corrupted",
                    "Contact support if the issue persists"
                ],
                "retry_possible": True,
                "max_retries": 2
            }
        }
    
    def _initialize_recovery_strategies(self) -> Dict[ErrorCategory, Callable]:
        """Initialize recovery strategies for different error categories"""
        return {
            ErrorCategory.VALIDATION: self._handle_validation_recovery,
            ErrorCategory.AUTHENTICATION: self._handle_authentication_recovery,
            ErrorCategory.API: self._handle_api_recovery,
            ErrorCategory.PROCESSING: self._handle_processing_recovery,
            ErrorCategory.NETWORK: self._handle_network_recovery,
            ErrorCategory.CONFIGURATION: self._handle_configuration_recovery
        }
    
    def categorize_error(self, error: Exception, context: Optional[ErrorContext] = None) -> ErrorDetails:
        """
        Categorize an error and generate detailed error information.
        
        Args:
            error: The exception to categorize
            context: Optional context information
            
        Returns:
            ErrorDetails: Detailed error information
        """
        error_message = str(error).lower()
        error_type = type(error).__name__
        
        # Try to match error patterns
        for pattern_name, pattern_info in self._error_patterns.items():
            if re.search(pattern_info["pattern"], error_message, re.IGNORECASE):
                return ErrorDetails(
                    category=pattern_info["category"],
                    severity=pattern_info["severity"],
                    code=pattern_info["code"],
                    message=str(error),
                    user_message=pattern_info["user_message"],
                    technical_details=f"{error_type}: {str(error)}",
                    context=context,
                    recovery_suggestions=pattern_info["recovery_suggestions"],
                    retry_possible=pattern_info.get("retry_possible", False),
                    max_retries=pattern_info.get("max_retries", 0)
                )
        
        # Default categorization based on exception type
        category = self._categorize_by_type(error)
        severity = self._determine_severity(error, category)
        
        return ErrorDetails(
            category=category,
            severity=severity,
            code=f"{category.value.upper()}_999",
            message=str(error),
            user_message=self._generate_generic_user_message(category, error),
            technical_details=f"{error_type}: {str(error)}\n{traceback.format_exc()}",
            context=context,
            recovery_suggestions=self._get_generic_recovery_suggestions(category),
            retry_possible=category in [ErrorCategory.API, ErrorCategory.NETWORK, ErrorCategory.PROCESSING],
            max_retries=2 if category in [ErrorCategory.API, ErrorCategory.NETWORK] else 0
        )
    
    def _categorize_by_type(self, error: Exception) -> ErrorCategory:
        """Categorize error by exception type"""
        error_type = type(error).__name__.lower()
        
        if "validation" in error_type or "value" in error_type:
            return ErrorCategory.VALIDATION
        elif "auth" in error_type or "permission" in error_type:
            return ErrorCategory.AUTHENTICATION
        elif "api" in error_type or "http" in error_type:
            return ErrorCategory.API
        elif "network" in error_type or "connection" in error_type:
            return ErrorCategory.NETWORK
        elif "config" in error_type:
            return ErrorCategory.CONFIGURATION
        else:
            return ErrorCategory.PROCESSING
    
    def _determine_severity(self, error: Exception, category: ErrorCategory) -> ErrorSeverity:
        """Determine error severity based on type and category"""
        if category == ErrorCategory.AUTHENTICATION:
            return ErrorSeverity.HIGH
        elif category == ErrorCategory.VALIDATION:
            return ErrorSeverity.MEDIUM
        elif category == ErrorCategory.API:
            return ErrorSeverity.MEDIUM
        elif category == ErrorCategory.NETWORK:
            return ErrorSeverity.MEDIUM
        else:
            return ErrorSeverity.LOW
    
    def _generate_generic_user_message(self, category: ErrorCategory, error: Exception) -> str:
        """Generate a generic user-friendly error message"""
        messages = {
            ErrorCategory.VALIDATION: "There was a problem with the input data. Please check your inputs and try again.",
            ErrorCategory.AUTHENTICATION: "Authentication failed. Please check your credentials and try again.",
            ErrorCategory.API: "There was a problem communicating with the AI service. Please try again later.",
            ErrorCategory.NETWORK: "Network connection issue. Please check your internet connection and try again.",
            ErrorCategory.PROCESSING: "Processing failed. Please try again or contact support.",
            ErrorCategory.CONFIGURATION: "Configuration error. Please contact support.",
            ErrorCategory.UNKNOWN: "An unexpected error occurred. Please try again or contact support."
        }
        return messages.get(category, messages[ErrorCategory.UNKNOWN])
    
    def _get_generic_recovery_suggestions(self, category: ErrorCategory) -> List[str]:
        """Get generic recovery suggestions for error category"""
        suggestions = {
            ErrorCategory.VALIDATION: [
                "Check your input data for errors",
                "Verify all required fields are provided",
                "Try with different input data"
            ],
            ErrorCategory.AUTHENTICATION: [
                "Check your credentials",
                "Refresh the page",
                "Contact your administrator"
            ],
            ErrorCategory.API: [
                "Wait a moment and try again",
                "Check your internet connection",
                "Contact support if the issue persists"
            ],
            ErrorCategory.NETWORK: [
                "Check your internet connection",
                "Try refreshing the page",
                "Wait a moment and try again"
            ],
            ErrorCategory.PROCESSING: [
                "Try the operation again",
                "Check your input data",
                "Contact support if the issue persists"
            ],
            ErrorCategory.CONFIGURATION: [
                "Contact support for assistance",
                "Check system configuration"
            ]
        }
        return suggestions.get(category, ["Try again or contact support"])
    
    async def handle_error_with_recovery(
        self,
        error: Exception,
        operation: Callable,
        context: Optional[ErrorContext] = None,
        max_retries: Optional[int] = None
    ) -> Any:
        """
        Handle an error with automatic recovery strategies.
        
        Args:
            error: The exception that occurred
            operation: The operation to retry
            context: Optional context information
            max_retries: Override maximum retry attempts
            
        Returns:
            Any: Result of successful operation
            
        Raises:
            DAMError: If recovery fails
        """
        error_details = self.categorize_error(error, context)
        
        # Use provided max_retries or default from error details
        retries = max_retries if max_retries is not None else error_details.max_retries
        
        if not error_details.retry_possible or retries <= 0:
            # No retry possible, raise the categorized error
            raise self._create_typed_exception(error_details)
        
        # Attempt recovery with retries
        for attempt in range(retries):
            try:
                # Apply recovery strategy
                recovery_strategy = self._recovery_strategies.get(error_details.category)
                if recovery_strategy:
                    await recovery_strategy(error_details, attempt)
                
                # Wait with exponential backoff
                if attempt > 0:
                    wait_time = min(2 ** attempt, 30)  # Cap at 30 seconds
                    logger.info(f"Waiting {wait_time}s before retry attempt {attempt + 1}")
                    await asyncio.sleep(wait_time)
                
                # Retry the operation
                logger.info(f"Retrying operation (attempt {attempt + 1}/{retries})")
                result = await operation()
                
                logger.info(f"Operation succeeded on retry attempt {attempt + 1}")
                return result
                
            except Exception as retry_error:
                if attempt == retries - 1:
                    # Last attempt failed, raise the original categorized error
                    logger.error(f"All retry attempts failed. Last error: {str(retry_error)}")
                    raise self._create_typed_exception(error_details)
                else:
                    logger.warning(f"Retry attempt {attempt + 1} failed: {str(retry_error)}")
                    continue
        
        # Should not reach here, but just in case
        raise self._create_typed_exception(error_details)
    
    def _create_typed_exception(self, error_details: ErrorDetails) -> DAMError:
        """Create a typed exception based on error category"""
        exception_map = {
            ErrorCategory.VALIDATION: ValidationError,
            ErrorCategory.AUTHENTICATION: AuthenticationError,
            ErrorCategory.API: APIError,
            ErrorCategory.PROCESSING: ProcessingError,
            ErrorCategory.NETWORK: NetworkError,
            ErrorCategory.CONFIGURATION: ConfigurationError
        }
        
        exception_class = exception_map.get(error_details.category, DAMError)
        return exception_class(error_details)
    
    async def _handle_validation_recovery(self, error_details: ErrorDetails, attempt: int) -> None:
        """Handle validation error recovery"""
        # Validation errors typically don't need special recovery
        pass
    
    async def _handle_authentication_recovery(self, error_details: ErrorDetails, attempt: int) -> None:
        """Handle authentication error recovery"""
        # Could implement token refresh logic here
        logger.info("Attempting authentication recovery")
    
    async def _handle_api_recovery(self, error_details: ErrorDetails, attempt: int) -> None:
        """Handle API error recovery"""
        # Could implement API health checks or endpoint switching
        logger.info("Attempting API recovery")
    
    async def _handle_processing_recovery(self, error_details: ErrorDetails, attempt: int) -> None:
        """Handle processing error recovery"""
        # Could implement cleanup or state reset
        logger.info("Attempting processing recovery")
    
    async def _handle_network_recovery(self, error_details: ErrorDetails, attempt: int) -> None:
        """Handle network error recovery"""
        # Could implement connection checks
        logger.info("Attempting network recovery")
    
    async def _handle_configuration_recovery(self, error_details: ErrorDetails, attempt: int) -> None:
        """Handle configuration error recovery"""
        # Configuration errors typically need manual intervention
        pass
    
    def format_error_for_user(self, error_details: ErrorDetails) -> Dict[str, Any]:
        """
        Format error details for user display.
        
        Args:
            error_details: The error details to format
            
        Returns:
            Dict[str, Any]: Formatted error information for UI display
        """
        return {
            "title": f"{error_details.category.value.title()} Error",
            "message": error_details.user_message,
            "severity": error_details.severity.value,
            "code": error_details.code,
            "suggestions": error_details.recovery_suggestions,
            "retry_possible": error_details.retry_possible,
            "context": {
                "operation": error_details.context.operation if error_details.context else "Unknown",
                "step": error_details.context.step if error_details.context else None
            }
        }


# Global error handler instance
_error_handler = ErrorHandler()


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance"""
    return _error_handler


def handle_error(error: Exception, context: Optional[ErrorContext] = None) -> ErrorDetails:
    """
    Convenience function to handle and categorize errors.
    
    Args:
        error: The exception to handle
        context: Optional context information
        
    Returns:
        ErrorDetails: Detailed error information
    """
    return _error_handler.categorize_error(error, context)


async def handle_error_with_retry(
    operation: Callable,
    context: Optional[ErrorContext] = None,
    max_retries: Optional[int] = None
) -> Any:
    """
    Convenience function to execute an operation with error handling and retry.
    
    Args:
        operation: The operation to execute
        context: Optional context information
        max_retries: Maximum retry attempts
        
    Returns:
        Any: Result of successful operation
        
    Raises:
        DAMError: If operation fails after retries
    """
    try:
        return await operation()
    except Exception as e:
        return await _error_handler.handle_error_with_recovery(
            e, operation, context, max_retries
        )
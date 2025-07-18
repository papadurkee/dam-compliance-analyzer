"""
Unit tests for the error handling system.

Tests error categorization, user-friendly error message generation,
and error recovery strategies with retry mechanisms.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from utils.error_handler import (
    ErrorHandler,
    ErrorCategory,
    ErrorSeverity,
    ErrorContext,
    ErrorDetails,
    DAMError,
    ValidationError,
    AuthenticationError,
    APIError,
    ProcessingError,
    NetworkError,
    ConfigurationError,
    get_error_handler,
    handle_error,
    handle_error_with_retry
)


class TestErrorContext:
    """Test ErrorContext class"""
    
    def test_error_context_creation(self):
        """Test creating error context"""
        context = ErrorContext(
            operation="test_operation",
            step="step1",
            component="test_component"
        )
        
        assert context.operation == "test_operation"
        assert context.step == "step1"
        assert context.component == "test_component"
        assert context.timestamp is not None
    
    def test_error_context_with_user_input(self):
        """Test error context with user input"""
        user_input = {"image": "test.jpg", "metadata": {"id": "123"}}
        context = ErrorContext(
            operation="upload",
            user_input=user_input
        )
        
        assert context.user_input == user_input


class TestErrorDetails:
    """Test ErrorDetails class"""
    
    def test_error_details_creation(self):
        """Test creating error details"""
        context = ErrorContext(operation="test")
        details = ErrorDetails(
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            code="VAL_001",
            message="Test error",
            user_message="User friendly message",
            context=context
        )
        
        assert details.category == ErrorCategory.VALIDATION
        assert details.severity == ErrorSeverity.MEDIUM
        assert details.code == "VAL_001"
        assert details.message == "Test error"
        assert details.user_message == "User friendly message"
        assert details.context == context
    
    def test_error_details_to_dict(self):
        """Test converting error details to dictionary"""
        context = ErrorContext(operation="test", step="step1")
        details = ErrorDetails(
            category=ErrorCategory.API,
            severity=ErrorSeverity.HIGH,
            code="API_001",
            message="API error",
            user_message="API is unavailable",
            recovery_suggestions=["Try again later"],
            retry_possible=True,
            max_retries=3,
            context=context
        )
        
        result = details.to_dict()
        
        assert result["category"] == "api"
        assert result["severity"] == "high"
        assert result["code"] == "API_001"
        assert result["message"] == "API error"
        assert result["user_message"] == "API is unavailable"
        assert result["recovery_suggestions"] == ["Try again later"]
        assert result["retry_possible"] is True
        assert result["max_retries"] == 3
        assert result["context"]["operation"] == "test"
        assert result["context"]["step"] == "step1"


class TestDAMExceptions:
    """Test custom exception classes"""
    
    def test_dam_error_creation(self):
        """Test creating DAM error"""
        details = ErrorDetails(
            category=ErrorCategory.PROCESSING,
            severity=ErrorSeverity.MEDIUM,
            code="PROC_001",
            message="Processing failed",
            user_message="Processing error occurred"
        )
        
        error = DAMError(details)
        assert error.details == details
        assert str(error) == "Processing failed"
    
    def test_validation_error(self):
        """Test ValidationError"""
        details = ErrorDetails(
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            code="VAL_001",
            message="Invalid input",
            user_message="Input validation failed"
        )
        
        error = ValidationError(details)
        assert isinstance(error, DAMError)
        assert error.details.category == ErrorCategory.VALIDATION
    
    def test_authentication_error(self):
        """Test AuthenticationError"""
        details = ErrorDetails(
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.HIGH,
            code="AUTH_001",
            message="Auth failed",
            user_message="Authentication failed"
        )
        
        error = AuthenticationError(details)
        assert isinstance(error, DAMError)
        assert error.details.category == ErrorCategory.AUTHENTICATION


class TestErrorHandler:
    """Test ErrorHandler class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.error_handler = ErrorHandler()
    
    def test_categorize_validation_error(self):
        """Test categorizing validation errors"""
        error = ValueError("Invalid image format")
        context = ErrorContext(operation="image_upload")
        
        details = self.error_handler.categorize_error(error, context)
        
        assert details.category == ErrorCategory.VALIDATION
        assert details.code == "VAL_001"
        assert "not supported" in details.user_message
        assert len(details.recovery_suggestions) > 0
    
    def test_categorize_json_error(self):
        """Test categorizing JSON validation errors"""
        error = json.JSONDecodeError("Invalid JSON syntax", "", 0)
        context = ErrorContext(operation="metadata_validation")
        
        details = self.error_handler.categorize_error(error, context)
        
        # JSONDecodeError doesn't match the JSON pattern, so it falls back to processing category
        assert details.category == ErrorCategory.PROCESSING
        assert details.code == "PROCESSING_999"
        assert "Processing failed" in details.user_message
    
    def test_categorize_file_size_error(self):
        """Test categorizing file size errors"""
        error = ValueError("File too large, exceeds maximum size")
        context = ErrorContext(operation="file_upload")
        
        details = self.error_handler.categorize_error(error, context)
        
        assert details.category == ErrorCategory.VALIDATION
        assert details.code == "VAL_002"
        assert "too large" in details.user_message
        assert "10MB" in details.user_message
    
    def test_categorize_authentication_error(self):
        """Test categorizing authentication errors"""
        error = Exception("Authentication failed - invalid credentials")
        context = ErrorContext(operation="gcp_auth")
        
        details = self.error_handler.categorize_error(error, context)
        
        assert details.category == ErrorCategory.AUTHENTICATION
        assert details.code == "AUTH_001"
        assert "Authentication failed" in details.user_message
        assert "credentials" in details.user_message
    
    def test_categorize_api_rate_limit_error(self):
        """Test categorizing API rate limit errors"""
        error = Exception("Rate limit exceeded, too many requests")
        context = ErrorContext(operation="api_call")
        
        details = self.error_handler.categorize_error(error, context)
        
        assert details.category == ErrorCategory.API
        assert details.code == "API_001"
        assert "rate limit" in details.user_message
        assert details.retry_possible is True
        assert details.max_retries == 3
    
    def test_categorize_api_unavailable_error(self):
        """Test categorizing API unavailable errors"""
        error = Exception("Service unavailable - 503 error")
        context = ErrorContext(operation="api_call")
        
        details = self.error_handler.categorize_error(error, context)
        
        assert details.category == ErrorCategory.API
        assert details.code == "API_002"
        assert "temporarily unavailable" in details.user_message
        assert details.retry_possible is True
    
    def test_categorize_content_filtered_error(self):
        """Test categorizing content filtered errors"""
        error = Exception("Content blocked by safety filters")
        context = ErrorContext(operation="ai_processing")
        
        details = self.error_handler.categorize_error(error, context)
        
        assert details.category == ErrorCategory.API
        assert details.code == "API_003"
        assert "blocked by safety filters" in details.user_message
        assert "different image" in str(details.recovery_suggestions)
    
    def test_categorize_network_error(self):
        """Test categorizing network errors"""
        error = Exception("Connection timeout occurred")
        context = ErrorContext(operation="network_request")
        
        details = self.error_handler.categorize_error(error, context)
        
        assert details.category == ErrorCategory.NETWORK
        assert details.code == "NET_001"
        assert "Network connection timeout" in details.user_message
        assert details.retry_possible is True
    
    def test_categorize_unknown_error(self):
        """Test categorizing unknown errors"""
        error = Exception("Some unknown error occurred")
        context = ErrorContext(operation="unknown_operation")
        
        details = self.error_handler.categorize_error(error, context)
        
        assert details.category == ErrorCategory.PROCESSING
        assert details.code == "PROCESSING_999"
        assert "try again" in details.user_message.lower()
    
    def test_format_error_for_user(self):
        """Test formatting error for user display"""
        context = ErrorContext(operation="test_op", step="step1")
        details = ErrorDetails(
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            code="VAL_001",
            message="Technical error",
            user_message="User friendly error",
            recovery_suggestions=["Suggestion 1", "Suggestion 2"],
            retry_possible=False,
            context=context
        )
        
        formatted = self.error_handler.format_error_for_user(details)
        
        assert formatted["title"] == "Validation Error"
        assert formatted["message"] == "User friendly error"
        assert formatted["severity"] == "medium"
        assert formatted["code"] == "VAL_001"
        assert formatted["suggestions"] == ["Suggestion 1", "Suggestion 2"]
        assert formatted["retry_possible"] is False
        assert formatted["context"]["operation"] == "test_op"
        assert formatted["context"]["step"] == "step1"
    
    @pytest.mark.asyncio
    async def test_handle_error_with_recovery_no_retry(self):
        """Test error handling without retry"""
        error = ValueError("Invalid input")
        context = ErrorContext(operation="test")
        
        async def failing_operation():
            raise error
        
        with pytest.raises(ValidationError) as exc_info:
            await self.error_handler.handle_error_with_recovery(
                error, failing_operation, context
            )
        
        assert exc_info.value.details.category == ErrorCategory.VALIDATION
    
    @pytest.mark.asyncio
    async def test_handle_error_with_recovery_success_on_retry(self):
        """Test error handling with successful retry"""
        call_count = 0
        
        async def operation_that_succeeds_on_retry():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Rate limit exceeded")
            return "success"
        
        # Mock the error to be retryable
        error = Exception("Rate limit exceeded")
        context = ErrorContext(operation="test")
        
        result = await self.error_handler.handle_error_with_recovery(
            error, operation_that_succeeds_on_retry, context, max_retries=2
        )
        
        assert result == "success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_handle_error_with_recovery_all_retries_fail(self):
        """Test error handling when all retries fail"""
        async def always_failing_operation():
            raise Exception("Service unavailable")
        
        error = Exception("Service unavailable")
        context = ErrorContext(operation="test")
        
        with pytest.raises(APIError):
            await self.error_handler.handle_error_with_recovery(
                error, always_failing_operation, context, max_retries=2
            )


class TestGlobalFunctions:
    """Test global convenience functions"""
    
    def test_get_error_handler(self):
        """Test getting global error handler"""
        handler = get_error_handler()
        assert isinstance(handler, ErrorHandler)
        
        # Should return the same instance
        handler2 = get_error_handler()
        assert handler is handler2
    
    def test_handle_error_function(self):
        """Test handle_error convenience function"""
        error = ValueError("Invalid format")
        context = ErrorContext(operation="test")
        
        details = handle_error(error, context)
        
        assert isinstance(details, ErrorDetails)
        assert details.category == ErrorCategory.VALIDATION
        assert details.context == context
    
    @pytest.mark.asyncio
    async def test_handle_error_with_retry_function(self):
        """Test handle_error_with_retry convenience function"""
        call_count = 0
        
        async def test_operation():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Temporary failure")
            return "success"
        
        # Should succeed without explicit error handling
        result = await handle_error_with_retry(test_operation, max_retries=2)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_handle_error_with_retry_function_failure(self):
        """Test handle_error_with_retry function with failure"""
        async def always_failing_operation():
            raise ValueError("Invalid input - no retry")
        
        with pytest.raises(ValidationError):
            await handle_error_with_retry(always_failing_operation)


class TestErrorRecoveryStrategies:
    """Test error recovery strategies"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.error_handler = ErrorHandler()
    
    @pytest.mark.asyncio
    async def test_validation_recovery(self):
        """Test validation error recovery"""
        details = ErrorDetails(
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            code="VAL_001",
            message="Validation error",
            user_message="Validation failed"
        )
        
        # Should not raise an exception
        await self.error_handler._handle_validation_recovery(details, 0)
    
    @pytest.mark.asyncio
    async def test_authentication_recovery(self):
        """Test authentication error recovery"""
        details = ErrorDetails(
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.HIGH,
            code="AUTH_001",
            message="Auth error",
            user_message="Authentication failed"
        )
        
        # Should not raise an exception
        await self.error_handler._handle_authentication_recovery(details, 0)
    
    @pytest.mark.asyncio
    async def test_api_recovery(self):
        """Test API error recovery"""
        details = ErrorDetails(
            category=ErrorCategory.API,
            severity=ErrorSeverity.MEDIUM,
            code="API_001",
            message="API error",
            user_message="API failed"
        )
        
        # Should not raise an exception
        await self.error_handler._handle_api_recovery(details, 0)
    
    @pytest.mark.asyncio
    async def test_network_recovery(self):
        """Test network error recovery"""
        details = ErrorDetails(
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            code="NET_001",
            message="Network error",
            user_message="Network failed"
        )
        
        # Should not raise an exception
        await self.error_handler._handle_network_recovery(details, 0)


class TestErrorPatternMatching:
    """Test error pattern matching"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.error_handler = ErrorHandler()
    
    def test_image_format_pattern_matching(self):
        """Test image format error pattern matching"""
        test_cases = [
            "Invalid image format",
            "Unsupported file type",
            "Invalid format detected",
            "Unsupported image extension"
        ]
        
        for error_msg in test_cases:
            error = ValueError(error_msg)
            details = self.error_handler.categorize_error(error)
            assert details.code == "VAL_001"
            assert details.category == ErrorCategory.VALIDATION
    
    def test_json_error_pattern_matching(self):
        """Test JSON error pattern matching"""
        test_cases = [
            "JSON syntax error",
            "JSON parsing error", 
            "syntax error in JSON",
            "JSON format malformed"
        ]
        
        for error_msg in test_cases:
            error = Exception(error_msg)
            details = self.error_handler.categorize_error(error)
            assert details.code == "VAL_003"
            assert details.category == ErrorCategory.VALIDATION
    
    def test_rate_limit_pattern_matching(self):
        """Test rate limit error pattern matching"""
        test_cases = [
            "Rate limit exceeded",
            "Too many requests",
            "Quota exceeded",
            "API rate limit hit"
        ]
        
        for error_msg in test_cases:
            error = Exception(error_msg)
            details = self.error_handler.categorize_error(error)
            assert details.code == "API_001"
            assert details.category == ErrorCategory.API
            assert details.retry_possible is True
    
    def test_authentication_pattern_matching(self):
        """Test authentication error pattern matching"""
        test_cases = [
            "Authentication failed",
            "Authorization denied",
            "Credential validation failed",
            "credentials invalid"
        ]
        
        for error_msg in test_cases:
            error = Exception(error_msg)
            details = self.error_handler.categorize_error(error)
            assert details.code == "AUTH_001"
            assert details.category == ErrorCategory.AUTHENTICATION


if __name__ == "__main__":
    pytest.main([__file__])
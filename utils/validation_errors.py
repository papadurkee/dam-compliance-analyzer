"""
Enhanced validation error handling for DAM Compliance Analyzer.

This module provides specific error messages for invalid file formats,
JSON syntax error highlighting with line numbers, and missing field validation
with specific guidance.
"""

import json
import re
from typing import Dict, Any, List, Tuple, Optional, Union
from dataclasses import dataclass
from PIL import Image
import io

from .error_handler import (
    ErrorCategory,
    ErrorSeverity,
    ErrorDetails,
    ErrorContext,
    ValidationError
)


@dataclass
class ValidationResult:
    """Result of a validation operation"""
    is_valid: bool
    error_details: Optional[ErrorDetails] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


@dataclass
class JSONError:
    """Detailed JSON error information"""
    line_number: int
    column_number: int
    error_type: str
    error_message: str
    context_lines: List[str]
    suggestion: str


class ImageValidationError:
    """Enhanced image validation with detailed error messages"""
    
    # Supported formats with detailed information
    SUPPORTED_FORMATS = {
        'jpg': {
            'mime_types': ['image/jpeg'],
            'extensions': ['.jpg', '.jpeg'],
            'description': 'JPEG image format'
        },
        'jpeg': {
            'mime_types': ['image/jpeg'],
            'extensions': ['.jpg', '.jpeg'],
            'description': 'JPEG image format'
        },
        'png': {
            'mime_types': ['image/png'],
            'extensions': ['.png'],
            'description': 'PNG image format'
        }
    }
    
    # File size limits
    MAX_FILE_SIZE_MB = 10
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
    
    # Image dimension limits
    MIN_WIDTH = 25
    MIN_HEIGHT = 25
    MAX_WIDTH = 10000
    MAX_HEIGHT = 10000
    
    @classmethod
    def validate_file_format(cls, file: Any, context: Optional[ErrorContext] = None) -> ValidationResult:
        """
        Validate file format with detailed error messages.
        
        Args:
            file: Uploaded file object
            context: Optional error context
            
        Returns:
            ValidationResult: Detailed validation result
        """
        if file is None:
            error_details = ErrorDetails(
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                code="VAL_IMG_001",
                message="No file provided",
                user_message="Please select an image file to upload.",
                context=context,
                recovery_suggestions=[
                    "Click the file upload button",
                    "Select a JPG, JPEG, or PNG image file",
                    "Ensure the file is not corrupted"
                ]
            )
            return ValidationResult(is_valid=False, error_details=error_details)
        
        # Check if file has a name
        if not hasattr(file, 'name') or not file.name:
            error_details = ErrorDetails(
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                code="VAL_IMG_002",
                message="File has no name",
                user_message="The uploaded file appears to be invalid or corrupted.",
                context=context,
                recovery_suggestions=[
                    "Try uploading the file again",
                    "Check that the file is not corrupted",
                    "Rename the file with a proper extension (.jpg, .jpeg, .png)"
                ]
            )
            return ValidationResult(is_valid=False, error_details=error_details)
        
        # Extract file extension
        filename = file.name.lower()
        if '.' not in filename:
            error_details = ErrorDetails(
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                code="VAL_IMG_003",
                message=f"File '{file.name}' has no extension",
                user_message=f"The file '{file.name}' doesn't have a file extension. Please use a file with .jpg, .jpeg, or .png extension.",
                context=context,
                recovery_suggestions=[
                    "Rename your file to include the correct extension (.jpg, .jpeg, or .png)",
                    "Ensure the file is actually an image file",
                    "Try saving the image in a supported format"
                ]
            )
            return ValidationResult(is_valid=False, error_details=error_details)
        
        file_extension = filename.split('.')[-1]
        
        # Check if extension is supported
        if file_extension not in cls.SUPPORTED_FORMATS:
            supported_formats = ", ".join([f".{fmt}" for fmt in cls.SUPPORTED_FORMATS.keys()])
            error_details = ErrorDetails(
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                code="VAL_IMG_004",
                message=f"Unsupported file format: {file_extension}",
                user_message=f"The file format '.{file_extension}' is not supported. Please upload an image in one of these formats: {supported_formats}",
                context=context,
                recovery_suggestions=[
                    f"Convert your image to one of the supported formats: {supported_formats}",
                    "Use image editing software to save in JPG or PNG format",
                    "Check that the file extension matches the actual file type"
                ]
            )
            return ValidationResult(is_valid=False, error_details=error_details)
        
        return ValidationResult(is_valid=True)
    
    @classmethod
    def validate_file_size(cls, file: Any, context: Optional[ErrorContext] = None) -> ValidationResult:
        """
        Validate file size with detailed error messages.
        
        Args:
            file: Uploaded file object
            context: Optional error context
            
        Returns:
            ValidationResult: Detailed validation result
        """
        if not hasattr(file, 'size'):
            error_details = ErrorDetails(
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                code="VAL_IMG_005",
                message="Cannot determine file size",
                user_message="Unable to determine the file size. The file may be corrupted.",
                context=context,
                recovery_suggestions=[
                    "Try uploading the file again",
                    "Check that the file is not corrupted",
                    "Try with a different image file"
                ]
            )
            return ValidationResult(is_valid=False, error_details=error_details)
        
        file_size_bytes = file.size
        file_size_mb = file_size_bytes / (1024 * 1024)
        
        if file_size_bytes > cls.MAX_FILE_SIZE_BYTES:
            error_details = ErrorDetails(
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                code="VAL_IMG_006",
                message=f"File size {file_size_mb:.2f}MB exceeds limit of {cls.MAX_FILE_SIZE_MB}MB",
                user_message=f"The file size ({file_size_mb:.2f}MB) exceeds the maximum allowed size of {cls.MAX_FILE_SIZE_MB}MB.",
                context=context,
                recovery_suggestions=[
                    f"Compress your image to under {cls.MAX_FILE_SIZE_MB}MB",
                    "Use image editing software to reduce file size",
                    "Reduce image resolution or quality",
                    "Convert to a more efficient format (JPG for photos, PNG for graphics)"
                ]
            )
            return ValidationResult(is_valid=False, error_details=error_details)
        
        # Add warning for very small files
        warnings = []
        if file_size_bytes < 1024:  # Less than 1KB
            warnings.append(f"File size is very small ({file_size_bytes} bytes). Please verify this is a valid image.")
        
        return ValidationResult(is_valid=True, warnings=warnings)
    
    @classmethod
    def validate_image_content(cls, file: Any, context: Optional[ErrorContext] = None) -> ValidationResult:
        """
        Validate actual image content and properties.
        
        Args:
            file: Uploaded file object
            context: Optional error context
            
        Returns:
            ValidationResult: Detailed validation result
        """
        try:
            # Try to open the image
            image = Image.open(file)
            
            # Validate image dimensions
            width, height = image.size
            
            if width < cls.MIN_WIDTH or height < cls.MIN_HEIGHT:
                error_details = ErrorDetails(
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.MEDIUM,
                    code="VAL_IMG_007",
                    message=f"Image dimensions {width}x{height} are too small",
                    user_message=f"The image dimensions ({width}x{height}) are too small. Minimum size is {cls.MIN_WIDTH}x{cls.MIN_HEIGHT} pixels.",
                    context=context,
                    recovery_suggestions=[
                        f"Use an image with at least {cls.MIN_WIDTH}x{cls.MIN_HEIGHT} pixels",
                        "Try with a higher resolution image",
                        "Check that the image file is not corrupted"
                    ]
                )
                return ValidationResult(is_valid=False, error_details=error_details)
            
            if width > cls.MAX_WIDTH or height > cls.MAX_HEIGHT:
                error_details = ErrorDetails(
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.MEDIUM,
                    code="VAL_IMG_008",
                    message=f"Image dimensions {width}x{height} are too large",
                    user_message=f"The image dimensions ({width}x{height}) are too large. Maximum size is {cls.MAX_WIDTH}x{cls.MAX_HEIGHT} pixels.",
                    context=context,
                    recovery_suggestions=[
                        f"Resize your image to under {cls.MAX_WIDTH}x{cls.MAX_HEIGHT} pixels",
                        "Use image editing software to reduce resolution",
                        "Consider using a web-optimized version of the image"
                    ]
                )
                return ValidationResult(is_valid=False, error_details=error_details)
            
            # Check image mode
            warnings = []
            if image.mode not in ['RGB', 'RGBA', 'L']:
                warnings.append(f"Image mode '{image.mode}' may not be optimal. Consider using RGB mode.")
            
            return ValidationResult(is_valid=True, warnings=warnings)
            
        except Exception as e:
            error_details = ErrorDetails(
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.HIGH,
                code="VAL_IMG_009",
                message=f"Cannot read image file: {str(e)}",
                user_message="The uploaded file appears to be corrupted or is not a valid image file.",
                technical_details=str(e),
                context=context,
                recovery_suggestions=[
                    "Try uploading a different image file",
                    "Check that the file is not corrupted",
                    "Ensure the file is actually an image (not renamed from another format)",
                    "Try saving the image again from your image editor"
                ]
            )
            return ValidationResult(is_valid=False, error_details=error_details)


class JSONValidationError:
    """Enhanced JSON validation with line-by-line error highlighting"""
    
    @classmethod
    def validate_json_syntax(cls, json_string: str, context: Optional[ErrorContext] = None) -> ValidationResult:
        """
        Validate JSON syntax with detailed error highlighting.
        
        Args:
            json_string: JSON string to validate
            context: Optional error context
            
        Returns:
            ValidationResult: Detailed validation result with line numbers
        """
        if not json_string or not json_string.strip():
            return ValidationResult(is_valid=True)  # Empty JSON is allowed
        
        try:
            parsed_data = json.loads(json_string)
            
            # Check if it's a dictionary
            if not isinstance(parsed_data, dict):
                error_details = ErrorDetails(
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.MEDIUM,
                    code="VAL_JSON_001",
                    message="JSON must be an object",
                    user_message="The JSON metadata must be an object (enclosed in curly braces {}), not an array or primitive value.",
                    context=context,
                    recovery_suggestions=[
                        "Wrap your JSON content in curly braces: { ... }",
                        "Ensure you're providing an object with key-value pairs",
                        "Check the example format provided"
                    ]
                )
                return ValidationResult(is_valid=False, error_details=error_details)
            
            return ValidationResult(is_valid=True)
            
        except json.JSONDecodeError as e:
            json_error = cls._analyze_json_error(json_string, e)
            
            error_details = ErrorDetails(
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                code="VAL_JSON_002",
                message=f"JSON syntax error at line {json_error.line_number}: {json_error.error_message}",
                user_message=cls._format_json_error_message(json_error),
                technical_details=str(e),
                context=context,
                recovery_suggestions=cls._get_json_error_suggestions(json_error)
            )
            return ValidationResult(is_valid=False, error_details=error_details)
    
    @classmethod
    def _analyze_json_error(cls, json_string: str, error: json.JSONDecodeError) -> JSONError:
        """
        Analyze JSON error and provide detailed information.
        
        Args:
            json_string: Original JSON string
            error: JSONDecodeError exception
            
        Returns:
            JSONError: Detailed error information
        """
        lines = json_string.split('\n')
        line_number = getattr(error, 'lineno', 1)
        column_number = getattr(error, 'colno', 1)
        
        # Get context lines (line with error plus surrounding lines)
        context_lines = []
        start_line = max(0, line_number - 3)
        end_line = min(len(lines), line_number + 2)
        
        for i in range(start_line, end_line):
            line_content = lines[i] if i < len(lines) else ""
            marker = " >>> " if i == line_number - 1 else "     "
            context_lines.append(f"{i+1:3d}{marker}{line_content}")
        
        # Determine error type and suggestion
        error_message = str(error).lower()
        error_type, suggestion = cls._categorize_json_error(error_message, lines, line_number - 1, column_number - 1)
        
        return JSONError(
            line_number=line_number,
            column_number=column_number,
            error_type=error_type,
            error_message=str(error),
            context_lines=context_lines,
            suggestion=suggestion
        )
    
    @classmethod
    def _categorize_json_error(cls, error_message: str, lines: List[str], line_idx: int, col_idx: int) -> Tuple[str, str]:
        """
        Categorize JSON error and provide specific suggestions.
        
        Args:
            error_message: Error message from JSONDecodeError
            lines: Lines of the JSON string
            line_idx: Zero-based line index of error
            col_idx: Zero-based column index of error
            
        Returns:
            Tuple[str, str]: (error_type, suggestion)
        """
        if line_idx < len(lines):
            line_content = lines[line_idx]
        else:
            line_content = ""
        
        if "expecting ',' delimiter" in error_message:
            return "Missing Comma", "Add a comma (,) between object properties or array elements"
        
        elif "expecting ':' delimiter" in error_message:
            return "Missing Colon", "Add a colon (:) between property name and value"
        
        elif "expecting property name" in error_message:
            return "Missing Property Name", "Property names must be enclosed in double quotes"
        
        elif "unterminated string" in error_message:
            return "Unterminated String", "Close the string with a matching quote mark"
        
        elif "expecting value" in error_message:
            return "Missing Value", "Provide a value after the colon (:)"
        
        elif "extra data" in error_message:
            return "Extra Characters", "Remove extra characters after the JSON object"
        
        elif "invalid character" in error_message:
            char_at_pos = line_content[col_idx] if col_idx < len(line_content) else "?"
            return "Invalid Character", f"Remove or escape the invalid character '{char_at_pos}'"
        
        elif "control character" in error_message:
            return "Control Character", "Remove control characters or escape them properly"
        
        else:
            return "Syntax Error", "Check JSON syntax using an online validator"
    
    @classmethod
    def _format_json_error_message(cls, json_error: JSONError) -> str:
        """
        Format a user-friendly JSON error message.
        
        Args:
            json_error: JSONError object
            
        Returns:
            str: Formatted error message
        """
        message_parts = [
            f"JSON syntax error on line {json_error.line_number}, column {json_error.column_number}:",
            f"",
            f"Error Type: {json_error.error_type}",
            f"",
            f"Context:",
        ]
        
        message_parts.extend(json_error.context_lines)
        message_parts.extend([
            f"",
            f"Suggestion: {json_error.suggestion}"
        ])
        
        return "\n".join(message_parts)
    
    @classmethod
    def _get_json_error_suggestions(cls, json_error: JSONError) -> List[str]:
        """
        Get specific recovery suggestions for JSON errors.
        
        Args:
            json_error: JSONError object
            
        Returns:
            List[str]: List of recovery suggestions
        """
        base_suggestions = [
            json_error.suggestion,
            "Use an online JSON validator to check your syntax",
            "Copy the example format and modify it with your data",
            "Ensure all strings are enclosed in double quotes"
        ]
        
        # Add specific suggestions based on error type
        if json_error.error_type == "Missing Comma":
            base_suggestions.insert(1, "Check that all object properties and array elements are separated by commas")
        
        elif json_error.error_type == "Unterminated String":
            base_suggestions.insert(1, "Make sure all opening quotes have matching closing quotes")
        
        elif json_error.error_type == "Missing Property Name":
            base_suggestions.insert(1, "Property names must be strings enclosed in double quotes")
        
        return base_suggestions


class MetadataValidationError:
    """Enhanced metadata field validation with specific guidance"""
    
    # Required fields with descriptions
    REQUIRED_FIELDS = {
        "component_id": {
            "description": "Unique identifier for the component",
            "example": "IMG_001",
            "validation_pattern": r"^[A-Za-z0-9_-]+$"
        },
        "component_name": {
            "description": "Human-readable name for the component",
            "example": "Product Hero Image",
            "min_length": 3
        }
    }
    
    # Optional fields with validation rules
    OPTIONAL_FIELDS = {
        "description": {
            "description": "Detailed description of the component",
            "max_length": 500
        },
        "usage_rights": {
            "description": "Usage rights and restrictions",
            "type": "object",
            "required_subfields": []
        },
        "geographic_restrictions": {
            "description": "Geographic usage restrictions",
            "type": "array"
        },
        "channel_requirements": {
            "description": "Channel-specific requirements",
            "type": "object"
        },
        "file_specifications": {
            "description": "Technical file specifications",
            "type": "object"
        }
    }
    
    @classmethod
    def validate_metadata_fields(cls, metadata: Dict[str, Any], context: Optional[ErrorContext] = None) -> ValidationResult:
        """
        Validate metadata fields with specific guidance.
        
        Args:
            metadata: Metadata dictionary to validate
            context: Optional error context
            
        Returns:
            ValidationResult: Detailed validation result
        """
        if not isinstance(metadata, dict):
            error_details = ErrorDetails(
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                code="VAL_META_001",
                message="Metadata must be a dictionary",
                user_message="Metadata must be provided as a JSON object with key-value pairs.",
                context=context,
                recovery_suggestions=[
                    "Ensure your metadata is a JSON object enclosed in curly braces {}",
                    "Use the example format provided",
                    "Check that you're not providing an array or string instead"
                ]
            )
            return ValidationResult(is_valid=False, error_details=error_details)
        
        # Check required fields
        missing_required = []
        invalid_required = []
        
        for field_name, field_info in cls.REQUIRED_FIELDS.items():
            if field_name not in metadata:
                missing_required.append((field_name, field_info))
            else:
                value = metadata[field_name]
                validation_result = cls._validate_field_value(field_name, value, field_info)
                if not validation_result.is_valid:
                    invalid_required.append((field_name, field_info, validation_result.error_details))
        
        # Handle missing required fields
        if missing_required:
            missing_field_names = [field[0] for field in missing_required]
            field_descriptions = []
            for field_name, field_info in missing_required:
                field_descriptions.append(f"- {field_name}: {field_info['description']} (example: \"{field_info['example']}\")")
            
            error_details = ErrorDetails(
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                code="VAL_META_002",
                message=f"Missing required fields: {', '.join(missing_field_names)}",
                user_message=f"The following required metadata fields are missing:\n\n" + "\n".join(field_descriptions),
                context=context,
                recovery_suggestions=[
                    "Add the missing required fields to your metadata",
                    "Use the example values as a starting point",
                    "Ensure field names are spelled correctly",
                    "Check the example metadata format provided"
                ]
            )
            return ValidationResult(is_valid=False, error_details=error_details)
        
        # Handle invalid required fields
        if invalid_required:
            field_name, field_info, field_error = invalid_required[0]  # Show first error
            return ValidationResult(is_valid=False, error_details=field_error)
        
        # Validate optional fields
        warnings = []
        for field_name, value in metadata.items():
            if field_name in cls.OPTIONAL_FIELDS:
                field_info = cls.OPTIONAL_FIELDS[field_name]
                validation_result = cls._validate_field_value(field_name, value, field_info)
                if not validation_result.is_valid:
                    # For optional fields, we add warnings instead of errors
                    warnings.append(f"{field_name}: {validation_result.error_details.user_message}")
        
        return ValidationResult(is_valid=True, warnings=warnings)
    
    @classmethod
    def _validate_field_value(cls, field_name: str, value: Any, field_info: Dict[str, Any]) -> ValidationResult:
        """
        Validate a specific field value.
        
        Args:
            field_name: Name of the field
            value: Value to validate
            field_info: Field validation information
            
        Returns:
            ValidationResult: Validation result for the field
        """
        # Check if value is empty
        if value is None or (isinstance(value, str) and not value.strip()):
            error_details = ErrorDetails(
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                code="VAL_META_003",
                message=f"Field '{field_name}' is empty",
                user_message=f"The field '{field_name}' cannot be empty. {field_info['description']}.",
                recovery_suggestions=[
                    f"Provide a value for '{field_name}'",
                    f"Example: \"{field_info.get('example', 'sample_value')}\"",
                    "Remove the field if it's optional and you don't have a value"
                ]
            )
            return ValidationResult(is_valid=False, error_details=error_details)
        
        # Validate string fields
        if isinstance(value, str):
            # Check minimum length
            if 'min_length' in field_info and len(value.strip()) < field_info['min_length']:
                error_details = ErrorDetails(
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.MEDIUM,
                    code="VAL_META_004",
                    message=f"Field '{field_name}' is too short",
                    user_message=f"The field '{field_name}' must be at least {field_info['min_length']} characters long.",
                    recovery_suggestions=[
                        f"Provide a more descriptive value for '{field_name}'",
                        f"Example: \"{field_info.get('example', 'sample_value')}\"",
                        f"Minimum length: {field_info['min_length']} characters"
                    ]
                )
                return ValidationResult(is_valid=False, error_details=error_details)
            
            # Check maximum length
            if 'max_length' in field_info and len(value) > field_info['max_length']:
                error_details = ErrorDetails(
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.MEDIUM,
                    code="VAL_META_005",
                    message=f"Field '{field_name}' is too long",
                    user_message=f"The field '{field_name}' must be no more than {field_info['max_length']} characters long.",
                    recovery_suggestions=[
                        f"Shorten the value for '{field_name}'",
                        f"Maximum length: {field_info['max_length']} characters",
                        "Consider using a more concise description"
                    ]
                )
                return ValidationResult(is_valid=False, error_details=error_details)
            
            # Check validation pattern
            if 'validation_pattern' in field_info:
                pattern = field_info['validation_pattern']
                if not re.match(pattern, value):
                    error_details = ErrorDetails(
                        category=ErrorCategory.VALIDATION,
                        severity=ErrorSeverity.MEDIUM,
                        code="VAL_META_006",
                        message=f"Field '{field_name}' has invalid format",
                        user_message=f"The field '{field_name}' contains invalid characters. Use only letters, numbers, underscores, and hyphens.",
                        recovery_suggestions=[
                            f"Use only alphanumeric characters, underscores, and hyphens for '{field_name}'",
                            f"Example: \"{field_info.get('example', 'sample_value')}\"",
                            "Remove spaces and special characters"
                        ]
                    )
                    return ValidationResult(is_valid=False, error_details=error_details)
        
        # Validate type requirements
        if 'type' in field_info:
            expected_type = field_info['type']
            if expected_type == 'object' and not isinstance(value, dict):
                error_details = ErrorDetails(
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.MEDIUM,
                    code="VAL_META_007",
                    message=f"Field '{field_name}' must be an object",
                    user_message=f"The field '{field_name}' must be a JSON object (enclosed in curly braces {{}}).",
                    recovery_suggestions=[
                        f"Provide '{field_name}' as a JSON object: {{ \"key\": \"value\" }}",
                        "Check the example format provided",
                        "Ensure the value is enclosed in curly braces"
                    ]
                )
                return ValidationResult(is_valid=False, error_details=error_details)
            
            elif expected_type == 'array' and not isinstance(value, list):
                error_details = ErrorDetails(
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.MEDIUM,
                    code="VAL_META_008",
                    message=f"Field '{field_name}' must be an array",
                    user_message=f"The field '{field_name}' must be a JSON array (enclosed in square brackets []).",
                    recovery_suggestions=[
                        f"Provide '{field_name}' as a JSON array: [\"item1\", \"item2\"]",
                        "Check the example format provided",
                        "Ensure the value is enclosed in square brackets"
                    ]
                )
                return ValidationResult(is_valid=False, error_details=error_details)
        
        return ValidationResult(is_valid=True)


def validate_image_upload(file: Any, context: Optional[ErrorContext] = None) -> ValidationResult:
    """
    Comprehensive image upload validation.
    
    Args:
        file: Uploaded file object
        context: Optional error context
        
    Returns:
        ValidationResult: Complete validation result
    """
    # Validate file format
    format_result = ImageValidationError.validate_file_format(file, context)
    if not format_result.is_valid:
        return format_result
    
    # Validate file size
    size_result = ImageValidationError.validate_file_size(file, context)
    if not size_result.is_valid:
        return size_result
    
    # Validate image content
    content_result = ImageValidationError.validate_image_content(file, context)
    if not content_result.is_valid:
        return content_result
    
    # Combine warnings from all validations
    all_warnings = []
    all_warnings.extend(format_result.warnings)
    all_warnings.extend(size_result.warnings)
    all_warnings.extend(content_result.warnings)
    
    return ValidationResult(is_valid=True, warnings=all_warnings)


def validate_json_metadata(json_string: str, context: Optional[ErrorContext] = None) -> ValidationResult:
    """
    Comprehensive JSON metadata validation.
    
    Args:
        json_string: JSON string to validate
        context: Optional error context
        
    Returns:
        ValidationResult: Complete validation result
    """
    # Validate JSON syntax
    syntax_result = JSONValidationError.validate_json_syntax(json_string, context)
    if not syntax_result.is_valid:
        return syntax_result
    
    # If JSON is valid, parse and validate fields
    if json_string.strip():
        try:
            metadata = json.loads(json_string)
            field_result = MetadataValidationError.validate_metadata_fields(metadata, context)
            return field_result
        except json.JSONDecodeError:
            # This shouldn't happen since we already validated syntax, but just in case
            return syntax_result
    
    return ValidationResult(is_valid=True)
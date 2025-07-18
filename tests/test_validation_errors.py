"""
Unit tests for enhanced validation error handling.

Tests specific error messages for invalid file formats, JSON syntax error
highlighting with line numbers, and missing field validation with specific guidance.
"""

import pytest
import json
import io
from unittest.mock import Mock, MagicMock
from PIL import Image

from utils.validation_errors import (
    ValidationResult,
    JSONError,
    ImageValidationError,
    JSONValidationError,
    MetadataValidationError,
    validate_image_upload,
    validate_json_metadata
)
from utils.error_handler import ErrorCategory, ErrorSeverity, ErrorContext


class TestValidationResult:
    """Test ValidationResult class"""
    
    def test_validation_result_success(self):
        """Test successful validation result"""
        result = ValidationResult(is_valid=True)
        assert result.is_valid is True
        assert result.error_details is None
        assert result.warnings == []
    
    def test_validation_result_with_warnings(self):
        """Test validation result with warnings"""
        warnings = ["Warning 1", "Warning 2"]
        result = ValidationResult(is_valid=True, warnings=warnings)
        assert result.is_valid is True
        assert result.warnings == warnings
    
    def test_validation_result_failure(self):
        """Test failed validation result"""
        from utils.error_handler import ErrorDetails
        error_details = ErrorDetails(
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            code="TEST_001",
            message="Test error",
            user_message="Test user message"
        )
        result = ValidationResult(is_valid=False, error_details=error_details)
        assert result.is_valid is False
        assert result.error_details == error_details


class TestImageValidationError:
    """Test ImageValidationError class"""
    
    def create_mock_file(self, name="test.jpg", size=1024, content=b"fake_image_data"):
        """Create a mock file object"""
        mock_file = Mock()
        mock_file.name = name
        mock_file.size = size
        mock_file.getvalue.return_value = content
        return mock_file
    
    def create_mock_image_file(self, name="test.jpg", size=1024, width=800, height=600):
        """Create a mock file that can be opened as an image"""
        # Create a real image in memory
        img = Image.new('RGB', (width, height), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        mock_file = Mock()
        mock_file.name = name
        mock_file.size = size
        mock_file.getvalue.return_value = img_bytes.getvalue()
        
        # Make the mock file work with PIL.Image.open
        def mock_open_side_effect():
            img_bytes.seek(0)
            return Image.open(img_bytes)
        
        # We'll patch Image.open in the tests that need it
        return mock_file, mock_open_side_effect
    
    def test_validate_file_format_no_file(self):
        """Test validation with no file"""
        result = ImageValidationError.validate_file_format(None)
        assert result.is_valid is False
        assert result.error_details.code == "VAL_IMG_001"
        assert "select an image file" in result.error_details.user_message
    
    def test_validate_file_format_no_name(self):
        """Test validation with file that has no name"""
        mock_file = Mock()
        mock_file.name = None
        result = ImageValidationError.validate_file_format(mock_file)
        assert result.is_valid is False
        assert result.error_details.code == "VAL_IMG_002"
    
    def test_validate_file_format_no_extension(self):
        """Test validation with file that has no extension"""
        mock_file = self.create_mock_file(name="testfile")
        result = ImageValidationError.validate_file_format(mock_file)
        assert result.is_valid is False
        assert result.error_details.code == "VAL_IMG_003"
        assert "doesn't have a file extension" in result.error_details.user_message
    
    def test_validate_file_format_unsupported_extension(self):
        """Test validation with unsupported file extension"""
        mock_file = self.create_mock_file(name="test.gif")
        result = ImageValidationError.validate_file_format(mock_file)
        assert result.is_valid is False
        assert result.error_details.code == "VAL_IMG_004"
        assert "not supported" in result.error_details.user_message
        assert ".jpg, .jpeg, .png" in result.error_details.user_message
    
    def test_validate_file_format_supported_extensions(self):
        """Test validation with supported file extensions"""
        supported_files = ["test.jpg", "test.jpeg", "test.png", "TEST.JPG"]
        
        for filename in supported_files:
            mock_file = self.create_mock_file(name=filename)
            result = ImageValidationError.validate_file_format(mock_file)
            assert result.is_valid is True, f"Failed for {filename}"
    
    def test_validate_file_size_no_size_attribute(self):
        """Test validation with file that has no size attribute"""
        mock_file = Mock()
        mock_file.name = "test.jpg"
        # Remove the size attribute completely
        if hasattr(mock_file, 'size'):
            delattr(mock_file, 'size')
        result = ImageValidationError.validate_file_size(mock_file)
        assert result.is_valid is False
        assert result.error_details.code == "VAL_IMG_005"
    
    def test_validate_file_size_too_large(self):
        """Test validation with file that's too large"""
        large_size = 15 * 1024 * 1024  # 15MB
        mock_file = self.create_mock_file(size=large_size)
        result = ImageValidationError.validate_file_size(mock_file)
        assert result.is_valid is False
        assert result.error_details.code == "VAL_IMG_006"
        assert "15.00MB" in result.error_details.user_message
        assert "10MB" in result.error_details.user_message
    
    def test_validate_file_size_acceptable(self):
        """Test validation with acceptable file size"""
        acceptable_size = 5 * 1024 * 1024  # 5MB
        mock_file = self.create_mock_file(size=acceptable_size)
        result = ImageValidationError.validate_file_size(mock_file)
        assert result.is_valid is True
    
    def test_validate_file_size_very_small_warning(self):
        """Test validation with very small file (should warn)"""
        small_size = 500  # 500 bytes
        mock_file = self.create_mock_file(size=small_size)
        result = ImageValidationError.validate_file_size(mock_file)
        assert result.is_valid is True
        assert len(result.warnings) > 0
        assert "very small" in result.warnings[0]
    
    @pytest.fixture
    def mock_image_open(self, monkeypatch):
        """Fixture to mock PIL.Image.open"""
        def mock_open(file):
            # Create a mock image
            mock_img = Mock()
            mock_img.size = (800, 600)
            mock_img.mode = 'RGB'
            return mock_img
        
        monkeypatch.setattr("PIL.Image.open", mock_open)
        return mock_open
    
    def test_validate_image_content_success(self, mock_image_open):
        """Test successful image content validation"""
        mock_file = self.create_mock_file()
        result = ImageValidationError.validate_image_content(mock_file)
        assert result.is_valid is True
    
    def test_validate_image_content_too_small(self, monkeypatch):
        """Test validation with image that's too small"""
        def mock_open(file):
            mock_img = Mock()
            mock_img.size = (50, 50)  # Too small
            mock_img.mode = 'RGB'
            return mock_img
        
        monkeypatch.setattr("PIL.Image.open", mock_open)
        
        mock_file = self.create_mock_file()
        result = ImageValidationError.validate_image_content(mock_file)
        assert result.is_valid is False
        assert result.error_details.code == "VAL_IMG_007"
        assert "too small" in result.error_details.user_message
    
    def test_validate_image_content_too_large(self, monkeypatch):
        """Test validation with image that's too large"""
        def mock_open(file):
            mock_img = Mock()
            mock_img.size = (15000, 15000)  # Too large
            mock_img.mode = 'RGB'
            return mock_img
        
        monkeypatch.setattr("PIL.Image.open", mock_open)
        
        mock_file = self.create_mock_file()
        result = ImageValidationError.validate_image_content(mock_file)
        assert result.is_valid is False
        assert result.error_details.code == "VAL_IMG_008"
        assert "too large" in result.error_details.user_message
    
    def test_validate_image_content_unusual_mode_warning(self, monkeypatch):
        """Test validation with unusual image mode (should warn)"""
        def mock_open(file):
            mock_img = Mock()
            mock_img.size = (800, 600)
            mock_img.mode = 'CMYK'  # Unusual mode
            return mock_img
        
        monkeypatch.setattr("PIL.Image.open", mock_open)
        
        mock_file = self.create_mock_file()
        result = ImageValidationError.validate_image_content(mock_file)
        assert result.is_valid is True
        assert len(result.warnings) > 0
        assert "CMYK" in result.warnings[0]
    
    def test_validate_image_content_corrupted_file(self, monkeypatch):
        """Test validation with corrupted image file"""
        def mock_open(file):
            raise Exception("Cannot identify image file")
        
        monkeypatch.setattr("PIL.Image.open", mock_open)
        
        mock_file = self.create_mock_file()
        result = ImageValidationError.validate_image_content(mock_file)
        assert result.is_valid is False
        assert result.error_details.code == "VAL_IMG_009"
        assert "corrupted" in result.error_details.user_message


class TestJSONValidationError:
    """Test JSONValidationError class"""
    
    def test_validate_json_syntax_empty_string(self):
        """Test validation with empty JSON string"""
        result = JSONValidationError.validate_json_syntax("")
        assert result.is_valid is True
        
        result = JSONValidationError.validate_json_syntax("   ")
        assert result.is_valid is True
    
    def test_validate_json_syntax_valid_object(self):
        """Test validation with valid JSON object"""
        valid_json = '{"key": "value", "number": 123}'
        result = JSONValidationError.validate_json_syntax(valid_json)
        assert result.is_valid is True
    
    def test_validate_json_syntax_array_not_object(self):
        """Test validation with JSON array (should fail)"""
        json_array = '["item1", "item2"]'
        result = JSONValidationError.validate_json_syntax(json_array)
        assert result.is_valid is False
        assert result.error_details.code == "VAL_JSON_001"
        assert "object" in result.error_details.user_message
        assert "curly braces" in result.error_details.user_message
    
    def test_validate_json_syntax_missing_comma(self):
        """Test validation with missing comma"""
        invalid_json = '{"key1": "value1" "key2": "value2"}'
        result = JSONValidationError.validate_json_syntax(invalid_json)
        assert result.is_valid is False
        assert result.error_details.code == "VAL_JSON_002"
        assert "line" in result.error_details.user_message
    
    def test_validate_json_syntax_missing_colon(self):
        """Test validation with missing colon"""
        invalid_json = '{"key1" "value1"}'
        result = JSONValidationError.validate_json_syntax(invalid_json)
        assert result.is_valid is False
        assert result.error_details.code == "VAL_JSON_002"
    
    def test_validate_json_syntax_unterminated_string(self):
        """Test validation with unterminated string"""
        invalid_json = '{"key": "unterminated string}'
        result = JSONValidationError.validate_json_syntax(invalid_json)
        assert result.is_valid is False
        assert result.error_details.code == "VAL_JSON_002"
    
    def test_validate_json_syntax_multiline_error(self):
        """Test validation with multiline JSON error"""
        invalid_json = '''
        {
            "key1": "value1",
            "key2": "value2"
            "key3": "value3"
        }
        '''
        result = JSONValidationError.validate_json_syntax(invalid_json)
        assert result.is_valid is False
        assert "line" in result.error_details.user_message
        assert ">>>" in result.error_details.user_message  # Context marker
    
    def test_analyze_json_error_missing_comma(self):
        """Test JSON error analysis for missing comma"""
        json_string = '{"key1": "value1" "key2": "value2"}'
        try:
            json.loads(json_string)
        except json.JSONDecodeError as e:
            json_error = JSONValidationError._analyze_json_error(json_string, e)
            assert json_error.error_type == "Missing Comma"
            assert "comma" in json_error.suggestion
    
    def test_analyze_json_error_missing_colon(self):
        """Test JSON error analysis for missing colon"""
        json_string = '{"key1" "value1"}'
        try:
            json.loads(json_string)
        except json.JSONDecodeError as e:
            json_error = JSONValidationError._analyze_json_error(json_string, e)
            assert json_error.error_type == "Missing Colon"
            assert "colon" in json_error.suggestion
    
    def test_format_json_error_message(self):
        """Test formatting of JSON error message"""
        json_error = JSONError(
            line_number=2,
            column_number=15,
            error_type="Missing Comma",
            error_message="Expecting ',' delimiter",
            context_lines=["  1     {", "  2 >>> \"key1\": \"value1\" \"key2\": \"value2\"", "  3     }"],
            suggestion="Add a comma (,) between object properties"
        )
        
        formatted = JSONValidationError._format_json_error_message(json_error)
        assert "line 2, column 15" in formatted
        assert "Missing Comma" in formatted
        assert ">>>" in formatted
        assert "Add a comma" in formatted
    
    def test_get_json_error_suggestions(self):
        """Test getting JSON error suggestions"""
        json_error = JSONError(
            line_number=1,
            column_number=1,
            error_type="Missing Comma",
            error_message="Test error",
            context_lines=[],
            suggestion="Add a comma"
        )
        
        suggestions = JSONValidationError._get_json_error_suggestions(json_error)
        assert "Add a comma" in suggestions
        assert "JSON validator" in " ".join(suggestions)
        assert "double quotes" in " ".join(suggestions)


class TestMetadataValidationError:
    """Test MetadataValidationError class"""
    
    def test_validate_metadata_fields_not_dict(self):
        """Test validation with non-dictionary metadata"""
        result = MetadataValidationError.validate_metadata_fields("not a dict")
        assert result.is_valid is False
        assert result.error_details.code == "VAL_META_001"
        assert "JSON object" in result.error_details.user_message
    
    def test_validate_metadata_fields_missing_required(self):
        """Test validation with missing required fields"""
        metadata = {"description": "Some description"}  # Missing component_id and component_name
        result = MetadataValidationError.validate_metadata_fields(metadata)
        assert result.is_valid is False
        assert result.error_details.code == "VAL_META_002"
        assert "component_id" in result.error_details.user_message
        assert "component_name" in result.error_details.user_message
    
    def test_validate_metadata_fields_valid_minimal(self):
        """Test validation with minimal valid metadata"""
        metadata = {
            "component_id": "IMG_001",
            "component_name": "Test Image"
        }
        result = MetadataValidationError.validate_metadata_fields(metadata)
        assert result.is_valid is True
    
    def test_validate_metadata_fields_valid_complete(self):
        """Test validation with complete valid metadata"""
        metadata = {
            "component_id": "IMG_001",
            "component_name": "Test Image",
            "description": "A test image for validation",
            "usage_rights": {"commercial_use": True},
            "geographic_restrictions": ["US", "CA"],
            "channel_requirements": {"web": "optimized"},
            "file_specifications": {"format": "JPEG"}
        }
        result = MetadataValidationError.validate_metadata_fields(metadata)
        assert result.is_valid is True
    
    def test_validate_field_value_empty_required(self):
        """Test validation of empty required field"""
        field_info = {"description": "Test field", "example": "test_value"}
        result = MetadataValidationError._validate_field_value("test_field", "", field_info)
        assert result.is_valid is False
        assert result.error_details.code == "VAL_META_003"
    
    def test_validate_field_value_too_short(self):
        """Test validation of field that's too short"""
        field_info = {"min_length": 5, "example": "test_value"}
        result = MetadataValidationError._validate_field_value("test_field", "abc", field_info)
        assert result.is_valid is False
        assert result.error_details.code == "VAL_META_004"
        assert "5 characters" in result.error_details.user_message
    
    def test_validate_field_value_too_long(self):
        """Test validation of field that's too long"""
        field_info = {"max_length": 10, "example": "test"}
        long_value = "a" * 15
        result = MetadataValidationError._validate_field_value("test_field", long_value, field_info)
        assert result.is_valid is False
        assert result.error_details.code == "VAL_META_005"
        assert "10 characters" in result.error_details.user_message
    
    def test_validate_field_value_invalid_pattern(self):
        """Test validation of field with invalid pattern"""
        field_info = {"validation_pattern": r"^[A-Za-z0-9_-]+$", "example": "valid_id"}
        result = MetadataValidationError._validate_field_value("test_field", "invalid id!", field_info)
        assert result.is_valid is False
        assert result.error_details.code == "VAL_META_006"
        assert "invalid characters" in result.error_details.user_message
    
    def test_validate_field_value_wrong_type_object(self):
        """Test validation of field with wrong type (should be object)"""
        field_info = {"type": "object"}
        result = MetadataValidationError._validate_field_value("test_field", "not an object", field_info)
        assert result.is_valid is False
        assert result.error_details.code == "VAL_META_007"
        assert "JSON object" in result.error_details.user_message
    
    def test_validate_field_value_wrong_type_array(self):
        """Test validation of field with wrong type (should be array)"""
        field_info = {"type": "array"}
        result = MetadataValidationError._validate_field_value("test_field", "not an array", field_info)
        assert result.is_valid is False
        assert result.error_details.code == "VAL_META_008"
        assert "JSON array" in result.error_details.user_message


class TestIntegratedValidationFunctions:
    """Test integrated validation functions"""
    
    def create_mock_file(self, name="test.jpg", size=1024):
        """Create a mock file object"""
        mock_file = Mock()
        mock_file.name = name
        mock_file.size = size
        mock_file.getvalue.return_value = b"fake_image_data"
        return mock_file
    
    @pytest.fixture
    def mock_image_open(self, monkeypatch):
        """Fixture to mock PIL.Image.open"""
        def mock_open(file):
            mock_img = Mock()
            mock_img.size = (800, 600)
            mock_img.mode = 'RGB'
            return mock_img
        
        monkeypatch.setattr("PIL.Image.open", mock_open)
        return mock_open
    
    def test_validate_image_upload_success(self, mock_image_open):
        """Test successful image upload validation"""
        mock_file = self.create_mock_file()
        result = validate_image_upload(mock_file)
        assert result.is_valid is True
    
    def test_validate_image_upload_invalid_format(self):
        """Test image upload validation with invalid format"""
        mock_file = self.create_mock_file(name="test.gif")
        result = validate_image_upload(mock_file)
        assert result.is_valid is False
        assert result.error_details.code == "VAL_IMG_004"
    
    def test_validate_image_upload_too_large(self):
        """Test image upload validation with file too large"""
        large_size = 15 * 1024 * 1024  # 15MB
        mock_file = self.create_mock_file(size=large_size)
        result = validate_image_upload(mock_file)
        assert result.is_valid is False
        assert result.error_details.code == "VAL_IMG_006"
    
    def test_validate_json_metadata_success(self):
        """Test successful JSON metadata validation"""
        valid_json = '{"component_id": "IMG_001", "component_name": "Test Image"}'
        result = validate_json_metadata(valid_json)
        assert result.is_valid is True
    
    def test_validate_json_metadata_empty(self):
        """Test JSON metadata validation with empty string"""
        result = validate_json_metadata("")
        assert result.is_valid is True
    
    def test_validate_json_metadata_invalid_syntax(self):
        """Test JSON metadata validation with invalid syntax"""
        invalid_json = '{"key": "value"'  # Missing closing brace
        result = validate_json_metadata(invalid_json)
        assert result.is_valid is False
        assert result.error_details.code == "VAL_JSON_002"
    
    def test_validate_json_metadata_missing_required_fields(self):
        """Test JSON metadata validation with missing required fields"""
        json_missing_fields = '{"description": "Some description"}'
        result = validate_json_metadata(json_missing_fields)
        assert result.is_valid is False
        assert result.error_details.code == "VAL_META_002"
    
    def test_validate_json_metadata_with_context(self):
        """Test JSON metadata validation with error context"""
        context = ErrorContext(operation="metadata_validation", step="input")
        invalid_json = '{"key": "value"'
        result = validate_json_metadata(invalid_json, context)
        assert result.is_valid is False
        assert result.error_details.context == context


class TestErrorContextIntegration:
    """Test error context integration with validation"""
    
    def test_validation_with_context(self):
        """Test that error context is properly passed through validation"""
        context = ErrorContext(
            operation="image_upload",
            step="validation",
            component="file_validator"
        )
        
        result = ImageValidationError.validate_file_format(None, context)
        assert result.is_valid is False
        assert result.error_details.context == context
        assert result.error_details.context.operation == "image_upload"
    
    def test_json_validation_with_context(self):
        """Test JSON validation with context"""
        context = ErrorContext(operation="metadata_input")
        invalid_json = '{"invalid": json}'
        
        result = JSONValidationError.validate_json_syntax(invalid_json, context)
        assert result.is_valid is False
        assert result.error_details.context == context


if __name__ == "__main__":
    pytest.main([__file__])
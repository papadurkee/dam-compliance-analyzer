"""
Tests for the image processing utilities.
"""
import io
import pytest
from unittest.mock import MagicMock, patch
from PIL import Image

from utils.image_processing import (
    validate_image_format,
    convert_to_bytes,
    generate_image_preview,
    get_image_metadata,
    resize_image_if_needed,
    ALLOWED_EXTENSIONS,
    MAX_IMAGE_SIZE_MB
)


class TestImageValidation:
    def test_validate_image_format_none(self):
        """Test validation with no file."""
        is_valid, error_message = validate_image_format(None)
        assert is_valid is False
        assert "No file uploaded" in error_message

    def test_validate_image_format_invalid_extension(self):
        """Test validation with invalid file extension."""
        mock_file = MagicMock()
        mock_file.name = "test.pdf"
        
        is_valid, error_message = validate_image_format(mock_file)
        assert is_valid is False
        assert "Unsupported file format" in error_message

    def test_validate_image_format_valid_extensions(self):
        """Test validation with all valid file extensions."""
        for ext in ALLOWED_EXTENSIONS:
            mock_file = MagicMock()
            mock_file.name = f"test.{ext}"
            mock_file.size = 1024 * 1024  # 1MB
            
            is_valid, error_message = validate_image_format(mock_file)
            assert is_valid is True
            assert error_message == ""

    def test_validate_image_format_size_limit(self):
        """Test validation with file exceeding size limit."""
        mock_file = MagicMock()
        mock_file.name = "test.jpg"
        mock_file.size = (MAX_IMAGE_SIZE_MB + 1) * 1024 * 1024  # Exceed limit by 1MB
        
        is_valid, error_message = validate_image_format(mock_file)
        assert is_valid is False
        assert "File size exceeds" in error_message


class TestImageConversion:
    def test_convert_to_bytes(self):
        """Test converting image to bytes."""
        test_bytes = b"test image bytes"
        mock_file = MagicMock()
        mock_file.getvalue.return_value = test_bytes
        
        result = convert_to_bytes(mock_file)
        assert result == test_bytes
        mock_file.getvalue.assert_called_once()


class TestImagePreview:
    @patch("utils.image_processing.Image.open")
    def test_generate_image_preview(self, mock_image_open):
        """Test generating image preview."""
        mock_image = MagicMock()
        mock_image_open.return_value = mock_image
        mock_file = MagicMock()
        
        result = generate_image_preview(mock_file)
        assert result == mock_image
        mock_image_open.assert_called_once_with(mock_file)

    def test_get_image_metadata(self):
        """Test extracting image metadata."""
        mock_image = MagicMock()
        mock_image.format = "JPEG"
        mock_image.mode = "RGB"
        mock_image.width = 800
        mock_image.height = 600
        
        metadata = get_image_metadata(mock_image)
        assert metadata["format"] == "JPEG"
        assert metadata["mode"] == "RGB"
        assert metadata["width"] == 800
        assert metadata["height"] == 600
        assert metadata["aspect_ratio"] == 1.33  # 800/600 = 1.33

    def test_get_image_metadata_zero_height(self):
        """Test extracting metadata with zero height (edge case)."""
        mock_image = MagicMock()
        mock_image.width = 800
        mock_image.height = 0
        
        metadata = get_image_metadata(mock_image)
        assert metadata["aspect_ratio"] is None

    def test_resize_image_if_needed_no_resize(self):
        """Test image not resized if under max width."""
        mock_image = MagicMock()
        mock_image.width = 500
        mock_image.height = 300
        
        result = resize_image_if_needed(mock_image, max_width=800)
        assert result == mock_image
        mock_image.resize.assert_not_called()

    def test_resize_image_if_needed_with_resize(self):
        """Test image resized if over max width."""
        mock_image = MagicMock()
        mock_image.width = 1000
        mock_image.height = 600
        
        resize_image_if_needed(mock_image, max_width=800)
        
        # Check that resize was called with correct parameters
        mock_image.resize.assert_called_once()
        args, kwargs = mock_image.resize.call_args
        assert args[0] == (800, 480)  # 800 width, height scaled proportionally
        assert args[1] == Image.LANCZOS
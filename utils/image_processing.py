"""
Image processing utilities for DAM Compliance Analyzer.

This module provides functions for validating, converting, and processing
images for use with the Vertex AI API and Streamlit UI.
"""
import io
from typing import Tuple, Dict, Any, Optional, Union
from PIL import Image
import streamlit as st


# Constants for image validation
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
MAX_IMAGE_SIZE_MB = 10  # Maximum image size in MB


def validate_image_format(file: Any) -> Tuple[bool, str]:
    """
    Validates if the uploaded file is in an acceptable format and size.
    
    Args:
        file: The uploaded file object from Streamlit
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if file is None:
        return False, "No file uploaded"
    
    # Check file extension
    file_extension = file.name.split(".")[-1].lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        return False, f"Unsupported file format. Please upload JPG, JPEG, or PNG files."
    
    # Check file size
    file_size_mb = file.size / (1024 * 1024)  # Convert bytes to MB
    if file_size_mb > MAX_IMAGE_SIZE_MB:
        return False, f"File size exceeds the {MAX_IMAGE_SIZE_MB}MB limit."
    
    return True, ""


def convert_to_bytes(image_file: Any) -> bytes:
    """
    Converts an uploaded image file to bytes for API consumption.
    
    Args:
        image_file: The uploaded file object from Streamlit
        
    Returns:
        bytes: The image as bytes
    """
    return image_file.getvalue()


def generate_image_preview(image_file: Any) -> Image.Image:
    """
    Creates a preview of the uploaded image for UI display.
    
    Args:
        image_file: The uploaded file object from Streamlit
        
    Returns:
        PIL.Image: The image preview
    """
    image = Image.open(image_file)
    return image


def get_image_metadata(image: Image.Image) -> Dict[str, Any]:
    """
    Extracts basic metadata from an image.
    
    Args:
        image: PIL Image object
        
    Returns:
        Dict[str, Any]: Dictionary containing image metadata
    """
    return {
        "format": image.format,
        "mode": image.mode,
        "width": image.width,
        "height": image.height,
        "aspect_ratio": round(image.width / image.height, 2) if image.height > 0 else None
    }


def resize_image_if_needed(image: Image.Image, max_width: int = 800) -> Image.Image:
    """
    Resizes an image for display if it exceeds the maximum width.
    
    Args:
        image: PIL Image object
        max_width: Maximum width for the image
        
    Returns:
        PIL.Image: Resized image if needed, original otherwise
    """
    if image.width > max_width:
        ratio = max_width / image.width
        new_height = int(image.height * ratio)
        return image.resize((max_width, new_height), Image.LANCZOS)
    return image
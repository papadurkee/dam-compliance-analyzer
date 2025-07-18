"""
Image processing utilities for DAM Compliance Analyzer.

This module provides functions for validating, converting, and processing
images for use with the Vertex AI API and Streamlit UI.
"""
import io
from typing import Tuple, Dict, Any, Optional, Union
from PIL import Image, ExifTags
import streamlit as st
import json
from datetime import datetime


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


def extract_exif_metadata(image: Image.Image) -> Dict[str, Any]:
    """
    Extracts EXIF metadata from an image.
    
    Args:
        image: PIL Image object
        
    Returns:
        Dict[str, Any]: Dictionary containing EXIF metadata
    """
    exif_data = {}
    
    try:
        # Get EXIF data
        exif = image.getexif()
        
        if exif is not None:
            for tag_id, value in exif.items():
                tag = ExifTags.TAGS.get(tag_id, tag_id)
                
                # Convert bytes to string if needed
                if isinstance(value, bytes):
                    try:
                        value = value.decode('utf-8')
                    except UnicodeDecodeError:
                        value = str(value)
                
                # Handle datetime fields
                if tag in ['DateTime', 'DateTimeOriginal', 'DateTimeDigitized']:
                    try:
                        # Convert EXIF datetime format to ISO format
                        dt = datetime.strptime(str(value), '%Y:%m:%d %H:%M:%S')
                        value = dt.isoformat() + 'Z'
                    except (ValueError, TypeError):
                        pass  # Keep original value if conversion fails
                
                exif_data[tag] = value
    
    except Exception as e:
        # If EXIF extraction fails, return empty dict
        exif_data['extraction_error'] = str(e)
    
    return exif_data


def extract_embedded_metadata(image_file: Any) -> Dict[str, Any]:
    """
    Extracts all available embedded metadata from an image file.
    
    Args:
        image_file: The uploaded file object from Streamlit
        
    Returns:
        Dict[str, Any]: Dictionary containing all extracted metadata
    """
    try:
        # Open image
        image = Image.open(image_file)
        
        # Get basic image metadata
        basic_metadata = get_image_metadata(image)
        
        # Get EXIF metadata
        exif_metadata = extract_exif_metadata(image)
        
        # Combine all metadata
        embedded_metadata = {
            "basic_info": basic_metadata,
            "exif_data": exif_metadata,
            "has_exif": len(exif_metadata) > 0 and 'extraction_error' not in exif_metadata
        }
        
        # Extract commonly used fields for DAM compliance
        dam_relevant_metadata = extract_dam_relevant_fields(exif_metadata)
        if dam_relevant_metadata:
            embedded_metadata["dam_relevant"] = dam_relevant_metadata
        
        return embedded_metadata
        
    except Exception as e:
        return {
            "extraction_error": str(e),
            "basic_info": {},
            "exif_data": {},
            "has_exif": False
        }


def extract_dam_relevant_fields(exif_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts DAM-relevant fields from EXIF data.
    
    Args:
        exif_data: Dictionary containing EXIF metadata
        
    Returns:
        Dict[str, Any]: Dictionary containing DAM-relevant metadata
    """
    dam_fields = {}
    
    # Mapping of EXIF tags to DAM-relevant field names
    field_mapping = {
        'Artist': 'photographer',
        'Copyright': 'copyright',
        'DateTime': 'creation_date',
        'DateTimeOriginal': 'shoot_date',
        'DateTimeDigitized': 'digitized_date',
        'Make': 'camera_make',
        'Model': 'camera_model',
        'Software': 'editing_software',
        'ImageDescription': 'description',
        'XResolution': 'x_resolution',
        'YResolution': 'y_resolution',
        'ResolutionUnit': 'resolution_unit',
        'ColorSpace': 'color_space',
        'WhiteBalance': 'white_balance',
        'Flash': 'flash_used',
        'FocalLength': 'focal_length',
        'ISO': 'iso_speed',
        'ExposureTime': 'exposure_time',
        'FNumber': 'aperture',
        'GPS': 'location_data'
    }
    
    for exif_tag, dam_field in field_mapping.items():
        if exif_tag in exif_data:
            dam_fields[dam_field] = exif_data[exif_tag]
    
    # Handle GPS data specially
    if 'GPSInfo' in exif_data:
        gps_info = exif_data['GPSInfo']
        if gps_info:
            dam_fields['has_location_data'] = True
            dam_fields['gps_info'] = gps_info
    
    return dam_fields


def merge_metadata_with_embedded(user_metadata: Dict[str, Any], embedded_metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merges user-provided metadata with embedded metadata, giving priority to user input.
    
    Args:
        user_metadata: User-provided JSON metadata
        embedded_metadata: Extracted embedded metadata
        
    Returns:
        Dict[str, Any]: Merged metadata dictionary
    """
    merged = user_metadata.copy()
    
    # Add embedded metadata section
    merged['embedded_metadata'] = embedded_metadata
    
    # If user didn't provide certain fields, try to fill from embedded data
    if embedded_metadata.get('has_exif') and 'dam_relevant' in embedded_metadata:
        dam_relevant = embedded_metadata['dam_relevant']
        
        # Fill missing fields from embedded data
        field_mappings = {
            'photographer': 'photographer',
            'copyright': 'copyright', 
            'creation_date': 'shoot_date',
            'camera_make': 'camera_make',
            'camera_model': 'camera_model'
        }
        
        # Create metadata_fields section if it doesn't exist
        if 'metadata_fields' not in merged:
            merged['metadata_fields'] = {}
        
        for user_field, embedded_field in field_mappings.items():
            if (user_field not in merged['metadata_fields'] or 
                not merged['metadata_fields'][user_field]) and embedded_field in dam_relevant:
                merged['metadata_fields'][user_field] = dam_relevant[embedded_field]
        
        # Add technical specifications from embedded data
        if 'file_specifications' not in merged:
            merged['file_specifications'] = {}
        
        basic_info = embedded_metadata.get('basic_info', {})
        if 'resolution' not in merged['file_specifications'] and basic_info:
            merged['file_specifications']['resolution'] = f"{basic_info.get('width', 'unknown')}x{basic_info.get('height', 'unknown')}"
        
        if 'current_format' not in merged['file_specifications'] and basic_info:
            merged['file_specifications']['current_format'] = basic_info.get('format', 'unknown')
    
    return merged
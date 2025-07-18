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


def get_mime_type_from_format(image_format: str) -> str:
    """
    Get the correct MIME type for an image format.
    
    Args:
        image_format: PIL image format (e.g., 'JPEG', 'PNG')
        
    Returns:
        str: MIME type for the image format
    """
    format_to_mime = {
        'JPEG': 'image/jpeg',
        'JPG': 'image/jpeg',
        'PNG': 'image/png',
        'WEBP': 'image/webp',
        'GIF': 'image/gif',
        'BMP': 'image/bmp',
        'TIFF': 'image/tiff'
    }
    
    return format_to_mime.get(image_format.upper(), 'image/jpeg')  # Default to JPEG


def detect_image_format_from_bytes(image_bytes: bytes) -> str:
    """
    Detect image format from raw bytes.
    
    Args:
        image_bytes: Raw image bytes
        
    Returns:
        str: Detected image format
    """
    try:
        from PIL import Image
        import io
        
        # Create a BytesIO object from the bytes
        image_stream = io.BytesIO(image_bytes)
        
        # Open the image to detect format
        with Image.open(image_stream) as img:
            return img.format or 'JPEG'
            
    except Exception:
        # Default to JPEG if detection fails
        return 'JPEG'


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
    Extracts all available embedded metadata from an image file, including custom JSON metadata.
    
    Args:
        image_file: The uploaded file object from Streamlit
        
    Returns:
        Dict[str, Any]: Dictionary containing all extracted metadata
    """
    try:
        # Reset file pointer to beginning
        image_file.seek(0)
        
        # Open image
        image = Image.open(image_file)
        
        # Get basic image metadata
        basic_metadata = get_image_metadata(image)
        
        # Get EXIF metadata
        exif_metadata = extract_exif_metadata(image)
        
        # Try to extract custom metadata from various sources
        custom_metadata = extract_custom_metadata(image, image_file)
        
        # Determine if we have any metadata
        has_metadata = (
            (len(exif_metadata) > 0 and 'extraction_error' not in exif_metadata) or
            bool(custom_metadata)
        )
        
        # Combine all metadata
        embedded_metadata = {
            "basic_info": basic_metadata,
            "exif_data": exif_metadata,
            "custom_metadata": custom_metadata,
            "has_exif": has_metadata,  # Renamed to has_metadata since it includes custom data too
            "has_custom_metadata": bool(custom_metadata)
        }
        
        # Extract commonly used fields for DAM compliance
        dam_relevant_metadata = extract_dam_relevant_fields(exif_metadata, custom_metadata)
        if dam_relevant_metadata:
            embedded_metadata["dam_relevant"] = dam_relevant_metadata
        
        return embedded_metadata
        
    except Exception as e:
        return {
            "extraction_error": str(e),
            "basic_info": {},
            "exif_data": {},
            "custom_metadata": {},
            "has_exif": False,
            "has_custom_metadata": False
        }


def extract_custom_metadata(image: Image.Image, image_file: Any) -> Dict[str, Any]:
    """
    Extracts custom metadata from various sources in the image file.
    
    Args:
        image: PIL Image object
        image_file: The uploaded file object
        
    Returns:
        Dict[str, Any]: Dictionary containing custom metadata
    """
    custom_metadata = {}
    
    try:
        # Reset file pointer
        image_file.seek(0)
        
        # Try to extract from image info (PNG text chunks, etc.)
        if hasattr(image, 'info') and image.info:
            for key, value in image.info.items():
                # Look for JSON-like strings in image info
                if isinstance(value, str) and (value.strip().startswith('{') or 'componentMetadata' in value):
                    try:
                        # Try to parse as JSON
                        parsed_json = json.loads(value)
                        custom_metadata['image_info_json'] = parsed_json
                        break
                    except json.JSONDecodeError:
                        # If not valid JSON, store as text
                        custom_metadata[f'image_info_{key}'] = value
                elif isinstance(value, str) and len(value) > 10:
                    # Store other text metadata
                    custom_metadata[f'image_info_{key}'] = value
        
        # Try to extract from EXIF UserComment or ImageDescription
        exif = image.getexif()
        if exif:
            # Check UserComment (tag 37510)
            if 37510 in exif:
                user_comment = exif[37510]
                if isinstance(user_comment, (str, bytes)):
                    try:
                        if isinstance(user_comment, bytes):
                            user_comment = user_comment.decode('utf-8', errors='ignore')
                        
                        # Try to parse as JSON
                        if user_comment.strip().startswith('{'):
                            parsed_json = json.loads(user_comment)
                            custom_metadata['exif_user_comment_json'] = parsed_json
                        else:
                            custom_metadata['exif_user_comment'] = user_comment
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        custom_metadata['exif_user_comment'] = str(user_comment)
            
            # Check ImageDescription (tag 270)
            if 270 in exif:
                image_desc = exif[270]
                if isinstance(image_desc, str) and image_desc.strip().startswith('{'):
                    try:
                        parsed_json = json.loads(image_desc)
                        custom_metadata['exif_description_json'] = parsed_json
                    except json.JSONDecodeError:
                        custom_metadata['exif_description'] = image_desc
        
        # For PNG files, check text chunks more thoroughly
        if image.format == 'PNG':
            custom_metadata.update(extract_png_text_metadata(image))
        
        # Try to read raw file data for embedded JSON (last resort)
        image_file.seek(0)
        file_content = image_file.read()
        
        # Look for JSON patterns in the file content
        json_patterns = [
            b'{"componentMetadata"',
            b'"componentMetadata"',
            b'{"id":',
            b'"COMP-'
        ]
        
        for pattern in json_patterns:
            if pattern in file_content:
                # Try to extract JSON from around the pattern
                start_idx = file_content.find(pattern)
                if start_idx != -1:
                    # Look for the start of JSON (opening brace)
                    json_start = file_content.rfind(b'{', 0, start_idx + len(pattern))
                    if json_start != -1:
                        # Look for the end of JSON (closing brace)
                        brace_count = 0
                        json_end = json_start
                        for i in range(json_start, len(file_content)):
                            if file_content[i:i+1] == b'{':
                                brace_count += 1
                            elif file_content[i:i+1] == b'}':
                                brace_count -= 1
                                if brace_count == 0:
                                    json_end = i + 1
                                    break
                        
                        if json_end > json_start:
                            try:
                                json_str = file_content[json_start:json_end].decode('utf-8', errors='ignore')
                                parsed_json = json.loads(json_str)
                                custom_metadata['embedded_json'] = parsed_json
                                break
                            except (json.JSONDecodeError, UnicodeDecodeError):
                                continue
        
    except Exception as e:
        custom_metadata['extraction_error'] = str(e)
    
    return custom_metadata


def extract_png_text_metadata(image: Image.Image) -> Dict[str, Any]:
    """
    Extracts text metadata from PNG files.
    
    Args:
        image: PIL Image object (PNG format)
        
    Returns:
        Dict[str, Any]: Dictionary containing PNG text metadata
    """
    png_metadata = {}
    
    try:
        if hasattr(image, 'text'):
            for key, value in image.text.items():
                if isinstance(value, str) and value.strip().startswith('{'):
                    try:
                        parsed_json = json.loads(value)
                        png_metadata[f'png_text_{key}_json'] = parsed_json
                    except json.JSONDecodeError:
                        png_metadata[f'png_text_{key}'] = value
                else:
                    png_metadata[f'png_text_{key}'] = value
    except Exception as e:
        png_metadata['png_extraction_error'] = str(e)
    
    return png_metadata


def extract_dam_relevant_fields(exif_data: Dict[str, Any], custom_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Extracts DAM-relevant fields from EXIF data and custom metadata.
    
    Args:
        exif_data: Dictionary containing EXIF metadata
        custom_metadata: Dictionary containing custom metadata
        
    Returns:
        Dict[str, Any]: Dictionary containing DAM-relevant metadata
    """
    dam_fields = {}
    
    # First, extract from custom metadata if available
    if custom_metadata:
        # Look for componentMetadata in various locations
        component_metadata = None
        
        for key, value in custom_metadata.items():
            if isinstance(value, dict):
                if 'componentMetadata' in value:
                    component_metadata = value['componentMetadata']
                    break
                elif 'id' in value and 'name' in value:
                    component_metadata = value
                    break
        
        if component_metadata:
            # Extract DAM-relevant fields from componentMetadata
            if 'id' in component_metadata:
                dam_fields['component_id'] = component_metadata['id']
            if 'name' in component_metadata:
                dam_fields['component_name'] = component_metadata['name']
            if 'description' in component_metadata:
                dam_fields['description'] = component_metadata['description']
            if 'componentType' in component_metadata:
                dam_fields['component_type'] = component_metadata['componentType']
            if 'status' in component_metadata:
                dam_fields['status'] = component_metadata['status']
            if 'version' in component_metadata:
                dam_fields['version'] = component_metadata['version']
            if 'creationDate' in component_metadata:
                dam_fields['creation_date'] = component_metadata['creationDate']
            if 'fileFormat' in component_metadata:
                dam_fields['file_format'] = component_metadata['fileFormat']
            if 'colorSpace' in component_metadata:
                dam_fields['color_space'] = component_metadata['colorSpace']
            if 'fileSize' in component_metadata:
                dam_fields['file_size'] = component_metadata['fileSize']
            
            # Extract dimensions
            if 'dimensions' in component_metadata:
                dims = component_metadata['dimensions']
                if 'width' in dims and 'height' in dims:
                    dam_fields['dimensions'] = f"{dims['width']}x{dims['height']}"
            
            # Extract usage rights
            if 'usageRights' in component_metadata:
                usage_rights = component_metadata['usageRights']
                dam_fields['usage_rights'] = usage_rights
            
            # Extract restrictions
            if 'geographicRestrictions' in component_metadata:
                dam_fields['geographic_restrictions'] = component_metadata['geographicRestrictions']
            if 'channelRestrictions' in component_metadata:
                dam_fields['channel_restrictions'] = component_metadata['channelRestrictions']
            
            # Extract lifespan
            if 'lifespan' in component_metadata:
                dam_fields['lifespan'] = component_metadata['lifespan']
    
    # Then, extract from EXIF data (this will not override custom metadata)
    exif_mapping = {
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
    
    for exif_tag, dam_field in exif_mapping.items():
        if exif_tag in exif_data and dam_field not in dam_fields:  # Don't override custom metadata
            dam_fields[dam_field] = exif_data[exif_tag]
    
    # Handle GPS data specially
    if 'GPSInfo' in exif_data and 'has_location_data' not in dam_fields:
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
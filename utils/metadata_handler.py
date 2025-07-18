"""
Metadata processing utilities for DAM Compliance Analyzer.

This module provides functions for validating, parsing, and processing
JSON metadata for digital assets in the compliance analysis workflow.
"""
import json
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict

from .validation_errors import validate_json_metadata as enhanced_validate_json_metadata, ValidationResult
from .error_handler import ErrorContext


@dataclass
class ComponentMetadata:
    """Data class representing component metadata structure."""
    component_id: str
    component_name: str
    description: Optional[str] = None
    usage_rights: Optional[Dict[str, Any]] = None
    geographic_restrictions: Optional[List[str]] = None
    channel_requirements: Optional[Dict[str, Any]] = None
    file_specifications: Optional[Dict[str, Any]] = None


def validate_json_metadata(json_string: str, context: Optional[ErrorContext] = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Validates JSON metadata syntax and structure.
    
    This function provides backward compatibility while using the enhanced validation system.
    
    Args:
        json_string: The JSON string to validate
        context: Optional error context for enhanced error reporting
        
    Returns:
        Tuple[bool, str, Optional[Dict]]: (is_valid, error_message, parsed_data)
    """
    # Use the enhanced validation system
    validation_result = enhanced_validate_json_metadata(json_string, context)
    
    if validation_result.is_valid:
        # Parse the JSON to return the data
        if json_string and json_string.strip():
            try:
                parsed_data = json.loads(json_string)
                return True, "", parsed_data
            except json.JSONDecodeError:
                # This shouldn't happen since validation passed, but handle it
                return False, "Unexpected JSON parsing error", None
        else:
            return True, "", {}  # Empty metadata is allowed
    else:
        # Return the enhanced error message
        error_message = validation_result.error_details.user_message
        return False, error_message, None


def validate_json_metadata_enhanced(json_string: str, context: Optional[ErrorContext] = None) -> ValidationResult:
    """
    Enhanced JSON metadata validation that returns detailed ValidationResult.
    
    Args:
        json_string: The JSON string to validate
        context: Optional error context for enhanced error reporting
        
    Returns:
        ValidationResult: Detailed validation result with enhanced error information
    """
    return enhanced_validate_json_metadata(json_string, context)


def enrich_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Adds default fields to metadata if missing.
    
    Args:
        metadata: The metadata dictionary to enrich
        
    Returns:
        Dict[str, Any]: Enriched metadata with default values
    """
    if not metadata:
        metadata = {}
    
    # Set default values for missing required fields
    enriched = metadata.copy()
    
    # Ensure component_id exists
    if "component_id" not in enriched:
        enriched["component_id"] = "unknown_component"
    
    # Ensure component_name exists
    if "component_name" not in enriched:
        enriched["component_name"] = "Unnamed Component"
    
    # Add default optional fields if not present
    if "description" not in enriched:
        enriched["description"] = None
    
    if "usage_rights" not in enriched:
        enriched["usage_rights"] = {
            "commercial_use": None,
            "editorial_use": None,
            "restrictions": None
        }
    
    if "geographic_restrictions" not in enriched:
        enriched["geographic_restrictions"] = []
    
    if "channel_requirements" not in enriched:
        enriched["channel_requirements"] = {
            "web": None,
            "print": None,
            "social_media": None,
            "broadcast": None
        }
    
    if "file_specifications" not in enriched:
        enriched["file_specifications"] = {
            "format": None,
            "resolution": None,
            "color_profile": None,
            "file_size": None
        }
    
    return enriched


def format_for_ai_prompt(metadata: Dict[str, Any]) -> str:
    """
    Formats metadata for AI consumption in prompts.
    
    Args:
        metadata: The metadata dictionary to format
        
    Returns:
        str: Formatted metadata string for AI prompts
    """
    if metadata is None:
        return "No metadata provided."
    
    # Enrich metadata first to ensure all fields are present
    enriched_metadata = enrich_metadata(metadata)
    
    formatted_lines = []
    formatted_lines.append("COMPONENT METADATA:")
    formatted_lines.append(f"- Component ID: {enriched_metadata.get('component_id', 'N/A')}")
    formatted_lines.append(f"- Component Name: {enriched_metadata.get('component_name', 'N/A')}")
    formatted_lines.append(f"- Description: {enriched_metadata.get('description') or 'Not provided'}")
    
    # Format usage rights
    usage_rights = enriched_metadata.get('usage_rights', {})
    if usage_rights and any(usage_rights.values()):
        formatted_lines.append("- Usage Rights:")
        for key, value in usage_rights.items():
            if value is not None:
                formatted_lines.append(f"  - {key.replace('_', ' ').title()}: {value}")
    else:
        formatted_lines.append("- Usage Rights: Not specified")
    
    # Format geographic restrictions
    geo_restrictions = enriched_metadata.get('geographic_restrictions', [])
    if geo_restrictions:
        formatted_lines.append(f"- Geographic Restrictions: {', '.join(geo_restrictions)}")
    else:
        formatted_lines.append("- Geographic Restrictions: None specified")
    
    # Format channel requirements
    channel_reqs = enriched_metadata.get('channel_requirements', {})
    if channel_reqs and any(channel_reqs.values()):
        formatted_lines.append("- Channel Requirements:")
        for channel, requirements in channel_reqs.items():
            if requirements is not None:
                formatted_lines.append(f"  - {channel.replace('_', ' ').title()}: {requirements}")
    else:
        formatted_lines.append("- Channel Requirements: Not specified")
    
    # Format file specifications
    file_specs = enriched_metadata.get('file_specifications', {})
    if file_specs and any(file_specs.values()):
        formatted_lines.append("- File Specifications:")
        for spec, value in file_specs.items():
            if value is not None:
                formatted_lines.append(f"  - {spec.replace('_', ' ').title()}: {value}")
    else:
        formatted_lines.append("- File Specifications: Not specified")
    
    return "\n".join(formatted_lines)


def create_component_metadata(data: Dict[str, Any]) -> ComponentMetadata:
    """
    Creates a ComponentMetadata object from a dictionary.
    
    Args:
        data: Dictionary containing metadata fields
        
    Returns:
        ComponentMetadata: Structured metadata object
    """
    enriched_data = enrich_metadata(data)
    
    return ComponentMetadata(
        component_id=enriched_data["component_id"],
        component_name=enriched_data["component_name"],
        description=enriched_data.get("description"),
        usage_rights=enriched_data.get("usage_rights"),
        geographic_restrictions=enriched_data.get("geographic_restrictions"),
        channel_requirements=enriched_data.get("channel_requirements"),
        file_specifications=enriched_data.get("file_specifications")
    )


def metadata_to_dict(metadata: ComponentMetadata) -> Dict[str, Any]:
    """
    Converts a ComponentMetadata object to a dictionary.
    
    Args:
        metadata: ComponentMetadata object
        
    Returns:
        Dict[str, Any]: Dictionary representation of metadata
    """
    return asdict(metadata)


def get_default_metadata_structure() -> Dict[str, Any]:
    """
    Returns the default metadata structure with all fields.
    
    Returns:
        Dict[str, Any]: Default metadata structure
    """
    return {
        "component_id": "",
        "component_name": "",
        "description": "",
        "usage_rights": {
            "commercial_use": "",
            "editorial_use": "",
            "restrictions": ""
        },
        "geographic_restrictions": [],
        "channel_requirements": {
            "web": "",
            "print": "",
            "social_media": "",
            "broadcast": ""
        },
        "file_specifications": {
            "format": "",
            "resolution": "",
            "color_profile": "",
            "file_size": ""
        }
    }


def validate_required_fields(metadata: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validates that required metadata fields are present and not empty.
    
    Args:
        metadata: Metadata dictionary to validate
        
    Returns:
        Tuple[bool, List[str]]: (is_valid, list_of_missing_fields)
    """
    required_fields = ["component_id", "component_name"]
    missing_fields = []
    
    for field in required_fields:
        if field not in metadata or not metadata[field] or not str(metadata[field]).strip():
            missing_fields.append(field)
    
    return len(missing_fields) == 0, missing_fields
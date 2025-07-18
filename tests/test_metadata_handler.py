"""
Tests for the metadata processing utilities.
"""
import json
import pytest
from typing import Dict, Any

from utils.metadata_handler import (
    ComponentMetadata,
    validate_json_metadata,
    enrich_metadata,
    format_for_ai_prompt,
    create_component_metadata,
    metadata_to_dict,
    get_default_metadata_structure,
    validate_required_fields
)


class TestJSONValidation:
    def test_validate_json_metadata_empty_string(self):
        """Test validation with empty string."""
        is_valid, error_message, parsed_data = validate_json_metadata("")
        assert is_valid is True
        assert error_message == ""
        assert parsed_data == {}

    def test_validate_json_metadata_whitespace_only(self):
        """Test validation with whitespace only."""
        is_valid, error_message, parsed_data = validate_json_metadata("   \n\t  ")
        assert is_valid is True
        assert error_message == ""
        assert parsed_data == {}

    def test_validate_json_metadata_valid_json(self):
        """Test validation with valid JSON."""
        test_json = '{"component_id": "test123", "component_name": "Test Component"}'
        is_valid, error_message, parsed_data = validate_json_metadata(test_json)
        assert is_valid is True
        assert error_message == ""
        assert parsed_data == {"component_id": "test123", "component_name": "Test Component"}

    def test_validate_json_metadata_invalid_json(self):
        """Test validation with invalid JSON syntax."""
        test_json = '{"component_id": "test123", "component_name": "Test Component"'  # Missing closing brace
        is_valid, error_message, parsed_data = validate_json_metadata(test_json)
        assert is_valid is False
        assert "JSON syntax error" in error_message
        assert parsed_data is None

    def test_validate_json_metadata_non_object(self):
        """Test validation with JSON that's not an object."""
        test_json = '["not", "an", "object"]'
        is_valid, error_message, parsed_data = validate_json_metadata(test_json)
        assert is_valid is False
        assert "must be an object" in error_message
        assert parsed_data is None


class TestMetadataEnrichment:
    def test_enrich_metadata_empty_dict(self):
        """Test enriching empty metadata."""
        result = enrich_metadata({})
        assert result["component_id"] == "unknown_component"
        assert result["component_name"] == "Unnamed Component"
        assert result["description"] is None
        assert "usage_rights" in result
        assert "geographic_restrictions" in result
        assert "channel_requirements" in result
        assert "file_specifications" in result

    def test_enrich_metadata_none_input(self):
        """Test enriching None metadata."""
        result = enrich_metadata(None)
        assert result["component_id"] == "unknown_component"
        assert result["component_name"] == "Unnamed Component"

    def test_enrich_metadata_partial_data(self):
        """Test enriching metadata with some existing fields."""
        input_data = {
            "component_id": "existing_id",
            "usage_rights": {"commercial_use": "allowed"}
        }
        result = enrich_metadata(input_data)
        
        # Existing fields should be preserved
        assert result["component_id"] == "existing_id"
        assert result["usage_rights"]["commercial_use"] == "allowed"
        
        # Missing fields should be added
        assert result["component_name"] == "Unnamed Component"
        assert result["description"] is None

    def test_enrich_metadata_complete_data(self):
        """Test enriching metadata that's already complete."""
        input_data = {
            "component_id": "test123",
            "component_name": "Test Component",
            "description": "A test component",
            "usage_rights": {"commercial_use": "allowed"},
            "geographic_restrictions": ["US", "CA"],
            "channel_requirements": {"web": "optimized"},
            "file_specifications": {"format": "JPEG"}
        }
        result = enrich_metadata(input_data)
        
        # All original data should be preserved
        assert result["component_id"] == "test123"
        assert result["component_name"] == "Test Component"
        assert result["description"] == "A test component"
        assert result["usage_rights"]["commercial_use"] == "allowed"
        assert result["geographic_restrictions"] == ["US", "CA"]


class TestAIPromptFormatting:
    def test_format_for_ai_prompt_empty_metadata(self):
        """Test formatting empty metadata."""
        result = format_for_ai_prompt({})
        assert "COMPONENT METADATA:" in result
        assert "Component ID: unknown_component" in result
        assert "Component Name: Unnamed Component" in result

    def test_format_for_ai_prompt_none_metadata(self):
        """Test formatting None metadata."""
        result = format_for_ai_prompt(None)
        assert result == "No metadata provided."

    def test_format_for_ai_prompt_complete_metadata(self):
        """Test formatting complete metadata."""
        metadata = {
            "component_id": "test123",
            "component_name": "Test Component",
            "description": "A test component for validation",
            "usage_rights": {
                "commercial_use": "allowed",
                "editorial_use": "restricted"
            },
            "geographic_restrictions": ["US", "CA", "UK"],
            "channel_requirements": {
                "web": "optimized for web",
                "print": "high resolution required"
            },
            "file_specifications": {
                "format": "JPEG",
                "resolution": "300 DPI"
            }
        }
        
        result = format_for_ai_prompt(metadata)
        
        assert "Component ID: test123" in result
        assert "Component Name: Test Component" in result
        assert "Description: A test component for validation" in result
        assert "Commercial Use: allowed" in result
        assert "Editorial Use: restricted" in result
        assert "Geographic Restrictions: US, CA, UK" in result
        assert "Web: optimized for web" in result
        assert "Format: JPEG" in result

    def test_format_for_ai_prompt_minimal_metadata(self):
        """Test formatting minimal metadata."""
        metadata = {
            "component_id": "minimal123",
            "component_name": "Minimal Component"
        }
        
        result = format_for_ai_prompt(metadata)
        
        assert "Component ID: minimal123" in result
        assert "Component Name: Minimal Component" in result
        assert "Description: Not provided" in result
        assert "Usage Rights: Not specified" in result
        assert "Geographic Restrictions: None specified" in result


class TestComponentMetadataClass:
    def test_create_component_metadata_minimal(self):
        """Test creating ComponentMetadata with minimal data."""
        data = {"component_id": "test123", "component_name": "Test"}
        metadata = create_component_metadata(data)
        
        assert isinstance(metadata, ComponentMetadata)
        assert metadata.component_id == "test123"
        assert metadata.component_name == "Test"
        assert metadata.description is None

    def test_create_component_metadata_complete(self):
        """Test creating ComponentMetadata with complete data."""
        data = {
            "component_id": "test123",
            "component_name": "Test Component",
            "description": "A test component",
            "usage_rights": {"commercial_use": "allowed"},
            "geographic_restrictions": ["US"],
            "channel_requirements": {"web": "optimized"},
            "file_specifications": {"format": "JPEG"}
        }
        metadata = create_component_metadata(data)
        
        assert metadata.component_id == "test123"
        assert metadata.component_name == "Test Component"
        assert metadata.description == "A test component"
        assert metadata.usage_rights["commercial_use"] == "allowed"

    def test_metadata_to_dict(self):
        """Test converting ComponentMetadata to dictionary."""
        metadata = ComponentMetadata(
            component_id="test123",
            component_name="Test Component",
            description="A test component"
        )
        
        result = metadata_to_dict(metadata)
        
        assert isinstance(result, dict)
        assert result["component_id"] == "test123"
        assert result["component_name"] == "Test Component"
        assert result["description"] == "A test component"


class TestDefaultStructure:
    def test_get_default_metadata_structure(self):
        """Test getting default metadata structure."""
        result = get_default_metadata_structure()
        
        assert isinstance(result, dict)
        assert "component_id" in result
        assert "component_name" in result
        assert "description" in result
        assert "usage_rights" in result
        assert "geographic_restrictions" in result
        assert "channel_requirements" in result
        assert "file_specifications" in result
        
        # Check nested structures
        assert isinstance(result["usage_rights"], dict)
        assert isinstance(result["geographic_restrictions"], list)
        assert isinstance(result["channel_requirements"], dict)
        assert isinstance(result["file_specifications"], dict)


class TestRequiredFieldValidation:
    def test_validate_required_fields_complete(self):
        """Test validation with all required fields present."""
        metadata = {
            "component_id": "test123",
            "component_name": "Test Component"
        }
        
        is_valid, missing_fields = validate_required_fields(metadata)
        assert is_valid is True
        assert missing_fields == []

    def test_validate_required_fields_missing_id(self):
        """Test validation with missing component_id."""
        metadata = {
            "component_name": "Test Component"
        }
        
        is_valid, missing_fields = validate_required_fields(metadata)
        assert is_valid is False
        assert "component_id" in missing_fields

    def test_validate_required_fields_missing_name(self):
        """Test validation with missing component_name."""
        metadata = {
            "component_id": "test123"
        }
        
        is_valid, missing_fields = validate_required_fields(metadata)
        assert is_valid is False
        assert "component_name" in missing_fields

    def test_validate_required_fields_empty_values(self):
        """Test validation with empty string values."""
        metadata = {
            "component_id": "",
            "component_name": "   "  # Whitespace only
        }
        
        is_valid, missing_fields = validate_required_fields(metadata)
        assert is_valid is False
        assert "component_id" in missing_fields
        assert "component_name" in missing_fields

    def test_validate_required_fields_none_values(self):
        """Test validation with None values."""
        metadata = {
            "component_id": None,
            "component_name": "Test Component"
        }
        
        is_valid, missing_fields = validate_required_fields(metadata)
        assert is_valid is False
        assert "component_id" in missing_fields
"""
Sample Data Integration Tests

This module tests that the sample data works correctly with the application.
"""

import pytest
import json
import os
from PIL import Image
from utils.image_processing import validate_image_format, convert_to_bytes
from utils.metadata_handler import validate_json_metadata_enhanced, format_for_ai_prompt
from utils.error_handler import ErrorContext


class TestSampleDataIntegration:
    """Test class for sample data integration"""
    
    def test_sample_images_exist_and_valid(self):
        """Test that all sample images exist and are valid"""
        
        sample_dir = "sample_data"
        expected_images = [
            "compliant_high_quality.jpg",
            "compliant_standard.jpg", 
            "non_compliant_low_res.jpg",
            "non_compliant_tiny.jpg",
            "social_media_square.jpg",
            "banner_wide.jpg"
        ]
        
        for image_name in expected_images:
            image_path = os.path.join(sample_dir, image_name)
            
            # Check file exists
            assert os.path.exists(image_path), f"Sample image {image_name} not found"
            
            # Check file can be opened as image
            try:
                with Image.open(image_path) as img:
                    assert img.format == 'JPEG', f"Image {image_name} should be JPEG format"
                    assert img.width > 0 and img.height > 0, f"Image {image_name} has invalid dimensions"
                    print(f"✅ {image_name}: {img.width}x{img.height} pixels")
            except Exception as e:
                pytest.fail(f"Failed to open sample image {image_name}: {e}")
    
    def test_sample_metadata_files_valid(self):
        """Test that all sample metadata files are valid JSON"""
        
        sample_dir = "sample_data"
        expected_metadata = [
            "complete_metadata.json",
            "minimal_metadata.json",
            "problematic_metadata.json"
        ]
        
        for metadata_name in expected_metadata:
            metadata_path = os.path.join(sample_dir, metadata_name)
            
            # Check file exists
            assert os.path.exists(metadata_path), f"Sample metadata {metadata_name} not found"
            
            # Check file is valid JSON
            try:
                with open(metadata_path, 'r') as f:
                    data = json.load(f)
                    assert isinstance(data, dict), f"Metadata {metadata_name} should be a JSON object"
                    assert "component_id" in data, f"Metadata {metadata_name} missing component_id"
                    assert "component_name" in data, f"Metadata {metadata_name} missing component_name"
                    print(f"✅ {metadata_name}: {data.get('component_id')} - {data.get('component_name')}")
            except Exception as e:
                pytest.fail(f"Failed to parse sample metadata {metadata_name}: {e}")
    
    def test_image_metadata_mapping_valid(self):
        """Test that the image-metadata mapping file is valid"""
        
        mapping_path = "sample_data/image_metadata_mapping.json"
        
        # Check file exists
        assert os.path.exists(mapping_path), "Image-metadata mapping file not found"
        
        # Load and validate mapping
        with open(mapping_path, 'r') as f:
            mapping = json.load(f)
        
        assert isinstance(mapping, dict), "Mapping should be a JSON object"
        
        # Check that all mapped images exist
        for image_name, metadata_name in mapping.items():
            image_path = os.path.join("sample_data", image_name)
            metadata_path = os.path.join("sample_data", metadata_name)
            
            assert os.path.exists(image_path), f"Mapped image {image_name} not found"
            assert os.path.exists(metadata_path), f"Mapped metadata {metadata_name} not found"
            
            print(f"✅ {image_name} → {metadata_name}")
    
    def test_sample_images_with_validation_functions(self):
        """Test sample images with the actual validation functions"""
        
        sample_dir = "sample_data"
        sample_images = [
            "compliant_high_quality.jpg",
            "compliant_standard.jpg",
            "non_compliant_low_res.jpg",
            "social_media_square.jpg"
        ]
        
        for image_name in sample_images:
            image_path = os.path.join(sample_dir, image_name)
            
            # Create mock file object
            class MockFile:
                def __init__(self, path):
                    self.name = os.path.basename(path)
                    with open(path, 'rb') as f:
                        self._data = f.read()
                    self.size = len(self._data)
                
                def read(self):
                    return self._data
                
                def seek(self, pos):
                    pass
                
                def getvalue(self):
                    return self._data
            
            mock_file = MockFile(image_path)
            
            # Test validation
            is_valid, error_msg = validate_image_format(mock_file)
            assert is_valid, f"Sample image {image_name} failed validation: {error_msg}"
            
            # Test conversion
            image_bytes = convert_to_bytes(mock_file)
            assert len(image_bytes) > 0, f"Failed to convert {image_name} to bytes"
            
            print(f"✅ {image_name}: validation and conversion successful")
    
    def test_sample_metadata_with_validation_functions(self):
        """Test sample metadata with the actual validation functions"""
        
        sample_dir = "sample_data"
        metadata_files = [
            "complete_metadata.json",
            "minimal_metadata.json",
            "problematic_metadata.json"
        ]
        
        for metadata_name in metadata_files:
            metadata_path = os.path.join(sample_dir, metadata_name)
            
            # Load metadata as string
            with open(metadata_path, 'r') as f:
                metadata_str = f.read()
            
            # Test validation
            context = ErrorContext(operation="test", step="validation", component="metadata")
            validation_result = validate_json_metadata_enhanced(metadata_str, context)
            
            assert validation_result.is_valid, f"Sample metadata {metadata_name} failed validation"
            
            # Test formatting
            metadata_dict = json.loads(metadata_str)
            formatted = format_for_ai_prompt(metadata_dict)
            assert len(formatted) > 0, f"Failed to format {metadata_name} for AI prompt"
            assert "Component ID:" in formatted, f"Formatted metadata missing component ID for {metadata_name}"
            
            print(f"✅ {metadata_name}: validation and formatting successful")
    
    def test_expected_compliance_scenarios(self):
        """Test that sample images represent expected compliance scenarios"""
        
        sample_dir = "sample_data"
        
        # High quality image should have large dimensions
        with Image.open(os.path.join(sample_dir, "compliant_high_quality.jpg")) as img:
            assert img.width >= 3840 and img.height >= 2160, "High quality image should be 4K resolution"
        
        # Standard image should have good dimensions
        with Image.open(os.path.join(sample_dir, "compliant_standard.jpg")) as img:
            assert img.width >= 1920 and img.height >= 1080, "Standard image should be Full HD resolution"
        
        # Low res image should have small dimensions
        with Image.open(os.path.join(sample_dir, "non_compliant_low_res.jpg")) as img:
            assert img.width < 1920 or img.height < 1080, "Low res image should be below Full HD"
        
        # Tiny image should have very small dimensions
        with Image.open(os.path.join(sample_dir, "non_compliant_tiny.jpg")) as img:
            assert img.width <= 400 and img.height <= 300, "Tiny image should be very small"
        
        # Square image should be square
        with Image.open(os.path.join(sample_dir, "social_media_square.jpg")) as img:
            assert img.width == img.height, "Square image should have equal width and height"
        
        # Wide image should be wide
        with Image.open(os.path.join(sample_dir, "banner_wide.jpg")) as img:
            assert img.width > img.height * 2, "Wide image should have width much greater than height"
        
        print("✅ All sample images have expected dimensions for their compliance scenarios")
    
    def test_metadata_compliance_scenarios(self):
        """Test that sample metadata represents different compliance scenarios"""
        
        sample_dir = "sample_data"
        
        # Complete metadata should have comprehensive information
        with open(os.path.join(sample_dir, "complete_metadata.json"), 'r') as f:
            complete = json.load(f)
        
        assert "usage_rights" in complete, "Complete metadata should have usage rights"
        assert "channel_requirements" in complete, "Complete metadata should have channel requirements"
        assert "quality_control" in complete, "Complete metadata should have quality control info"
        
        # Minimal metadata should have only basic fields
        with open(os.path.join(sample_dir, "minimal_metadata.json"), 'r') as f:
            minimal = json.load(f)
        
        assert len(minimal.keys()) < len(complete.keys()), "Minimal metadata should have fewer fields"
        assert "component_id" in minimal, "Minimal metadata should have component_id"
        assert "component_name" in minimal, "Minimal metadata should have component_name"
        
        # Problematic metadata should have issues
        with open(os.path.join(sample_dir, "problematic_metadata.json"), 'r') as f:
            problematic = json.load(f)
        
        # Check for problematic values
        usage_rights = problematic.get("usage_rights", {})
        assert usage_rights.get("license_type") == "unknown", "Problematic metadata should have unknown license"
        
        print("✅ All sample metadata files represent their intended compliance scenarios")


if __name__ == "__main__":
    # Run the sample data integration tests
    pytest.main([__file__, "-v", "-s"])
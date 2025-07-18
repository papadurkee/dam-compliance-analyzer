#!/usr/bin/env python3
"""
Test script to verify EXIF metadata extraction and auto-population functionality.
"""

import json
from PIL import Image
from utils.image_processing import extract_embedded_metadata
from utils.metadata_handler import get_default_metadata_structure

def test_exif_extraction():
    """Test EXIF extraction with sample images."""
    
    print("🔧 Testing EXIF Metadata Extraction")
    print("=" * 50)
    
    # Test with sample images in the sample_data directory
    sample_images = [
        "sample_data/compliant_high_quality.jpg",
        "sample_data/compliant_standard.jpg", 
        "sample_data/non_compliant_low_res.jpg"
    ]
    
    for image_path in sample_images:
        try:
            print(f"\n📸 Testing: {image_path}")
            
            # Open image file
            with open(image_path, 'rb') as f:
                # Create a mock uploaded file object
                class MockUploadedFile:
                    def __init__(self, file_obj, name):
                        self.file_obj = file_obj
                        self.name = name
                    
                    def read(self):
                        return self.file_obj.read()
                    
                    def seek(self, pos):
                        return self.file_obj.seek(pos)
                
                mock_file = MockUploadedFile(f, image_path.split('/')[-1])
                
                # Extract metadata
                embedded_metadata = extract_embedded_metadata(mock_file)
                
                print(f"✅ EXIF detected: {embedded_metadata.get('has_exif', False)}")
                
                # Show basic info regardless of EXIF
                basic_info = embedded_metadata.get('basic_info', {})
                if basic_info:
                    print(f"  • Format: {basic_info.get('format', 'Unknown')}")
                    print(f"  • Dimensions: {basic_info.get('width', 'Unknown')}x{basic_info.get('height', 'Unknown')}")
                
                if embedded_metadata.get('has_exif'):
                    print("📋 EXIF Data Found:")
                    
                    # Show DAM-relevant data
                    dam_data = embedded_metadata.get('dam_relevant', {})
                    if dam_data:
                        print("  📝 DAM-Relevant Metadata:")
                        for key, value in dam_data.items():
                            print(f"    - {key}: {value}")
                    
                    # Test auto-population
                    print("\n🔄 Testing Auto-Population:")
                    auto_metadata = create_metadata_from_exif_test(image_path.split('/')[-1], embedded_metadata)
                    print("✅ Auto-populated metadata structure created")
                    print(f"📏 JSON length: {len(json.dumps(auto_metadata, indent=2))} characters")
                    
                    # Show sample of auto-populated data
                    print("\n📋 Sample Auto-Populated Fields:")
                    print(f"  • Component ID: {auto_metadata.get('component_id', 'N/A')}")
                    print(f"  • Component Name: {auto_metadata.get('component_name', 'N/A')}")
                    print(f"  • Description: {auto_metadata.get('description', 'N/A')}")
                    
                    if 'additional_metadata' in auto_metadata:
                        print("  • Additional Metadata:")
                        for key, value in auto_metadata['additional_metadata'].items():
                            print(f"    - {key}: {value}")
                
                else:
                    print("ℹ️ No EXIF metadata found")
                    # Still test basic auto-population functionality
                    print("\n🔄 Testing Basic Auto-Population (without EXIF):")
                    auto_metadata = create_metadata_from_exif_test(image_path.split('/')[-1], embedded_metadata)
                    print("✅ Basic metadata structure created")
                    print(f"  • Component ID: {auto_metadata.get('component_id', 'N/A')}")
                    print(f"  • Component Name: {auto_metadata.get('component_name', 'N/A')}")
                    print(f"  • Resolution: {auto_metadata['file_specifications'].get('resolution', 'N/A')}")
                    print(f"  • Format: {auto_metadata['file_specifications'].get('format', 'N/A')}")
                    
        except Exception as e:
            print(f"❌ Error processing {image_path}: {str(e)}")
    
    # Test with simulated EXIF data
    print(f"\n📸 Testing: Simulated EXIF Data")
    test_simulated_exif()
    
    print("\n" + "=" * 50)
    print("✅ EXIF extraction test completed!")


def test_simulated_exif():
    """Test with simulated EXIF data to show full functionality."""
    
    # Create simulated embedded metadata with EXIF
    simulated_metadata = {
        "basic_info": {
            "format": "JPEG",
            "width": 2048,
            "height": 1536,
            "mode": "RGB"
        },
        "exif_data": {
            "Make": "Canon",
            "Model": "EOS R5",
            "Artist": "John Photographer",
            "Copyright": "© 2024 John Photographer",
            "DateTime": "2024:01:15 14:30:22",
            "DateTimeOriginal": "2024:01:15 14:30:22",
            "ISO": 400,
            "FNumber": 2.8,
            "ExposureTime": "1/125",
            "ColorSpace": "sRGB"
        },
        "has_exif": True,
        "dam_relevant": {
            "camera_make": "Canon",
            "camera_model": "EOS R5", 
            "photographer": "John Photographer",
            "copyright": "© 2024 John Photographer",
            "shoot_date": "2024-01-15T14:30:22Z",
            "iso_speed": 400,
            "aperture": 2.8,
            "exposure_time": "1/125",
            "color_space": "sRGB"
        }
    }
    
    print("✅ EXIF detected: True (simulated)")
    print("📋 Simulated EXIF Data:")
    
    # Show DAM-relevant data
    dam_data = simulated_metadata.get('dam_relevant', {})
    if dam_data:
        print("  📝 DAM-Relevant Metadata:")
        for key, value in dam_data.items():
            print(f"    - {key}: {value}")
    
    # Test auto-population
    print("\n🔄 Testing Auto-Population with Simulated Data:")
    auto_metadata = create_metadata_from_exif_test("test_image.jpg", simulated_metadata)
    print("✅ Auto-populated metadata structure created")
    
    # Show the full JSON structure
    print("\n📋 Complete Auto-Populated JSON:")
    print(json.dumps(auto_metadata, indent=2))
    
    print(f"\n📏 JSON length: {len(json.dumps(auto_metadata, indent=2))} characters")


def create_metadata_from_exif_test(filename, embedded_metadata):
    """
    Test version of create_metadata_from_exif function.
    """
    # Start with default structure
    metadata = get_default_metadata_structure()
    
    # Extract component ID from filename (remove extension)
    component_id = filename.rsplit('.', 1)[0].upper()
    metadata['component_id'] = component_id
    metadata['component_name'] = filename
    
    # Add basic file information
    basic_info = embedded_metadata.get('basic_info', {})
    if basic_info:
        metadata['file_specifications']['format'] = basic_info.get('format', '')
        if 'width' in basic_info and 'height' in basic_info:
            metadata['file_specifications']['resolution'] = f"{basic_info['width']}x{basic_info['height']}"
    
    # Add DAM-relevant metadata if available
    if embedded_metadata.get('has_exif') and 'dam_relevant' in embedded_metadata:
        dam_data = embedded_metadata['dam_relevant']
        
        # Add additional metadata fields section for EXIF data
        if 'photographer' in dam_data or 'copyright' in dam_data or 'shoot_date' in dam_data:
            metadata['additional_metadata'] = {}
            
            if 'photographer' in dam_data:
                metadata['additional_metadata']['photographer'] = dam_data['photographer']
            
            if 'copyright' in dam_data:
                metadata['additional_metadata']['copyright'] = dam_data['copyright']
            
            if 'shoot_date' in dam_data:
                metadata['additional_metadata']['creation_date'] = dam_data['shoot_date']
        
        # Add camera information to description
        camera_info = []
        if 'camera_make' in dam_data:
            camera_info.append(dam_data['camera_make'])
        if 'camera_model' in dam_data:
            camera_info.append(dam_data['camera_model'])
        
        if camera_info:
            camera_desc = f"Captured with {' '.join(camera_info)}"
            
            # Add technical settings to description
            tech_settings = []
            if 'iso_speed' in dam_data:
                tech_settings.append(f"ISO {dam_data['iso_speed']}")
            if 'aperture' in dam_data:
                tech_settings.append(f"f/{dam_data['aperture']}")
            if 'exposure_time' in dam_data:
                tech_settings.append(f"{dam_data['exposure_time']}s")
            
            if tech_settings:
                camera_desc += f" ({', '.join(tech_settings)})"
            
            metadata['description'] = camera_desc
        
        # Add color space information if available
        if 'color_space' in dam_data:
            metadata['file_specifications']['color_profile'] = str(dam_data['color_space'])
    
    # Add a note about EXIF auto-population
    if not metadata.get('description'):
        metadata['description'] = "Metadata auto-populated from EXIF data"
    else:
        metadata['description'] += " - Auto-populated from EXIF data"
    
    return metadata


if __name__ == "__main__":
    test_exif_extraction()
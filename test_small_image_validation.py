#!/usr/bin/env python3
"""
Test script to verify that small images (25x25 pixels) are now accepted.
"""

import sys
import io
from PIL import Image

# Add the current directory to the path so we can import our modules
sys.path.append('.')

from utils.validation_errors import ImageValidationError, ValidationResult
from utils.error_handler import ErrorContext

def test_small_image_validation():
    """Test that images as small as 25x25 pixels are now accepted."""
    
    print("🔧 Testing Small Image Validation (25x25 minimum)")
    print("=" * 60)
    
    # Test cases with different image sizes
    test_cases = [
        {"size": (24, 24), "should_pass": False, "description": "Below minimum (24x24)"},
        {"size": (25, 25), "should_pass": True, "description": "Exactly minimum (25x25)"},
        {"size": (30, 20), "should_pass": False, "description": "Width OK, height too small (30x20)"},
        {"size": (20, 30), "should_pass": False, "description": "Height OK, width too small (20x30)"},
        {"size": (50, 50), "should_pass": True, "description": "Above minimum (50x50)"},
        {"size": (100, 100), "should_pass": True, "description": "Old minimum (100x100)"},
        {"size": (25, 100), "should_pass": True, "description": "Minimum width, tall height (25x100)"},
        {"size": (100, 25), "should_pass": True, "description": "Wide width, minimum height (100x25)"}
    ]
    
    print("Testing various image dimensions:")
    print()
    
    for i, test_case in enumerate(test_cases, 1):
        width, height = test_case["size"]
        should_pass = test_case["should_pass"]
        description = test_case["description"]
        
        print(f"{i}. {description}")
        print(f"   Size: {width}x{height} pixels")
        
        # Create test image
        img = Image.new('RGB', (width, height), color='red')
        
        # Convert to bytes and create mock file
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        class MockFile:
            def __init__(self, bytes_io, filename):
                self.bytes_io = bytes_io
                self.name = filename
                self.size = len(bytes_io.getvalue())
            
            def read(self):
                return self.bytes_io.read()
            
            def seek(self, pos):
                return self.bytes_io.seek(pos)
        
        mock_file = MockFile(img_bytes, f"test_{width}x{height}.jpg")
        
        # Test validation
        context = ErrorContext(operation="test", step="validation", component="size_test")
        result = ImageValidationError.validate_image_content(mock_file, context)
        
        # Check result
        if should_pass:
            if result.is_valid:
                print(f"   Result: ✅ PASSED (as expected)")
            else:
                print(f"   Result: ❌ FAILED (should have passed)")
                print(f"   Error: {result.error_details.user_message}")
                return False
        else:
            if not result.is_valid:
                print(f"   Result: ✅ REJECTED (as expected)")
                print(f"   Reason: {result.error_details.user_message}")
            else:
                print(f"   Result: ❌ PASSED (should have been rejected)")
                return False
        
        print()
    
    return True


def test_minimum_size_constants():
    """Test that the minimum size constants are correctly set."""
    
    print("🔧 Testing Minimum Size Constants")
    print("=" * 60)
    
    print(f"MIN_WIDTH: {ImageValidationError.MIN_WIDTH}")
    print(f"MIN_HEIGHT: {ImageValidationError.MIN_HEIGHT}")
    print(f"MAX_WIDTH: {ImageValidationError.MAX_WIDTH}")
    print(f"MAX_HEIGHT: {ImageValidationError.MAX_HEIGHT}")
    
    # Verify the constants are set correctly
    assert ImageValidationError.MIN_WIDTH == 25, f"Expected MIN_WIDTH=25, got {ImageValidationError.MIN_WIDTH}"
    assert ImageValidationError.MIN_HEIGHT == 25, f"Expected MIN_HEIGHT=25, got {ImageValidationError.MIN_HEIGHT}"
    
    print("\n✅ Constants are correctly set to 25x25 minimum")
    return True


def test_user_scenario():
    """Test the specific user scenario - small logo/icon upload."""
    
    print("\n🔧 Testing User Scenario: Small Logo Upload")
    print("=" * 60)
    
    # Create a small logo-like image (similar to what user might have)
    logo_sizes = [
        (32, 32, "Small icon"),
        (64, 64, "Medium icon"), 
        (25, 25, "Minimum size logo"),
        (50, 25, "Wide logo"),
        (25, 50, "Tall logo")
    ]
    
    for width, height, description in logo_sizes:
        print(f"\n📋 Testing {description} ({width}x{height}):")
        
        # Create PNG logo with transparency (typical for logos)
        img = Image.new('RGBA', (width, height), color=(0, 100, 200, 255))
        
        # Add some simple "logo" content
        for x in range(width):
            for y in range(height):
                if (x + y) % 10 == 0:  # Simple pattern
                    img.putpixel((x, y), (255, 255, 255, 255))
        
        # Convert to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        class MockFile:
            def __init__(self, bytes_io, filename):
                self.bytes_io = bytes_io
                self.name = filename
                self.size = len(bytes_io.getvalue())
            
            def read(self):
                return self.bytes_io.read()
            
            def seek(self, pos):
                return self.bytes_io.seek(pos)
        
        mock_file = MockFile(img_bytes, f"logo_{width}x{height}.png")
        
        # Test complete validation pipeline
        context = ErrorContext(operation="logo_upload", step="validation", component="user_test")
        
        # Test format validation
        format_result = ImageValidationError.validate_file_format(mock_file, context)
        print(f"  • Format validation: {'✅ PASSED' if format_result.is_valid else '❌ FAILED'}")
        
        # Test size validation
        size_result = ImageValidationError.validate_file_size(mock_file, context)
        print(f"  • Size validation: {'✅ PASSED' if size_result.is_valid else '❌ FAILED'}")
        
        # Test content validation (dimensions)
        content_result = ImageValidationError.validate_image_content(mock_file, context)
        print(f"  • Content validation: {'✅ PASSED' if content_result.is_valid else '❌ FAILED'}")
        
        if not content_result.is_valid:
            print(f"    Error: {content_result.error_details.user_message}")
        
        # Overall result
        overall_valid = format_result.is_valid and size_result.is_valid and content_result.is_valid
        print(f"  • Overall: {'✅ ACCEPTED' if overall_valid else '❌ REJECTED'}")
        
        if not overall_valid:
            return False
    
    print(f"\n✅ All small logo scenarios passed!")
    return True


def main():
    """Run all small image validation tests."""
    
    print("🚀 Testing Small Image Validation (Updated to 25x25 minimum)")
    print("=" * 70)
    
    try:
        # Run all tests
        if not test_minimum_size_constants():
            return False
        
        if not test_small_image_validation():
            return False
        
        if not test_user_scenario():
            return False
        
        print("\n" + "=" * 70)
        print("✅ All small image validation tests passed!")
        
        print("\n🎯 Summary of Changes:")
        print("  • Minimum image size reduced from 100x100 to 25x25 pixels")
        print("  • Small logos and icons now accepted")
        print("  • Validation works for both square and rectangular small images")
        print("  • PNG logos with transparency supported")
        print("  • User can now upload images as small as 25x25 pixels")
        
        print("\n📱 User Experience:")
        print("  • Small logos (32x32, 64x64, etc.) now upload successfully")
        print("  • Icons and favicons accepted")
        print("  • Minimum size error threshold lowered significantly")
        print("  • Better support for UI elements and small graphics")
        
        print("\n🎉 Small image support successfully implemented!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Small image validation test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
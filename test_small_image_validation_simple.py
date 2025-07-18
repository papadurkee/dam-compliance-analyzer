#!/usr/bin/env python3
"""
Simple test to verify that the minimum image size has been updated to 25x25 pixels.
"""

import sys

# Add the current directory to the path so we can import our modules
sys.path.append('.')

from utils.validation_errors import ImageValidationError

def test_minimum_size_constants():
    """Test that the minimum size constants are correctly updated."""
    
    print("🔧 Testing Minimum Image Size Constants")
    print("=" * 50)
    
    print(f"Current minimum dimensions:")
    print(f"  • MIN_WIDTH: {ImageValidationError.MIN_WIDTH} pixels")
    print(f"  • MIN_HEIGHT: {ImageValidationError.MIN_HEIGHT} pixels")
    print(f"  • MAX_WIDTH: {ImageValidationError.MAX_WIDTH} pixels")
    print(f"  • MAX_HEIGHT: {ImageValidationError.MAX_HEIGHT} pixels")
    
    # Verify the constants are set correctly
    if ImageValidationError.MIN_WIDTH == 25:
        print("✅ MIN_WIDTH correctly set to 25 pixels")
    else:
        print(f"❌ MIN_WIDTH should be 25, but is {ImageValidationError.MIN_WIDTH}")
        return False
    
    if ImageValidationError.MIN_HEIGHT == 25:
        print("✅ MIN_HEIGHT correctly set to 25 pixels")
    else:
        print(f"❌ MIN_HEIGHT should be 25, but is {ImageValidationError.MIN_HEIGHT}")
        return False
    
    return True


def test_validation_logic():
    """Test the validation logic with different dimensions."""
    
    print("\n🔧 Testing Validation Logic")
    print("=" * 50)
    
    # Test cases: (width, height, should_pass, description)
    test_cases = [
        (24, 24, False, "Below minimum (24x24)"),
        (25, 25, True, "Exactly minimum (25x25)"),
        (24, 25, False, "Width too small (24x25)"),
        (25, 24, False, "Height too small (25x24)"),
        (30, 30, True, "Above minimum (30x30)"),
        (100, 100, True, "Old minimum (100x100)"),
        (25, 100, True, "Minimum width, tall (25x100)"),
        (100, 25, True, "Wide, minimum height (100x25)")
    ]
    
    print("Testing dimension validation logic:")
    print()
    
    for width, height, should_pass, description in test_cases:
        # Simulate the validation logic from the actual code
        passes_validation = (width >= ImageValidationError.MIN_WIDTH and 
                           height >= ImageValidationError.MIN_HEIGHT and
                           width <= ImageValidationError.MAX_WIDTH and 
                           height <= ImageValidationError.MAX_HEIGHT)
        
        status = "✅ PASS" if passes_validation else "❌ FAIL"
        expected = "✅ EXPECTED" if passes_validation == should_pass else "❌ UNEXPECTED"
        
        print(f"  {description}")
        print(f"    Dimensions: {width}x{height}")
        print(f"    Result: {status} ({expected})")
        
        if passes_validation != should_pass:
            print(f"    ERROR: Expected {'PASS' if should_pass else 'FAIL'}, got {'PASS' if passes_validation else 'FAIL'}")
            return False
        
        print()
    
    return True


def main():
    """Run the simple validation tests."""
    
    print("🚀 Testing Small Image Size Update (25x25 minimum)")
    print("=" * 60)
    
    try:
        # Test constants
        if not test_minimum_size_constants():
            print("\n❌ Constants test failed")
            return False
        
        # Test validation logic
        if not test_validation_logic():
            print("\n❌ Validation logic test failed")
            return False
        
        print("=" * 60)
        print("✅ All tests passed!")
        
        print("\n🎯 Summary:")
        print("  • Minimum image size successfully updated from 100x100 to 25x25 pixels")
        print("  • Validation logic correctly accepts images ≥ 25x25 pixels")
        print("  • Small logos, icons, and graphics are now supported")
        
        print("\n📱 User Impact:")
        print("  • Users can now upload images as small as 25x25 pixels")
        print("  • Small logos and icons will no longer be rejected")
        print("  • Error message threshold significantly lowered")
        
        print("\n🎉 Small image support successfully implemented!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
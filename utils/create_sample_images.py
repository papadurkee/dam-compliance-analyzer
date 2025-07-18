"""
Sample Image Generator for DAM Compliance Analyzer

This script creates sample images for testing different compliance scenarios.
"""

import os
from PIL import Image, ImageDraw, ImageFont
import json


def create_sample_image(width, height, color, text, filename):
    """
    Create a sample image with specified dimensions, color, and text.
    
    Args:
        width: Image width in pixels
        height: Image height in pixels
        color: Background color (RGB tuple or color name)
        text: Text to display on the image
        filename: Output filename
    """
    # Create image
    img = Image.new('RGB', (width, height), color)
    draw = ImageDraw.Draw(img)
    
    # Try to use a default font, fall back to basic font if not available
    try:
        # Try to use a larger font
        font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 24)
    except (OSError, IOError):
        try:
            # Try alternative system font
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
        except (OSError, IOError):
            # Fall back to default font
            font = ImageFont.load_default()
    
    # Calculate text position (centered)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    
    # Draw text
    draw.text((x, y), text, fill='white' if color != 'white' else 'black', font=font)
    
    # Add border
    draw.rectangle([0, 0, width-1, height-1], outline='gray', width=2)
    
    # Save image
    img.save(filename, 'JPEG', quality=85)
    print(f"Created sample image: {filename}")


def create_all_sample_images():
    """Create all sample images for different compliance scenarios."""
    
    # Ensure sample_data directory exists
    os.makedirs('sample_data', exist_ok=True)
    
    # 1. High-quality compliant image
    create_sample_image(
        width=3840,
        height=2160,
        color='darkblue',
        text='HIGH QUALITY\nCOMPLIANT IMAGE\n4K Resolution',
        filename='sample_data/compliant_high_quality.jpg'
    )
    
    # 2. Standard compliant image
    create_sample_image(
        width=1920,
        height=1080,
        color='darkgreen',
        text='STANDARD QUALITY\nCOMPLIANT IMAGE\nFull HD Resolution',
        filename='sample_data/compliant_standard.jpg'
    )
    
    # 3. Low resolution non-compliant image
    create_sample_image(
        width=800,
        height=600,
        color='darkred',
        text='LOW RESOLUTION\nNON-COMPLIANT\n800x600',
        filename='sample_data/non_compliant_low_res.jpg'
    )
    
    # 4. Very small non-compliant image
    create_sample_image(
        width=400,
        height=300,
        color='orange',
        text='VERY SMALL\nNON-COMPLIANT\n400x300',
        filename='sample_data/non_compliant_tiny.jpg'
    )
    
    # 5. Square format image (social media)
    create_sample_image(
        width=1080,
        height=1080,
        color='purple',
        text='SQUARE FORMAT\nSOCIAL MEDIA\n1080x1080',
        filename='sample_data/social_media_square.jpg'
    )
    
    # 6. Wide format image (banner)
    create_sample_image(
        width=1920,
        height=600,
        color='teal',
        text='WIDE BANNER FORMAT\n1920x600',
        filename='sample_data/banner_wide.jpg'
    )
    
    print("\n✅ All sample images created successfully!")
    print("\nSample images created:")
    print("- compliant_high_quality.jpg (4K, should pass all checks)")
    print("- compliant_standard.jpg (Full HD, should pass most checks)")
    print("- non_compliant_low_res.jpg (Low res, should fail resolution checks)")
    print("- non_compliant_tiny.jpg (Very small, should fail multiple checks)")
    print("- social_media_square.jpg (Square format for social media)")
    print("- banner_wide.jpg (Wide format for banners)")


def create_sample_metadata_mapping():
    """Create a mapping file that links sample images to their metadata."""
    
    mapping = {
        "compliant_high_quality.jpg": "complete_metadata.json",
        "compliant_standard.jpg": "minimal_metadata.json", 
        "non_compliant_low_res.jpg": "problematic_metadata.json",
        "non_compliant_tiny.jpg": "problematic_metadata.json",
        "social_media_square.jpg": "minimal_metadata.json",
        "banner_wide.jpg": "minimal_metadata.json"
    }
    
    with open('sample_data/image_metadata_mapping.json', 'w') as f:
        json.dump(mapping, f, indent=2)
    
    print("✅ Created image-to-metadata mapping file")


if __name__ == "__main__":
    print("Creating sample images for DAM Compliance Analyzer...")
    create_all_sample_images()
    create_sample_metadata_mapping()
    print("\n🎉 Sample data creation complete!")
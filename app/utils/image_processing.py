"""
Image processing utilities using Pillow.
"""
from PIL import Image
import io
import logging

logger = logging.getLogger(__name__)


def process_hero_image(image_data: bytes, max_width: int = 1170, max_height: int = 2532, quality: int = 85) -> bytes:
    """
    Process and optimize hero images for mobile display.

    This function:
    - Resizes images to fit within max dimensions (maintains aspect ratio)
    - Converts any format to JPEG
    - Handles transparency (RGBA → RGB)
    - Removes EXIF metadata
    - Optimizes file size with quality setting

    Args:
        image_data: Raw image bytes
        max_width: Maximum width in pixels (default: 1170 for iPhone)
        max_height: Maximum height in pixels (default: 2532 for iPhone)
        quality: JPEG quality 1-95 (default: 85)

    Returns:
        Optimized JPEG image bytes

    Raises:
        ValueError: If image_data is invalid or corrupt
    """
    try:
        # Open image from bytes
        img = Image.open(io.BytesIO(image_data))

        logger.info(f"Processing image: {img.format} {img.size} {img.mode}")

        # Calculate dimensions and size for optimization checks
        original_width, original_height = img.size
        original_size_kb = len(image_data) / 1024

        # Check if processing is actually needed
        needs_resize = (original_width > max_width or original_height > max_height)
        is_oversized = original_size_kb > 600  # Target max ~600KB
        needs_format_conversion = img.mode in ('RGBA', 'LA', 'P') or img.format != 'JPEG'

        # If image is already optimal, return unchanged
        if not needs_resize and not is_oversized and not needs_format_conversion:
            logger.info(f"Image already optimal ({original_width}x{original_height}, "
                       f"{original_size_kb:.2f}KB, {img.format}, {img.mode}), skipping processing")
            return image_data  # Return original bytes unchanged

        # Convert RGBA/LA/P to RGB (JPEG doesn't support transparency)
        if img.mode in ('RGBA', 'LA', 'P'):
            # Create white background
            rgb_img = Image.new('RGB', img.size, (255, 255, 255))

            # Paste image with alpha mask if available
            if img.mode == 'RGBA':
                rgb_img.paste(img, mask=img.split()[-1])
            elif img.mode == 'LA':
                rgb_img.paste(img, mask=img.split()[-1])
            else:  # P mode
                img = img.convert('RGBA')
                rgb_img.paste(img, mask=img.split()[-1])

            img = rgb_img
        elif img.mode != 'RGB':
            # Convert any other mode to RGB
            img = img.convert('RGB')

        # Calculate resize dimensions (maintain aspect ratio)
        # Note: original_width, original_height already calculated above
        if original_width > max_width or original_height > max_height:
            # Calculate scaling factor
            width_ratio = max_width / original_width
            height_ratio = max_height / original_height
            scale_ratio = min(width_ratio, height_ratio)

            new_width = int(original_width * scale_ratio)
            new_height = int(original_height * scale_ratio)

            # Resize with high-quality resampling
            img = img.resize((new_width, new_height), Image.LANCZOS)
            logger.info(f"Resized image from {original_width}x{original_height} to {new_width}x{new_height}")

        # Save optimized JPEG to bytes
        output = io.BytesIO()
        img.save(
            output,
            format='JPEG',
            quality=quality,
            optimize=True,
            progressive=True  # Progressive JPEGs load faster on slow connections
        )

        output_bytes = output.getvalue()
        output_size_kb = len(output_bytes) / 1024

        logger.info(f"Optimized image size: {output_size_kb:.2f} KB (quality={quality})")

        return output_bytes

    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        raise ValueError(f"Invalid or corrupt image file: {str(e)}")


def validate_image(image_data: bytes) -> dict:
    """
    Validate image data and return metadata.

    Args:
        image_data: Raw image bytes

    Returns:
        dict with keys: format, width, height, mode, size_kb

    Raises:
        ValueError: If image_data is invalid
    """
    try:
        img = Image.open(io.BytesIO(image_data))

        return {
            'format': img.format,
            'width': img.width,
            'height': img.height,
            'mode': img.mode,
            'size_kb': len(image_data) / 1024
        }

    except Exception as e:
        raise ValueError(f"Invalid image file: {str(e)}")


def detect_image_format(image_data: bytes) -> str:
    """
    Detect image format from raw bytes.

    Args:
        image_data: Raw image bytes

    Returns:
        Format string (e.g., 'JPEG', 'PNG', 'WebP', 'GIF')

    Raises:
        ValueError: If format cannot be detected
    """
    try:
        img = Image.open(io.BytesIO(image_data))
        return img.format or 'UNKNOWN'

    except Exception as e:
        raise ValueError(f"Cannot detect image format: {str(e)}")

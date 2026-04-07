"""
Image helper functions for handling large images safely
"""
from PIL import Image

def increase_image_decompression_limit():
    """
    Increases the Pillow image decompression bomb limit to avoid errors with very large images.
    Call this at the start of your application if you'll be working with large images.
    """
    # The default limit is around 178 million pixels
    # We'll increase this to handle 4K images safely (3840x2160 = 8.3 million pixels)
    # and allow for some margin by multiplying by 50
    new_limit = 3840 * 2160 * 50  # Approximately 415 million pixels
    
    # Set the new limit
    Image.MAX_IMAGE_PIXELS = new_limit
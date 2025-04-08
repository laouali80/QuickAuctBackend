import secrets
import os
from PIL import Image
import random
import string
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile


# def upload_thumbnail(instance, filename):
#     """This function upload an profile image to media/thumbnails file"""
    
#     path = f'thumbnails/{instance.username}'
#     extension = filename.split('.')[-1]

#     if extension:
#         path = path + '.' + extension

#     return path

def upload_thumbnail(instance, filename):
    """
    Generates a secure random filename for a thumbnail image
    and stores it in the thumbnails/ directory.
    """
    # Generate a random hex string
    random_hex = secrets.token_hex(8)

    # Extract the file extension
    _, extension = os.path.splitext(filename)

    # Sanitize extension (remove dot, default to .jpg if missing)
    ext = extension.lower().lstrip('.') or 'jpg'

    # Construct the secure path
    new_filename = f"{random_hex}.{ext}"
    return f"thumbnails/{new_filename}"


def generate_otp():
    """Generate a 4-digit OTP."""
    return ''.join(random.choices(string.digits, k=4))



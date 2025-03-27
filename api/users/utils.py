import secrets
import os
from PIL import Image
import random
import string

def upload_thumbnail(instance, filename):
    """This function upload an image to media/thumbnails file"""
    
    path = f'thumbnails/{instance.username}'
    extension = filename.split('.')[-1]

    if extension:
        path = path + '.' + extension

    return path


def generate_otp():
    """Generate a 4-digit OTP."""
    return ''.join(random.choices(string.digits, k=4))


# def save_picture(form_picture):
#     """ the function allows us to save a picture upload in our static/profile_pics"""

#     random_hex = secrets.token_hex(8)

#     # to get the extension of a file
#     # _ means we don't need the data store in _ == f_name
#     _, f_ext = os.path.splitext(form_picture.filename)

#     # assigning a new name with hex num to our picture
#     picture_fn = random_hex + f_ext

#     # storing the picture in profile_pics folder
#     picture_path = os.path.join(current_app.root_path, 'static/profile_pics', picture_fn)

#     # resize the picture
#     output_size = (125, 125)
#     i = Image.open(form_picture)
#     i.thumbnail(output_size)
    
#     i.save(picture_path)

#     return picture_fn
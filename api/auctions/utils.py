import random
import string
import secrets

def upload_img(instance, filename):
    """This function upload an image to media/thumbnails file"""
    print(filename.split('.'))

    random_hex = secrets.token_hex(8)


    extension = filename.split('.')[-1]
    path = f'auction_images/{random_hex}'
    if extension:
        path = path + '.' + extension

    return path
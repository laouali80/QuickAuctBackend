def upload_img(instance, filename):
    """This function upload an image to media/thumbnails file"""
    
    path = f'auction_images/{instance.username}'
    extension = filename.split('.')[-1]

    if extension:
        path = path + '.' + extension

    return path
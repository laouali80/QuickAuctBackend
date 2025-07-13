import secrets
from datetime import timedelta

from django.utils import timezone


def upload_img(instance, filename):
    """This function upload an image to media/thumbnails file"""
    # print(filename.split('.'))

    random_hex = secrets.token_hex(8)

    extension = filename.split(".")[-1]
    path = f"auction_images/{random_hex}"
    if extension:
        path = path + "." + extension

    return path


def ConvertEndingTime(endingTime):
    """
    Returns a future datetime by adding the specified duration (in [days, hours, minutes, seconds]) to the current time.

    Parameters:
        endingTime (list): Duration list containing time parts.
            - Format:
                [days, hours, minutes, seconds] (length = 4)
                [hours, minutes, seconds] (length = 3)
                [minutes, seconds] (length = 2)

    Returns:
        datetime: The future datetime
    """
    current_datetime = timezone.now()

    if not isinstance(endingTime, list) or not all(
        isinstance(x, int) for x in endingTime
    ):
        raise ValueError("endingTime must be a list of integers")

    if len(endingTime) == 4:
        days, hours, minutes, seconds = endingTime
    elif len(endingTime) == 3:
        days = 0
        hours, minutes, seconds = endingTime
    elif len(endingTime) == 2:
        days = 0
        hours = 0
        minutes, seconds = endingTime
    else:
        raise ValueError("endingTime must be a list of 2, 3, or 4 integers")

    delta = timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
    return current_datetime + delta

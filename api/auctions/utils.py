import secrets
from datetime import timedelta

import boto3
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone

bucket_name = settings.AWS_STORAGE_BUCKET_NAME
region = settings.AWS_S3_REGION_NAME
s3 = boto3.client(
    "s3",
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
)


def upload_img(file):
    pass


def upload_local(instance, filename):
    """This function upload an image to media/thumbnails file"""
    # print(filename.split('.'))

    random_hex = secrets.token_hex(8)

    extension = filename.split(".")[-1]
    path = f"auction_images/{random_hex}"
    if extension:
        path = path + "." + extension

    return path


def upload_to_s3(instance, file_path):
    # Create unique path for the file in the S3 bucket
    random_hex = secrets.token_hex(8)
    extension = file_path.split(".")[-1]
    path = f"media/auction_images/{random_hex}.{extension}"

    with open(file_path, "rb") as file_obj:
        s3.upload_fileobj(
            file_obj,
            bucket_name,
            path,  # use the generated S3 key, not just the file name
            ExtraArgs={"ContentType": file_obj.content_type},
        )

    # Get region-aware URL
    bucket_location = s3.get_bucket_location(Bucket=bucket_name)
    region_name = bucket_location["LocationConstraint"] or region

    file_url = f"https://{bucket_name}.s3.{region_name}.amazonaws.com/{path}"
    f"File uploaded succesfully: {file_url}"
    return file_url


# def get_s3_objects(bucket_name):

#     response = s3.list_objects_v2(Bucket=bucket_name)
#     if "Contents" in response:
#         return [obj["Key"] for obj in response["Contents"]]
#     return []


# def upload_file(request):
#     if request.method == "POST" and request.FILES.get("file"):
#         file = upload_to_s3(request.FILES["file"], settings.AWS_STORAGE_BUCKET_NAME)

#         messages.success(request, "File uploaded successfully.")
#         object_keys = get_s3_objects(settings.AWS_STORAGE_BUCKET_NAME)
#         s3_url = f"https://s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{settings.AWS_STORAGE_BUCKET_NAME}/"
#         images = [{"url": s3_url + key} for key in object_keys]
#         return render(request, "home.html", {"images": images})

#     object_keys = get_s3_objects(settings.AWS_STORAGE_BUCKET_NAME)
#     s3_url = f"https://s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{settings.AWS_STORAGE_BUCKET_NAME}/"
#     images = [{"url": s3_url + key} for key in object_keys]

#     return render(request, "home.html", {"images": images})


def delete_image(request):
    if request.method == "POST":
        image_key = request.POST.get("image_key")
        print(image_key)
        object_key = image_key.split(f"{bucket_name}/")[1]

        try:
            s3.delete_object(Bucket=bucket_name, Key=object_key)
            messages.success(request, "File deleted successfully.")
        except Exception as e:
            messages.error(request, f"Error deleting image: {str(e)}")

        return redirect("upload")


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

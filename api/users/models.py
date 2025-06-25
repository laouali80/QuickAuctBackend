import uuid

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
)
from django.db import models

# from django.utils.translation import gettext_lazy as _
from .custom import CustomUserManager
from .utils import generate_unique_username, upload_thumbnail

# Create your models here.


class User(AbstractBaseUser, PermissionsMixin):
    userId = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=35, null=True, blank=True)
    last_name = models.CharField(max_length=35, null=True, blank=True)
    username = models.CharField(
        max_length=35, unique=True, null=True, default=generate_unique_username
    )
    address = models.TextField(null=True, blank=True)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, null=True, blank=True)
    thumbnail = models.ImageField(
        default="assets/default.png", upload_to=upload_thumbnail, null=True, blank=True
    )
    aggrement = models.BooleanField(default=False)
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)
    latest_location = models.CharField(max_length=35, blank=True, null=True)

    # Django authentication fields
    is_active = models.BooleanField(default=True)  # Required for authentication
    is_staff = models.BooleanField(default=False)  # Required for admin access

    objects = CustomUserManager()

    USERNAME_FIELD = "username"  # Used for authentication
    # REQUIRED_FIELDS = ["email", "first_name", "last_name"]  # Fields required when using createsuperuser

    def __str__(self):
        return (
            f"{self.first_name.title()} {self.last_name.title()}"
            if self.first_name and self.last_name
            else self.email
        )

    def save(self, *args, **kwargs):
        """Ensure password is hashed before saving."""
        if self.password and not self.password.startswith("pbkdf2_sha256$"):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)


# class User(AbstractBaseUser, PermissionsMixin):
#     userId = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     first_name = models.CharField(max_length=35)
#     last_name = models.CharField(max_length=35)
#     username = models.CharField(max_length=35, unique=True)
#     email = models.EmailField(unique=True)
#     phone_number = models.CharField(max_length=15)
#     password = models.CharField(max_length=128)
#     thumbnail = models.ImageField(default='assets/default.png', upload_to=upload_thumbnail, null=True,blank=True)
#     aggrement = models.BooleanField(default=False)
#     createdAt = models.DateTimeField(auto_now_add=True)
#     updatedAt = models.DateTimeField(auto_now=True)


#     # Django authentication fields
#     is_active = models.BooleanField(default=True)  # Required for authentication
#     is_staff = models.BooleanField(default=False)  # Required for admin access

#     objects = CustomUserManager()

#     USERNAME_FIELD = "username"  # Used for authentication
#     REQUIRED_FIELDS = ["email", "first_name", "last_name"]  # Fields required when using createsuperuser


#     def __str__(self):
#         return f"{self.first_name.title()} {self.last_name.title()}"

#     def save(self, *args, **kwargs):
#         """Ensure password is hashed before saving."""
#         if self.password and not self.password.startswith('pbkdf2_sha256$'):
#             self.password = make_password(self.password)
#         super().save(*args, **kwargs)


# class otpToken(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otps')
#     otp_code = models.CharField(max_length=4, default=secrets.token_hex(3))
#     tp_created_at = models.DateTimeField(auto_now_add=True) #to automaticly set the time
#     otp_expires_at = models.DateTimeField(blank=True, null=True)

# class UserProfile(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE)
#     # picture = models.ImageField(default='', upload_to='profile_pics')

#     def __str__(self):
#         return f"Profile of {self.user.username}"

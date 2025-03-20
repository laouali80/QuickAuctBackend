from django.db import models
import uuid
from .custom import CustomUser 
from django.contrib.auth.hashers import make_password
from .utils import upload_thumbnail


# Create your models here.

class User(models.Model):
    userId = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=35)
    last_name = models.CharField(max_length=35)
    username = models.CharField(max_length=35, unique=True)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15)
    password = models.CharField(max_length=128)
    thumbnail = models.ImageField(default='assets/default.png', upload_to=upload_thumbnail, null=True,blank=True)
    aggrement = models.BooleanField(default=False)
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)

    
    def __str__(self):
        return f"{self.first_name.title()} {self.last_name.title()}"
    
    def save(self, *args, **kwargs):
        """Ensure password is hashed before saving."""
        if self.password and not self.password.startswith('pbkdf2_sha256$'):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)
    

# class UserProfile(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE)
#     # picture = models.ImageField(default='', upload_to='profile_pics')

#     def __str__(self):
#         return f"Profile of {self.user.username}"
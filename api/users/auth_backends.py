from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.hashers import check_password
from .models import User  # Import your Client model

class UserAuthBackend(ModelBackend):
    """Custom authentication backend for Client model."""

    def authenticate(self, request, email=None, password=None, **kwargs):
        """Authenticate client using email and password."""
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return None  # No client found
        
        print(check_password(password, user.password))

        if check_password(password, user.password):  # Compare hashed password
            return user
        return None

    def get_user(self, user_id):
        """Retrieve user by ID."""
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

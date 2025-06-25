from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _


class CustomUserManager(BaseUserManager):
    """ "Custom user model where email is the unique identifiers for authentication instead of usernames."""

    def create_user(self, username, email, password=None, **extra_fields):
        """Create and return a regular user."""
        if not email:
            raise ValueError(_("Email is required"))
        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)

        user = self.model(username=username, email=email, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        """Create and return a superuser."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        return self.create_user(username, email, password, **extra_fields)

    # def create_user(self, email, password, **extra_fields):
    #     """Create and save a User with the given email and password."""

    #     if not email:
    #         raise ValueError(_("The Email must be set"))
    #     email = self.normalize_email(email)
    #     user = self.model(email=email, **extra_fields)
    #     user.set_password(password)
    #     user.save(using=self._db)

    #     return user

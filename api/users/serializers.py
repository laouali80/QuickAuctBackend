# serializers.py
from api.users.models import User
from django.db import IntegrityError
from rest_framework import serializers
from rest_framework.validators import UniqueValidator


class UserSerializer(serializers.ModelSerializer):
    # userId = serializers.UUIDField(source='userId')
    userId = serializers.CharField(read_only=True)  # Convert UUID to string

    class Meta:
        model = User
        fields = [
            "userId",
            "first_name",
            "last_name",
            "username",
            "email",
            "phone_number",
            "thumbnail",
            "latest_location",
            "address",
        ]


class RegisterUserSerializer(serializers.ModelSerializer):

    email = serializers.EmailField(
        required=True,
        validators=[
            UniqueValidator(
                queryset=User.objects.all(), message="Email already in use."
            )
        ],
    )

    class Meta:
        model = User
        fields = ["email", "password", "aggrement"]
        extra_kwargs = {
            "password": {
                "write_only": True,
                "error_messages": {"blank": "must not be null."},
            },
            "aggrement": {"error_messages": {"blank": "must not be null."}},
        }

    # this function is called when we want to save the serialize user with the data(validated_data)
    def create(self, validated_data):
        # print(validated_data)
        # password = validated_data.pop('password')
        try:
            # user = User.objects.create(
            #     username=validated_data['username'].lower(),
            #     first_name=validated_data['first_name'].lower(),
            #     last_name=validated_data['last_name'].lower(),
            #     email=validated_data['email'],
            #     password=validated_data['password'],  # Automatically hashed
            # )

            user = User.objects.create(**validated_data)
            # user.set_password(password)

            user.save()

        except IntegrityError as e:
            raise serializers.ValidationError(str(e))

        return user


class UpdateUserSerializer(serializers.ModelSerializer):
    username = serializers.CharField(
        required=True,
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "phone_number", "address"]
        extra_kwargs = {
            "first_name": {
                "error_messages": {"message": "First name must not be null."}
            },
            "last_name": {"error_messages": {"message": "Last name must not be null."}},
            "username": {"error_messages": {"message": "Username must not be null."}},
            "phone_number": {
                "error_messages": {"message": "Phone number must not be null."}
            },
            "address": {"error_messages": {"message": "Address must not be null."}},
        }

    def validate_username(self, value):
        """
        Allow current user to keep their existing username.
        """
        user = self.instance  # instance is the user object being updated
        if User.objects.exclude(pk=user.pk).filter(username=value).exists():
            raise serializers.ValidationError("Username already taken.")
        return value

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

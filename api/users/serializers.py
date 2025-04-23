# serializers.py
from rest_framework import serializers
from django.db import IntegrityError
from api.users.models import User
from rest_framework.validators import UniqueValidator

class UserSerializer(serializers.ModelSerializer):
    # userId = serializers.UUIDField(source='userId')
    userId = serializers.CharField(read_only=True)  # Convert UUID to string


    class Meta:
        model = User
        fields = ['userId','first_name', 'last_name', 'username','email', 'phone_number', 'thumbnail', 'latest_location']

class RegisterUserSerializer(serializers.ModelSerializer):

    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all(), message="Email already in use.")]
    )
    username = serializers.CharField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all(), message="Username already taken.")]
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'phone_number', 'password', 'aggrement']
        extra_kwargs = {
            'password': {'write_only': True, 'error_messages': {'blank': 'must not be null.'}},
            'first_name': {'error_messages': {'blank': 'must not be null.'}},
            'last_name': {'error_messages': {'blank': 'must not be null.'}},
            'aggrement': {'error_messages': {'blank': 'must not be null.'}},
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
        

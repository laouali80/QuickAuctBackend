# serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
# from .users.models import Organisation
from rest_framework.response import Response
from rest_framework import status
from django.db import IntegrityError
from api.users.models import User
from api.auctions.models import Auction

class UserSerializer(serializers.ModelSerializer):
    # userId = serializers.UUIDField(source='userId')
    userId = serializers.CharField(read_only=True)  # Convert UUID to string


    class Meta:
        model = User
        fields = ['userId','first_name', 'last_name', 'email', 'phone_number', 'thumbnail']

class RegisterUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'password']
        extra_kwargs = {'password': {
            # Ensure that when serializing, this field will be excluded
            'write_only': True
            },
                        'first_name': {'error_messages': {'blank': 'must not be null.'}},
                        'last_name': {'error_messages': {'blank': 'must not be null.'}},
                        'username': {'error_messages': {'blank': 'must not be null.'}},
                        'email': {'error_messages': {'blank': 'must be unique and must not be null.'}},
                        'password': {'error_messages': {'blank': 'must not be null.'}},
                        }

    # this function is called when we want to save the serialize user with the data(validated_data)
    def create(self, validated_data):
        print(validated_data)
        try:
            user = User.objects.create(
                username=validated_data['username'].lower(),
                first_name=validated_data['first_name'].lower(),
                last_name=validated_data['last_name'].lower(),
                email=validated_data['email'],
                password=validated_data['password'],  # Automatically hashed
            )

            user.save()

        except IntegrityError as e:
            raise serializers.ValidationError(str(e))
        
        return user
        

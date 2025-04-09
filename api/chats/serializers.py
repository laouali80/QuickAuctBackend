# serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework.response import Response
from rest_framework import status
from django.db import IntegrityError
from api.users.models import User
from .models import Connection
from api.users.serializers import UserSerializer

class ChatsSerializer(serializers.ModelSerializer):
    friend = serializers.SerializerMethodField()
    preview = serializers.SerializerMethodField()

    class Meta:
        model = Connection
        fields = ['id','friend', 'preview', 'updated']

    def get_friend(self, obj):
        # if we are the sender/ the one who initiate the connection
        if self.context['user'] == obj.sender: 
            return UserSerializer(obj.receiver).data
        # if we are the receiver/ the one who receive the connection
        elif self.context['user'] == obj.receiver:
            return UserSerializer(obj.sender).data
        else:
            print('Error: No user found in chatSerializer')
            
    def get_preview(self, data):
        return 'Really cool preview string'
     

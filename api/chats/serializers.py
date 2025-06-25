# serializers.py
from api.users.serializers import UserSerializer
from rest_framework import serializers

from .models import Connection, Message


class ChatSerializer(serializers.ModelSerializer):
    friend = serializers.SerializerMethodField()
    preview = serializers.SerializerMethodField()
    updated = serializers.SerializerMethodField()

    class Meta:
        model = Connection
        fields = ["id", "friend", "preview", "updated"]

    def get_friend(self, obj):
        # if we are the sender/ the one who initiate the connection
        if self.context["user"] == obj.sender:
            return UserSerializer(obj.receiver).data
        # if we are the receiver/ the one who receive the connection
        elif self.context["user"] == obj.receiver:
            return UserSerializer(obj.sender).data
        else:
            print("Error: No user found in chatSerializer")

    def get_preview(self, obj):
        """Return the latest content message"""
        if not obj.latest_content:
            return "New Connection"
        latest_content = obj.latest_content

        return latest_content

    def get_updated(self, obj):
        """Return the latest updated message"""
        date = obj.latest_created or obj.updated

        return date.isoformat()


class MessageSerializer(serializers.ModelSerializer):
    is_me = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ["id", "is_me", "content", "created"]

    def get_is_me(self, obj):
        return self.context["user"] == obj.user

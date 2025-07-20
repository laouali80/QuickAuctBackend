# serializers.py

from api.auctions.serializers import AuctionSerializer
from api.users.serializers import UserSerializer
from rest_framework import serializers

from .models import Connection, Message


class ConversationSerializer(serializers.ModelSerializer):
    friend = serializers.SerializerMethodField()
    # sender = UserSerializer(read_only=True)
    # receiver = UserSerializer(read_only=True)
    last_message_content = serializers.SerializerMethodField()
    last_updated = serializers.SerializerMethodField()

    class Meta:
        model = Connection
        fields = [
            "connectionId",
            "friend",
            # "sender",
            # "receiver",
            "last_message_content",
            "last_updated",
        ]

    def get_friend(self, obj):
        # if we are the sender/ the one who initiate the connection
        if self.context["user"] == obj.sender:
            return UserSerializer(obj.receiver).data
        # if we are the receiver/ the one who receive the connection
        elif self.context["user"] == obj.receiver:
            return UserSerializer(obj.sender).data
        else:
            print("Error: No user found in chatSerializer")

    def get_last_message_content(self, obj):
        """Return the latest content message"""

        last_message = obj.most_recent_message
        if not last_message:
            return "New Connection"
        return last_message.content

    def get_last_updated(self, obj):
        """Return the latest updated message"""
        last_message = obj.most_recent_message
        return (
            last_message.created.isoformat()
            if last_message
            else obj.updated.isoformat()
        )


class MessageSerializer(serializers.ModelSerializer):
    is_me = serializers.SerializerMethodField()
    auction = AuctionSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ["id", "is_me", "content", "created", "auction"]

    def get_is_me(self, obj):
        return self.context["user"] == obj.user

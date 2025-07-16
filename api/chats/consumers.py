import base64
import json
import logging
import os
from io import BytesIO

import jwt
from api.users.models import User
from api.users.serializers import UserSerializer
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.db.models import OuterRef, Q
from django.db.models.functions import Coalesce
from PIL import Image, UnidentifiedImageError

from .models import Connection, Message
from .serializers import ConversationSerializer, MessageSerializer

logger = logging.getLogger(__name__)

MODE = settings.ENVIRONMENT


class ChatConsumer(WebsocketConsumer):
    """WebSocket consumer for handling real-time chat communication."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.username = None

    def connect(self):
        """Authenticate and establish WebSocket connection."""
        print(settings.ENVIRONMENT == "DEVELOPMENT")
        try:
            token = self._extract_token()
            if not token:
                raise ValueError("No authentication token provided")

            self.user = self._authenticate_token(token)
            if not self.user:
                raise ValueError("Invalid authentication credentials")

            self._initialize_connection()
            logger.info(f"✅ Authenticated WebSocket connection for user: {self.user}")

        except Exception as e:
            logger.error(f"🚨 WebSocket connection failed: {str(e)}")
            self.close()

    def disconnect(self, close_code):
        """Clean up on WebSocket disconnect."""
        if hasattr(self, "username") and self.username:
            self._leave_group()
            logger.info(f"User {self.username} disconnected with code: {close_code}")

    def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = self._parse_message(text_data)
            handler = self._get_message_handler(data.get("source"))
            if handler:
                handler(data)
            else:
                self._send_error("Unsupported message type")

        except json.JSONDecodeError:
            self._send_error("Invalid message format")
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            self._send_error("Internal server error")

    # ----------------------
    #  Authentication Helpers
    # ----------------------

    def _extract_token(self):
        """Extract token from query string."""
        query_string = self.scope["query_string"].decode()
        if "tokens=" in query_string:
            return query_string.split("tokens=")[-1]
        return None

    def _authenticate_token(self, token):
        """Validate JWT token and return user."""
        try:
            payload = jwt.decode(
                token,
                os.getenv("JWT_SECRET_KEY"),
                algorithms=[os.getenv("JWT_ALGORITHM")],
                options={"verify_signature": False},
            )
            return get_user_model().objects.get(pk=payload["user_id"])
        except jwt.ExpiredSignatureError:
            logger.warning("Expired authentication token")
        except jwt.DecodeError:
            logger.warning("Invalid authentication token")
        except ObjectDoesNotExist:
            logger.warning("User not found for valid token")
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
        return None

    # ----------------------
    #  Connection Management
    # ----------------------

    def _initialize_connection(self):
        """Set up user connection and groups."""
        self.scope["user"] = self.user
        self.username = self.user.username

        # Join user to their personal group
        async_to_sync(self.channel_layer.group_add)(self.username, self.channel_name)
        self.accept()

    def _leave_group(self):
        """Remove connection from user group."""
        async_to_sync(self.channel_layer.group_discard)(
            self.username, self.channel_name
        )

    # ----------------------
    #  Message Handling
    # ----------------------

    def _parse_message(self, text_data):
        """Parse and validate incoming message."""
        data = json.loads(text_data)

        # print('client receive data: ', json.dumps(data, indent=2))
        # print('client receive data: ', data)

        if not isinstance(data, dict):
            raise ValueError("Message must be a JSON object")
        return data

    def _get_message_handler(self, message_type):
        """Get appropriate handler for message type."""
        handlers = {
            "thumbnail": self._handle_thumbnail_update,
            # "FetchChatsList": self._handle_fetch_chats_list,
            "fetchConversationsList": self._handle_fetch_conversations,
            "message_send": self._handle_message_send,
            "fetchChatMessages": self._handle_fetch_chat,
            "message_typing": self._handle_message_typing,
        }
        return handlers.get(message_type)

    def _handle_thumbnail_update(self, data):
        """Update user thumbnail."""

        user = self.user

        base64_data = data.get("base64")
        filename = data.get("filename")

        if not base64_data or not filename:
            raise ValueError("Missing required thumbnail data")

        # Remove metadata header if present
        if "," in base64_data:
            base64_data = base64_data.split(",")[1]

        try:
            image_data = base64.b64decode(base64_data)
        except base64.binascii.Error as e:
            raise ValueError("Invalid base64 base64_data") from e

        # Load and resize the image using Pillow
        try:
            image = Image.open(BytesIO(image_data))
            image.thumbnail((125, 125))
        except UnidentifiedImageError:
            raise ValueError("Cannot identify image file")

        # Prepare file to be saved
        output_io = BytesIO()
        image_format = image.format or "JPEG"
        image.save(output_io, format=image_format)
        output_io.seek(0)

        resized_image_file = ContentFile(output_io.read(), name=filename)

        # Delete previous thumbnail if it's not the default
        current_thumbnail = user.thumbnail.name

        if current_thumbnail:
            if MODE == "DEVELOPMENT":
                if current_thumbnail.startswith("thumbnails/"):
                    full_path = os.path.join(settings.MEDIA_ROOT, current_thumbnail)
                    if os.path.isfile(full_path):
                        os.remove(full_path)
                    user.thumbnail.delete(save=False)

            else:  # In production, using S3
                default_url = "https://quicauct-mediafiles.s3.us-east-1.amazonaws.com/static/assets/default.png"
                current_url = user.thumbnail.url if user.thumbnail else ""

                if current_url and current_url != default_url:
                    user.thumbnail.delete(save=False)

        # Save new image
        user.thumbnail.save(filename, resized_image_file, save=True)

        # Broadcast update
        serialized = UserSerializer(user)
        self._broadcast_to_user("thumbnail", serialized.data)

    def _handle_fetch_conversations(self, data):
        """Fetches the list of conversation the user had."""
        user = self.user
        request_data = data.get("data", {})
        page = request_data.get("page", 1)
        page_size = 20

        start = (page - 1) * page_size
        end = page * page_size + 1  # Fetch one extra to check for next page

        # Latest message subquery
        latest_messages = Message.objects.filter(connection=OuterRef("pk")).order_by(
            "-created"
        )[:1]

        # Get connections for user
        # annotate allows us to add a pseudo field to our queryset.
        # Coalesce('latest_created', 'updated') allows us to arrange the chats from the latest created message to the latest updated connection
        base_qs = (
            Connection.objects.filter(Q(sender=user) | Q(receiver=user))
            .annotate(
                latest_content=latest_messages.values("content"),
                latest_created=latest_messages.values("created"),
            )
            .order_by(Coalesce("latest_created", "updated").desc())
        )
        # [page * page_size : (page + 1) * page_size]
        connections = list(base_qs[start:end])

        serialized = ConversationSerializer(
            connections, context={"user": user}, many=True
        )

        # Compute the next page
        next_page = page + 1 if base_qs.count() > (page + 1) * page_size else None

        has_next = base_qs.count() > page_size

        # print('serialized: ', serialized.data)
        self._broadcast_to_user(
            "conversationsList",
            {
                "data": serialized.data,
                "pagination": {
                    "hasNext": has_next,
                    "nextPage": next_page,
                    "loaded": page != 1,
                },
            },
        )

    def _handle_message_send(self, data):
        """Handle message send by a user to another user."""
        # print(data)
        user = self.user
        ConnectionId = data.get("connectionId")
        content = data.get("content")

        try:
            connection = Connection.objects.get(id=ConnectionId)
            # print('existing: ',connection)
        except Connection.DoesNotExist:
            print("Error: couldn't find connection")
            return

        message = Message.objects.create(
            connection=connection, user=user, content=content
        )

        # determine the recipient friend
        recipient = connection.sender
        if connection.sender == user:
            recipient = connection.receiver

        # send new message back to sender
        serialized_message = MessageSerializer(message, context={"user": user})

        serialized_friend = UserSerializer(recipient)
        data = {"message": serialized_message.data, "friend": serialized_friend.data}

        # Broadcast to sender user the message
        self._broadcast_to_user("message_send", data)

        # send new message to receiver
        serialized_message = MessageSerializer(message, context={"user": recipient})

        serialized_friend = UserSerializer(user)
        data = {"message": serialized_message.data, "friend": serialized_friend.data}

        # Broadcast to the recipient user the message
        self._broadcast_to_recipient(recipient.username, "message_send", data)

    def _handle_fetch_chat(self, data):
        """Fetchs the list of message a user had 2 users had."""

        user = self.user
        request_data = data.get("data", {})
        ConnectionId = request_data.get("connectionId")
        page = request_data.get("page")
        page_size = 30

        print("reach: ", ConnectionId)

        try:
            connection = Connection.objects.get(pk=ConnectionId)
        except Connection.DoesNotExist:
            print("Error: couldn't find connection")
            return

        start = (page - 1) * page_size
        end = page * page_size + 1  # Fetch one extra to check for next page

        # Check if the user is part of the connection
        # Safeguard against unauthorized access
        if user not in [connection.sender, connection.receiver]:
            return self._send_error("Access denied")

        # Get messages per pagination
        base_qs = Message.objects.filter(connection=connection)

        messages = list(base_qs[start:end])

        # print('messages: ', messages)
        # Serialized message
        serialized_messages = MessageSerializer(
            messages, context={"user": user}, many=True
        )
        # print(serialized_messages.data)

        # Get recipient friend
        recipient = connection.sender
        if connection.sender == user:
            recipient = connection.receiver

        # Serialize friend
        serialized_friend = UserSerializer(recipient)

        # Count the total number of messages for this connection
        has_next = base_qs.count() > page_size

        # Compute the next page
        next_page = page + 1 if base_qs.count() > (page + 1) * page_size else None

        data = {
            "connectionId": ConnectionId,
            "messages": serialized_messages.data,
            "friend": serialized_friend.data,
            "pagination": {
                "currentPage": page,
                "hasNext": has_next,
                "nextPage": next_page,
                "loaded": page != 1,
            },
        }

        # send back to the requestor
        self._broadcast_to_user("fetchChatMessages", data)

    def _handle_new_connection(self, data):
        sender = self.user
        receiver_id = data.get("receiver_id")
        content = data.get("content")

        #   # Create connection and first message for perfomance
        # with transaction.atomic():
        #     connection = Connection.objects.create(
        #         sender=sender,
        #         receiver=receiver
        #     )

        #     message = Message.objects.create(
        #         connection=connection,
        #         user=sender,
        #         content=content
        #     )

        try:
            receiver = User.objects.get(pk=receiver_id)
            try:
                new_connection = Connection.objects.create(
                    sender=sender, receiver=receiver
                )
            except Exception as e:
                logger.error(f"Error creating connection: {str(e)}")
                self._send_error("Failed to create connection")
        except User.DoesNotExist:
            logger.error(f"Receiver {receiver_id} not found")
            self._send_error("Recipient user not found")

        message = Message.objects.create(
            connection=new_connection, user=sender, content=content
        )

        # send new message back to sender
        serialized_message = MessageSerializer(message, context={"user": sender})

        serialized_friend = UserSerializer(receiver)
        data = {"message": serialized_message.data, "friend": serialized_friend.data}

        # Broadcast to sender user the message
        self._broadcast_to_user("new_connection", data)

        # send new message to receiver
        serialized_message = MessageSerializer(message, context={"user": receiver})

        serialized_friend = UserSerializer(sender)
        data = {"message": serialized_message.data, "friend": serialized_friend.data}

        # Broadcast to the recipient user the message
        self._broadcast_to_recipient(receiver.username, "new_connection", data)

    def _handle_message_typing(self, data):
        """Handle the message typing animation."""

        user = self.user
        recipient_username = data.get("username")

        data = {"username": user.username}

        self._broadcast_to_recipient(recipient_username, "message_typing", data)

    # ----------------------
    #  Response Methods
    # ----------------------

    def _broadcast_to_user(self, source, data):
        """Send data to the user's personal group."""
        async_to_sync(self.channel_layer.group_send)(
            self.username, {"type": "broadcast.message", "source": source, "data": data}
        )

    def _broadcast_to_recipient(self, recipient, source, data):
        """Send data to the user's personal group."""
        async_to_sync(self.channel_layer.group_send)(
            recipient, {"type": "broadcast.message", "source": source, "data": data}
        )

    def _send_error(self, message):
        """Send error message to client."""
        self.send(text_data=json.dumps({"type": "error", "message": message}))

    # ----------------------
    #  Group Message Handlers
    # ----------------------

    def broadcast_message(self, event):
        """Handle messages sent to the user's group."""
        try:
            self.send(
                text_data=json.dumps({"source": event["source"], "data": event["data"]})
            )
        except Exception as e:
            logger.error(f"Error broadcasting message: {str(e)}")


import json
import jwt
import os
import base64
import logging
from PIL import Image, UnidentifiedImageError
from io import BytesIO
from django.core.exceptions import ObjectDoesNotExist
from channels.generic.websocket import WebsocketConsumer
from django.contrib.auth import get_user_model
from asgiref.sync import async_to_sync
from django.core.files.base import ContentFile
from api.users.serializers import UserSerializer
from .models import Connection, Message
from api.users.models import User
from django.db.models import Q, OuterRef
from django.db.models.functions import Coalesce
from .serializers import ChatSerializer, MessageSerializer
from django.conf import settings

logger = logging.getLogger(__name__)

class ChatConsumer(WebsocketConsumer):
    """WebSocket consumer for handling real-time chat communication."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.username = None

    def connect(self):
        """Authenticate and establish WebSocket connection."""
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
        if hasattr(self, 'username') and self.username:
            self._leave_group()
            logger.info(f"User {self.username} disconnected with code: {close_code}")

    def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = self._parse_message(text_data)
            handler = self._get_message_handler(data.get('source'))
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
                options={"verify_signature": False}
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
        async_to_sync(self.channel_layer.group_add)(
            self.username, 
            self.channel_name
        )
        self.accept()

    def _leave_group(self):
        """Remove connection from user group."""
        async_to_sync(self.channel_layer.group_discard)(
            self.username, 
            self.channel_name
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
            'thumbnail': self._handle_thumbnail_update,
            'FetchChatsList': self._handle_fetch_chats_list,
            'message_send':self._handle_message_send,
            'fetchMessagesList':self._handle_fetch_messages_list,
            'message_typing': self._handle_message_typing,
        }
        return handlers.get(message_type)

    def _handle_thumbnail_update(self, data):
        """Process thumbnail update requests."""

        user = self.user
 

        if not data.get('base64') or not data.get('filename'):
            raise ValueError("Missing required thumbnail data")

        
        # image_file = ContentFile(image_data, name=data['filename'])
        # Update user thumbnail
        # self.user.thumbnail.save(data['filename'], image_file, save=True)


        base64_data = data['base64']

        # Remove metadata header if present
        if ',' in base64_data:
            base64_data = base64_data.split(',')[1]

        try:
            image_data = base64.b64decode(base64_data)
        except base64.binascii.Error as e:
            raise ValueError("Invalid base64 data") from e

        try:
            image = Image.open(BytesIO(image_data))
            image.thumbnail((125, 125))  # Resize to thumbnail
        except UnidentifiedImageError:
            raise ValueError("Cannot identify image file")

        # Save image to memory
        output_io = BytesIO()
        image_format = image.format or 'JPEG'  # Fallback in case format is None
        image.save(output_io, format=image_format)
        output_io.seek(0)

        # Create a ContentFile from the resized image
        resized_image_file = ContentFile(output_io.read(), name=data['filename'])

        # Check if current thumbnail is not the default
        current_thumbnail = user.thumbnail.name

        
        # Delete current thumbnail only if it's a custom uploaded one
        if current_thumbnail and current_thumbnail.startswith("thumbnails/"):
            
            full_path = os.path.join(settings.MEDIA_ROOT, current_thumbnail)
            if os.path.isfile(full_path):
                os.remove(full_path)
            user.thumbnail.delete(save=False)

       
        # Save the resized image
        user.thumbnail.save(data['filename'], resized_image_file, save=True)

       
        # Broadcast update
        serialized = UserSerializer(user)

        self._broadcast_to_user('thumbnail', serialized.data)


    def _handle_fetch_chats_list(self, data):
        """Fetches the list of chats the user had."""
        user = self.user

        # Latest message subquery
        latest_messages = Message.objects.filter(
            connection=OuterRef('pk')
        ).order_by('-created')[:1]
        
        # Get connections for user
        # annotate allows us to add a pseudo field to our queryset.
        # Coalesce('latest_created', 'updated') allows us to arrange the chats from the latest created message to the latest updated connection
        connections = Connection.objects.filter(
            Q(sender=user) | Q(receiver=user)
        )\
        .annotate(
            latest_content = latest_messages.values('content'),
            latest_created = latest_messages.values('created')
        )\
        .order_by(
            Coalesce('latest_created', 'updated').desc()
        )
        

        serialized = ChatSerializer(connections, context={'user': user} ,many=True)
        # print('serialized: ', serialized.data)
        self._broadcast_to_user('chatsList', serialized.data)


    def _handle_message_send(self, data):
        """Handle message send by a user to another user."""
        # print(data)
        user = self.user
        ConnectionId = data.get('connectionId')
        content = data.get('content')

        try:
            connection = Connection.objects.get(id=ConnectionId)
            # print('existing: ',connection)
        except Connection.DoesNotExist:
            print("Error: couldn't find connection")
            return 
        
        
        message = Message.objects.create(
            connection=connection,
            user=user,
            content=content
        )

        # determine the recipient friend
        recipient = connection.sender
        if connection.sender == user:
            recipient = connection.receiver


        # send new message back to sender 
        serialized_message = MessageSerializer(
            message,
            context={'user': user}
        )

        serialized_friend = UserSerializer(recipient)
        data = {
            'message': serialized_message.data,
            'friend': serialized_friend.data
        }

        # Broadcast to sender user the message
        self._broadcast_to_user('message_send', data)


        

        # send new message to receiver 
        serialized_message = MessageSerializer(
            message,
            context={'user': recipient}
        )

        serialized_friend = UserSerializer(user)
        data = {
            'message': serialized_message.data,
            'friend': serialized_friend.data
        }

        # Broadcast to the recipient user the message
        self._broadcast_to_recipient(recipient.username, 'message_send', data)


    def _handle_fetch_messages_list(self, data):
        """Fetchs the list of message a user had 2 users had."""

        user = self.user
        ConnectionId = data.get('connectionId')
        page = data.get('page')
        page_size = 6
        

        
        try:
            connection = Connection.objects.get(id=ConnectionId)
        except Connection.DoesNotExist:
            print("Error: couldn't find connection")
            return 
       
        # Get messages per pagination
        messages = Message.objects.filter(
            connection=connection
        )[page * page_size:(page + 1) * page_size]

        # [page * page_size:(page + 1) * page_size]
        
        
        # print('messages: ', messages)
        # Serialized message
        serialized_messages = MessageSerializer(
            messages,
            context={'user': user},
            many=True
        )
        # print(serialized_messages.data)

        # Get recipient friend
        recipient = connection.sender
        if connection.sender == user:
            recipient = connection.receiver

        
        # Serialize friend
        serialized_friend = UserSerializer(recipient)

        # Count the total number of messages for this connection
        total_messages = Message.objects.filter(
            connection=connection
        ).count()

        # Compute the next page
        next_page = page + 1 if total_messages > (page + 1) * page_size else None

        # print('Pages:', page, next_page)
        data = {
            'messages': serialized_messages.data,
            'next': next_page,
            'friend': serialized_friend.data
        }

        # send back to the requestor
        self._broadcast_to_user('messagesList', data)


    def _handle_new_connection(self, data):
        sender = self.user
        receiver_id = data.get('receiver_id')
        content = data.get('content')

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
                    sender=sender,
                    receiver=receiver
                )
            except Exception as e:
                logger.error(f"Error creating connection: {str(e)}")
                self._send_error("Failed to create connection")
        except User.DoesNotExist:
            logger.error(f"Receiver {receiver_id} not found")
            self._send_error("Recipient user not found") 

        message = Message.objects.create(
            connection=new_connection,
            user=sender,
            content=content
        )


        # send new message back to sender 
        serialized_message = MessageSerializer(
            message,
            context={'user': sender}
        )

        serialized_friend = UserSerializer(receiver)
        data = {
            'message': serialized_message.data,
            'friend': serialized_friend.data
        }

        # Broadcast to sender user the message
        self._broadcast_to_user('new_connection', data)


        

        # send new message to receiver 
        serialized_message = MessageSerializer(
            message,
            context={'user': receiver}
        )

        serialized_friend = UserSerializer(sender)
        data = {
            'message': serialized_message.data,
            'friend': serialized_friend.data
        }

        # Broadcast to the recipient user the message
        self._broadcast_to_recipient(receiver.username, 'new_connection', data)


    def _handle_message_typing(self, data):
        """Handle the message typing animation."""

        user = self.user
        recipient_username = data.get('username')

        data = {
            'username': user.username
        }

        self._broadcast_to_recipient(recipient_username, 'message_typing', data)



    # ----------------------
    #  Response Methods
    # ----------------------

    def _broadcast_to_user(self, source, data):
        """Send data to the user's personal group."""
        async_to_sync(self.channel_layer.group_send)(
            self.username,
            {
                'type': 'broadcast.message',
                'source': source,
                'data': data
            }
        )
    
    def _broadcast_to_recipient(self, recipient, source, data):
        """Send data to the user's personal group."""
        async_to_sync(self.channel_layer.group_send)(
            recipient,
            {
                'type': 'broadcast.message',
                'source': source,
                'data': data
            }
        )

    def _send_error(self, message):
        """Send error message to client."""
        self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))

    # ----------------------
    #  Group Message Handlers
    # ----------------------

    def broadcast_message(self, event):
        """Handle messages sent to the user's group."""
        try:
            self.send(text_data=json.dumps({
                'source': event['source'],
                'data': event['data']
            }))
        except Exception as e:
            logger.error(f"Error broadcasting message: {str(e)}")


# class ChatConsumer(WebsocketConsumer):
#     def connect(self):
#         """The first function to connect the user to websocket connection."""

#         query_string = self.scope["query_string"].decode()
#         token = query_string.split("tokens=")[-1] if "tokens=" in query_string else None

#         print(f"🔑 Received Token: {token}")  # Debugging

#         if token:
#             self.user = self.authenticate_token(token)
#             if self.user:
#                 self.scope["user"] = self.user

#                 # Save username to use as a group name for this user
#                 self.username = self.user.username

#                 # Join this user to a group with their username
#                 async_to_sync(self.channel_layer.group_add)(
#                     self.username, self.channel_name
#                 )
                
#                 # This is to accept the client connection
#                 self.accept()

#                 # this is to send a message to anyone connect 
#                 # self.send(text_data=json.dumps({
#                 #     'type':'connection_established',
#                 #     'message': 'You are now connected'
#                 # }))
                
#                 print(f"✅ Authenticated WebSocket: {self.user}")
#                 return
            
#         print("🚨 WebSocket rejected: Invalid token!")
#         self.close()
 
#     def disconnect(self, close_code):
#         """This method is call when a user disconnect from the connection"""
#         # Leave room/group
#         async_to_sync(self.channel_layer.group_discard)(
#             self.username, self.channel_name
#         )
        


#     def authenticate_token(self, token):
#         User = get_user_model()
       
#         try:
#             payload = jwt.decode(token, os.getenv("JWT_SECRET_KEY"), algorithms=[os.getenv("JWT_ALGORITHM")], options={"verify_signature": False})
#             print('chat verif: ',payload["user_id"])
#             # print(User.objects.get(pk=payload["user_id"]))
#             return User.objects.get(pk=payload["user_id"])
#         except jwt.ExpiredSignatureError:
#             print("🚨 Token expired")
#         except jwt.DecodeError:
#             print("🚨 Token invalid")
#         except User.DoesNotExist:
#             print("🚨 User not found")
#         return None
    
#     #---------------------
#     #       HANDLE REQUEST
#     #---------------------

#     def receive(self, text_data):
#         """This function is called whenever any data is sent to the server from the client."""

#         # rECEIV MESAGE FROM WEBSOCKET
#         data = json.loads(text_data)
#         data_source = data.get('source')
#         # self.send(json.dumps({"message": f"Echo: {data}"}))

#         # Pretty print python dict
#         print('receive', json.dumps(data, indent=2))


#         # Thumbnail update
#         if data_source == 'thumbnail':
#             self.receive_thumbnail(data)


#     def receive_thumbnail(self, data):

#         user = self.scope['user']

#         # convert base64 to django content file
#         image_str = data.get('base64')
#         image = ContentFile(base64.b64decode(image_str))

#         # Update thumbnail field
#         filename = data.get('filename')
#         user.thumbnail.save(filename, image, save=True)

#         # Serialize user
#         serialized = UserSerializer(user)

#         # Send back / broadcast updated to the user
#         self.send_group(self.username, 'thumbnail', serialized.data)


#     #-----------------------------------
#     #      catch/all broadcast to client
#     #------------------------------------


#     def send_group(self, group, source, data):
#         """This method broadcast data to client."""

#         response = {
#             'type': 'broadcast_group',  # this type 'broadcast_group' is always a function that this send_group method will call 
#             'source':source,
#             'data': data
#         }

#         # send to group name which is username, response contains the of information of the message
#         async_to_sync(self.channel_layer.group_send)(
#             group, response
#         )

#     def broacast_group(self, data):
#         """This function is always called based on the type of send_group method"""
#         """
#         data:
#             - type: 'broadcast_group'
#             - source: where it originated from
#             - data: what ever you want to send as a dict
#         """

#         # we pop type because it is only usefull for the sake of calling this method
#         data.pop('type')

#         """
#         return data(data that user will receive):
#             - source: where it originated from
#             - data: what ever you want to send as a ict
#         """
#         self.send(text_data=json.dumps(data))
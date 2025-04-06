
import json
import jwt
import os
import base64
import logging
from django.core.exceptions import ObjectDoesNotExist
from channels.generic.websocket import WebsocketConsumer
from django.contrib.auth import get_user_model
from asgiref.sync import async_to_sync
from django.core.files.base import ContentFile
from api.users.serializers import UserSerializer

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
        if not isinstance(data, dict):
            raise ValueError("Message must be a JSON object")
        return data

    def _get_message_handler(self, message_type):
        """Get appropriate handler for message type."""
        handlers = {
            'thumbnail': self._handle_thumbnail_update,
        }
        return handlers.get(message_type)

    def _handle_thumbnail_update(self, data):
        """Process thumbnail update requests."""
        if not data.get('base64') or not data.get('filename'):
            raise ValueError("Missing required thumbnail data")

        image_data = base64.b64decode(data['base64'])
        image_file = ContentFile(image_data, name=data['filename'])

        # Update user thumbnail
        self.user.thumbnail.save(data['filename'], image_file, save=True)
        
        # Broadcast update
        serialized = UserSerializer(self.user)
        self._broadcast_to_user('thumbnail', serialized.data)

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
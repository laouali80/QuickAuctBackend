from channels.generic.websocket import WebsocketConsumer
import json
from django.contrib.auth import get_user_model
import jwt
import base64
import os
import logging
from asgiref.sync import async_to_sync
from django.db.models import Q
from .models import Auction,AuctionImage
from .serializers import (
    AuctionSerializer, 
    AuctionCreateSerializer, 
    BidCreateSerializer, 
    BidSerializer,
    AuctionImageSerializer)
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile

from django.db import transaction


logger = logging.getLogger(__name__)

class AuctionConsumer(WebsocketConsumer):
    """WebSocket consumer for handling auction-related real-time communication."""
    
    GROUP_NAME = 'auction'  # Constant for group name

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
            # print('auction verif: ',payload["user_id"])

            return get_user_model().objects.get(pk=payload["user_id"])
        except jwt.ExpiredSignatureError:
            print("🚨 Token expired")
        except jwt.DecodeError:
            print("🚨 Token invalid")
        except ObjectDoesNotExist:
            print("🚨 User not found")
        except Exception as e:
            print(f"🚨 Authentication error: {str(e)}")
        return None

    # ----------------------
    #  Group Management
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

    def _join_group(self):
        """Add connection to auction group."""
        async_to_sync(self.channel_layer.group_add)(
            self.GROUP_NAME,
            self.channel_name
        )

    def _leave_group(self):
        """Remove connection from auction group."""
        async_to_sync(self.channel_layer.group_discard)(
            self.GROUP_NAME,
            self.channel_name
        )

    # ----------------------
    #  Message Handlers
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
            'search': self._handle_search,
            'FetchAuctionsList': self._handle_fetch_auctions_list,
            'create_auction':self._handle_create_auction,
            # 'fetchMessagesList':self._handle_fetch_messages_list,
            # 'message_typing': self._handle_message_typing,
        }
        return handlers.get(message_type)

    def _handle_search(self, data):
        """Process auction search requests."""
        query = data.get('query', '').strip()

        # print('handle search: ',query)
        if not query:
            self._send_error("Empty search query")
            return

        auctions = self._search_auctions(query)
        # print('search auctions: ',auctions)
        
        serialized = AuctionSerializer(auctions, many=True)
        # print('serialized data: ',serialized.data)
        

        self._send_search_results(serialized.data)


    def _search_auctions(self, query):
        """Perform auction search query."""

        # print('search auction: ',query)
        return Auction.objects.filter(
            Q(title__istartswith=query) |
            Q(title__icontains=query)
        ).exclude(seller=self.user)
    

    def _handle_fetch_auctions_list(self, data):
        """Fetches the list of chats the user had."""
        user = self.user

        auctions =  Auction.objects.filter(
            status='ongoing'
        ).exclude(seller=user).order_by('-created_at')
        
        
        # print('auctions: ',auctions)

        serialized = AuctionSerializer(auctions ,many=True)
        # print('serialized: ', serialized.data)
        self._broadcast_to_user('auctionsList', serialized.data)


    def _handle_create_auction(self, data):
        user = self.user
        data = data.get('data')
        image = data.pop('image', [])

        # Validate image data first before creating auction
        if not image.get('uri') or not image.get('fileName'):
            raise ValueError("Missing required thumbnail data")

        try:
            base64_data = image.get('uri')
            if ',' in base64_data:
                base64_data = base64_data.split(',')[1]
            image_data = base64.b64decode(base64_data)
        except (base64.binascii.Error, AttributeError) as e:
            raise ValueError("Invalid base64 image data") from e

        # Wrap everything in a transaction
        try:
            # Atomic operations (all succeeds or all fails)
            # Wrapped the entire operation in transaction.atomic() so if image saving fails, the auction creation is rolled back
            with transaction.atomic():
                # Create auction
                serializer = AuctionCreateSerializer(data=data, context={'user': user})
                
                if not serializer.is_valid():
                    error_msg = "Auction validation failed: " + str(serializer.errors)
                    raise ValueError(error_msg)
                
                new_auction = serializer.save()
                
                # Save auction image
                try:
                    image_file = ContentFile(image_data, name=image.get('fileName'))
                    auction_image = AuctionImage(auction=new_auction, image=image_file)
                    auction_image.save()
                except Exception as e:
                    raise ValueError(f"Failed to save auction image: {str(e)}") from e
                
                return new_auction
                
        except Exception as e:
            # Log the full error here if needed
            print(f"Error in auction creation: {str(e)}")
            raise  # Re-raise the exception after logging    
       
        
        

    # ----------------------
    #  Response Methods
    # ----------------------

    def _send_search_results(self, results):
        """Send search results back to client."""
        # print('send from server to client: ',results)
        self.send(text_data=json.dumps({
            'type': 'search_results',
            'source':'search',
            'data': results
        }))

    def _send_error(self, message):
        """Send error message to client."""
        self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))

    def _reject_connection(self, reason):
        """Reject WebSocket connection with reason."""
        print(f"🚨 WebSocket rejected: {reason}")
        self.close()

    # ----------------------
    #  Group Broadcast Methods
    # ----------------------

    def broadcast_group(self, event):
        """Handler for group broadcast messages."""
        try:
            self.send(text_data=json.dumps(event['data']))
        except Exception as e:
            print(f"Error broadcasting message: {str(e)}")

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


    def broadcast_message(self, event):
        """Handle messages sent to the user's group."""
        try:
            self.send(text_data=json.dumps({
                'source': event['source'],
                'data': event['data']
            }))
        except Exception as e:
            logger.error(f"Error broadcasting message: {str(e)}")


    def auction_creation(self, event):
        """Broadcast new auction to group."""
        self.send(text_data=json.dumps({
            'type': 'auction_created',
            'data': event['message']
        }))

     




# class AuctionConsumer(WebsocketConsumer):
#     def connect(self):
#         """The first function to connect the user to websocket connection."""

#         query_string = self.scope["query_string"].decode()
#         token = query_string.split("tokens=")[-1] if "tokens=" in query_string else None

#         print(f"🔑 Received Token: {token}")  # Debugging

#         if token:
#             self.user = self.authenticate_token(token)
#             if self.user:

#                 # create a room group name of auction
#                 self.room_group_name = 'auction'

#                 # Create a room group of auction where every connected client will receive the auctions
#                 async_to_sync(self.channel_layer.group_add)(
#                     self.room_group_name,   # this is for the group name
#                     self.channel_name       # this is to add any user to this channel
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
#             self.room_group_name, self.channel_name
#         )
        


#     def authenticate_token(self, token):
#         User = get_user_model()
       
#         try:
#             payload = jwt.decode(token, os.getenv("JWT_SECRET_KEY"), algorithms=[os.getenv("JWT_ALGORITHM")], options={"verify_signature": False})
#             print(payload["user_id"])
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
#         """This function is called when we receive data/message from client."""

#         # receive data/message from connected client
#         data = json.loads(text_data)
#         data_source = data.get('source')
     

#         # Pretty print python dict
#         # print('receive', json.dumps(auction_data, index=2))

#         # Search / filter auctions
#         if data_source == 'search':
#             self.receive_search(data)


#         # this is to broadcast the message to each connected user
#         # async_to_sync(self.channel_layer.group_send)(
#         #     self.room_group_name,
#         #     {
#         #         'type': 'auction_creation',
#         #         'message': auction_data
#         #     }
#         # )

#     def receive_search(self, data):
#         """"""
#         query = data.get('query')

#         # Get auction(s) from query search term
#         auctions = Auction.objects.filter(
#             Q(title__istartswith=query) |  # Case-insensitive starts with
#             Q(title__icontains=query)      # Case-insensitive contains
#         ).exclude(
#             seller=self.user
#         )
#         # .annotate(
#         #     pen
#         # )

#         # serialize results
#         serialized = AuctionSerializer(auctions, many=True)
#         # Send search results back to the user
#         self.send_group(self.username, 'search', serialized.data)


#     def auction_creation(self, event):
#         """This method is to broadcast a created auction to each connected user."""

#         auction = event['message']

#         self.send(text_data=json.dumps({
#             'type':'auction',
#             'message': auction
#         }))

#        #-----------------------------------
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
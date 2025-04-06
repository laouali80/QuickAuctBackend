from channels.generic.websocket import WebsocketConsumer
import json
from django.contrib.auth import get_user_model
import jwt
import os
from asgiref.sync import async_to_sync
from django.db.models import Q
from .models import Auction
from .serializers import AuctionSerializer
from django.core.exceptions import ObjectDoesNotExist

class AuctionConsumer(WebsocketConsumer):
    """WebSocket consumer for handling auction-related real-time communication."""
    
    GROUP_NAME = 'auction'  # Constant for group name

    def connect(self):
        """Authenticate and establish WebSocket connection."""
        token = self._extract_token()
        
        if not token:
            self._reject_connection("No token provided")
            return

        try:
            self.user = self._authenticate_token(token)
            if not self.user:
                self._reject_connection("Invalid token")
                return

            self._join_group()
            self.accept()
            print(f"✅ Authenticated WebSocket: {self.user}")

        except Exception as e:
            self._reject_connection(f"Connection error: {str(e)}")

    def disconnect(self, close_code):
        """Clean up on WebSocket disconnect."""
        self._leave_group()

    def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(text_data)
            source = data.get('source')
            # print(data.get('source'))
            if source == 'search':
                self._handle_search(data)
            else:
                self._send_error("Unknown message source")

        except json.JSONDecodeError:
            self._send_error("Invalid JSON format")
        except Exception as e:
            self._send_error(f"Processing error: {str(e)}")

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
            print('auction verif: ',payload["user_id"])

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
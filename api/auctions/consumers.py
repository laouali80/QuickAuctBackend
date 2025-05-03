from channels.generic.websocket import WebsocketConsumer
import json
from django.contrib.auth import get_user_model
import jwt
import base64
import os
import logging
from asgiref.sync import async_to_sync
from django.db.models import Q
from .models import Auction,AuctionImage, Bid
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
        print('reach socket')

        try:
            token = self._extract_token()
            if not token:
                raise ValueError("No authentication token provided")

            self.user = self._authenticate_token(token)
            if not self.user:
                raise ValueError("Invalid authentication credentials")

            self._initialize_connection()
            self._join_group()
            logger.info(f"✅ Authenticated WebSocket connection for user: {self.user}")
            logger.info(f"{self.username} joined auction group.")


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

         # Join common auction broadcast group
        async_to_sync(self.channel_layer.group_add)(
            self.GROUP_NAME,
            self.channel_name
        )

        # self.accept()

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
            'place_bid':self._handle_place_bid,
            'watch_auction': self._handle_watch_auction,
            'delete_auction': self._handle_delete_auction,
            'edit_auction': self._handle_edit_auction,
            'close_auction': self._handle_close_auction,
            'reopen_auction': self._handle_reopen_auction,
            'report_user': self._handle_report_user,
            'load_more': self._handle_fetch_auctions_list,
            'likesAuctions': self._handle_fetch_likes_auctions
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
        """Fetches the list of auctions for the user using over-fetching to avoid count()."""

        user = self.user
        request_data = data.get('data', {})
        page = request_data.get('page', 1)
        page_size = 5

        start = (page - 1) * page_size
        end = page * page_size + 1  # Fetch one extra to check for next page

        # Base queryset: exclude the seller's own auctions
        base_qs = Auction.objects.active().exclude(seller=user).order_by('-created_at')

        results = list(base_qs[start:end])
        has_next = len(results) > page_size

        paginated_auctions = results[:page_size]  # Trim the extra item if it exists
        serialized = AuctionSerializer(paginated_auctions, many=True)

        next_page = page + 1 if has_next else None

      
        self._broadcast_to_user('auctionsList', {
            'auctions': serialized.data,
            'nextPage': next_page,
            'loaded': page != 1,
        })

        
    def _handle_create_auction(self, data):
        user = self.user
        data = data.get('data')
        image = data.pop('image', [])

        # print('reach', data)

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
                
                # print('create serializer: ',AuctionSerializer(new_auction,many=False))

                # Serialize the created auction
                broadcast_data = AuctionSerializer(new_auction,many=False).data
                
                
                # Broadcast to all connected users in the group
                self._broadcast_group('new_auction', broadcast_data)
                
                return new_auction
                
        except Exception as e:
            # Log the full error here if needed
            print(f"Error in auction creation: {str(e)}")
            raise  # Re-raise the exception after logging    
       

    def _handle_place_bid(self, data):

        user = self.user
        data = data.get('data')
        auction_id = data.get('auction_id')
        current_price = data.get('current_price')

        
        try:
            auction = Auction.objects.get(pk=auction_id)
        except Auction.DoesNotExist:
            logger.error(f"Auction {auction_id} not found")
            self._send_error(f"Auction {auction_id} not found")
            return  # stop further execution
        
        # Check if user has already an existing bid
        new_amount = current_price + auction.bid_increment
        
        # print(new_amount)

        with transaction.atomic():
            try:
                bid, created = Bid.objects.get_or_create(
                    auction=auction,
                    bidder=user,
                    defaults={'amount': new_amount}
                )
                if not created:
                    bid.amount = new_amount
                    bid.save()

                auction.current_price = new_amount
                auction.save()

            except Exception as e:
                logger.exception("Error while placing bid")
                self._send_error("Failed to place bid.")
                return
        
         # Serialize and broadcast to group so all connected users see the update
        broadcast_data = AuctionSerializer(auction).data
        # print(broadcast_data)
        self._broadcast_group('new_bid', broadcast_data)


    def _handle_watch_auction(self, data):
        user = self.user
        data = data.get('data')
        auction_id = data.get('auction_id')

        try:
            auction = Auction.objects.get(pk=auction_id)
        except Auction.DoesNotExist:
            logger.error(f"Auction {auction_id} not found")
            self._send_error(f"Auction {auction_id} not found")
            return  # stop further execution

        
        # Check if user is a watcher
        is_watcher = auction.watchers.filter(pk=user.pk).exists()
        
        if is_watcher:
            auction.watchers.remove(user)           
        else:
            auction.watchers.add(user)
            
        auction.save()

        # Serialize and broadcast to group so all connected users see the update
        broadcast_data = AuctionSerializer(auction).data
        # print(broadcast_data)
        self._broadcast_to_user('watcher', broadcast_data)


    def _handle_delete_auction(self, data):
        pass


    def _handle_fetch_likes_auctions(self, data):

        user = self.user
        request_data = data.get('data', {})
        page = request_data.get('page', 1)
        page_size = 5

        

        start = (page - 1) * page_size
        end = page * page_size + 1  # Fetch one extra to check for next page

        # Base queryset: exclude the seller's own auctions
        base_qs = Auction.objects.likes(user).order_by('-created_at')

        # print(base_qs)

        results = list(base_qs[start:end])
        has_next = len(results) > page_size

        paginated_auctions = results[:page_size]  # Trim the extra item if it exists
        # print('reach: ', page, paginated_auctions)
        serialized = AuctionSerializer(paginated_auctions, many=True)

        next_page = page + 1 if has_next else None

      
        self._broadcast_to_user('likesAuctions', {
            'auctions': serialized.data,
            'nextPage': next_page,
            'loaded': page != 1,
        })


    def _handle_edit_auction(self, data):
        pass


    def _handle_close_auction(self, data):
        pass


    def _handle_reopen_auction(self, data):
        pass


    def _handle_report_user(self, data):
        pass



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

    def _broadcast_to_user(self, source, data):
        """Send data to the user's personal group."""

        try:
            async_to_sync(self.channel_layer.group_send)(
                self.username,
                {
                    'type': 'broadcast.message',
                    'source': source,
                    'data': data
                }
            )
        except Exception as e:
            logger.error(f"Error broadcasting message: {str(e)}")
            print(f"Error broadcasting message: {str(e)}")
    
    
    def _broadcast_group(self, source, data):
        """Handler for group broadcast messages."""
        try:
            # Broadcast to all connected users in the group
            async_to_sync(self.channel_layer.group_send)(
                self.GROUP_NAME,
                {
                    'type': 'broadcast.message',
                    'source': source,
                    'data': data
                }
            )
        except Exception as e:
            logger.error(f"Error broadcasting message: {str(e)}")
            print(f"Error broadcasting message: {str(e)}")


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
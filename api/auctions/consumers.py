from channels.generic.websocket import WebsocketConsumer
import json
from django.contrib.auth import get_user_model
import jwt
import os
from asgiref.sync import async_to_sync


class AuctionConsumer(WebsocketConsumer):
    def connect(self):
        """The first function to connect the user to websocket connection."""

        query_string = self.scope["query_string"].decode()
        token = query_string.split("tokens=")[-1] if "tokens=" in query_string else None

        print(f"🔑 Received Token: {token}")  # Debugging

        if token:
            self.user = self.authenticate_token(token)
            if self.user:

                # create a room group name of auction
                self.room_group_name = 'auction'

                # Create a room group of auction where every connected client will receive the auctions
                async_to_sync(self.channel_layer.group_add)(
                    self.room_group_name,   # this is for the group name
                    self.channel_name       # this is to add any user to this channel
                )
                
                # This is to accept the client connection
                self.accept()

                # this is to send a message to anyone connect 
                # self.send(text_data=json.dumps({
                #     'type':'connection_established',
                #     'message': 'You are now connected'
                # }))
                
                print(f"✅ Authenticated WebSocket: {self.user}")
                return
            
        print("🚨 WebSocket rejected: Invalid token!")
        self.close()
 
    def disconnect(self, close_code):
        """This method is call when a user disconnect from the connection"""
        # Leave room/group
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name, self.channel_name
        )
        


    def authenticate_token(self, token):
        User = get_user_model()
       
        try:
            payload = jwt.decode(token, os.getenv("JWT_SECRET_KEY"), algorithms=[os.getenv("JWT_ALGORITHM")], options={"verify_signature": False})
            print(payload["user_id"])
            # print(User.objects.get(pk=payload["user_id"]))
            return User.objects.get(pk=payload["user_id"])
        except jwt.ExpiredSignatureError:
            print("🚨 Token expired")
        except jwt.DecodeError:
            print("🚨 Token invalid")
        except User.DoesNotExist:
            print("🚨 User not found")
        return None
    
    #---------------------
    #       HANDLE REQUEST
    #---------------------

    def receive(self, text_data):
        """This function is called when we receive data/message from client."""

        # receive data/message from connected client
        auction_data = json.loads(text_data)


        # Pretty print python dict
        # print('receive', json.dumps(auction_data, index=2))

        # this is to broadcast the message to each connected user
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'auction_creation',
                'message': auction_data
            }
        )

    def auction_creation(self, event):
        """This method is to broadcast a created auction to each connected user."""

        auction = event['message']

        self.send(text_data=json.dumps({
            'type':'auction',
            'message': auction
        }))
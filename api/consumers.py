from channels.generic.websocket import WebsocketConsumer
import json
from django.contrib.auth import get_user_model
import jwt
import os
from asgiref.sync import async_to_sync


class ChatConsumer(WebsocketConsumer):
    def connect(self):
        """The first function to connect the user to websocket connection."""

        query_string = self.scope["query_string"].decode()
        token = query_string.split("tokens=")[-1] if "tokens=" in query_string else None

        print(f"🔑 Received Token: {token}")  # Debugging

        if token:
            self.user = self.authenticate_token(token)
            if self.user:
                self.scope["user"] = self.user

                # Save username to use as a group name for this user
                self.username = self.user.username

                # Join this user to a group with their username
                async_to_sync(self.channel_layer.group_add)(
                    self.username, self.channel_name
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
            self.username, self.channel_name
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
        """This function is called whenever any data is sent to the server from the client."""

        # rECEIV MESAGE FROM WEBSOCKET
        data = json.loads(text_data)
        # self.send(json.dumps({"message": f"Echo: {data}"}))

        # Pretty print python dict
        print('receive', json.dumps(data, indent=2))

from channels.generic.websocket import WebsocketConsumer

class ChatConsumer(WebsocketConsumer):

    def connect(self):
        user = self.scope["user"]
        print(f"User: {user}, Authenticated: {user.is_authenticated}")

        if not user.is_authenticated:
            self.close()
            return

        self.accept()

    def disconnect(self, code):
        pass

#  routing.py same as urls.py for normal endpoint
# it contains all the path of the websocket connection
from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path('ws/chat/', consumers.ChatConsumer.as_asgi())
]
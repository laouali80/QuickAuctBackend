"""
ASGI config for auctionBackend project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

# Import both routing modules
from api.auctions import routing as auctions_routing
from api.chats import routing as chats_routing
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application
from django_channels_jwt_auth_middleware.auth import JWTAuthMiddlewareStack

# Combine all websocket routes
websocket_urlpatterns = (
    auctions_routing.websocket_urlpatterns + chats_routing.websocket_urlpatterns
)


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "auctionBackend.settings")

django_asgi_app = get_asgi_application()

# Ensure User model is imported

# application = ProtocolTypeRouter({
#     "http": django_asgi_app,
#     "websocket": JWTAuthMiddlewareStack(  # Remove `AllowedHostsOriginValidator`
#         URLRouter(api.routing.websocket_urlpatterns)
#     ),
# })

application = ProtocolTypeRouter(
    {  # Correct
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            JWTAuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        ),
    }
)

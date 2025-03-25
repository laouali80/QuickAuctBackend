"""
ASGI config for auctionBackend project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os
import api.routing

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django_channels_jwt_auth_middleware.auth import JWTAuthMiddlewareStack
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auctionBackend.settings')

django_asgi_app = get_asgi_application()


application = ProtocolTypeRouter({  # Correct
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        JWTAuthMiddlewareStack(
            URLRouter(api.routing.websocket_urlpatterns)
        )
    ),
})

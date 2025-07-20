from django.urls import path

from . import views

urlpatterns = [
    path("", views.welcome, name="welcome"),
    path(
        "connections/<str:sellerId>",
        views.check_connection,
        name="check_connection",
    ),
    path(
        "messages/<str:connectionId>",
        views.get_messages,
        name="get_messages",
    ),
]

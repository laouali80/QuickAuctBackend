from django.urls import path, include


urlpatterns = [   
    path('users/', include('api.users.urls')), 
    path('auctions/', include('api.auctions.urls')),
    path('chats/', include('api.chats.urls')),
]



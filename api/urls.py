from django.urls import path, include


urlpatterns = [    
    path('auctions/', include('api.auctions.urls')),
    path('users/', include('api.users.urls')),
]



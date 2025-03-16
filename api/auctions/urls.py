from django.urls import path
from . import views

urlpatterns = [
    path('', views.get_auctions, name='get_actions'),
    path('create/', views.create_auction, name='create_auction'),
    path('<str:auctId>/', views.get_auction, name='get_auction'),
    path('<str:auctId>/bid/', views.place_bid, name='place_bid'),
    path('<str:auctId>/delete/', views.delete_auction, name='delete_auction'),
    path('<str:auctId>/update/', views.update_auction, name='update_auction'),
]

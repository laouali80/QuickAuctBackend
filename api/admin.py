from django.contrib import admin
from .users.models import User
from .auctions.models import (Auction, 
                              Category, 
                              Bid, 
                              AuctionImage, 
                              AuctionTransaction,
                              AuctionReport)
from .chats.models import Connection,Message
# Register your models here.


admin.site.register(User)


# Auction models
admin.site.register(Auction)
admin.site.register(Category)
admin.site.register(Bid)
admin.site.register(AuctionImage)
admin.site.register(AuctionTransaction)
admin.site.register(AuctionReport)

# Chats models
admin.site.register(Connection)
admin.site.register(Message)

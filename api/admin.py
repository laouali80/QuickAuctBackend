from django.contrib import admin

from .auctions.models import (
    Auction,
    AuctionImage,
    AuctionReport,
    AuctionTransaction,
    Bid,
    Category,
)
from .chats.models import Connection, Message
from .users.models import User

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

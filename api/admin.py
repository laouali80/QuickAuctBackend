from django.contrib import admin
from .users.models import User
from .auctions.models import Auction

# Register your models here.


admin.site.register(User)
admin.site.register(Auction)
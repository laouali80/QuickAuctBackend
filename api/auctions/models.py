from django.db import models
import uuid
from api.users.models import User
# Create your models here.

class Auction(models.Model):
    STATUS_CHOICES = [
        ('completed', 'Completed'),
        ('ended', 'Ended'),
        ('winner', 'Winner'),
        ('hold', 'On Hold'),
        ('ongoing', 'Ongoing'),
    ]
    auctId = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    current_price = models.BigIntegerField()
    bid_increment  = models.IntegerField(default=1)
    expiration_date = models.DateTimeField()
    # status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ongoing') 
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='auctions')
    top_bidder = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='bidder')
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    

        
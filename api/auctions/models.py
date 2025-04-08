from django.db import models
import uuid
from api.users.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
from .utils import upload_img
# Create your models here.


class Category(models.Model):
    name = models.CharField(max_length=64, unique=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name.title()
    
    def get_active_auctions_count(self):
        return self.auctions.filter(status=Auction.Status.ONGOING).count()



class Auction(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        ONGOING = 'ongoing', 'Ongoing'
        ENDED = 'ended', 'Ended'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
        PAID = 'paid', 'Paid'
        SHIPPED = 'shipped', 'Shipped'
        DELIVERED = 'delivered', 'Delivered'


    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField()
    starting_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    current_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    bid_increment = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        default=1.00,
        validators=[MinValueValidator(0.01)]
    )
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.DRAFT
    )
    seller = models.ForeignKey(
        'User', 
        on_delete=models.CASCADE, 
        related_name='auctions'
    )
    winner = models.ForeignKey(
        'User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='won_auctions'
    )
    category = models.ForeignKey(
        Category, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='auctions'
    )
    watchers = models.ManyToManyField(
        'User', 
        blank=True, 
        related_name='watchlist'
    )
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField()
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    shipping_details = models.TextField(blank=True, null=True)
    payment_methods = models.JSONField(default=list)  # List of accepted payment methods
    item_condition = models.CharField(
        max_length=20,
        choices=[
            ('new', 'New'),
            ('used', 'Used'),
            ('refurbished', 'Refurbished'),
        ],
        default='used'
    )
   
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'end_time']),
            models.Index(fields=['seller']),
            models.Index(fields=['category']),
        ]


    def __str__(self):
        return f"{self.title} (${self.current_price})"
    
    @property
    def is_active(self):
        return self.status == self.Status.ONGOING and self.end_time > timezone.now()
    
    @property
    def has_ended(self):
        return self.end_time <= timezone.now()
    
    @property
    def time_remaining(self):
        if self.has_ended:
            return None
        return self.end_time - timezone.now()
    
    def get_highest_bid(self):
        return self.bids.order_by('-amount').first()



class AuctionImage(models.Model):
    auction = models.ForeignKey(
        Auction, 
        on_delete=models.CASCADE, 
        related_name='images'
    )
    image = models.ImageField(default="assets/defaultAuct.jpg",  upload_to=upload_img)
    is_primary = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['is_primary', 'uploaded_at']
    
    def __str__(self):
        return f"Image for {self.auction.title}"  



class Bid(models.Model):
    auction = models.ForeignKey(
        Auction, 
        on_delete=models.CASCADE, 
        related_name='bids'
    )
    bidder = models.ForeignKey(
        'User', 
        on_delete=models.CASCADE, 
        related_name='bids'
    )
    amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    placed_at = models.DateTimeField(auto_now_add=True)
    is_winner = models.BooleanField(default=False)

    class Meta:
        ordering = ['-placed_at']
        get_latest_by = 'placed_at'
    
    def __str__(self):
        return f"${self.amount} on {self.auction.title} by {self.bidder}"
    
    def save(self, *args, **kwargs):
        # Set is_winner=False for all bids when saving a new winning bid
        if self.is_winner:
            self.auction.bids.exclude(id=self.id).update(is_winner=False)
        super().save(*args, **kwargs)

    @property
    def is_highest_bid(self):
        return self == self.auction.get_highest_bid()
    
    @property
    def was_outbid(self):
        if not self.is_highest_bid and self.placed_at < timezone.now():
            return True
        return False


    
class AuctionTransaction(models.Model):
    auction = models.OneToOneField(
        Auction, 
        on_delete=models.CASCADE, 
        related_name='transaction'
    )
    buyer = models.ForeignKey(
        'User', 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='purchases'
    )
    seller = models.ForeignKey(
        'User', 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='sales'
    )
    final_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    payment_method = models.CharField(max_length=50)
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
            ('refunded', 'Refunded'),
        ],
        default='pending'
    )
    payment_date = models.DateTimeField(null=True, blank=True)
    shipping_status = models.CharField(
        max_length=20,
        choices=[
            ('not_shipped', 'Not Shipped'),
            ('shipped', 'Shipped'),
            ('delivered', 'Delivered'),
            ('returned', 'Returned'),
        ],
        default='not_shipped'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Transaction for {self.auction.title}"
# serializers.py
from rest_framework import serializers
from rest_framework.response import Response
from django.db import IntegrityError
from api.users.models import User
from api.auctions.models import (
    Category, 
    Auction, 
    AuctionImage, 
    Bid, 
    AuctionTransaction
)
from api.users.serializers import UserSerializer
from .utils import ConvertEndingTime
from django.utils.timezone import make_aware, is_naive
from django.utils.dateparse import parse_datetime


class CategorySerializer(serializers.ModelSerializer):
    # active_auctions_count = serializers.SerializerMethodField()
    key = serializers.IntegerField(source='id')
    value = serializers.CharField(source='name')

    class Meta:
        model = Category
        fields = ['key', 'value']
    
    def get_active_auctions_count(self, obj):
        return obj.get_active_auctions_count()

class AuctionImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = AuctionImage
        fields = [
            'id', 
            'image', 
            'image_url',
            'is_primary', 
            'uploaded_at'
        ]
    
    def get_image_url(self, obj):
        if obj.image:
            return obj.image.url
        return None
    

class BidSerializer(serializers.ModelSerializer):
    bidder = UserSerializer(read_only=True)
    is_highest_bid = serializers.SerializerMethodField()
    auction = serializers.CharField(source='auction_id')
    # was_outbid = serializers.SerializerMethodField()

    class Meta:
        model = Bid
        fields = [
            'id',
            'auction',
            'bidder',
            'amount',
            'placed_at',
            'is_winner',
            'is_highest_bid',
        ]
        read_only_fields = ['placed_at', 'is_winner']

    def get_is_highest_bid(self, obj):
        return obj.is_highest_bid
    
    # def get_was_outbid(self, obj):
    #     return obj.was_outbid


class AuctionSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)  # Convert UUID to string
    seller = UserSerializer(read_only=True)
    winner = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    images = AuctionImageSerializer(many=True, read_only=True)
    bids = BidSerializer(many=True, read_only=True)
    highest_bid = serializers.SerializerMethodField()
    time_remaining = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    has_ended = serializers.SerializerMethodField()
    watchers = serializers.PrimaryKeyRelatedField(
        many=True, 
        queryset=User.objects.all(),
        required=False
    )

    class Meta:
        model = Auction
        fields = [
            'id',
            'title',
            'description',
            'starting_price',
            'current_price',
            'bid_increment',
            'status',
            'seller',
            'winner',
            'category',
            'watchers',
            'start_time',
            'end_time',
            'created_at',
            'updated_at',
            'shipping_details',
            'payment_methods',
            'item_condition',
            'images',
            'bids',
            'highest_bid',
            'time_remaining',
            'is_active',
            'has_ended'
        ]
        read_only_fields = [
            'id',
            'current_price',
            'created_at',
            'updated_at',
            'highest_bid',
            'time_remaining',
            'is_active',
            'has_ended'
        ]


    def get_highest_bid(self, obj):
        highest_bid = obj.get_highest_bid()
        if highest_bid:
            return BidSerializer(highest_bid).data
        return None
    
    def get_time_remaining(self, obj):
        if obj.time_remaining:
            return str(obj.time_remaining)
        return None
    
    def get_is_active(self, obj):
        return obj.is_active
    
    def get_has_ended(self, obj):
        return obj.has_ended
    

class AuctionTransactionSerializer(serializers.ModelSerializer):
    auction = serializers.StringRelatedField()
    buyer = UserSerializer(read_only=True)
    seller = UserSerializer(read_only=True)
    total_amount = serializers.SerializerMethodField()

    class Meta:
        model = AuctionTransaction
        fields = [
            'id',
            'auction',
            'buyer',
            'seller',
            'final_price',
            'total_amount',
            'payment_method',
            'payment_status',
            'payment_date',
            'shipping_status',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'created_at',
            'updated_at',
            'total_amount'
        ]
    
    def get_total_amount(self, obj):
        return obj.final_price


class AuctionCreateSerializer(serializers.ModelSerializer):
    end_time = serializers.ListField(
        child=serializers.IntegerField(min_value=0),
        write_only=True
    )

    class Meta:
        model = Auction
        fields = [
            'title',
            'description',
            'starting_price',
            'bid_increment',
            'category',
            'end_time',
            'shipping_details',
            'payment_methods',
            'item_condition',
        ]
    
 
    
    def validate_end_time(self, value):
        if not isinstance(value, list) or len(value) not in [2, 3, 4]:
            raise serializers.ValidationError("Invalid end_time format")
        return ConvertEndingTime(value)

    def create(self, validated_data):
        # print('I got you: ',self.context['user'])
        validated_data['seller'] = self.context['user']
        validated_data['current_price'] = validated_data['starting_price']
        validated_data['status'] = 'ongoing'
        
        try:
            auction = Auction.objects.create(**validated_data)
            auction.save()

        except IntegrityError as e:
            raise serializers.ValidationError(str(e))
        return auction
        


class BidCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bid
        fields = ['amount']
    
    def validate_amount(self, value):
        auction = self.context['auction']
        if value < auction.current_price + auction.bid_increment:
            raise serializers.ValidationError(
                f"Bid must be at least {auction.current_price + auction.bid_increment}"
            )
        return value
    

# class AuctionSerializer(serializers.ModelSerializer):
#     auctId = serializers.CharField(read_only=True)  # Convert UUID to string
#     # seller = serializers.StringRelatedField()  # Uses User.__str__()
#     # top_bidder = serializers.StringRelatedField()  # Optional: Replace with UserSerializer if needed
#     seller = UserSerializer()
#     top_bidder = UserSerializer()

#     class Meta:
#         model = Auction
#         fields = '__all__'  # Includes all model fields



# class CreateAuctionSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Auction
#         fields = ['title','description', 'current_price','expiration_date','seller',]
#         extra_kwargs = {
#                         'title': {'error_messages': {'blank': 'Required and cannot be null.'}},
#                         }

#     def create(self, validated_data):
#         try:
#             auction = Auction.objects.create(
#                 title=validated_data['title'],
#                 decription=validated_data['description'],
#                 current_price=validated_data['current_price'],
#                 expiration_date=validated_data['expiration_date'],
#                 seller=validated_data['seller']
#             )
#             Auction.save()
#         except IntegrityError as e:
#             raise serializers.ValidationError(str(e))
        
#         return auction
    
    
# serializers.py
from rest_framework import serializers

from rest_framework.response import Response
from django.db import IntegrityError
from api.users.models import User
from api.auctions.models import Auction
from api.users.serializers import UserSerializer

class AuctionSerializer(serializers.ModelSerializer):
    auctId = serializers.CharField(read_only=True)  # Convert UUID to string
    # seller = serializers.StringRelatedField()  # Uses User.__str__()
    # top_bidder = serializers.StringRelatedField()  # Optional: Replace with UserSerializer if needed
    seller = UserSerializer()
    top_bidder = UserSerializer()

    class Meta:
        model = Auction
        fields = '__all__'  # Includes all model fields



class CreateAuctionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Auction
        fields = ['title','description', 'current_price','expiration_date','seller',]
        extra_kwargs = {
                        'title': {'error_messages': {'blank': 'Required and cannot be null.'}},
                        }

    def create(self, validated_data):
        try:
            auction = Auction.objects.create(
                title=validated_data['title'],
                decription=validated_data['description'],
                current_price=validated_data['current_price'],
                expiration_date=validated_data['expiration_date'],
                seller=validated_data['seller']
            )
            Auction.save()
        except IntegrityError as e:
            raise serializers.ValidationError(str(e))
        
        return auction
    
    
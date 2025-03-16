# serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
# from .users.models import Organisation
from rest_framework.response import Response
from rest_framework import status
from django.db import IntegrityError
from api.users.models import User
from api.auctions.models import Auction


class AuctionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Auction
        fields = [all]



class CreateAuctionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Auction
        fields = ['name', 'current_price']
        extra_kwargs = {
                        'name': {'error_messages': {'blank': 'Required and cannot be null.'}},
                        }

    def create(self, validated_data):
        try:
            auction = Auction.objects.create(
                name=validated_data['name'],
                current_price=validated_data['current_price']
            )
            Auction.save()
        except IntegrityError as e:
            raise serializers.ValidationError(str(e))
        
        return auction
    
    
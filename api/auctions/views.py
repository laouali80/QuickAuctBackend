from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Auction
from .serializers import AuctionSerializer, CreateAuctionSerializer



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_auction(request):
    """Create a new auction."""

    if request.method == 'POST':
        
        new_auct_data = {
            "name": request.data.get('name'),
            "description": request.data.get('description'),
            'seller': request.user
        }
        new_auct_serializer = CreateAuctionSerializer(data=new_auct_data)

        if new_auct_serializer.is_valid():
            auction = new_auct_serializer.save()

            return Response(auction, status=status.HTTP_201_CREATED)
            

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_auction(request, auctId):
    """Retrieve an auction"""
    auction = get_object_or_404(Auction, pk=auctId)
    serializer = AuctionSerializer(auction)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['POST', 'GET'])
@permission_classes([IsAuthenticated])
def get_auctions(request):
    """get all user auctions."""

    if request.method == 'GET':
        auctions = request.user.auctions.all()

        
        serializer = AuctionSerializer(auctions, many=True)
        response_data = {
                "auctions": serializer.data
            }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    return Response({
        "status": "Bad Request",
        "message": "Client error",
        "statusCode": 400
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def place_bid(request, auctId):
    """Place a bid on an auction"""
    auction = get_object_or_404(Auction, pk=auctId)

    if request.user == auction.seller:
        return Response({"error": "Sellers cannot bid on their own auctions"},
                        status=status.HTTP_403_FORBIDDEN)

    # The action of bidding more than the required bidding increment
    jump_bid = request.data.get('bid')

    if jump_bid is None:
            auction.current_price += auction.bid_increment
    else:
        if jump_bid > auction.current_price:
            auction.current_price = jump_bid
        else:
            return Response({"error": "Bid must be higher than the current price"},
                        status=status.HTTP_400_BAD_REQUEST)
        
    auction.top_bidder = request.user
    auction.save()

    serializer = AuctionSerializer(auction)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_auction(request, auctId):
    """Delete an auction"""
    auction = get_object_or_404(Auction, pk=auctId)
    
    if request.user != auction.seller:
        return Response({"error": "Only the seller can delete the auction"},
                        status=status.HTTP_403_FORBIDDEN)

    auction.delete()
    return Response({"message": "Auction deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_auction(request, auctId):
    """Update an auction"""

    
    auction = get_object_or_404(Auction, pk=auctId)

    if request.user != auction.seller:
        return Response({"error": "Only the seller can update the auction"},
                        status=status.HTTP_403_FORBIDDEN)

    auction.name = request.data.get('name', auction.name)
    auction.description = request.data.get('description', auction.description)
    auction.save()

    serializer = AuctionSerializer(auction)
    return Response(serializer.data, status=status.HTTP_200_OK)

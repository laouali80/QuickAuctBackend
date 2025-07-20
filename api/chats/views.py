from api.users.models import User
from django.db.models import Q
from django.shortcuts import redirect
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Connection, Message
from .serializers import ConversationSerializer, MessageSerializer

# Create your views here.


@api_view(["GET"])
@permission_classes([AllowAny])
def welcome(request):
    return redirect("register")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
# @permission_classes([AllowAny])
def check_connection(request, sellerId):
    """Check if a connection exists with the seller."""
    if request.method == "GET":
        user = request.user
        page = 1
        page_size = 30

        # print("get_connection: ", user, sellerId)

        start = (page - 1) * page_size
        end = page * page_size + 1  # Fetch one extra to check for next page

        try:
            seller = User.objects.get(pk=sellerId)
            #     # Check if a connection exists between the user and the seller
            hasConnection = Connection.objects.filter(
                Q(sender=user)
                | Q(receiver=user)
                | Q(sender=seller)
                | Q(receiver=seller)
            )

            # print("hasConnection: ", hasConnection)

            if not hasConnection.exists():
                return Response(
                    {
                        "isConnected": hasConnection.exists(),
                        "message": "No connection found with the seller",
                    },
                    status=status.HTTP_200_OK,
                )

            connection = hasConnection.first()

            #     # If a connection exists, retrieve it
            #     # Get messages for the connection
            mssg_qs = Message.objects.filter(connection=connection)

            # print("mssg_qs: ", mssg_qs)
            messages = list(mssg_qs[start:end])

            # return Response(
            #     {
            #         "status": "success",
            #         "message": "Welcome to the chat API",
            #         "statusCode": 200,
            #     },
            #     status=status.HTTP_200_OK,
            # )

            # print('messages: ', messages)
            # Serialized message
            serialized_messages = MessageSerializer(
                messages, context={"user": user}, many=True
            )

            serialized_conversation = ConversationSerializer(
                connection, context={"user": user}, many=False
            )

            return Response(
                {
                    "isConnected": hasConnection.exists(),
                    "message": "Retrieved connection and messages successfully",
                    "connection": serialized_conversation.data,
                    "messages": serialized_messages.data,
                },
                status=status.HTTP_200_OK,
            )

        except User.DoesNotExist:
            print(f"Seller {sellerId} not found")
            return Response(
                {
                    "status": "error",
                    "message": "Seller user not found",
                    "statusCode": 404,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

    # Response(
    #         {
    #             "status": "success",
    #             "message": "Profile updated",
    #             "data": {
    #                 "tokens": {
    #                     "access": str(refresh.access_token),
    #                     "refresh": str(refresh),
    #                 },
    #                 "user": user_data,
    #             },
    #             "statusCode": 200,
    #         },
    #         status=status.HTTP_200_OK,
    #     )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_messages(request, connectionId):
    """Get messages for a specific connection."""
    if request.method == "GET":
        user = request.user
        page = 1
        page_size = 30

        start = (page - 1) * page_size
        end = page * page_size + 1  # Fetch one extra to check for next page

        try:
            connection = Connection.objects.get(pk=connectionId)

            # Get messages for the connection
            mssg_qs = Message.objects.filter(connection=connection)

            messages = list(mssg_qs[start:end])

            # Serialized message
            serialized_messages = MessageSerializer(
                messages, context={"user": user}, many=True
            )

            return Response(
                {
                    "status": "success",
                    "message": "Retrieved messages successfully",
                    "messages": serialized_messages.data,
                },
                status=status.HTTP_200_OK,
            )

        except Connection.DoesNotExist:
            return Response(
                {"status": "error", "message": "Connection not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

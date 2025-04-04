from django.shortcuts import redirect
from django.contrib.auth import authenticate
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from api.users.models import User
# from .auctions.models import Auction
from .serializers import UserSerializer, RegisterUserSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status

# Create your views here.

@api_view(['GET'])
@permission_classes([AllowAny])
def welcome(request):
    return redirect('register')

@api_view(['GET','POST'])
@permission_classes([AllowAny])
def register_user(request):
    """Register a user."""
    
    if request.method == "POST":
        
        serializer = RegisterUserSerializer(data=request.data)

        if serializer.is_valid():
            
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            # access_token = str(refresh.access_token)
            user_data = UserSerializer(user).data
 
                # {
                # "status": "success",
                # "message": "Registration successful",
                # "data": {
                #     "accessToken": access_token,
                #     "user": user_data
                #     }
                # }, status=status.HTTP_201_CREATED
            
            return Response({
                    
                    "user": user_data,
                    "tokens":{
                        "access": str(refresh.access_token),
                        'refresh': str(refresh)
                    }
                }, status=status.HTTP_201_CREATED)
            
        
        resp = {
                "errors": [
                    {
                        "field": list(serializer.errors.keys())[0],
                        "message": serializer.errors[f"{list(serializer.errors.keys())[0]}"][0]
                    }
                ]
            }
        return Response(resp, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        
    else:
        return Response({
                    "status": "Method not allowed",
                    "message": "This request method is not allow.",
                    "statusCode": 400
                }, status=status.HTTP_400_BAD_REQUEST)
    
@api_view(['GET','POST'])
@permission_classes([AllowAny])
def login(request):
    """Logs in a user and returns a JWT access token."""

    if request.method == "POST":
        email = request.data.get('email')
        password = request.data.get('password')

        user = authenticate(request, email=email, password=password)
        
        
        if user is not None:
            # RefreshToken allows us to create a token for a user
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            # print(access_token)
            user_data = UserSerializer(user).data

            return Response({
                "status": "success",
                "message": "Login successful",
                "data": {
                    "accessToken": access_token,
                    "user": user_data
                }
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "status": "Bad request",
                "message": "Authentication failed",
                "statusCode": 401
            }, status=status.HTTP_401_UNAUTHORIZED)

    else:
        return Response({
                    "status": "Method not allowed",
                    "message": "This request method is not allow.",
                    "statusCode": 405
                }, status=status.HTTP_405_METHOD_NOT_ALLOWED)




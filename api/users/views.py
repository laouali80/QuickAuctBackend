from django.shortcuts import redirect
from django.contrib.auth import authenticate
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from api.users.models import User
from .serializers import UserSerializer, RegisterUserSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime, timedelta
from .utils import generate_otp
import os
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.shortcuts import render
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import redirect

# Create your views here.

@api_view(['GET'])
@permission_classes([AllowAny])
def welcome(request):
    return Response({'status':'reach'}, status=status.HTTP_201_CREATED)


@api_view(['GET','POST'])
@permission_classes([AllowAny])
def register_user(request):
    """Register a user."""
    
    if request.method == "POST":
        # print(request.data)
        serializer = RegisterUserSerializer(data=request.data)
        # print(serializer.is_valid())

        if serializer.is_valid():
            
            user = serializer.save()
            # print(user)
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
  


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """Logs in a user and returns a JWT access token."""

    if request.method == "POST":

        email = request.data.get('email')
        password = request.data.get('password')
        # print(email, password)
        
 
        user = authenticate(request, email=email, password=password)
        # print('user: ',authenticate(request, email=email, password=password))
        
        
        if user is not None:
            # RefreshToken allows us to create a token for a user
            refresh = RefreshToken.for_user(user)
            # access_token = str(refresh.access_token)
            # print(access_token)
            user_data = UserSerializer(user).data

            return Response({
                "status": "success",
                "message": "Login successful",
                "data": {
                    "tokens":{
                        "access": str(refresh.access_token),
                        'refresh': str(refresh)
                    },
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



@api_view(['POST'])
@permission_classes([AllowAny])
def refreshToken(request):
    """
    Accepts a refresh token and returns a new access token (and optionally a new refresh token if ROTATE is enabled).
    """
    
    serializer = TokenRefreshSerializer(data=request.data)
    # print(serializer.is_valid())
    try:
        serializer.is_valid(raise_exception=True)
    except TokenError as e:
        return Response({
            "status": "error",
            "message": "Token refresh failed",
            "details": e.args[0]
        }, status=status.HTTP_401_UNAUTHORIZED)

    # print('New tokens: ',serializer.validated_data)
    return Response({
        "status": "success",
        "message": "Token refreshed",
        "data": serializer.validated_data
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def send_otp(request):
    """Send a 4-digit OTP to the email of an unregistered user."""
    
    email = request.data.get('email')
    first_name = request.data.get('first_name')

    if not email:
        return Response({"message": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

    otp = generate_otp()
    minutes = 15
    valid_until = datetime.now() + timedelta(minutes=minutes)

    request.session['otp_secret_key'] = otp  # Store OTP in session
    request.session['otp_valid_date'] = str(valid_until)

    # print(f'Your OTP is: {otp}')  # Debugging purposes

    # message = f'Hi {first_name}, your OTP is: {otp}'

    # print('email: ',settings.EMAIL_HOST_USER)

    

    html_content = render_to_string('users/AccountVerification.html', {
        'first_name': first_name.title(),
        'otp': otp,
        'valid_time':minutes,
        'year': datetime.now().strftime("%Y")
    })
    text_content = strip_tags(html_content)  # Fallback text version
    try:
       

        email_msg = EmailMultiAlternatives(
            subject="QuickAuct Email Verification",
            body=text_content,
            from_email=settings.EMAIL_HOST_USER,
            to=[email]
        )
        email_msg.attach_alternative(html_content, "text/html")
        email_msg.send()

        return Response({"message": "OTP sent successfully"}, status=status.HTTP_200_OK)
    # return Response({otp}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            "message": "Failed to send OTP",
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def otp_validation(request):
    """Verify the OTP submitted by the unregistered user."""
    otp = request.data.get('otp')

    # print("otp: ",request.session.get('otp_valid_date'))

    if not otp:
        return Response({"message": "OTP is required"}, status=status.HTTP_400_BAD_REQUEST)

    otp_secret_key = request.session.get('otp_secret_key')
    otp_valid_date = request.session.get('otp_valid_date')

    if not otp_secret_key or not otp_valid_date:
        return Response({"message": "OTP not found or expired"}, status=status.HTTP_400_BAD_REQUEST)

    valid_until = datetime.fromisoformat(otp_valid_date)

    if datetime.now() > valid_until:
        del request.session['otp_secret_key']
        del request.session['otp_valid_date']

       
        return Response({"message": "OTP has expired"}, status=status.HTTP_400_BAD_REQUEST)
        
        
    if otp == otp_secret_key:
        del request.session['otp_secret_key']
        del request.session['otp_valid_date']

        return Response({"message": "Valid OTP"}, status=status.HTTP_200_OK)
    
    else:
        return Response({"message": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)
    
# @permission_classes([IsAuthenticated])
@api_view(['POST'])
@permission_classes([AllowAny])
def update_location(request):
    """Update the latest user Location."""
    location = request.data.get('location')

    # print(request.user)
    # return Response({'location':location}, status=status.HTTP_201_CREATED)

    request.user.latest_location = location

    request.user.save()
    
    # RefreshToken allows us to create a token for a user
    refresh = RefreshToken.for_user(request.user)
    user_data = UserSerializer(request.user).data
    
    return Response({
        "status": "success",
        "message": "Login successful",
        "data": {
            "tokens":{
                "access": str(refresh.access_token),
                'refresh': str(refresh)
            },
            "user": user_data
        }
    }, status=status.HTTP_200_OK)

from django.shortcuts import redirect
from django.contrib.auth import authenticate
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status

# Create your views here.

@api_view(['GET'])
@permission_classes([AllowAny])
def welcome(request):
    return redirect('register')


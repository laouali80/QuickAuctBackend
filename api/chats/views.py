from django.shortcuts import redirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

# Create your views here.


@api_view(["GET"])
@permission_classes([AllowAny])
def welcome(request):
    return redirect("register")

from django.urls import path
from . import views

app_name = "users"
urlpatterns = [
    path('', views.welcome, name='welcome'),
    path('auth/register/', views.register_user, name='register'),
    path('auth/login/', views.login, name='login'),
    path("auth/jwt/token/refresh/", views.refreshToken, name='Refresh_Token'),
    path('auth/verification/', views.send_otp, name='login'),
    path('auth/otpValidation/', views.otp_validation, name='login'),
    path('location/', views.update_location, name='location'),
    path('update/', views.updateUser, name='update User'),
]

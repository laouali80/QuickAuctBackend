from django.urls import path
from . import views

app_name = "users"
urlpatterns = [
    path('', views.welcome, name='welcome'),
    path('auth/register/', views.register_user, name='register'),
    path('auth/login/', views.login, name='login'),
    path('auth/verification/', views.send_otp, name='login'),
    path('auth/otpValidation/', views.otp_validation, name='login'),
]

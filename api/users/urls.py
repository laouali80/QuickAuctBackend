from django.urls import path
from . import views

urlpatterns = [
    path('', views.welcome, name='welcome'),
    path('auth/register/', views.register_user, name='register'),
    path('auth/login/', views.login, name='login'),
]

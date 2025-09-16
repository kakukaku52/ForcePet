from django.urls import path
from . import views

app_name = 'streaming'

urlpatterns = [
    path('', views.streaming_home, name='home'),
]
from django.urls import path
from . import views

app_name = 'rest_explorer'

urlpatterns = [
    path('', views.rest_explorer_home, name='home'),
]
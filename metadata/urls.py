from django.urls import path
from . import views

app_name = 'metadata'

urlpatterns = [
    path('', views.metadata_home, name='home'),
    # Add more URLs as needed
]
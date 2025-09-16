from django.urls import path
from . import views

app_name = 'apex'

urlpatterns = [
    path('', views.apex_home, name='home'),
]
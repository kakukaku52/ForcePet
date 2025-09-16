from django.urls import path
from . import views

app_name = 'bulk'

urlpatterns = [
    path('', views.bulk_home, name='home'),
]
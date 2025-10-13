from django.urls import path
from . import views

app_name = 'metadata'

urlpatterns = [
    path('', views.metadata_home, name='home'),
    path('detail/<str:metadata_type>/<str:identifier>/', views.metadata_detail_page, name='detail'),
]

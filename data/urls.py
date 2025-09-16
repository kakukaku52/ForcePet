from django.urls import path
from . import views

app_name = 'data'

urlpatterns = [
    path('', views.data_home, name='home'),
    path('insert/', views.insert_view, name='insert'),
    path('update/', views.update_view, name='update'),
    path('delete/', views.delete_view, name='delete'),
    path('upsert/', views.upsert_view, name='upsert'),
    path('undelete/', views.undelete_view, name='undelete'),
    path('api/sobject-fields/', views.get_sobject_fields, name='api_sobject_fields'),
]
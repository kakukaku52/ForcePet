from django.urls import path
from . import views

app_name = 'query'

urlpatterns = [
    path('', views.QueryIndexView.as_view(), name='index'),
    path('search/', views.SearchView.as_view(), name='search'),
    path('more/', views.query_more, name='query_more'),
    path('export/<int:history_id>/', views.ExportResultsView.as_view(), name='export'),
    path('saved/', views.SavedQueryView.as_view(), name='saved_queries'),
    path('saved/<int:query_id>/delete/', views.delete_saved_query, name='delete_saved_query'),
    path('saved/<int:query_id>/load/', views.load_saved_query, name='load_saved_query'),
    path('history/', views.QueryHistoryView.as_view(), name='history'),
    path('api/objects/', views.get_objects, name='get_objects'),
    path('api/fields/', views.get_object_fields, name='get_object_fields'),
    path('record/<str:object_type>/<str:record_id>/', views.record_detail, name='record_detail'),
    path('record/<str:object_type>/<str:record_id>/update/', views.update_record, name='update_record'),
    path('record/<str:object_type>/<str:record_id>/delete/', views.delete_record, name='delete_record'),
    path('test-api/', views.test_api_view, name='test_api'),
]
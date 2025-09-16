from django.urls import path
from . import views

app_name = 'authentication'

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('callback/', views.OAuthCallbackView.as_view(), name='oauth_callback'),
    path('session/', views.SessionInfoView.as_view(), name='session_info'),
    path('settings/', views.SettingsView.as_view(), name='settings'),
    path('refresh-token/', views.refresh_token, name='refresh_token'),
    path('health/', views.health_check, name='health_check'),
]
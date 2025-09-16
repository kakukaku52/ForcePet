from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from .models import SalesforceConnection
import logging

logger = logging.getLogger('workbench')


class SalesforceSessionMiddleware:
    """
    Middleware to check and manage Salesforce session state
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # URLs that don't require Salesforce authentication
        self.exempt_urls = [
            '/auth/login/',
            '/auth/callback/',
            '/auth/logout/',
            '/auth/health/',
            '/admin/',
            '/static/',
            '/media/',
            '/query/api/',  # Allow API calls to handle their own auth
        ]
    
    def __call__(self, request):
        # Check if URL is exempt from authentication
        if any(request.path.startswith(url) for url in self.exempt_urls):
            # For API endpoints, still try to attach the connection if available
            if request.path.startswith('/query/api/'):
                connection_id = request.session.get('sf_connection_id')
                if connection_id:
                    try:
                        connection = SalesforceConnection.objects.get(id=connection_id, is_active=True)
                        request.sf_connection = connection
                    except SalesforceConnection.DoesNotExist:
                        pass
            return self.get_response(request)
        
        # Check if we have a Salesforce connection
        connection_id = request.session.get('sf_connection_id')
        if not connection_id:
            if not request.path.startswith('/auth/'):
                messages.info(request, 'Please log in to Salesforce to continue.')
                return redirect('authentication:login')
            return self.get_response(request)
        
        try:
            # Get connection and verify it's still active
            connection = SalesforceConnection.objects.get(id=connection_id, is_active=True)
            
            # Add connection to request for easy access
            request.sf_connection = connection
            
            # Check if connection has expired
            if connection.is_expired():
                logger.info(f"Connection {connection_id} has expired")
                connection.is_active = False
                connection.save()
                
                # Clear session
                if 'sf_connection_id' in request.session:
                    del request.session['sf_connection_id']
                
                messages.warning(request, 'Your Salesforce session has expired. Please log in again.')
                return redirect('authentication:login')
                
        except SalesforceConnection.DoesNotExist:
            logger.warning(f"Invalid connection ID in session: {connection_id}")
            # Clear invalid session
            if 'sf_connection_id' in request.session:
                del request.session['sf_connection_id']
            
            messages.error(request, 'Invalid session. Please log in again.')
            return redirect('authentication:login')
        
        return self.get_response(request)
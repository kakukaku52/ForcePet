from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.urls import reverse
from django.conf import settings
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from urllib.parse import urlencode
import uuid
import logging
import hashlib
import base64
import secrets

from .models import SalesforceConnection, WorkbenchSettings
from .salesforce_client import SalesforceClient, SalesforceAPIError
from .forms import LoginForm, StandardLoginForm

logger = logging.getLogger('workbench')


class LoginView(View):
    """
    Handle Salesforce OAuth and standard login
    """
    template_name = 'authentication/login.html'
    
    def get(self, request):
        """Display login form"""
        if request.session.get('sf_connection_id'):
            return redirect('query:index')
        
        context = {
            'oauth_form': LoginForm(),
            'standard_form': StandardLoginForm(),
            'oauth_enabled': bool(settings.SALESFORCE_CONSUMER_KEY),
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        """Handle login form submission"""
        login_type = request.POST.get('login_type', 'oauth')
        
        if login_type == 'oauth':
            return self._handle_oauth_login(request)
        elif login_type == 'standard':
            return self._handle_standard_login(request)
        else:
            messages.error(request, 'Invalid login type selected.')
            return self.get(request)
    
    def _handle_oauth_login(self, request):
        """Handle OAuth login flow"""
        form = LoginForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Please correct the errors below.')
            return self.get(request)

        # Generate PKCE code verifier and challenge
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode('utf-8')).digest()
        ).decode('utf-8').rstrip('=')

        # Build OAuth URL with code challenge
        auth_url = self._build_oauth_url(form.cleaned_data, code_challenge)

        # Store state and PKCE verifier in session for security
        request.session['oauth_state'] = form.cleaned_data['state']
        request.session['oauth_environment'] = form.cleaned_data['environment']
        request.session['oauth_code_verifier'] = code_verifier

        return redirect(auth_url)
    
    def _handle_standard_login(self, request):
        """Handle username/password login"""
        form = StandardLoginForm(request.POST)

        # Check if this is an Ajax request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if not form.is_valid():
            if is_ajax:
                errors = {}
                for field, error_list in form.errors.items():
                    errors[field] = error_list[0] if error_list else ''
                return JsonResponse({
                    'success': False,
                    'errors': errors,
                    'message': 'Please correct the errors below.'
                }, status=400)
            messages.error(request, 'Please correct the errors below.')
            return self.get(request)

        try:
            # Create connection using username/password
            connection = self._create_standard_connection(request, form.cleaned_data)

            # Store connection in session
            request.session['sf_connection_id'] = connection.id

            # Create or get Django user
            user, created = User.objects.get_or_create(
                username=connection.salesforce_username,
                defaults={'email': connection.salesforce_username}
            )

            # Associate connection with user
            connection.user = user
            connection.save()

            # Login Django user (using ModelBackend)
            from django.contrib.auth import authenticate
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)

            success_message = f'Successfully connected to {connection.organization_name}'

            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': success_message,
                    'redirect_url': reverse('query:index')
                })

            messages.success(request, success_message)
            return redirect('query:index')

        except SalesforceAPIError as e:
            logger.error(f"Standard login failed: {e}")
            error_message = str(e)

            if is_ajax:
                # Parse Salesforce error for better display
                error_details = {
                    'message': error_message,
                    'type': 'authentication_error'
                }

                # Try to extract more specific error information
                if 'INVALID_LOGIN' in error_message:
                    error_details['message'] = 'Invalid username, password, security token, or user locked out.'
                    error_details['type'] = 'invalid_credentials'
                elif 'API_DISABLED_FOR_ORG' in error_message:
                    error_details['message'] = 'API is not enabled for this organization.'
                    error_details['type'] = 'api_disabled'
                elif 'LOGIN_MUST_USE_SECURITY_TOKEN' in error_message:
                    error_details['message'] = 'Security token is required. Please append your security token to your password.'
                    error_details['type'] = 'token_required'

                return JsonResponse({
                    'success': False,
                    'error': error_details
                }, status=401)

            messages.error(request, f'Login failed: {error_message}')
            return self.get(request)
        except Exception as e:
            logger.error(f"Unexpected error during login: {e}")
            error_message = 'An unexpected error occurred. Please try again.'

            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'error': {'message': error_message, 'type': 'system_error'}
                }, status=500)

            messages.error(request, error_message)
            return self.get(request)
    
    def _build_oauth_url(self, form_data, code_challenge=None):
        """Build Salesforce OAuth authorization URL"""
        environment = form_data['environment']

        if environment == 'production':
            base_url = 'https://login.salesforce.com'
        elif environment == 'sandbox':
            base_url = 'https://test.salesforce.com'
        else:  # custom
            base_url = form_data['custom_domain'].rstrip('/')

        params = {
            'response_type': 'code',
            'client_id': settings.SALESFORCE_CONSUMER_KEY,
            'redirect_uri': settings.SALESFORCE_REDIRECT_URI,
            'state': form_data['state'],
            'scope': 'full refresh_token',
            'prompt': 'login',  # Force login prompt
        }

        # Add PKCE parameters if code challenge is provided
        if code_challenge:
            params['code_challenge'] = code_challenge
            params['code_challenge_method'] = 'S256'

        return f"{base_url}/services/oauth2/authorize?" + urlencode(params)
    
    def _create_standard_connection(self, request, form_data):
        """Create connection using username/password"""
        from simple_salesforce import Salesforce
        import uuid
        
        # Determine login URL based on environment
        environment = form_data['environment']
        if environment == 'sandbox':
            domain = 'test'
        elif environment == 'custom':
            domain = form_data['custom_domain'].replace('https://', '').replace('http://', '').rstrip('/')
        else:
            domain = None
        
        try:
            # Use simple-salesforce for username/password auth
            sf = Salesforce(
                username=form_data['username'],
                password=form_data['password'],
                security_token=form_data.get('security_token', ''),
                domain=domain,
                version=form_data['api_version'],
            )
            
            # Get user info using the identity URL
            # Note: simple-salesforce doesn't automatically fetch identity for password auth
            # We need to query for it or use a workaround
            
            user_id = ""
            org_id = ""
            org_name = "Unknown Org"
            
            try:
                # Get organization name and ID
                org_query = sf.query("SELECT Name, Id FROM Organization LIMIT 1")
                if org_query['records']:
                    org_name = org_query['records'][0]['Name']
                    org_id = org_query['records'][0]['Id']

                # Get current user info
                # We use the username we just logged in with
                user_query = sf.query(f"SELECT Id, Email FROM User WHERE Username = '{form_data['username']}' LIMIT 1")
                if user_query['records']:
                    user_id = user_query['records'][0]['Id']
            except Exception as e:
                logger.warning(f"Could not fetch additional user/org info: {e}")

            # Connection Management Logic:
            # 1. Find if there is already a Django user for this Salesforce username
            # 2. If so, check if they have an existing connection profile
            # 3. Update or Create accordingly

            sf_username = form_data['username']
            
            # Try to find existing Django user
            user = User.objects.filter(username=sf_username).first()
            
            connection = None
            if user:
                # User exists, look for their connection
                connection = SalesforceConnection.objects.filter(
                    user=user,
                    salesforce_username=sf_username
                ).first()
            
            unique_session_id = f"{sf.session_id}_{uuid.uuid4().hex[:8]}"

            if connection:
                # Update existing connection
                connection.session_id = unique_session_id
                connection.server_url = sf.base_url
                connection.instance_url = sf.base_url
                connection.salesforce_user_id = user_id
                connection.organization_id = org_id
                connection.organization_name = org_name
                connection.environment = environment
                connection.api_version = form_data['api_version']
                connection.is_active = True
                connection.set_access_token(sf.session_id)
            else:
                # Create new connection (and user will be linked later in the view)
                connection = SalesforceConnection(
                    user=user,  # Might be None if user doesn't exist yet
                    session_id=unique_session_id,
                    server_url=sf.base_url,
                    instance_url=sf.base_url,
                    salesforce_username=sf_username,
                    salesforce_user_id=user_id,
                    organization_id=org_id,
                    organization_name=org_name,
                    login_type='standard',
                    environment=environment,
                    api_version=form_data['api_version'],
                )
                connection.set_access_token(sf.session_id)

            connection.save()
            
            return connection
            
        except Exception as e:
            raise SalesforceAPIError(f"Authentication failed: {str(e)}")


class OAuthCallbackView(View):
    """
    Handle OAuth callback from Salesforce
    """
    
    def get(self, request):
        """Handle OAuth callback"""
        code = request.GET.get('code')
        state = request.GET.get('state')
        error = request.GET.get('error')
        
        if error:
            messages.error(request, f'OAuth error: {request.GET.get("error_description", error)}')
            return redirect('authentication:login')
        
        if not code or not state:
            messages.error(request, 'Invalid OAuth callback parameters.')
            return redirect('authentication:login')
        
        # Verify state
        session_state = request.session.pop('oauth_state', None)
        if state != session_state:
            messages.error(request, 'Invalid OAuth state. Please try again.')
            return redirect('authentication:login')
        
        try:
            # Get code verifier from session
            code_verifier = request.session.pop('oauth_code_verifier', None)

            # Exchange code for tokens
            client = SalesforceClient.from_oauth_callback(
                code=code,
                state=state,
                redirect_uri=settings.SALESFORCE_REDIRECT_URI,
                code_verifier=code_verifier
            )
            
            # Store connection in session
            request.session['sf_connection_id'] = client.connection.id
            
            # Create or get Django user
            user, created = User.objects.get_or_create(
                username=client.connection.salesforce_username,
                defaults={'email': client.connection.salesforce_username}
            )
            
            # Associate connection with user
            client.connection.user = user
            client.connection.save()
            
            # Login Django user
            login(request, user)
            
            # Create user settings if needed
            WorkbenchSettings.objects.get_or_create(user=user)
            
            messages.success(
                request, 
                f'Successfully connected to {client.connection.organization_name}'
            )
            return redirect('query:index')
            
        except Exception as e:
            logger.error(f"OAuth callback failed: {e}")
            messages.error(request, f'OAuth login failed: {str(e)}')
            return redirect('authentication:login')


class LogoutView(View):
    """
    Handle logout and cleanup
    """
    
    def get(self, request):
        """Handle logout"""
        return self.post(request)
    
    def post(self, request):
        """Handle logout"""
        sf_logout_url = None

        # Get current connection to determine Salesforce logout URL
        connection_id = request.session.get('sf_connection_id')
        if connection_id:
            try:
                connection = SalesforceConnection.objects.get(id=connection_id)
                # Construct Salesforce logout URL if instance_url is available
                if connection.instance_url:
                    sf_logout_url = f"{connection.instance_url}/secur/logout.jsp"
                
                # Deactivate connection
                connection.is_active = False
                connection.save()
            except SalesforceConnection.DoesNotExist:
                pass
        
        # Clear session
        request.session.flush()
        
        # Logout Django user
        logout(request)
        
        # Render logout page with hidden iframe for Salesforce logout
        return render(request, 'authentication/logout.html', {
            'sf_logout_url': sf_logout_url
        })


class SessionInfoView(View):
    """
    Display current session information
    """
    template_name = 'authentication/session_info.html'
    
    def get(self, request):
        """Display session info"""
        connection_id = request.session.get('sf_connection_id')
        if not connection_id:
            messages.error(request, 'No active Salesforce connection.')
            return redirect('authentication:login')
        
        try:
            connection = SalesforceConnection.objects.get(id=connection_id)
            client = SalesforceClient(connection)
            
            # Get additional info from Salesforce
            try:
                org_limits = client.get_organization_limits()
                user_info = client.get_user_info()
            except Exception as e:
                logger.warning(f"Could not fetch additional session info: {e}")
                org_limits = None
                user_info = None
            
            context = {
                'connection': connection,
                'org_limits': org_limits,
                'user_info': user_info,
            }
            
            return render(request, self.template_name, context)
            
        except SalesforceConnection.DoesNotExist:
            messages.error(request, 'Invalid session. Please log in again.')
            return redirect('authentication:login')


@require_http_methods(["POST"])
def refresh_token(request):
    """
    AJAX endpoint to refresh access token
    """
    connection_id = request.session.get('sf_connection_id')
    if not connection_id:
        return JsonResponse({'error': 'No active connection'}, status=401)
    
    try:
        connection = SalesforceConnection.objects.get(id=connection_id)
        client = SalesforceClient(connection)
        client.refresh_access_token()
        
        return JsonResponse({'success': True, 'message': 'Token refreshed successfully'})
        
    except SalesforceConnection.DoesNotExist:
        return JsonResponse({'error': 'Invalid connection'}, status=404)
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        return JsonResponse({'error': str(e)}, status=500)


def health_check(request):
    """
    Simple health check endpoint
    """
    return JsonResponse({'status': 'ok', 'message': 'Workbench is running'})


class SettingsView(View):
    """
    Display and update user settings
    """
    template_name = 'authentication/settings.html'
    
    def get(self, request):
        """Display settings form"""
        if not request.user.is_authenticated:
            return redirect('authentication:login')
        
        try:
            settings_obj = WorkbenchSettings.objects.get(user=request.user)
        except WorkbenchSettings.DoesNotExist:
            settings_obj = WorkbenchSettings.objects.create(user=request.user)
        
        context = {
            'settings': settings_obj,
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        """Update settings"""
        if not request.user.is_authenticated:
            return redirect('authentication:login')
        
        try:
            settings_obj = WorkbenchSettings.objects.get(user=request.user)
        except WorkbenchSettings.DoesNotExist:
            settings_obj = WorkbenchSettings.objects.create(user=request.user)
        
        # Update settings from form data
        settings_obj.default_query_results_format = request.POST.get(
            'default_query_results_format', 
            settings_obj.default_query_results_format
        )
        settings_obj.query_timeout = int(request.POST.get('query_timeout', settings_obj.query_timeout))
        settings_obj.max_query_results = int(request.POST.get('max_query_results', settings_obj.max_query_results))
        settings_obj.batch_size = int(request.POST.get('batch_size', settings_obj.batch_size))
        settings_obj.enable_rollback_on_error = request.POST.get('enable_rollback_on_error') == 'on'
        settings_obj.timezone_preference = request.POST.get('timezone_preference', settings_obj.timezone_preference)
        settings_obj.api_timeout = int(request.POST.get('api_timeout', settings_obj.api_timeout))
        settings_obj.debug_mode = request.POST.get('debug_mode') == 'on'
        
        settings_obj.save()
        
        messages.success(request, 'Settings updated successfully.')
        return redirect('authentication:settings')

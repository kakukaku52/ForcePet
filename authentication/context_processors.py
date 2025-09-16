from .models import SalesforceConnection


def salesforce_context(request):
    """
    Context processor to add Salesforce connection info to all templates
    """
    context = {
        'sf_connection': None,
        'sf_user_info': {},
        'workbench_version': '1.0.0',  # Update this as needed
    }
    
    # Add connection info if available
    if hasattr(request, 'sf_connection'):
        context['sf_connection'] = request.sf_connection
        context['sf_user_info'] = {
            'username': request.sf_connection.salesforce_username,
            'organization_name': request.sf_connection.organization_name,
            'environment': request.sf_connection.get_environment_display(),
            'api_version': request.sf_connection.api_version,
        }
    
    return context
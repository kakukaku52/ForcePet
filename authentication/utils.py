from simple_salesforce import Salesforce
from .models import SalesforceConnection
from django.core.exceptions import ObjectDoesNotExist

def get_salesforce_client(user):
    """Get Salesforce client for a user"""
    try:
        connection = SalesforceConnection.objects.get(user=user)

        # Use simple-salesforce library
        sf = Salesforce(
            instance_url=connection.instance_url,
            session_id=connection.access_token,
            version=connection.api_version
        )

        return sf
    except ObjectDoesNotExist:
        raise Exception("No Salesforce connection found for user. Please login first.")
    except Exception as e:
        raise Exception(f"Failed to create Salesforce client: {str(e)}")
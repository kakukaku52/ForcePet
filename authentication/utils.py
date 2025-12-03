from simple_salesforce import Salesforce
from django.core.exceptions import ObjectDoesNotExist

from .models import SalesforceConnection


def _select_salesforce_connection(user):
    """
    Return the most recent active Salesforce connection for the given user.
    Falls back to any connection if no active one exists.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        raise ObjectDoesNotExist("User must be authenticated to access Salesforce.")

    connection = (
        SalesforceConnection.objects.filter(user=user, is_active=True)
        .order_by("-updated_at")
        .first()
    )
    if connection is None:
        connection = (
            SalesforceConnection.objects.filter(user=user)
            .order_by("-updated_at")
            .first()
        )

    if connection is None:
        raise ObjectDoesNotExist("No Salesforce connection found for user. Please login first.")

    return connection


def get_salesforce_client(user):
    """Get Salesforce client for a user using the most recent connection."""
    try:
        connection = get_salesforce_connection(user)

        try:
            access_token = connection.get_access_token()
        except Exception as exc:
            raise Exception("Failed to decrypt Salesforce access token. Please reconnect.") from exc

        if not access_token:
            raise Exception("No Salesforce access token found. Please reconnect.")

        instance_url = connection.instance_url or connection.server_url
        if not instance_url:
            raise Exception("Salesforce instance URL is missing. Please reconnect.")

        return Salesforce(
            instance_url=instance_url,
            session_id=access_token,
            version=connection.api_version,
        )
    except ObjectDoesNotExist as exc:
        raise Exception(str(exc))
    except Exception as exc:
        raise Exception(f"Failed to create Salesforce client: {exc}")


def get_salesforce_connection(user):
    """Return the most recent Salesforce connection for the user."""
    return _select_salesforce_connection(user)

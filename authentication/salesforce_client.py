"""
Salesforce API Client for Django Workbench
Provides unified interface to Salesforce SOAP, REST, Bulk, and Streaming APIs
"""

import requests
import json
import logging
from urllib.parse import urljoin, quote
from simple_salesforce import Salesforce
from simple_salesforce.exceptions import SalesforceError
from zeep import Client as SOAPClient
from zeep.exceptions import Fault
from django.conf import settings
import xml.etree.ElementTree as ET

logger = logging.getLogger('workbench')


class SalesforceAPIError(Exception):
    """Custom exception for Salesforce API errors"""
    pass


class SalesforceClient:
    """
    Unified Salesforce API client supporting multiple authentication methods
    and API types (SOAP, REST, Bulk, Streaming)
    """
    
    def __init__(self, connection):
        """
        Initialize with a SalesforceConnection model instance
        """
        self.connection = connection
        self.session = requests.Session()
        self._soap_client = None
        self._sf_client = None
        
        # Set up session headers
        self.session.headers.update({
            'Authorization': f'Bearer {connection.get_access_token()}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })
    
    @classmethod
    def from_oauth_callback(cls, code, state, redirect_uri, code_verifier=None):
        """
        Create client from OAuth callback parameters
        """
        token_url = 'https://login.salesforce.com/services/oauth2/token'

        data = {
            'grant_type': 'authorization_code',
            'client_id': settings.SALESFORCE_CONSUMER_KEY,
            'client_secret': settings.SALESFORCE_CONSUMER_SECRET,
            'code': code,
            'redirect_uri': redirect_uri,
        }

        # Add code_verifier for PKCE if provided
        if code_verifier:
            data['code_verifier'] = code_verifier

        response = requests.post(token_url, data=data)
        response.raise_for_status()

        token_data = response.json()
        return cls._create_connection_from_token_data(token_data)
    
    @classmethod
    def _create_connection_from_token_data(cls, token_data):
        """
        Create SalesforceConnection from OAuth token response
        """
        from .models import SalesforceConnection
        import uuid
        
        # Get user info from Salesforce
        identity_response = requests.get(
            token_data['id'],
            headers={'Authorization': f"Bearer {token_data['access_token']}"}
        )
        identity_response.raise_for_status()
        identity = identity_response.json()
        
        # Create connection record
        connection = SalesforceConnection(
            session_id=str(uuid.uuid4()),
            server_url=token_data['instance_url'],
            instance_url=token_data['instance_url'],
            salesforce_user_id=identity['user_id'],
            salesforce_username=identity['username'],
            organization_id=identity['organization_id'],
            organization_name=identity.get('display_name', 'Unknown'),
            login_type='oauth',
        )
        
        connection.set_access_token(token_data['access_token'])
        if 'refresh_token' in token_data:
            connection.set_refresh_token(token_data['refresh_token'])
        
        connection.save()
        return cls(connection)
    
    def refresh_access_token(self):
        """
        Refresh the access token using refresh token
        """
        if not self.connection.get_refresh_token():
            raise SalesforceAPIError("No refresh token available")
        
        token_url = 'https://login.salesforce.com/services/oauth2/token'
        
        data = {
            'grant_type': 'refresh_token',
            'client_id': settings.SALESFORCE_CONSUMER_KEY,
            'client_secret': settings.SALESFORCE_CONSUMER_SECRET,
            'refresh_token': self.connection.get_refresh_token(),
        }
        
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        self.connection.set_access_token(token_data['access_token'])
        self.connection.save()
        
        # Update session headers
        self.session.headers.update({
            'Authorization': f'Bearer {token_data["access_token"]}',
        })
    
    def get_simple_salesforce_client(self):
        """
        Get configured simple-salesforce client
        """
        if not self._sf_client:
            self._sf_client = Salesforce(
                instance_url=self.connection.instance_url,
                session_id=self.connection.get_access_token(),
                version=self.connection.api_version
            )
        return self._sf_client
    
    # SOQL/SOSL Methods
    def query(self, soql, include_deleted=False):
        """
        Execute SOQL query
        """
        try:
            sf = self.get_simple_salesforce_client()
            if include_deleted:
                return sf.query_all(soql, include_deleted=True)
            return sf.query(soql)
        except SalesforceError as e:
            logger.error(f"SOQL query error: {e}")
            # Extract error message from Salesforce response
            error_msg = str(e)
            # Try to parse the error message for better formatting
            if 'MALFORMED_QUERY' in error_msg:
                # Extract just the error message part
                import re
                match = re.search(r"'message': '([^']+)'", error_msg)
                if match:
                    error_detail = match.group(1).replace('\\n', '\n')
                    raise SalesforceAPIError(f"Malformed query:\n{error_detail}")
            raise SalesforceAPIError(f"Query failed: {e}")
    
    def query_more(self, next_records_url):
        """
        Get more query results using nextRecordsUrl
        """
        try:
            sf = self.get_simple_salesforce_client()
            return sf.query_more(next_records_url, identifier_is_url=True)
        except SalesforceError as e:
            logger.error(f"Query more error: {e}")
            raise SalesforceAPIError(f"Query more failed: {e}")
    
    def search(self, sosl):
        """
        Execute SOSL search
        """
        try:
            sf = self.get_simple_salesforce_client()
            return sf.search(sosl)
        except SalesforceError as e:
            logger.error(f"SOSL search error: {e}")
            raise SalesforceAPIError(f"Search failed: {e}")
    
    # Data Manipulation Methods
    def insert(self, sobject, data):
        """
        Insert single record
        """
        try:
            sf = self.get_simple_salesforce_client()
            sobject_type = getattr(sf, sobject)
            return sobject_type.create(data)
        except SalesforceError as e:
            logger.error(f"Insert error: {e}")
            raise SalesforceAPIError(f"Insert failed: {e}")
    
    def update(self, sobject, record_id, data):
        """
        Update single record
        """
        try:
            sf = self.get_simple_salesforce_client()
            sobject_type = getattr(sf, sobject)
            return sobject_type.update(record_id, data)
        except SalesforceError as e:
            logger.error(f"Update error: {e}")
            raise SalesforceAPIError(f"Update failed: {e}")
    
    def delete(self, sobject, record_id):
        """
        Delete single record
        """
        try:
            sf = self.get_simple_salesforce_client()
            sobject_type = getattr(sf, sobject)
            return sobject_type.delete(record_id)
        except SalesforceError as e:
            logger.error(f"Delete error: {e}")
            raise SalesforceAPIError(f"Delete failed: {e}")
    
    def upsert(self, sobject, external_id_field, external_id, data):
        """
        Upsert single record
        """
        try:
            sf = self.get_simple_salesforce_client()
            sobject_type = getattr(sf, sobject)
            return sobject_type.upsert(f"{external_id_field}/{external_id}", data)
        except SalesforceError as e:
            logger.error(f"Upsert error: {e}")
            raise SalesforceAPIError(f"Upsert failed: {e}")
    
    def undelete(self, record_ids):
        """
        Undelete records
        """
        try:
            sf = self.get_simple_salesforce_client()
            return sf.restful(f'sobjects/undelete', method='POST', json={'ids': record_ids})
        except SalesforceError as e:
            logger.error(f"Undelete error: {e}")
            raise SalesforceAPIError(f"Undelete failed: {e}")
    
    # Metadata Methods
    def describe_global(self):
        """
        Get global describe information
        """
        try:
            sf = self.get_simple_salesforce_client()
            return sf.describe()
        except SalesforceError as e:
            logger.error(f"Describe global error: {e}")
            raise SalesforceAPIError(f"Describe global failed: {e}")
    
    def describe_sobject(self, sobject):
        """
        Describe specific sObject
        """
        try:
            sf = self.get_simple_salesforce_client()
            sobject_type = getattr(sf, sobject)
            return sobject_type.describe()
        except SalesforceError as e:
            logger.error(f"Describe sObject error: {e}")
            raise SalesforceAPIError(f"Describe {sobject} failed: {e}")

    def describe_object(self, sobject):
        """Alias for describe_sobject for compatibility"""
        return self.describe_sobject(sobject)

    def update_record(self, sobject, record_id, data):
        """Alias for update for compatibility"""
        return self.update(sobject, record_id, data)

    def delete_record(self, sobject, record_id):
        """Alias for delete for compatibility"""
        return self.delete(sobject, record_id)
    
    def list_metadata(self, metadata_type, folder=None):
        """
        List metadata of specific type
        """
        # This would typically use the Metadata API
        # For now, we'll use a REST approach where possible
        url = f"{self.connection.get_rest_endpoint_url()}/tooling/query/"
        
        # Build query based on metadata type
        soql_queries = {
            'CustomObject': "SELECT Id, DeveloperName, MasterLabel FROM CustomObject",
            'CustomField': "SELECT Id, DeveloperName, MasterLabel FROM CustomField",
            'ApexClass': "SELECT Id, Name FROM ApexClass",
            'ApexTrigger': "SELECT Id, Name FROM ApexTrigger",
        }
        
        if metadata_type in soql_queries:
            params = {'q': soql_queries[metadata_type]}
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        
        raise SalesforceAPIError(f"Metadata type {metadata_type} not supported")
    
    # Apex Methods
    def execute_anonymous(self, apex_code):
        """
        Execute anonymous Apex code
        """
        url = f"{self.connection.get_rest_endpoint_url()}/tooling/executeAnonymous/"
        params = {'anonymousBody': apex_code}
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def run_tests(self, class_ids=None, suite_ids=None):
        """
        Run Apex tests
        """
        url = f"{self.connection.get_rest_endpoint_url()}/tooling/runTestsAsynchronous/"
        
        data = {}
        if class_ids:
            data['classids'] = ','.join(class_ids)
        if suite_ids:
            data['suiteids'] = ','.join(suite_ids)
        
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()
    
    # REST API Methods
    def rest_request(self, method, endpoint, data=None, params=None):
        """
        Make generic REST API request
        """
        url = urljoin(self.connection.get_rest_endpoint_url(), endpoint)
        
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, params=params)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, params=params)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data, params=params)
            elif method.upper() == 'PATCH':
                response = self.session.patch(url, json=data, params=params)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, params=params)
            else:
                raise SalesforceAPIError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            
            # Try to parse JSON, return text if not JSON
            try:
                return response.json()
            except ValueError:
                return response.text
                
        except requests.RequestException as e:
            logger.error(f"REST request error: {e}")
            raise SalesforceAPIError(f"REST request failed: {e}")
    
    # Bulk API Methods
    def create_bulk_job(self, operation, object_type, external_id_field=None):
        """
        Create a new bulk job
        """
        url = f"{self.connection.get_bulk_endpoint_url()}/job"
        
        job_data = {
            'operation': operation,
            'object': object_type,
            'contentType': 'CSV',
        }
        
        if external_id_field and operation == 'upsert':
            job_data['externalIdFieldName'] = external_id_field
        
        # Convert to XML for Bulk API 1.0
        xml_data = self._dict_to_xml(job_data, 'jobInfo')
        
        headers = {
            'Authorization': f'Bearer {self.connection.get_access_token()}',
            'Content-Type': 'application/xml',
        }
        
        response = requests.post(url, data=xml_data, headers=headers)
        response.raise_for_status()
        
        return self._xml_to_dict(response.text)
    
    def add_batch_to_job(self, job_id, data):
        """
        Add a batch to an existing bulk job
        """
        url = f"{self.connection.get_bulk_endpoint_url()}/job/{job_id}/batch"
        
        headers = {
            'Authorization': f'Bearer {self.connection.get_access_token()}',
            'Content-Type': 'text/csv',
        }
        
        response = requests.post(url, data=data, headers=headers)
        response.raise_for_status()
        
        return self._xml_to_dict(response.text)
    
    def close_bulk_job(self, job_id):
        """
        Close a bulk job
        """
        url = f"{self.connection.get_bulk_endpoint_url()}/job/{job_id}"
        
        job_data = {'state': 'Closed'}
        xml_data = self._dict_to_xml(job_data, 'jobInfo')
        
        headers = {
            'Authorization': f'Bearer {self.connection.get_access_token()}',
            'Content-Type': 'application/xml',
        }
        
        response = requests.post(url, data=xml_data, headers=headers)
        response.raise_for_status()
        
        return self._xml_to_dict(response.text)
    
    def get_bulk_job_status(self, job_id):
        """
        Get bulk job status
        """
        url = f"{self.connection.get_bulk_endpoint_url()}/job/{job_id}"
        
        headers = {
            'Authorization': f'Bearer {self.connection.get_access_token()}',
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        return self._xml_to_dict(response.text)
    
    def get_batch_status(self, job_id, batch_id):
        """
        Get batch status
        """
        url = f"{self.connection.get_bulk_endpoint_url()}/job/{job_id}/batch/{batch_id}"
        
        headers = {
            'Authorization': f'Bearer {self.connection.get_access_token()}',
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        return self._xml_to_dict(response.text)
    
    def get_batch_result(self, job_id, batch_id):
        """
        Get batch results
        """
        url = f"{self.connection.get_bulk_endpoint_url()}/job/{job_id}/batch/{batch_id}/result"
        
        headers = {
            'Authorization': f'Bearer {self.connection.get_access_token()}',
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        return response.text  # CSV format
    
    # Utility Methods
    def _dict_to_xml(self, data, root_name):
        """
        Convert dictionary to XML for Bulk API
        """
        root = ET.Element(root_name)
        root.set('xmlns', 'http://www.force.com/2009/06/async/dataload')
        
        for key, value in data.items():
            elem = ET.SubElement(root, key)
            elem.text = str(value)
        
        return ET.tostring(root, encoding='unicode')
    
    def _xml_to_dict(self, xml_string):
        """
        Convert XML response to dictionary
        """
        root = ET.fromstring(xml_string)
        result = {}
        
        # Remove namespace for easier processing
        for elem in root.iter():
            if '}' in elem.tag:
                elem.tag = elem.tag.split('}')[1]
        
        for child in root:
            result[child.tag] = child.text
        
        return result
    
    def get_organization_limits(self):
        """
        Get organization limits
        """
        try:
            return self.rest_request('GET', 'limits/')
        except Exception as e:
            logger.error(f"Error getting org limits: {e}")
            raise SalesforceAPIError(f"Failed to get org limits: {e}")
    
    def get_user_info(self):
        """
        Get current user information
        """
        try:
            user_id = self.connection.user_id
            return self.rest_request('GET', f'sobjects/User/{user_id}')
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            raise SalesforceAPIError(f"Failed to get user info: {e}")
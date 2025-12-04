"""
Salesforce API Client for Django Workbench
Provides unified interface to Salesforce SOAP, REST, Bulk, and Streaming APIs
"""

import json
import logging
from typing import Any, Dict, List
from urllib.parse import quote

import requests
from simple_salesforce import Salesforce
from simple_salesforce.exceptions import SalesforceError
from zeep import Client as SOAPClient
from zeep.exceptions import Fault
from django.conf import settings
import xml.etree.ElementTree as ET

logger = logging.getLogger('workbench')


def _to_18_char_id(sf_id: str | None) -> str | None:
    if not sf_id or len(sf_id) != 15:
        return sf_id
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ012345"
    checksum = ""
    for i in range(0, 15, 5):
        chunk = sf_id[i : i + 5]
        bits = 0
        for index, char in enumerate(chunk):
            if "A" <= char <= "Z":
                bits |= 1 << index
        checksum += alphabet[bits]
    return sf_id + checksum

METADATA_TYPE_OVERRIDES = {
    'CustomObject': {
        'tooling_type': 'EntityDefinition',
        'describe': False,
        'query_fields': [
            'DurableId',
            'QualifiedApiName',
            'Label',
            'PluralLabel',
            'IsQueryable',
            'IsCustomizable',
            'NamespacePrefix',
        ],
        'preferred_fields': ['Label', 'QualifiedApiName', 'PluralLabel', 'IsCustomizable', 'IsQueryable', 'NamespacePrefix'],
        'query_filter': "IsCustomizable = true",
        'lookup_fields': ['QualifiedApiName', 'DeveloperName', 'DurableId'],
        'order_field': 'QualifiedApiName',
        'id_field': 'DurableId',
    },
    'ApexClass': {
        'describe': False,
        'query_fields': [
            'Id',
            'Name',
            'Status',
            'ApiVersion',
            'LengthWithoutComments',
            'NamespacePrefix',
            'LastModifiedDate',
            'CreatedDate',
        ],
        'preferred_fields': ['Name', 'Status', 'ApiVersion', 'LengthWithoutComments', 'LastModifiedDate'],
        'order_field': 'LastModifiedDate',
        'lookup_fields': ['Name', 'DeveloperName'],
        'id_field': 'Id',
    },
    'ApexTrigger': {
        'describe': False,
        'query_fields': [
            'Id',
            'Name',
            'TableEnumOrId',
            'Status',
            'UsageBeforeInsert',
            'UsageBeforeUpdate',
            'UsageAfterInsert',
            'UsageAfterUpdate',
            'UsageIsBulk',
            'NamespacePrefix',
            'LastModifiedDate',
            'CreatedDate',
        ],
        'preferred_fields': ['Name', 'TableEnumOrId', 'Status', 'UsageBeforeInsert', 'LastModifiedDate'],
        'order_field': 'LastModifiedDate',
        'lookup_fields': ['Name', 'DeveloperName'],
        'id_field': 'Id',
    },
    'ApexPage': {
        'describe': False,
        'query_fields': [
            'Id',
            'Name',
            'MasterLabel',
            'ApiVersion',
            'NamespacePrefix',
            'IsAvailableInTouch',
            'LastModifiedDate',
            'CreatedDate',
        ],
        'preferred_fields': ['Name', 'MasterLabel', 'ApiVersion', 'IsAvailableInTouch', 'LastModifiedDate'],
        'order_field': 'LastModifiedDate',
        'lookup_fields': ['Name', 'DeveloperName'],
        'id_field': 'Id',
    },
    'ApexComponent': {
        'describe': False,
        'query_fields': [
            'Id',
            'Name',
            'MasterLabel',
            'ApiVersion',
            'NamespacePrefix',
            'ControllerType',
            'LastModifiedDate',
            'CreatedDate',
        ],
        'preferred_fields': ['Name', 'MasterLabel', 'ApiVersion', 'ControllerType', 'LastModifiedDate'],
        'order_field': 'LastModifiedDate',
        'lookup_fields': ['Name', 'DeveloperName'],
        'id_field': 'Id',
    },
    'ApprovalProcess': {
        'tooling_type': 'ProcessDefinition',
        'describe': True,
        'use_tooling': False,
        'query_fields': None,
        'preferred_fields': ['Name', 'DeveloperName', 'TableEnumOrId', 'Type', 'LastModifiedDate'],
        'query_filter': "Type = 'Approval'",
        'order_field': 'LastModifiedDate',
        'lookup_fields': ['Id', 'DeveloperName', 'Name'],
        'id_field': 'Id',
    },
    'Report': {
        'tooling_type': 'Report',
        'describe': True,
        'use_tooling': False,
        'query_fields': None,
        'preferred_fields': ['Name', 'DeveloperName', 'Format', 'LastRunDate', 'LastModifiedDate'],
        'order_field': 'LastModifiedDate',
        'lookup_fields': ['Id', 'DeveloperName', 'Name'],
        'id_field': 'Id',
    },
    'ReportType': {
        'tooling_type': 'CustomReportType',
        'custom_list_handler': 'report_type',
        'custom_detail_handler': 'report_type',
    },
    'Profile': {
        'tooling_type': 'Profile',
        'describe': True,
        'use_tooling': False,
        'query_fields': None,
        'preferred_fields': ['Name', 'UserLicenseId', 'UserType', 'LastModifiedDate'],
        'order_field': 'LastModifiedDate',
        'lookup_fields': ['Id', 'Name'],
        'id_field': 'Id',
    },
    'NamedCredential': {
        'tooling_type': 'NamedCredential',
        'describe': True,
        'use_tooling': False,
        'query_fields': None,
        'preferred_fields': ['MasterLabel', 'DeveloperName', 'PrincipalType', 'LastModifiedDate'],
        'order_field': 'LastModifiedDate',
        'lookup_fields': ['Id', 'DeveloperName', 'MasterLabel'],
        'id_field': 'Id',
    },
    'ExternalCredential': {
        'tooling_type': 'ExternalCredential',
        'describe': True,
        'use_tooling': False,
        'query_fields': None,
        'preferred_fields': ['MasterLabel', 'DeveloperName', 'AuthenticationProtocol', 'LastModifiedDate'],
        'order_field': 'LastModifiedDate',
        'lookup_fields': ['Id', 'DeveloperName', 'MasterLabel'],
        'id_field': 'Id',
    },
    'ConnectedApp': {
        'tooling_type': 'ConnectedApplication',
        'describe': True,
        'use_tooling': False,
        'query_fields': None,
        'preferred_fields': ['Name', 'ContactEmail', 'Status', 'LastModifiedDate'],
        'order_field': 'LastModifiedDate',
        'lookup_fields': ['Id', 'Name'],
        'id_field': 'Id',
    },
    'CompactLayout': {
        'tooling_type': 'CompactLayout',
        'describe': False,
        'use_tooling': True,
        'query_fields': [
            'Id',
            'DeveloperName',
            'Name',
            'TableEnumOrId',
            'Label',
            'LastModifiedDate',
        ],
        'preferred_fields': ['Name', 'DeveloperName', 'TableEnumOrId', 'LastModifiedDate'],
        'order_field': 'LastModifiedDate',
        'lookup_fields': ['Id', 'DeveloperName', 'Name'],
        'id_field': 'Id',
    },
    'DuplicateRule': {
        'tooling_type': 'DuplicateRule',
        'metadata_endpoint': '/services/data/v{api_version}/metadata/',
        'metadata_filter': {
            'queries': [
                {
                    'type': 'DuplicateRule',
                },
            ],
        },
    },
}

DEFAULT_METADATA_LOOKUP_FIELDS = ['QualifiedApiName', 'DeveloperName', 'Name', 'FullName']


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
    
    def explain_query(self, soql):
        """
        Get query plan (explain) for a SOQL query
        """
        try:
            # Explain API endpoint: /services/data/vXX.0/query/?explain=SOQL
            # Note: simple-salesforce doesn't have a direct explain method, so we use rest_request
            
            # URL encode the query
            encoded_query = quote(soql)
            endpoint = f"query/?explain={encoded_query}"
            
            return self.rest_request('GET', endpoint)
        except SalesforceAPIError as e:
            # Pass through SalesforceAPIError directly
            raise e
        except Exception as e:
            logger.error(f"Explain query error: {e}")
            raise SalesforceAPIError(f"Explain failed: {str(e)}")

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
    
    def list_metadata(self, metadata_type, name_filter=None, limit=None):
        """
        List metadata entries for the requested type using the Tooling API.
        """
        override = METADATA_TYPE_OVERRIDES.get(metadata_type, {})

        # Handle custom list handlers
        custom_list_handler = override.get('custom_list_handler')
        if custom_list_handler == 'report_type':
            return self._list_report_types(name_filter=name_filter)

        # Handle Metadata API fallback
        metadata_endpoint_template = override.get('metadata_endpoint')
        if metadata_endpoint_template:
            return self.metadata_api_query(metadata_type, override, metadata_endpoint_template, name_filter=name_filter)

        tooling_type = override.get('tooling_type', metadata_type)
        use_tooling = override.get('use_tooling', True)

        fields = []
        describe_endpoint = f"/{'tooling/' if use_tooling else ''}sobjects/{tooling_type}/describe"
        describe_error = None
        use_fields_all = False

        if override and override.get('describe') is False:
            fields = [{'name': field} for field in override.get('query_fields', [])]
        else:
            try:
                describe_payload = self.rest_request('GET', describe_endpoint)
                fields = describe_payload.get('fields', [])
            except SalesforceAPIError as exc:
                describe_error = exc
                if override and override.get('query_fields'):
                    fields = [{'name': field} for field in override['query_fields']]
                else:
                    use_fields_all = True

        if not fields and override and override.get('query_fields'):
            fields = [{'name': field} for field in override['query_fields']]

        if not fields and not use_fields_all:
            message = "Metadata description is not available"
            if describe_error:
                message = f"{message}: {describe_error}"
            raise SalesforceAPIError(message)

        preferred_fields = [
            'Label',
            'QualifiedApiName',
            'DeveloperName',
            'Name',
            'FullName',
            'NamespacePrefix',
            'LastModifiedDate',
            'CreatedDate',
        ]

        override_preferred = override.get('preferred_fields')
        if override_preferred:
            preferred_fields = override_preferred + [field for field in preferred_fields if field not in override_preferred]

        field_names = {field['name']: field for field in fields}
        soql_fields: List[str] = []
        display_columns: List[str] = []
        id_field = override.get('id_field', 'Id')

        if not use_fields_all:
            if id_field:
                soql_fields.append(id_field)
            if 'Id' not in soql_fields:
                soql_fields.append('Id')

            for field_name in preferred_fields:
                if field_name in field_names:
                    soql_fields.append(field_name)
                    display_columns.append(field_name)

            for field in fields:
                name = field.get('name')
                if name and name not in soql_fields and len(soql_fields) < 12:
                    soql_fields.append(name)
                    display_columns.append(name)

        def _dedupe(seq):
            seen = set()
            result = []
            for item in seq:
                if item and item not in seen:
                    seen.add(item)
                    result.append(item)
            return result

        soql_fields = _dedupe(soql_fields)
        display_columns = _dedupe(display_columns)

        if not use_fields_all:
            if 'Id' not in soql_fields:
                soql_fields.insert(0, 'Id')
        else:
            if not id_field:
                id_field = 'Id'

        order_field = None
        if 'LastModifiedDate' in soql_fields:
            order_field = 'LastModifiedDate'
        elif 'CreatedDate' in soql_fields:
            order_field = 'CreatedDate'

        filters = []
        if name_filter and not use_fields_all:
            like_value = name_filter.replace("'", "\\'").lower()
            searchable_fields = [
                field for field in ['Label', 'QualifiedApiName', 'DeveloperName', 'Name', 'FullName']
                if field in field_names
            ]
            if searchable_fields:
                filter_terms = [
                    f"LOWER({field}) LIKE '%{like_value}%'"
                    for field in searchable_fields
                ]
                filters.append(f"({' OR '.join(filter_terms)})")

        override_filter = override.get('query_filter')
        if override_filter:
            filters.append(f"({override_filter})")

        if use_fields_all:
            soql = f"SELECT FIELDS(ALL) FROM {tooling_type}"
            if limit:
                soql = f"{soql} LIMIT {int(limit)}"
        else:
            soql = f"SELECT {', '.join(soql_fields)} FROM {tooling_type}"
            if filters:
                soql = f"{soql} WHERE {' AND '.join(filters)}"
            if override.get('order_field'):
                order_field = override['order_field']
            if order_field:
                soql = f"{soql} ORDER BY {order_field} DESC"
            if limit:
                soql = f"{soql} LIMIT {int(limit)}"

        query_endpoint = f"{self.connection.get_rest_endpoint_url()}/{'tooling/' if use_tooling else ''}query/"
        try:
            response = self.session.get(query_endpoint, params={'q': soql})
            response.raise_for_status()
        except requests.HTTPError as err:
            error_detail = None
            if err.response is not None:
                try:
                    payload = err.response.json()
                    if isinstance(payload, list) and payload:
                        error_detail = payload[0].get('message')
                    elif isinstance(payload, dict):
                        error_detail = payload.get('message') or payload.get('error')
                except ValueError:
                    error_detail = err.response.text

            message = f"Metadata query failed for {metadata_type}"
            if error_detail:
                message = f"{message}: {error_detail}"
            raise SalesforceAPIError(message) from err

        payload = response.json()
        records = payload.get('records', [])
        next_records_url = payload.get('nextRecordsUrl')

        while next_records_url and not limit:
            try:
                next_response = self.session.get(f"{self.connection.instance_url}{next_records_url}")
                next_response.raise_for_status()
                next_payload = next_response.json()
                records.extend(next_payload.get('records', []))
                next_records_url = next_payload.get('nextRecordsUrl')
            except requests.HTTPError:
                break

        payload['records'] = records
        payload.pop('nextRecordsUrl', None)
        columns = []
        if use_fields_all:
            if records:
                columns = [key for key in records[0].keys() if key != 'attributes']
        else:
            if 'Label' in display_columns:
                columns.append('Label')
            columns.extend([col for col in display_columns if col != 'Label'])
            columns = columns or display_columns or soql_fields
        payload['columns'] = columns
        payload['tooling_type'] = tooling_type
        payload['id_field'] = id_field
        return payload

    def fetch_metadata_detail(self, metadata_type, record_id=None, api_name=None):
        """
        Fetch detailed metadata information for a single entry.
        """
        override = METADATA_TYPE_OVERRIDES.get(metadata_type, {})

        custom_detail_handler = override.get('custom_detail_handler')
        if custom_detail_handler == 'report_type':
            return self._fetch_report_type_detail(identifier=record_id, api_name=api_name)

        tooling_type = override.get('tooling_type', metadata_type)
        use_tooling = override.get('use_tooling', True)
        base_endpoint = f"/{'tooling/' if use_tooling else ''}sobjects/{tooling_type}"

        target_record = None

        record_error = None

        raw_record_id = record_id

        if record_id:
            safe_record_id = _to_18_char_id(record_id) or record_id
            try:
                endpoint = f"{'tooling/' if use_tooling else ''}sobjects/{tooling_type}/{safe_record_id}"
                target_record = self.rest_request('GET', endpoint)
            except SalesforceAPIError as exc:
                record_error = exc

        lookup_candidates = []
        id_field = override.get('id_field')
        if record_id:
            if id_field:
                lookup_candidates.append((id_field, raw_record_id))
            lookup_candidates.append(('Id', _to_18_char_id(record_id) or record_id))

        if api_name:
            lookup_fields = override.get('lookup_fields', DEFAULT_METADATA_LOOKUP_FIELDS)
            lookup_candidates.extend((field, api_name) for field in lookup_fields)

        attempted = set()
        if target_record is None and lookup_candidates:
            for field, value in lookup_candidates:
                if not value:
                    continue
                lookup_value = _to_18_char_id(value) if field == 'Id' else value
                key = (field, value)
                if key in attempted:
                    continue
                attempted.add(key)
                soql = (
                    f"SELECT Id FROM {tooling_type} "
                    f"WHERE {field} = '{lookup_value}' LIMIT 1"
                )
                try:
                    response = self.session.get(
                        f"{self.connection.get_rest_endpoint_url()}/{'tooling/' if use_tooling else ''}query/",
                        params={'q': soql},
                    )
                    response.raise_for_status()
                    data = response.json()
                    records = data.get('records', [])
                    if records:
                        record_row = records[0]
                        record_id = record_row.get('Id')
                        if record_id:
                            try:
                                target_record = self.rest_request('GET', f"{base_endpoint}/{record_id}")
                            except SalesforceAPIError:
                                target_record = record_row
                            else:
                                break
                        else:
                            target_record = record_row
                            break
                except requests.HTTPError:
                    continue
        if target_record is None:
            if record_error:
                raise SalesforceAPIError(f"{metadata_type} の詳細を取得できませんでした: {record_error}") from record_error
            raise SalesforceAPIError(f"{metadata_type} のレコードが見つかりません。")

        detail_payload: Dict[str, Any] = {
            'metadata_type': metadata_type,
            'record': target_record,
        }
        detail_payload['tooling_type'] = tooling_type

        # Enrich CustomObject / EntityDefinition detail with describe data.
        object_api = None
        if metadata_type in {'CustomObject', 'EntityDefinition'} or tooling_type == 'EntityDefinition':
            object_api = (
                target_record.get('QualifiedApiName')
                or target_record.get('DeveloperName')
                or target_record.get('DurableId')
            )
        elif metadata_type == 'CustomField':
            object_api = target_record.get('TableEnumOrId')

        if object_api:
            try:
                describe_result = self.describe_object(object_api)
                fields = describe_result.get('fields', [])
                detail_payload['object'] = {
                    'label': describe_result.get('label'),
                    'api_name': describe_result.get('name'),
                    'plural_label': describe_result.get('labelPlural'),
                    'fields': [
                        {
                            'name': field.get('name'),
                            'label': field.get('label'),
                            'type': field.get('type'),
                            'length': field.get('length'),
                            'precision': field.get('precision'),
                            'scale': field.get('scale'),
                            'updateable': field.get('updateable'),
                            'createable': field.get('createable'),
                            'nillable': field.get('nillable'),
                            'calculated': field.get('calculated'),
                            'referenceTo': field.get('referenceTo'),
                            'picklistValues': [
                                {
                                    'value': pick.get('value'),
                                    'label': pick.get('label'),
                                }
                                for pick in field.get('picklistValues', [])
                                if pick.get('active')
                            ],
                        }
                        for field in fields
                    ],
                }
            except SalesforceAPIError:
                # Ignore describe errors for types that are not sObjects.
                detail_payload['object'] = None

        return detail_payload

    def fetch_field_detail(self, object_api_name, field_name):
        """
        Retrieve detailed information about a specific field on an sObject.
        """
        describe_result = self.describe_object(object_api_name)
        fields = describe_result.get('fields', [])
        for field in fields:
            if field.get('name') == field_name:
                return field
        raise SalesforceAPIError(f"{object_api_name}.{field_name} は見つかりませんでした。")

    def get_custom_field_tree(self, name_filter: str | None = None) -> List[Dict[str, Any]]:
        """
        Build a tree of custom objects and their custom fields.
        """
        describe_global = self.describe_global()
        sobjects = describe_global.get('sobjects', [])
        custom_objects = [obj for obj in sobjects if obj.get('custom')]

        name_filter_lower = name_filter.lower() if name_filter else None
        tree: List[Dict[str, Any]] = []

        def _matches_filter(field_info: Dict[str, Any], object_api_name: str) -> bool:
            if not name_filter_lower:
                return True
            candidates = [
                field_info.get('name', ''),
                field_info.get('label', ''),
                f"{object_api_name}.{field_info.get('name', '')}",
            ]
            return any(name_filter_lower in (candidate or '').lower() for candidate in candidates)

        for metadata_object in sorted(
            custom_objects,
            key=lambda obj: (obj.get('label') or obj.get('name') or '').lower(),
        ):
            api_name = metadata_object.get('name')
            label = metadata_object.get('label') or api_name

            try:
                describe = self.describe_object(api_name)
            except SalesforceAPIError:
                continue

            fields = []
            for field in describe.get('fields', []):
                if not field.get('custom'):
                    continue
                if not _matches_filter(field, api_name):
                    continue
                full_name = f"{api_name}.{field.get('name')}"
                fields.append(
                    {
                        'name': field.get('name'),
                        'label': field.get('label'),
                        'type': field.get('type'),
                        'full_name': full_name,
                    }
                )

            if fields:
                fields.sort(key=lambda item: (item['label'] or item['name'] or '').lower())
                tree.append(
                    {
                        'object_api_name': api_name,
                        'object_label': label,
                        'fields': fields,
                    }
                )

        tree.sort(key=lambda node: (node['object_label'] or node['object_api_name'] or '').lower())
        return tree
    
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
        if endpoint.startswith('http'):
            url = endpoint
        else:
            base = self.connection.get_rest_endpoint_url().rstrip('/')
            url = f"{base}/{endpoint.lstrip('/')}"
        
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
    def metadata_api_query(self, metadata_type, override, endpoint_template, name_filter=None):
        """Fallback query using the Metadata API listMetadata call."""
        api_version = self.connection.api_version
        endpoint = endpoint_template.format(api_version=api_version)
        url = f"{self.connection.instance_url}{endpoint}listMetadata"

        if override and override.get('metadata_filter'):
            query = json.loads(json.dumps(override['metadata_filter']))
            if 'queries' not in query:
                query['queries'] = []
            for q in query['queries']:
                if 'type' not in q:
                    q['type'] = override.get('tooling_type', metadata_type)
        else:
            query = {
                "queries": [
                    {
                        "type": override.get('tooling_type', metadata_type),
                    }
                ]
            }

        try:
            response = self.session.post(url, json=query)
            response.raise_for_status()
        except requests.HTTPError as err:
            message = f"Metadata query failed for {metadata_type}"
            try:
                payload = err.response.json()
                if isinstance(payload, list) and payload:
                    message = f"{message}: {payload[0].get('message')}"
                elif isinstance(payload, dict):
                    message = f"{message}: {payload.get('message') or payload.get('error')}"
            except ValueError:
                message = f"{message}: {err.response.text}"
            raise SalesforceAPIError(message) from err

        records = response.json() or []
        if name_filter:
            lowered = name_filter.lower()
            filtered = []
            for record in records:
                values = [str(record.get(key) or '') for key in record.keys()]
                if any(lowered in value.lower() for value in values):
                    filtered.append(record)
            records = filtered

        columns = sorted({key for record in records for key in record.keys()}) if records else []

        return {
            "records": records,
            "columns": columns,
            "totalSize": len(records),
            "done": True,
        }

    def _list_report_types(self, name_filter=None):
        api_version = self.connection.api_version
        endpoint = f"/services/data/v{api_version}/analytics/reportTypes"
        url = f"{self.connection.instance_url}{endpoint}"

        try:
            response = self.session.get(url)
            response.raise_for_status()
        except requests.HTTPError as err:
            message = "ReportType query failed"
            try:
                payload = err.response.json()
                if isinstance(payload, dict):
                    message = f"{message}: {payload.get('message') or payload.get('error') or payload}"
            except ValueError:
                message = f"{message}: {err.response.text}"
            raise SalesforceAPIError(message) from err

        payload = response.json()

        # Handle case where API returns a list directly instead of a dict
        if isinstance(payload, list):
            categories_payload = payload
        elif isinstance(payload, dict):
            categories_payload = payload.get('reportTypeCategories') or payload.get('reportTypes') or []
        else:
            categories_payload = []

        flat_report_types = []

        stack = [(categories_payload, None)]
        while stack:
            node, category_label = stack.pop()
            if isinstance(node, dict):
                report_types = node.get('reportTypes', None)
                if report_types is not None:
                    new_label = node.get('label') or node.get('name') or category_label
                    stack.append((report_types, new_label))
                    continue

                record = node.copy()
                if category_label and not record.get('category'):
                    record['category'] = category_label
                flat_report_types.append(record)
            elif isinstance(node, list):
                for item in node:
                    stack.append((item, category_label))

        if name_filter:
            lowered = name_filter.lower()
            filtered = []
            for item in flat_report_types:
                if not isinstance(item, dict):
                    continue
                values = [
                    str(item.get('name') or ''),
                    str(item.get('label') or ''),
                    str(item.get('developerName') or ''),
                    str(item.get('category') or ''),
                ]
                if any(lowered in value.lower() for value in values):
                    filtered.append(item)
            flat_report_types = filtered

        records = []
        for item in flat_report_types:
            if not isinstance(item, dict):
                continue
            records.append(
                {
                    'Name': item.get('label') or item.get('name'),
                    'DeveloperName': item.get('developerName'),
                    'Category': item.get('category'),
                    'Description': item.get('description'),
                    'DataType': item.get('dataCategory'),
                    'SupportsDashboard': item.get('supportsDashboard'),
                    'SupportsCharting': item.get('supportsCharting'),
                    'DetailUrl': item.get('url'),
                    'FullName': item.get('name'),
                }
            )

        columns = [
            'Name',
            'DeveloperName',
            'Category',
            'Description',
            'DataType',
            'SupportsDashboard',
            'SupportsCharting',
            'FullName',
        ]

        return {
            'records': records,
            'columns': columns,
            'totalSize': len(records),
            'done': True,
        }

    def _fetch_report_type_detail(self, identifier=None, api_name=None):
        api_version = self.connection.api_version
        target_name = api_name or identifier
        if not target_name:
            raise SalesforceAPIError('ReportType の識別子が指定されていません。')

        endpoint = f"/services/data/v{api_version}/analytics/reportTypes/{target_name}"
        url = f"{self.connection.instance_url}{endpoint}"

        try:
            response = self.session.get(url)
            response.raise_for_status()
        except requests.HTTPError as err:
            message = f"ReportType {target_name} の詳細取得に失敗しました"
            try:
                payload = err.response.json()
                if isinstance(payload, dict):
                    message = f"{message}: {payload.get('message') or payload.get('error') or payload}"
            except ValueError:
                message = f"{message}: {err.response.text}"
            raise SalesforceAPIError(message) from err

        detail = response.json() or {}
        record = {
            'Name': detail.get('label') or detail.get('name'),
            'DeveloperName': detail.get('developerName'),
            'Category': detail.get('category'),
            'Description': detail.get('description'),
            'DataType': detail.get('dataCategory'),
            'SupportsDashboard': detail.get('supportsDashboard'),
            'SupportsCharting': detail.get('supportsCharting'),
            'DetailUrl': detail.get('url'),
            'FullName': detail.get('name'),
        }

        sections = detail.get('sections') or {}
        detail_payload: Dict[str, Any] = {
            'metadata_type': 'ReportType',
            'record': record,
            'sections': sections,
        }

        return detail_payload

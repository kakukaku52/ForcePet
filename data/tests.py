import json
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import DataOperation
from authentication.models import SalesforceConnection


class CreateRecordViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='tester',
            email='tester@example.com',
            password='password123',
        )
        self.client.force_login(self.user)
        self.url = reverse('data:insert')

        # Simulate active Salesforce session for middleware
        self.connection = SalesforceConnection.objects.create(
            user=self.user,
            session_id='SESSION123',
            server_url='https://example.salesforce.com',
            login_type='oauth',
            environment='production',
            api_version='62.0',
            instance_url='https://example.salesforce.com',
        )
        session = self.client.session
        session['sf_connection_id'] = self.connection.id
        session.save()

    @patch('data.views.SalesforceClient')
    @patch('data.views.get_salesforce_connection')
    def test_get_renders_sobject_list(self, mock_get_connection, mock_client_cls):
        mock_get_connection.return_value = self.connection

        mock_sf = MagicMock()
        mock_sf.describe_global.return_value = {
            'sobjects': [
                {'name': 'Account', 'label': 'Account', 'labelPlural': 'Accounts', 'createable': True},
                {'name': 'Contact', 'label': 'Contact', 'labelPlural': 'Contacts', 'createable': True},
                {'name': 'Forbidden', 'label': 'Forbidden', 'labelPlural': 'Forbidden', 'createable': False},
            ]
        }
        mock_client_cls.return_value = mock_sf

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('"name": "Account"', content)
        self.assertIn('"label": "Account"', content)
        self.assertIn('"name": "Contact"', content)
        self.assertIn('"name": "Forbidden"', content)
        self.assertContains(response, 'id="sobject-filter-input"')
        self.assertContains(response, 'id="sobject-toggle"')
        self.assertContains(response, 'id="sobject-options-data"')
        mock_sf.describe_global.assert_called_once()

    @patch('data.views.SalesforceClient')
    @patch('data.views.get_salesforce_connection')
    def test_single_record_insert_success(self, mock_get_connection, mock_client_cls):
        mock_get_connection.return_value = self.connection
        mock_sf = MagicMock()
        mock_sf.insert.return_value = {'id': '001000000000AAA', 'success': True, 'errors': []}
        mock_client_cls.return_value = mock_sf

        payload = {
            'mode': 'single',
            'sobject': 'Account',
            'fields': [{'field': 'Name', 'value': 'Test Account'}],
        }

        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('001000000000AAA', data['message'])
        operation = DataOperation.objects.get()
        self.assertEqual(operation.sobject, 'Account')
        self.assertEqual(operation.record_count, 1)
        self.assertEqual(operation.success_count, 1)
        self.assertEqual(operation.error_count, 0)

    @patch('data.views.SalesforceClient')
    @patch('data.views.get_salesforce_connection')
    def test_csv_insert_creates_operations(self, mock_get_connection, mock_client_cls):
        mock_get_connection.return_value = self.connection
        mock_sf = MagicMock()
        mock_sf.insert.side_effect = [
            {'id': '001000000000AAA', 'success': True, 'errors': []},
            {'id': '001000000000AAB', 'success': True, 'errors': []},
        ]
        mock_client_cls.return_value = mock_sf

        csv_content = 'Name,Phone\nAcme,123456\nBeta,987654\n'
        csv_file = SimpleUploadedFile('records.csv', csv_content.encode('utf-8'), content_type='text/csv')
        mapping = [{'field': 'Name', 'csvField': 'Name'}, {'field': 'Phone', 'csvField': 'Phone'}]

        response = self.client.post(
            self.url,
            data={
                'mode': 'csv',
                'sobject': 'Account',
                'mapping': json.dumps(mapping),
                'csv_file': csv_file,
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['summary']['success_count'], 2)
        operation = DataOperation.objects.get()
        self.assertEqual(operation.record_count, 2)
        self.assertEqual(operation.success_count, 2)
        self.assertEqual(operation.error_count, 0)

    @patch('data.views.SalesforceClient')
    @patch('data.views.get_salesforce_connection')
    def test_single_record_requires_field_values(self, mock_get_connection, mock_client_cls):
        mock_get_connection.return_value = self.connection
        mock_sf = MagicMock()
        mock_client_cls.return_value = mock_sf

        payload = {
            'mode': 'single',
            'sobject': 'Account',
            'fields': [],
        }

        response = self.client.post(
            self.url,
            data=json.dumps(payload),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('至少需要提供一个字段值', data['message'])
        self.assertEqual(DataOperation.objects.count(), 0)

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from cryptography.fernet import Fernet
from django.conf import settings
import json
import base64


class SalesforceConnection(models.Model):
    """Model to store Salesforce connection information"""
    
    LOGIN_TYPE_CHOICES = [
        ('oauth', 'OAuth'),
        ('standard', 'Username/Password'),
        ('advanced', 'Advanced'),
    ]
    
    ENVIRONMENT_CHOICES = [
        ('production', 'Production (login.salesforce.com)'),
        ('sandbox', 'Sandbox (test.salesforce.com)'),
        ('custom', 'Custom Domain'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=255, unique=True)
    server_url = models.URLField()
    
    # Connection details
    login_type = models.CharField(max_length=20, choices=LOGIN_TYPE_CHOICES, default='oauth')
    environment = models.CharField(max_length=20, choices=ENVIRONMENT_CHOICES, default='production')
    custom_domain = models.URLField(null=True, blank=True)
    api_version = models.CharField(max_length=10, default='62.0')
    
    # OAuth tokens (encrypted)
    access_token = models.TextField(null=True, blank=True)
    refresh_token = models.TextField(null=True, blank=True)
    instance_url = models.URLField(null=True, blank=True)
    
    # User info
    salesforce_user_id = models.CharField(max_length=255, null=True, blank=True)
    salesforce_username = models.CharField(max_length=255, null=True, blank=True)
    organization_id = models.CharField(max_length=255, null=True, blank=True)
    organization_name = models.CharField(max_length=255, null=True, blank=True)
    
    # Session management
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'salesforce_connections'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.salesforce_username}@{self.organization_name} ({self.environment})"
    
    def get_encryption_key(self):
        """Generate or get encryption key for this connection"""
        # Use a combination of secret key and connection ID for encryption
        key_material = f"{settings.SECRET_KEY}_{self.id}".encode()
        return base64.urlsafe_b64encode(key_material[:32])
    
    def encrypt_token(self, token):
        """Encrypt a token for storage"""
        if not token:
            return None
        f = Fernet(self.get_encryption_key())
        return f.encrypt(token.encode()).decode()
    
    def decrypt_token(self, encrypted_token):
        """Decrypt a stored token"""
        if not encrypted_token:
            return None
        f = Fernet(self.get_encryption_key())
        return f.decrypt(encrypted_token.encode()).decode()
    
    def set_access_token(self, token):
        """Set encrypted access token"""
        self.access_token = self.encrypt_token(token)
    
    def get_access_token(self):
        """Get decrypted access token"""
        return self.decrypt_token(self.access_token)
    
    def set_refresh_token(self, token):
        """Set encrypted refresh token"""
        self.refresh_token = self.encrypt_token(token)
    
    def get_refresh_token(self):
        """Get decrypted refresh token"""
        return self.decrypt_token(self.refresh_token)
    
    def is_expired(self):
        """Check if the connection has expired"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    def get_soap_endpoint_url(self):
        """Get SOAP API endpoint URL"""
        base_url = self.instance_url or self.server_url
        return f"{base_url}/services/Soap/u/{self.api_version}"
    
    def get_rest_endpoint_url(self):
        """Get REST API endpoint URL"""
        base_url = self.instance_url or self.server_url
        return f"{base_url}/services/data/v{self.api_version}"
    
    def get_bulk_endpoint_url(self):
        """Get Bulk API endpoint URL"""
        base_url = self.instance_url or self.server_url
        return f"{base_url}/services/async/{self.api_version}"
    
    def get_streaming_endpoint_url(self):
        """Get Streaming API endpoint URL"""
        base_url = self.instance_url or self.server_url
        return f"{base_url}/cometd/{self.api_version}"


class WorkbenchSettings(models.Model):
    """Store user-specific Workbench settings"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # Query settings
    default_query_results_format = models.CharField(
        max_length=20, 
        choices=[('table', 'Table'), ('csv', 'CSV'), ('json', 'JSON')], 
        default='table'
    )
    query_timeout = models.IntegerField(default=120)  # seconds
    max_query_results = models.IntegerField(default=2000)
    
    # Data settings
    batch_size = models.IntegerField(default=200)
    enable_rollback_on_error = models.BooleanField(default=True)
    
    # Display settings
    timezone_preference = models.CharField(max_length=50, default='UTC')
    date_format = models.CharField(max_length=20, default='YYYY-MM-DD')
    time_format = models.CharField(max_length=20, default='HH:mm:ss')
    
    # Advanced settings
    api_timeout = models.IntegerField(default=60)
    debug_mode = models.BooleanField(default=False)
    
    # Session data (JSON)
    session_data = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'workbench_settings'
    
    def __str__(self):
        return f"Settings for {self.user.username}"


class AsyncJob(models.Model):
    """Track asynchronous jobs (Bulk API, large queries, etc.)"""
    
    JOB_TYPE_CHOICES = [
        ('bulk_query', 'Bulk Query'),
        ('bulk_insert', 'Bulk Insert'),
        ('bulk_update', 'Bulk Update'),
        ('bulk_upsert', 'Bulk Upsert'),
        ('bulk_delete', 'Bulk Delete'),
        ('metadata_deploy', 'Metadata Deploy'),
        ('metadata_retrieve', 'Metadata Retrieve'),
    ]
    
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('aborted', 'Aborted'),
    ]
    
    connection = models.ForeignKey(SalesforceConnection, on_delete=models.CASCADE)
    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    
    # Job identifiers
    salesforce_job_id = models.CharField(max_length=255, null=True, blank=True)
    celery_task_id = models.CharField(max_length=255, null=True, blank=True)
    
    # Job parameters
    parameters = models.JSONField(default=dict)
    
    # Results
    result_data = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(null=True, blank=True)
    
    # Progress tracking
    records_processed = models.IntegerField(default=0)
    total_records = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'async_jobs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.job_type} - {self.status} ({self.created_at})"
    
    @property
    def progress_percentage(self):
        """Calculate progress percentage"""
        if self.total_records == 0:
            return 0
        return (self.records_processed / self.total_records) * 100
    
    @property
    def duration(self):
        """Calculate job duration"""
        if not self.started_at:
            return None
        end_time = self.completed_at or timezone.now()
        return end_time - self.started_at

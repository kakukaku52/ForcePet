from django.db import models
from django.contrib.auth.models import User
from authentication.models import SalesforceConnection


class SavedQuery(models.Model):
    """Store saved SOQL queries for reuse"""
    
    QUERY_TYPE_CHOICES = [
        ('soql', 'SOQL Query'),
        ('sosl', 'SOSL Search'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    query_text = models.TextField()
    query_type = models.CharField(max_length=10, choices=QUERY_TYPE_CHOICES, default='soql')
    
    # Query parameters
    include_deleted = models.BooleanField(default=False)
    max_results = models.IntegerField(default=2000)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'saved_queries'
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.name} ({self.query_type.upper()})"


class QueryHistory(models.Model):
    """Track query execution history"""
    
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('error', 'Error'),
        ('timeout', 'Timeout'),
    ]
    
    connection = models.ForeignKey(SalesforceConnection, on_delete=models.CASCADE)
    query_text = models.TextField()
    query_type = models.CharField(max_length=10, choices=SavedQuery.QUERY_TYPE_CHOICES, default='soql')
    
    # Execution details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    execution_time = models.FloatField(null=True, blank=True)  # seconds
    record_count = models.IntegerField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    
    # Results metadata
    has_more_results = models.BooleanField(default=False)
    next_records_url = models.TextField(null=True, blank=True)
    
    executed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'query_history'
        ordering = ['-executed_at']
    
    def __str__(self):
        return f"{self.query_type.upper()} - {self.status} ({self.executed_at})"

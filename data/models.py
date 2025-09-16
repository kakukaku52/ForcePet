from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class DataOperation(models.Model):
    """Model to track data operations performed"""
    OPERATION_TYPES = [
        ('INSERT', 'Insert'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('UPSERT', 'Upsert'),
        ('UNDELETE', 'Undelete'),
        ('BULK', 'Bulk Operation'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    operation_type = models.CharField(max_length=20, choices=OPERATION_TYPES)
    sobject = models.CharField(max_length=100)
    record_count = models.IntegerField(default=0)
    success_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['operation_type']),
        ]
    
    def __str__(self):
        return f"{self.operation_type} on {self.sobject} by {self.user.username}"
    
    @property
    def success_rate(self):
        if self.record_count == 0:
            return 0
        return (self.success_count / self.record_count) * 100

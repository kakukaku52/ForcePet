from django.contrib import admin
from .models import SalesforceConnection, WorkbenchSettings, AsyncJob


@admin.register(SalesforceConnection)
class SalesforceConnectionAdmin(admin.ModelAdmin):
    list_display = ('salesforce_username', 'organization_name', 'environment', 'login_type', 'is_active', 'created_at')
    list_filter = ('environment', 'login_type', 'is_active', 'created_at')
    search_fields = ('salesforce_username', 'organization_name', 'organization_id')
    readonly_fields = ('session_id', 'access_token', 'refresh_token', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Connection Info', {
            'fields': ('user', 'session_id', 'server_url', 'instance_url')
        }),
        ('Authentication', {
            'fields': ('login_type', 'environment', 'custom_domain', 'api_version')
        }),
        ('User Details', {
            'fields': ('salesforce_user_id', 'salesforce_username', 'organization_id', 'organization_name')
        }),
        ('Session Management', {
            'fields': ('is_active', 'expires_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Tokens', {
            'fields': ('access_token', 'refresh_token'),
            'classes': ('collapse',)
        })
    )


@admin.register(WorkbenchSettings)
class WorkbenchSettingsAdmin(admin.ModelAdmin):
    list_display = ('user', 'default_query_results_format', 'query_timeout', 'batch_size', 'debug_mode')
    list_filter = ('default_query_results_format', 'debug_mode', 'enable_rollback_on_error')
    search_fields = ('user__username', 'user__email')
    
    fieldsets = (
        ('Query Settings', {
            'fields': ('default_query_results_format', 'query_timeout', 'max_query_results')
        }),
        ('Data Settings', {
            'fields': ('batch_size', 'enable_rollback_on_error')
        }),
        ('Display Settings', {
            'fields': ('timezone_preference', 'date_format', 'time_format')
        }),
        ('Advanced Settings', {
            'fields': ('api_timeout', 'debug_mode'),
            'classes': ('collapse',)
        })
    )


@admin.register(AsyncJob)
class AsyncJobAdmin(admin.ModelAdmin):
    list_display = ('job_type', 'status', 'connection', 'progress_percentage', 'created_at')
    list_filter = ('job_type', 'status', 'created_at')
    search_fields = ('salesforce_job_id', 'celery_task_id', 'connection__salesforce_username')
    readonly_fields = ('created_at', 'started_at', 'completed_at', 'duration')
    
    fieldsets = (
        ('Job Info', {
            'fields': ('connection', 'job_type', 'status')
        }),
        ('Identifiers', {
            'fields': ('salesforce_job_id', 'celery_task_id')
        }),
        ('Progress', {
            'fields': ('records_processed', 'total_records')
        }),
        ('Timing', {
            'fields': ('created_at', 'started_at', 'completed_at'),
            'classes': ('collapse',)
        }),
        ('Results', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        })
    )
    
    def progress_percentage(self, obj):
        return f"{obj.progress_percentage:.1f}%"
    progress_percentage.short_description = 'Progress'

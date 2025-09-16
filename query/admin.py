from django.contrib import admin
from .models import SavedQuery, QueryHistory


@admin.register(SavedQuery)
class SavedQueryAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'query_type', 'created_at', 'updated_at')
    list_filter = ('query_type', 'created_at', 'updated_at')
    search_fields = ('name', 'description', 'query_text', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Query Info', {
            'fields': ('user', 'name', 'description', 'query_type')
        }),
        ('Query Details', {
            'fields': ('query_text', 'include_deleted', 'max_results')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(QueryHistory)
class QueryHistoryAdmin(admin.ModelAdmin):
    list_display = ('query_type', 'status', 'connection', 'record_count', 'execution_time', 'executed_at')
    list_filter = ('query_type', 'status', 'executed_at')
    search_fields = ('query_text', 'connection__username', 'error_message')
    readonly_fields = ('executed_at',)
    
    fieldsets = (
        ('Query Info', {
            'fields': ('connection', 'query_type', 'query_text')
        }),
        ('Execution Results', {
            'fields': ('status', 'execution_time', 'record_count', 'error_message')
        }),
        ('Pagination', {
            'fields': ('has_more_results', 'next_records_url'),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('executed_at',)
        })
    )

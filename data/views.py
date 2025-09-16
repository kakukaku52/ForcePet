from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db import transaction
import json
import csv
import io
from authentication.models import SalesforceConnection
from authentication.utils import get_salesforce_client
from .models import DataOperation
from .forms import (
    InsertForm, UpdateForm, DeleteForm, 
    UpsertForm, UndeleteForm, BulkDataForm
)


@login_required
def data_home(request):
    """Data operations home page"""
    recent_operations = DataOperation.objects.filter(
        user=request.user
    ).order_by('-created_at')[:10]
    
    return render(request, 'data/home.html', {
        'recent_operations': recent_operations
    })


@login_required
def insert_view(request):
    """Insert records into Salesforce"""
    if request.method == 'POST':
        form = InsertForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                client = get_salesforce_client(request.user)
                sobject = form.cleaned_data['sobject']
                
                # Handle file upload or direct data
                if request.FILES.get('csv_file'):
                    records = parse_csv_file(request.FILES['csv_file'])
                else:
                    records = json.loads(form.cleaned_data['data'])
                
                # Perform insert
                results = []
                errors = []
                for record in records:
                    try:
                        result = client.sobject(sobject).create(record)
                        results.append(result)
                    except Exception as e:
                        errors.append({'record': record, 'error': str(e)})
                
                # Log operation
                DataOperation.objects.create(
                    user=request.user,
                    operation_type='INSERT',
                    sobject=sobject,
                    record_count=len(records),
                    success_count=len(results),
                    error_count=len(errors),
                    details={
                        'results': results,
                        'errors': errors
                    }
                )
                
                if results:
                    messages.success(request, f'Successfully inserted {len(results)} records')
                if errors:
                    messages.warning(request, f'{len(errors)} records failed to insert')
                    
                return render(request, 'data/operation_results.html', {
                    'operation': 'Insert',
                    'results': results,
                    'errors': errors
                })
                
            except Exception as e:
                messages.error(request, f'Insert operation failed: {str(e)}')
    else:
        form = InsertForm()
    
    return render(request, 'data/insert.html', {'form': form})


@login_required
def update_view(request):
    """Update records in Salesforce"""
    if request.method == 'POST':
        form = UpdateForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                client = get_salesforce_client(request.user)
                sobject = form.cleaned_data['sobject']
                
                # Handle file upload or direct data
                if request.FILES.get('csv_file'):
                    records = parse_csv_file(request.FILES['csv_file'])
                else:
                    records = json.loads(form.cleaned_data['data'])
                
                # Perform update
                results = []
                errors = []
                for record in records:
                    try:
                        record_id = record.pop('Id')
                        result = client.sobject(sobject).update(record_id, record)
                        results.append({'Id': record_id, 'success': True})
                    except Exception as e:
                        errors.append({'record': record, 'error': str(e)})
                
                # Log operation
                DataOperation.objects.create(
                    user=request.user,
                    operation_type='UPDATE',
                    sobject=sobject,
                    record_count=len(records),
                    success_count=len(results),
                    error_count=len(errors),
                    details={
                        'results': results,
                        'errors': errors
                    }
                )
                
                if results:
                    messages.success(request, f'Successfully updated {len(results)} records')
                if errors:
                    messages.warning(request, f'{len(errors)} records failed to update')
                    
                return render(request, 'data/operation_results.html', {
                    'operation': 'Update',
                    'results': results,
                    'errors': errors
                })
                
            except Exception as e:
                messages.error(request, f'Update operation failed: {str(e)}')
    else:
        form = UpdateForm()
    
    return render(request, 'data/update.html', {'form': form})


@login_required
def delete_view(request):
    """Delete records from Salesforce"""
    if request.method == 'POST':
        form = DeleteForm(request.POST)
        if form.is_valid():
            try:
                client = get_salesforce_client(request.user)
                sobject = form.cleaned_data['sobject']
                ids = form.cleaned_data['ids'].split(',')
                
                # Perform delete
                results = []
                errors = []
                for record_id in ids:
                    try:
                        client.sobject(sobject).delete(record_id.strip())
                        results.append({'Id': record_id.strip(), 'success': True})
                    except Exception as e:
                        errors.append({'Id': record_id.strip(), 'error': str(e)})
                
                # Log operation
                DataOperation.objects.create(
                    user=request.user,
                    operation_type='DELETE',
                    sobject=sobject,
                    record_count=len(ids),
                    success_count=len(results),
                    error_count=len(errors),
                    details={
                        'results': results,
                        'errors': errors
                    }
                )
                
                if results:
                    messages.success(request, f'Successfully deleted {len(results)} records')
                if errors:
                    messages.warning(request, f'{len(errors)} records failed to delete')
                    
                return render(request, 'data/operation_results.html', {
                    'operation': 'Delete',
                    'results': results,
                    'errors': errors
                })
                
            except Exception as e:
                messages.error(request, f'Delete operation failed: {str(e)}')
    else:
        form = DeleteForm()
    
    return render(request, 'data/delete.html', {'form': form})


@login_required
def upsert_view(request):
    """Upsert records in Salesforce"""
    if request.method == 'POST':
        form = UpsertForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                client = get_salesforce_client(request.user)
                sobject = form.cleaned_data['sobject']
                external_id_field = form.cleaned_data['external_id_field']
                
                # Handle file upload or direct data
                if request.FILES.get('csv_file'):
                    records = parse_csv_file(request.FILES['csv_file'])
                else:
                    records = json.loads(form.cleaned_data['data'])
                
                # Perform upsert
                results = []
                errors = []
                for record in records:
                    try:
                        external_id = record.get(external_id_field)
                        result = client.sobject(sobject).upsert(
                            external_id_field, 
                            external_id, 
                            record
                        )
                        results.append(result)
                    except Exception as e:
                        errors.append({'record': record, 'error': str(e)})
                
                # Log operation
                DataOperation.objects.create(
                    user=request.user,
                    operation_type='UPSERT',
                    sobject=sobject,
                    record_count=len(records),
                    success_count=len(results),
                    error_count=len(errors),
                    details={
                        'external_id_field': external_id_field,
                        'results': results,
                        'errors': errors
                    }
                )
                
                if results:
                    messages.success(request, f'Successfully upserted {len(results)} records')
                if errors:
                    messages.warning(request, f'{len(errors)} records failed to upsert')
                    
                return render(request, 'data/operation_results.html', {
                    'operation': 'Upsert',
                    'results': results,
                    'errors': errors
                })
                
            except Exception as e:
                messages.error(request, f'Upsert operation failed: {str(e)}')
    else:
        form = UpsertForm()
    
    return render(request, 'data/upsert.html', {'form': form})


@login_required
def undelete_view(request):
    """Undelete records in Salesforce"""
    if request.method == 'POST':
        form = UndeleteForm(request.POST)
        if form.is_valid():
            try:
                client = get_salesforce_client(request.user)
                ids = form.cleaned_data['ids'].split(',')
                
                # Perform undelete
                results = []
                errors = []
                for record_id in ids:
                    try:
                        result = client.undelete(record_id.strip())
                        results.append({'Id': record_id.strip(), 'success': True})
                    except Exception as e:
                        errors.append({'Id': record_id.strip(), 'error': str(e)})
                
                # Log operation
                DataOperation.objects.create(
                    user=request.user,
                    operation_type='UNDELETE',
                    sobject='Multiple',
                    record_count=len(ids),
                    success_count=len(results),
                    error_count=len(errors),
                    details={
                        'results': results,
                        'errors': errors
                    }
                )
                
                if results:
                    messages.success(request, f'Successfully undeleted {len(results)} records')
                if errors:
                    messages.warning(request, f'{len(errors)} records failed to undelete')
                    
                return render(request, 'data/operation_results.html', {
                    'operation': 'Undelete',
                    'results': results,
                    'errors': errors
                })
                
            except Exception as e:
                messages.error(request, f'Undelete operation failed: {str(e)}')
    else:
        form = UndeleteForm()
    
    return render(request, 'data/undelete.html', {'form': form})


def parse_csv_file(file):
    """Parse CSV file and return list of dictionaries"""
    text_file = io.StringIO(file.read().decode('utf-8'))
    reader = csv.DictReader(text_file)
    return list(reader)


@login_required
@require_http_methods(['GET'])
def get_sobject_fields(request):
    """API endpoint to get fields for a specific sobject"""
    sobject = request.GET.get('sobject')
    if not sobject:
        return JsonResponse({'error': 'No sobject specified'}, status=400)
    
    try:
        client = get_salesforce_client(request.user)
        describe = client.sobject(sobject).describe()
        
        fields = [
            {
                'name': field['name'],
                'label': field['label'],
                'type': field['type'],
                'createable': field['createable'],
                'updateable': field['updateable'],
                'required': not field['nillable'] and field['createable']
            }
            for field in describe['fields']
        ]
        
        return JsonResponse({'fields': fields})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

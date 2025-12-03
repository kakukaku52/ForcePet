from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db import transaction
from django.urls import reverse
import json
import csv
import io
from authentication.utils import get_salesforce_client, get_salesforce_connection
from authentication.salesforce_client import SalesforceClient, SalesforceAPIError
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
@require_http_methods(['GET', 'POST'])
def create_record_view(request):
    """Wizard-style view for creating Salesforce records."""
    connection_error = None
    connection = getattr(request, 'sf_connection', None)
    if connection is None:
        try:
            connection = get_salesforce_connection(request.user)
        except Exception as exc:
            connection = None
            connection_error = exc

    sf_client = None
    if connection:
        try:
            sf_client = SalesforceClient(connection)
        except Exception as exc:
            sf_client = None
            connection_error = exc

    if request.method == 'GET':
        sobjects = []
        if sf_client:
            try:
                describe = sf_client.describe_global()
                for obj in describe.get('sobjects', []):
                    api_name = obj.get('name')
                    if not api_name:
                        continue

                    sobjects.append({
                        'name': api_name,
                        'label': obj.get('label') or api_name,
                        'label_plural': obj.get('labelPlural') or obj.get('label') or api_name,
                        'custom': bool(obj.get('custom')),
                        'createable': obj.get('createable', False),
                    })

                sobjects.sort(key=lambda item: (item['label'] or item['name']).lower())
            except SalesforceAPIError as exc:
                messages.error(request, f"加载 Salesforce 对象失败：{exc}")
            except Exception as exc:
                messages.error(request, f"加载 Salesforce 对象失败：{exc}")
        elif connection_error:
            messages.error(request, f"无法连接 Salesforce：{connection_error}")

        context = {
            'sobjects': sobjects,
            'fields_api_url': reverse('data:api_sobject_fields'),
            'insert_post_url': reverse('data:insert'),
        }
        return render(request, 'data/create_record.html', context)

    if not sf_client:
        message = 'Salesforce 会话不可用，请重新登录。'
        if connection_error:
            message = f"Salesforce 会话不可用：{connection_error}"
        return JsonResponse({'success': False, 'message': message}, status=400)

    content_type = request.META.get('CONTENT_TYPE', '')
    if content_type.startswith('application/json'):
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({'success': False, 'message': '请求体格式不合法。'}, status=400)

        mode = payload.get('mode')
        sobject = payload.get('sobject')
        fields = payload.get('fields', [])

        if mode != 'single':
            return JsonResponse({'success': False, 'message': '当前请求模式不支持。'}, status=400)
        if not sobject:
            return JsonResponse({'success': False, 'message': '必须选择 Salesforce 对象。'}, status=400)

        record = {}
        for item in fields:
            field_name = item.get('field') or item.get('name')
            value = item.get('value')
            if field_name and value not in [None, '']:
                record[field_name] = value

        if not record:
            return JsonResponse({'success': False, 'message': '至少需要提供一个字段值。'}, status=400)

        operation_details = {'record': record}
        try:
            result = sf_client.insert(sobject, record)
            operation_details['result'] = result
            DataOperation.objects.create(
                user=request.user,
                operation_type='INSERT',
                sobject=sobject,
                record_count=1,
                success_count=1 if result.get('success', True) else 0,
                error_count=0 if result.get('success', True) else 1,
                details=operation_details,
            )
        except SalesforceAPIError as exc:
            operation_details['error'] = str(exc)
            DataOperation.objects.create(
                user=request.user,
                operation_type='INSERT',
                sobject=sobject,
                record_count=1,
                success_count=0,
                error_count=1,
                details=operation_details,
            )
            return JsonResponse({'success': False, 'message': f'插入失败：{exc}'}, status=400)
        except Exception as exc:
            operation_details['error'] = str(exc)
            DataOperation.objects.create(
                user=request.user,
                operation_type='INSERT',
                sobject=sobject,
                record_count=1,
                success_count=0,
                error_count=1,
                details=operation_details,
            )
            return JsonResponse({'success': False, 'message': f'插入失败：{exc}'}, status=400)

        message = f"成功创建记录（ID: {result.get('id')})" if result.get('id') else "记录创建成功。"
        return JsonResponse({'success': True, 'message': message, 'result': result})

    mode = request.POST.get('mode')
    if mode != 'csv':
        return JsonResponse({'success': False, 'message': '请求模式不受支持。'}, status=400)

    sobject = request.POST.get('sobject')
    if not sobject:
        return JsonResponse({'success': False, 'message': '必须选择 Salesforce 对象。'}, status=400)

    mapping_raw = request.POST.get('mapping')
    if not mapping_raw:
        return JsonResponse({'success': False, 'message': '缺少字段映射数据。'}, status=400)

    try:
        mappings = json.loads(mapping_raw)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': '字段映射数据格式不正确。'}, status=400)

    csv_file = request.FILES.get('csv_file')
    if not csv_file:
        return JsonResponse({'success': False, 'message': '必须上传 CSV 文件。'}, status=400)

    try:
        file_bytes = csv_file.read()
        text_io = io.StringIO(file_bytes.decode('utf-8-sig'))
        reader = csv.DictReader(text_io)
    except Exception as exc:
        return JsonResponse({'success': False, 'message': f'读取 CSV 文件失败：{exc}'}, status=400)

    records = []
    for row in reader:
        record = {}
        for mapping in mappings:
            field_name = mapping.get('field')
            csv_field = mapping.get('csvField')
            if field_name and csv_field:
                record[field_name] = row.get(csv_field)
        if record:
            records.append(record)

    if not records:
        return JsonResponse({'success': False, 'message': '根据映射没有生成任何记录，请检查 CSV 和映射设置。'}, status=400)

    results = []
    errors = []
    for record in records:
        try:
            result = sf_client.insert(sobject, record)
            results.append(result)
        except SalesforceAPIError as exc:
            errors.append({'record': record, 'error': str(exc)})
        except Exception as exc:
            errors.append({'record': record, 'error': str(exc)})

    success_count = len(results)
    error_count = len(errors)

    DataOperation.objects.create(
        user=request.user,
        operation_type='INSERT',
        sobject=sobject,
        record_count=len(records),
        success_count=success_count,
        error_count=error_count,
        details={
            'mappings': mappings,
            'results': results,
            'errors': errors,
        }
    )

    message = f"成功插入 {success_count} 条记录"
    if error_count:
        message += f"，{error_count} 条记录失败"

    status_code = 200 if success_count else 400
    return JsonResponse({
        'success': success_count > 0,
        'message': message,
        'summary': {
            'record_count': len(records),
            'success_count': success_count,
            'error_count': error_count,
        },
        'errors': errors,
    }, status=status_code)


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

    connection = getattr(request, 'sf_connection', None)
    if connection is None:
        try:
            connection = get_salesforce_connection(request.user)
        except Exception as exc:
            return JsonResponse({'error': f'Salesforce 会话不可用：{exc}'}, status=401)

    try:
        client = SalesforceClient(connection)
        describe = client.describe_sobject(sobject)

        fields = []
        for field in describe.get('fields', []):
            fields.append({
                'name': field.get('name'),
                'label': field.get('label'),
                'type': field.get('type'),
                'createable': field.get('createable', False),
                'updateable': field.get('updateable', False),
                'required': not field.get('nillable', True) and field.get('createable', False)
            })

        return JsonResponse({'fields': fields})

    except SalesforceAPIError as exc:
        return JsonResponse({'error': str(exc)}, status=400)
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=500)

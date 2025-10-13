from collections import OrderedDict

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.cache import cache_page
from django.urls import reverse
import json
import time
import csv
import io
import logging

from authentication.salesforce_client import SalesforceClient, SalesforceAPIError
from authentication.models import SalesforceConnection
from .models import SavedQuery, QueryHistory
from .forms import QueryForm, SavedQueryForm, SearchForm

logger = logging.getLogger('workbench')


class QueryIndexView(View):
    """
    Main SOQL query interface
    """
    template_name = 'query/index.html'
    
    def get(self, request):
        """Display query form"""
        form = QueryForm()
        
        # Get recent queries for this user
        recent_queries = QueryHistory.objects.filter(
            connection__user=request.user
        )[:10]

        # Get saved queries
        saved_queries = SavedQuery.objects.filter(
            user=request.user,
            query_type='soql'
        )[:10]

        # Check if user has active Salesforce connection
        has_sf_connection = False
        if hasattr(request, 'sf_connection'):
            has_sf_connection = True
        elif request.user.is_authenticated:
            # Try to find an active connection
            connection = SalesforceConnection.objects.filter(
                user=request.user,
                is_active=True
            ).first()
            has_sf_connection = connection is not None

        # Preload Salesforce objects for the selector when a connection is available.
        available_objects = {
            'standard': [],
            'custom': [],
        }
        if has_sf_connection:
            try:
                connection = getattr(request, 'sf_connection', None)
                if connection is None and request.user.is_authenticated:
                    connection = SalesforceConnection.objects.filter(
                        user=request.user,
                        is_active=True
                    ).order_by('-updated_at').first()

                if connection:
                    client = SalesforceClient(connection)
                    describe_result = client.describe_global()

                    for sobject in describe_result.get('sobjects', []):
                        if not sobject.get('queryable'):
                            continue

                        obj_data = {
                            'name': sobject.get('name'),
                            'label': sobject.get('label'),
                            'custom': sobject.get('custom', False),
                        }

                        if obj_data['custom']:
                            available_objects['custom'].append(obj_data)
                        else:
                            available_objects['standard'].append(obj_data)

                    available_objects['standard'].sort(key=lambda x: x['label'])
                    available_objects['custom'].sort(key=lambda x: x['label'])
            except SalesforceAPIError as exc:
                logger.warning("Failed to preload Salesforce objects: %s", exc)

        context = {
            'form': form,
            'recent_queries': recent_queries,
            'saved_queries': saved_queries,
            'has_sf_connection': has_sf_connection,
            'available_objects': available_objects,
            'has_initial_objects': bool(available_objects['standard'] or available_objects['custom']),
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        """Execute SOQL query"""
        form = QueryForm(request.POST)
        if not form.is_valid():
            messages.error(request, '入力内容のエラーを修正してください。')
            return self.get(request)
        
        try:
            client = SalesforceClient(request.sf_connection)
            query_text = form.cleaned_data['query']
            include_deleted = form.cleaned_data.get('include_deleted', False)
            
            # Start timing
            start_time = time.time()
            
            # Execute query
            result = client.query(query_text, include_deleted=include_deleted)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Save to history
            history = QueryHistory.objects.create(
                connection=request.sf_connection,
                query_text=query_text,
                query_type='soql',
                status='success',
                execution_time=execution_time,
                record_count=result.get('totalSize', 0),
                has_more_results=not result.get('done', True),
                next_records_url=result.get('nextRecordsUrl', None)
            )
            
            # Extract object type from query (for ID links)
            object_type = None
            if result.get('records') and len(result['records']) > 0:
                # Get object type from attributes if available
                if 'attributes' in result['records'][0]:
                    object_type = result['records'][0]['attributes'].get('type')

                # If not, try to parse from query
                if not object_type:
                    import re
                    match = re.search(r'FROM\s+(\w+)', query_text, re.IGNORECASE)
                    if match:
                        object_type = match.group(1)

            # Process results for display
            results_data = {
                'totalSize': result.get('totalSize', 0),
                'done': result.get('done', True),
                'records': result.get('records', []),
                'nextRecordsUrl': result.get('nextRecordsUrl', None),
                'execution_time': execution_time,
                'history_id': history.id,
                'object_type': object_type
            }

            context = {
                'form': form,
                'results': results_data,
                'query_executed': True,
            }
            
            messages.success(
                request,
                f'クエリが正常に完了しました。{results_data["totalSize"]} 件を {execution_time:.2f} 秒で取得しました。'
            )
            
            return render(request, self.template_name, context)
            
        except SalesforceAPIError as e:
            # Save error to history
            QueryHistory.objects.create(
                connection=request.sf_connection,
                query_text=form.cleaned_data['query'],
                query_type='soql',
                status='error',
                error_message=str(e)
            )
            
            logger.error(f"Query execution failed: {e}")
            messages.error(request, f'クエリに失敗しました: {str(e)}')
            return self.get(request)


class SearchView(View):
    """SOSL search interface."""

    template_name = 'query/search.html'
    SAMPLE_QUERIES = [
        'FIND {Acme} IN ALL FIELDS RETURNING Account(Id, Name), Contact(Id, Name)',
        'FIND {"Tom"} IN NAME FIELDS RETURNING Contact(Id, FirstName, LastName), Lead(Id, Name)',
        'FIND {Partner} IN ALL FIELDS RETURNING Opportunity(Id, Name, StageName)',
    ]

    def _get_sidebar_data(self, request):
        recent = QueryHistory.objects.filter(
            connection__user=request.user,
            query_type='sosl'
        ).order_by('-executed_at')[:10]

        saved = SavedQuery.objects.filter(
            user=request.user,
            query_type='sosl'
        ).order_by('-updated_at')[:10]
        return recent, saved

    def _build_context(self, request, form, *, grouped_results=None, summary=None, history=None):
        recent, saved = self._get_sidebar_data(request)
        instance_url = ''
        connection = getattr(request, 'sf_connection', None)
        if connection is not None:
            instance_url = getattr(connection, 'instance_url', '')

        context = {
            'form': form,
            'recent_searches': recent,
            'saved_searches': saved,
            'search_executed': grouped_results is not None,
            'grouped_results': grouped_results or [],
            'search_summary': summary,
            'history': history,
            'sample_queries': self.SAMPLE_QUERIES,
            'instance_url': instance_url,
        }
        return context

    def _group_results(self, raw_results):
        grouped = OrderedDict()

        for record in raw_results or []:
            if not isinstance(record, dict):
                continue
            attributes = record.get('attributes') or {}
            obj_type = attributes.get('type') or 'Unknown'
            grouped.setdefault(obj_type, []).append(record)

        grouped_results = []
        for obj_type, records in grouped.items():
            field_names = []
            for record in records:
                for field in record.keys():
                    if field == 'attributes':
                        continue
                    if field not in field_names:
                        field_names.append(field)

            rows = []
            for record in records:
                attributes = record.get('attributes') or {}
                record_id = record.get('Id') or record.get('id')
                record_url = attributes.get('url')

                cells = []
                for field in field_names:
                    value = record.get(field)
                    link = record_url if field.lower() == 'id' and record_url else None
                    cells.append({
                        'field': field,
                        'value': value,
                        'link': link,
                    })

                rows.append({
                    'record': record,
                    'cells': cells,
                    'record_id': record_id,
                    'record_url': record_url,
                })

            grouped_results.append({
                'object_type': obj_type,
                'field_names': field_names,
                'rows': rows,
                'count': len(records),
            })

        return grouped_results

    def get(self, request):
        form = SearchForm()
        context = self._build_context(request, form)
        return render(request, self.template_name, context)

    def post(self, request):
        form = SearchForm(request.POST)
        if not form.is_valid():
            messages.error(request, '入力内容のエラーを修正してください。')
            return self.get(request)

        search_text = form.cleaned_data['search_query']

        try:
            client = SalesforceClient(request.sf_connection)
        except AttributeError:
            messages.error(request, '有効な Salesforce 接続がありません。先に認証してください。')
            return self.get(request)

        try:
            start_time = time.time()
            raw_results = client.search(search_text) or []
            execution_time = time.time() - start_time
            total_records = sum(1 for record in raw_results if isinstance(record, dict))

            history = QueryHistory.objects.create(
                connection=request.sf_connection,
                query_text=search_text,
                query_type='sosl',
                status='success',
                execution_time=execution_time,
                record_count=total_records
            )

            grouped_results = self._group_results(raw_results)

            summary = {
                'total_records': total_records,
                'execution_time': execution_time,
                'query_text': search_text,
                'history_id': history.id,
            }

            messages.success(
                request,
                f'検索が完了しました。{total_records} 件を {execution_time:.2f} 秒で取得しました。'
            )

            context = self._build_context(
                request,
                form,
                grouped_results=grouped_results,
                summary=summary,
                history=history,
            )
            return render(request, self.template_name, context)

        except SalesforceAPIError as exc:
            QueryHistory.objects.create(
                connection=request.sf_connection,
                query_text=search_text,
                query_type='sosl',
                status='error',
                error_message=str(exc)
            )

            logger.error(f"Search execution failed: {exc}")
            messages.error(request, f'検索に失敗しました: {exc}')
            return self.get(request)


@require_http_methods(["GET"])
def query_more(request):
    """
    Get more query results using nextRecordsUrl
    """
    next_url = request.GET.get('nextRecordsUrl')
    if not next_url:
        return JsonResponse({'error': 'nextRecordsUrl パラメータが指定されていません'}, status=400)

    try:
        client = SalesforceClient(request.sf_connection)
        result = client.query_more(next_url)

        # Extract object type from records
        object_type = None
        if result.get('records') and len(result['records']) > 0:
            if 'attributes' in result['records'][0]:
                object_type = result['records'][0]['attributes'].get('type')

        return JsonResponse({
            'success': True,
            'records': result.get('records', []),
            'done': result.get('done', True),
            'nextRecordsUrl': result.get('nextRecordsUrl', None),
            'object_type': object_type
        })

    except SalesforceAPIError as e:
        logger.error(f"Query more failed: {e}")
        return JsonResponse({'error': str(e)}, status=500)


class ExportResultsView(View):
    """
    Export query results in various formats
    """
    
    def get(self, request, history_id):
        """Export query results"""
        history = get_object_or_404(QueryHistory, id=history_id, connection__user=request.user)
        format_type = request.GET.get('format', 'csv').lower()
        
        if history.status != 'success':
            messages.error(request, '失敗したクエリの結果はエクスポートできません。')
            return redirect('query:index')
        
        try:
            # Re-execute the query to get fresh results
            client = SalesforceClient(request.sf_connection)
            
            if history.query_type == 'soql':
                result = client.query(history.query_text)
                records = result.get('records', [])
            else:  # sosl
                result = client.search(history.query_text)
                # Flatten SOSL results
                records = []
                for object_records in result:
                    records.extend(object_records)
            
            if format_type == 'csv':
                return self._export_csv(records, history)
            elif format_type == 'json':
                return self._export_json(records, history)
            else:
                messages.error(request, f'未対応のエクスポート形式です: {format_type}')
                return redirect('query:index')
                
        except SalesforceAPIError as e:
            logger.error(f"Export failed: {e}")
            messages.error(request, f'エクスポートに失敗しました: {str(e)}')
            return redirect('query:index')
    
    def _export_csv(self, records, history):
        """Export as CSV"""
        if not records:
            response = HttpResponse('No records to export', content_type='text/plain')
            return response

        # Create CSV
        output = io.StringIO()

        # Get field names from first record, excluding 'attributes'
        fieldnames = [key for key in records[0].keys() if key != 'attributes'] if records else []

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for record in records:
            # Clean the record (remove None values, handle nested objects, exclude attributes)
            clean_record = {}
            for key, value in record.items():
                if key == 'attributes':
                    continue  # Skip attributes field
                if isinstance(value, dict):
                    clean_record[key] = json.dumps(value)
                elif value is None:
                    clean_record[key] = ''
                else:
                    clean_record[key] = str(value)

            writer.writerow(clean_record)
        
        # Create response
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{history.query_type}_results_{history.id}.csv"'
        
        return response
    
    def _export_json(self, records, history):
        """Export as JSON"""
        # Filter out attributes field from each record
        cleaned_records = []
        for record in records:
            cleaned_record = {k: v for k, v in record.items() if k != 'attributes'}
            cleaned_records.append(cleaned_record)

        response_data = {
            'query': history.query_text,
            'executed_at': history.executed_at.isoformat(),
            'record_count': len(cleaned_records),
            'records': cleaned_records
        }
        
        response = HttpResponse(
            json.dumps(response_data, indent=2, default=str),
            content_type='application/json'
        )
        response['Content-Disposition'] = f'attachment; filename="{history.query_type}_results_{history.id}.json"'
        
        return response


class SavedQueryView(View):
    """
    Manage saved queries
    """
    template_name = 'query/saved_queries.html'
    
    def get(self, request):
        """Display saved queries"""
        queries = SavedQuery.objects.filter(user=request.user)
        
        # Paginate results
        paginator = Paginator(queries, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'queries': page_obj,
            'form': SavedQueryForm()
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        """Save a new query"""
        form = SavedQueryForm(request.POST)
        if form.is_valid():
            saved_query = form.save(commit=False)
            saved_query.user = request.user
            saved_query.save()
            
            messages.success(request, f'クエリ「{saved_query.name}」を保存しました。')
            return redirect('query:saved_queries')
        
        # If form is invalid, redisplay with errors
        queries = SavedQuery.objects.filter(user=request.user)
        paginator = Paginator(queries, 20)
        page_obj = paginator.get_page(1)
        
        context = {
            'queries': page_obj,
            'form': form
        }
        return render(request, self.template_name, context)


@require_http_methods(["POST"])
def delete_saved_query(request, query_id):
    """Delete a saved query"""
    query = get_object_or_404(SavedQuery, id=query_id, user=request.user)
    query_name = query.name
    query.delete()
    
    messages.success(request, f'クエリ「{query_name}」を削除しました。')
    return redirect('query:saved_queries')


@require_http_methods(["GET"])
def load_saved_query(request, query_id):
    """Load a saved query into the query interface"""
    query = get_object_or_404(SavedQuery, id=query_id, user=request.user)
    
    if query.query_type == 'soql':
        return redirect(f'/query/?q={query.id}')
    else:
        return redirect(f'/query/search/?q={query.id}')


class QueryHistoryView(View):
    """
    Display query execution history
    """
    template_name = 'query/history.html'
    
    def get(self, request):
        """Display query history"""
        history = QueryHistory.objects.filter(connection__user=request.user)
        
        # Filter by query type if specified
        query_type = request.GET.get('type')
        if query_type in ['soql', 'sosl']:
            history = history.filter(query_type=query_type)
        
        # Filter by status if specified
        status = request.GET.get('status')
        if status in ['success', 'error', 'timeout']:
            history = history.filter(status=status)
        
        # Paginate results
        paginator = Paginator(history, 50)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'history': page_obj,
            'query_type_filter': query_type,
            'status_filter': status,
        }
        return render(request, self.template_name, context)


@require_http_methods(["GET"])
def get_objects(request):
    """Get all Salesforce objects for the dropdown"""
    try:
        logger.info("Loading Salesforce objects for user=%s", request.user if request.user.is_authenticated else 'anonymous')
        # Prefer middleware provided connection. If missing, try to recover from session/user.
        connection = getattr(request, 'sf_connection', None)
        if connection is None:
            connection_id = request.session.get('sf_connection_id')
            if connection_id:
                connection = SalesforceConnection.objects.filter(
                    id=connection_id,
                    is_active=True
                ).first()

        if connection is None and request.user.is_authenticated:
            connection = SalesforceConnection.objects.filter(
                user=request.user,
                is_active=True
            ).order_by('-updated_at').first()

        if connection is None:
            return JsonResponse({
                'success': False,
                'error': '有効な Salesforce 接続が見つかりません。Salesforce にログインしてください。'
            }, status=401)

        # Attach for downstream use to keep behaviour consistent with middleware
        request.sf_connection = connection

        client = SalesforceClient(connection)
        describe_result = client.describe_global()

        # Extract object information
        objects = []
        for sobject in describe_result.get('sobjects', []):
            # Only include queryable objects
            if sobject.get('queryable'):
                objects.append({
                    'name': sobject.get('name'),
                    'label': sobject.get('label'),
                    'custom': sobject.get('custom', False),
                    'keyPrefix': sobject.get('keyPrefix', ''),
                })

        # Sort objects by label
        objects.sort(key=lambda x: x['label'])

        return JsonResponse({
            'success': True,
            'objects': objects
        })

    except SalesforceAPIError as e:
        logger.error(f"Failed to get objects: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
    except Exception as e:
        logger.error(f"Unexpected error in get_objects: {e}")
        return JsonResponse({
            'success': False,
            'error': f"An unexpected error occurred: {str(e)}"
        }, status=500)


@require_http_methods(["GET"])
def get_object_fields(request):
    """Get fields for a specific Salesforce object"""
    object_name = request.GET.get('object')
    if not object_name:
        return JsonResponse({'error': 'Object name is required'}, status=400)

    try:
        logger.info("Loading fields for object=%s user=%s", object_name, request.user if request.user.is_authenticated else 'anonymous')
        connection = getattr(request, 'sf_connection', None)
        if connection is None:
            connection_id = request.session.get('sf_connection_id')
            if connection_id:
                connection = SalesforceConnection.objects.filter(
                    id=connection_id,
                    is_active=True
                ).first()

        if connection is None and request.user.is_authenticated:
            connection = SalesforceConnection.objects.filter(
                user=request.user,
                is_active=True
            ).order_by('-updated_at').first()

        if connection is None:
            return JsonResponse({
                'success': False,
                'error': '有効な Salesforce 接続が見つかりません。Salesforce にログインしてください。'
            }, status=401)

        request.sf_connection = connection

        client = SalesforceClient(connection)
        describe_result = client.describe_sobject(object_name)

        # Extract field information
        fields = []
        for field in describe_result.get('fields', []):
            fields.append({
                'name': field.get('name'),
                'label': field.get('label'),
                'type': field.get('type'),
                'length': field.get('length'),
                'relationshipName': field.get('relationshipName'),
                'referenceTo': field.get('referenceTo'),
                'custom': field.get('custom', False),
                'filterable': field.get('filterable', False),
                'sortable': field.get('sortable', False),
                'groupable': field.get('groupable', False),
                'createable': field.get('createable', False),
                'updateable': field.get('updateable', False),
                'nillable': field.get('nillable', False),
            })

        # Sort fields by label
        fields.sort(key=lambda x: x['label'])

        return JsonResponse({
            'success': True,
            'object': object_name,
            'fields': fields,
            'childRelationships': describe_result.get('childRelationships', []),
            'recordTypeInfos': describe_result.get('recordTypeInfos', [])
        })


    except SalesforceAPIError as e:
        logger.error(f"Failed to get fields for {object_name}: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def record_detail(request, object_type, record_id):
    """Display detailed view of a single record"""
    try:
        # Get Salesforce client
        client = SalesforceClient(request.sf_connection)

        # Get object describe to get all field information
        describe_result = client.describe_object(object_type)

        # Build query with all fields
        field_names = [field['name'] for field in describe_result.get('fields', [])]
        query = f"SELECT {', '.join(field_names)} FROM {object_type} WHERE Id = '{record_id}'"

        # Execute query
        result = client.query(query)

        if not result.get('records'):
            messages.error(request, f'レコード {record_id} が見つかりません。')
            return redirect('query:index')

        record = result['records'][0]

        # Prepare field information with values
        fields_with_values = []
        for field in describe_result.get('fields', []):
            field_info = {
                'label': field.get('label'),
                'name': field.get('name'),
                'type': field.get('type'),
                'value': record.get(field['name']),
                'updateable': field.get('updateable', False),
                'createable': field.get('createable', False),
                'length': field.get('length'),
                'precision': field.get('precision'),
                'scale': field.get('scale'),
                'referenceTo': field.get('referenceTo'),
                'picklistValues': field.get('picklistValues', []),
                'nillable': field.get('nillable', False),
                'calculated': field.get('calculated', False),
                'custom': field.get('custom', False),
            }
            fields_with_values.append(field_info)

        # Sort fields by creation order (system fields first, then custom)
        fields_with_values.sort(key=lambda x: (x['custom'], x['name']))

        context = {
            'object_type': object_type,
            'record_id': record_id,
            'record': record,
            'fields': fields_with_values,
            'org_instance': request.sf_connection.instance_url,
        }

        return render(request, 'query/record_detail.html', context)

    except Exception as e:
        logger.error(f"Failed to load record detail: {e}")
        messages.error(request, f'レコードの読み込みに失敗しました: {str(e)}')
        return redirect('query:index')


@login_required
@require_http_methods(["POST"])
def update_record(request, object_type, record_id):
    """Update a Salesforce record"""
    try:
        client = SalesforceClient(request.sf_connection)

        # Get the update data from request
        update_data = {}
        for key, value in request.POST.items():
            if key not in ['csrfmiddlewaretoken', 'object_type', 'record_id']:
                # Convert empty strings to None for null values
                if value == '':
                    update_data[key] = None
                else:
                    update_data[key] = value

        # Update the record
        client.update_record(object_type, record_id, update_data)

        messages.success(request, f'レコード {record_id} を更新しました。')
        return JsonResponse({'success': True})

    except Exception as e:
        logger.error(f"Failed to update record: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def delete_record(request, object_type, record_id):
    """Delete a Salesforce record"""
    try:
        client = SalesforceClient(request.sf_connection)

        # Delete the record
        client.delete_record(object_type, record_id)

        messages.success(request, f'レコード {record_id} を削除しました。')
        return JsonResponse({
            'success': True,
            'redirect_url': reverse('query:index')
        })

    except Exception as e:
        logger.error(f"Failed to delete record: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def test_objects_view(request):
    """Test view for debugging Salesforce objects loading"""
    return render(request, 'query/test_objects.html')


def test_api_view(request):
    """Test view for debugging API calls"""
    return render(request, 'query/test_api.html')

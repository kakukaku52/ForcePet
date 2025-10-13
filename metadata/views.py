import datetime
from typing import Any, Dict, List, Sequence
from urllib.parse import unquote, urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import reverse

from authentication.salesforce_client import SalesforceAPIError, SalesforceClient

from .forms import ListMetadataForm


def _serialize_value(value: Any) -> Any:
    """Recursively convert Salesforce response values for display."""
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [_serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize_value(val) for key, val in value.items()}
    return value


def _determine_display_columns(records: Sequence[Dict[str, Any]]) -> List[str]:
    """Infer sensible display columns when the API does not supply them."""
    if not records:
        return []

    preferred_order = [
        "Label",
        "QualifiedApiName",
        "DeveloperName",
        "Name",
        "FullName",
        "NamespacePrefix",
        "LastModifiedDate",
        "CreatedDate",
    ]

    first_row = records[0]
    keys = [key for key in first_row.keys() if key != "attributes"]

    ordered = [key for key in preferred_order if key in keys]
    ordered.extend(key for key in keys if key not in ordered)
    return ordered


def _determine_label_map(columns: Sequence[str]) -> List[str]:
    """Provide Japanese labels for common Salesforce metadata columns."""
    column_label_map = {
        "Id": "ID",
        "DurableId": "Durable ID",
        "Label": "ラベル",
        "QualifiedApiName": "修飾 API 名",
        "DeveloperName": "開発者名",
        "Name": "名前",
        "FullName": "完全名",
        "NamespacePrefix": "名前空間",
        "LastModifiedDate": "最終更新日",
        "CreatedDate": "作成日",
        "ApiVersion": "API バージョン",
        "Status": "ステータス",
        "MasterLabel": "表示ラベル",
        "PluralLabel": "複数形ラベル",
        "IsQueryable": "SOQL 参照可",
        "IsCustomizable": "カスタマイズ可",
        "LengthWithoutComments": "コメント除く長さ",
        "TableEnumOrId": "対象オブジェクト/ID",
    }
    return [column_label_map.get(column, column) for column in columns]


def _to_18_char_id(sf_id: str | None) -> str | None:
    """Convert 15-character Salesforce ID to 18-character case-safe ID."""
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


def _prepare_org_summary(client: SalesforceClient) -> Dict[str, Any]:
    """Build organisation level snapshot for the hero section."""
    describe_global = client.describe_global()
    sobjects = describe_global.get("sobjects", [])
    custom_objects = [obj for obj in sobjects if obj.get("custom")]
    standard_objects = [obj for obj in sobjects if not obj.get("custom")]

    def _object_display(obj):
        return obj.get("label") or obj.get("name")

    return {
        "summary": {
            "total_objects": len(sobjects),
            "custom_objects": len(custom_objects),
            "standard_objects": len(standard_objects),
            "queryable_objects": sum(1 for obj in sobjects if obj.get("queryable")),
            "searchable_objects": sum(1 for obj in sobjects if obj.get("searchable")),
            "layoutable_objects": sum(1 for obj in sobjects if obj.get("layoutable")),
        },
        "custom_preview": sorted(custom_objects, key=_object_display)[:8],
        "standard_preview": sorted(
            (obj for obj in standard_objects if obj.get("custom") is False),
            key=_object_display,
        )[:8],
    }


@login_required
def metadata_home(request):
    """Render the Metadata workspace landing page."""

    connection = getattr(request, "sf_connection", None)
    list_form = ListMetadataForm(prefix="list")

    metadata_records: List[Dict[str, Any]] = []
    metadata_rows: List[List[Any]] = []
    metadata_columns: List[str] = []
    metadata_column_labels: List[str] = []
    metadata_table_rows: List[Dict[str, Any]] = []
    metadata_selected_type = None
    metadata_selected_type_label = None
    metadata_result_info = None
    metadata_error = None
    metadata_name_filter = ""
    metadata_tree: List[Dict[str, Any]] = []
    org_summary = None
    custom_objects_preview: List[Dict[str, Any]] = []
    standard_objects_preview: List[Dict[str, Any]] = []

    quick_actions = [
        {
            "title": "メタデータエクスプローラ",
            "description": "Tooling API を活用してコンポーネントを検索し、詳細を確認します。",
            "icon": "fa-list-check",
            "target": "#metadata-explorer",
            "disabled": False,
        },
        {
            "title": "パッケージ取得",
            "description": "ソース管理やレビュー用にメタデータバンドルをダウンロードします。",
            "icon": "fa-download",
            "target": None,
            "disabled": True,
            "badge": "準備中",
        },
        {
            "title": "変更のデプロイ",
            "description": "パッケージ XML の変更を検証し、組織へデプロイします。",
            "icon": "fa-rocket",
            "target": None,
            "disabled": True,
            "badge": "準備中",
        },
    ]

    if not connection:
        messages.error(
            request,
            "Salesforce への接続が有効ではありません。認証してからメタデータツールをご利用ください。",
        )
        return render(
            request,
            "metadata/home.html",
            {
                "needs_connection": True,
                "quick_actions": quick_actions,
                "list_form": list_form,
            },
        )

    client = SalesforceClient(connection)

    try:
        org_snapshot = _prepare_org_summary(client)
        org_summary = org_snapshot["summary"]
        custom_objects_preview = org_snapshot["custom_preview"]
        standard_objects_preview = org_snapshot["standard_preview"]
    except SalesforceAPIError as exc:
        messages.warning(request, f"組織のオブジェクト概要を読み込めませんでした: {exc}")

    def perform_query(bound_form: ListMetadataForm) -> None:
        nonlocal metadata_records, metadata_rows, metadata_columns, metadata_column_labels
        nonlocal metadata_table_rows, metadata_selected_type, metadata_selected_type_label
        nonlocal metadata_result_info, metadata_error, metadata_name_filter, metadata_tree

        metadata_selected_type = bound_form.cleaned_data["metadata_type"]
        metadata_selected_type_label = bound_form.get_choice_label(metadata_selected_type)
        metadata_name_filter = bound_form.cleaned_data.get("name_filter") or ""

        if metadata_selected_type == 'CustomField':
            try:
                base_tree = client.get_custom_field_tree(metadata_name_filter or None)
            except SalesforceAPIError as exc:
                metadata_error = str(exc)
                return

            metadata_error = None
            metadata_tree = []
            total_fields = 0
            return_params = {"initial_type": metadata_selected_type}
            if metadata_name_filter:
                return_params["initial_name"] = metadata_name_filter

            for node in base_tree:
                enriched_fields = []
                for field in node['fields']:
                    total_fields += 1
                    detail_params = return_params.copy()
                    detail_params["apiName"] = field['full_name']
                    detail_path = reverse(
                        "metadata:detail",
                        kwargs={
                            "metadata_type": 'CustomField',
                            "identifier": 'lookup',
                        },
                    )
                    detail_url = detail_path
                    if detail_params:
                        detail_url = f"{detail_path}?{urlencode(detail_params)}"

                    enriched_fields.append(
                        {
                            **field,
                            'detail_url': detail_url,
                        }
                    )

                metadata_tree.append(
                    {
                        'object_api_name': node['object_api_name'],
                        'object_label': node['object_label'],
                        'fields': enriched_fields,
                    }
                )

            metadata_records = []
            metadata_rows = []
            metadata_columns = []
            metadata_column_labels = []
            metadata_table_rows = []
            metadata_result_info = {
                "total_size": total_fields,
                "done": True,
                "size_returned": total_fields,
            }
            return

        try:
            metadata_payload = client.list_metadata(
                metadata_selected_type,
                name_filter=metadata_name_filter,
                limit=None,
            )
        except SalesforceAPIError as exc:
            metadata_error = str(exc)
            return

        metadata_error = None
        metadata_records = metadata_payload.get("records", [])
        metadata_columns = metadata_payload.get("columns") or _determine_display_columns(metadata_records)
        metadata_column_labels = _determine_label_map(metadata_columns)
        metadata_result_info = {
            "total_size": metadata_payload.get("totalSize", len(metadata_records)),
            "done": metadata_payload.get("done", True),
            "size_returned": len(metadata_records),
        }

        metadata_id_field = metadata_payload.get("id_field", "Id")
        metadata_rows = []
        metadata_table_rows = []

        return_params = {"initial_type": metadata_selected_type}
        if metadata_name_filter:
            return_params["initial_name"] = metadata_name_filter

        for record in metadata_records:
            label_value = (
                record.get("Label")
                or record.get("DeveloperName")
                or record.get("Name")
                or record.get("FullName")
                or record.get("QualifiedApiName")
            )
            api_name_value = (
                record.get("QualifiedApiName")
                or record.get("FullName")
                or record.get("DeveloperName")
                or record.get("Name")
                or label_value
            )
            record_identifier = _to_18_char_id(
                record.get("Id")
                or record.get(metadata_id_field)
                or record.get("DurableId")
            )

            row_values = [record.get(column) for column in metadata_columns]
            if row_values:
                row_values[0] = label_value
            metadata_rows.append(row_values)

            identifier_for_url = record_identifier or "lookup"
            detail_path = reverse(
                "metadata:detail",
                kwargs={
                    "metadata_type": metadata_selected_type,
                    "identifier": identifier_for_url,
                },
            )
            detail_params = return_params.copy()
            if api_name_value:
                detail_params["apiName"] = api_name_value

            detail_url = detail_path
            if detail_params:
                detail_url = f"{detail_path}?{urlencode(detail_params)}"

            metadata_table_rows.append(
                {
                    "values": row_values,
                    "label": label_value,
                    "detail_url": detail_url,
                }
            )

    # Handle auto-refresh via query parameters when returning from detail page.
    if request.method == "GET":

        initial_type = request.GET.get("initial_type")
        initial_name = request.GET.get("initial_name")

        if initial_type:
            bound_data = {
                "list-metadata_type": initial_type,
                "list-name_filter": initial_name or "",
            }
            bound_form = ListMetadataForm(bound_data, prefix="list")
            if bound_form.is_valid():
                list_form = bound_form
                perform_query(bound_form)
            else:
                list_form = ListMetadataForm(prefix="list")
                metadata_error = "検索条件の復元に失敗しました。再度検索を実行してください。"

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "list":
            list_form = ListMetadataForm(request.POST, prefix="list")
            if list_form.is_valid():
                perform_query(list_form)
            else:
                metadata_error = "メタデータ一覧フォームの入力内容を確認してください。"

    context = {
        "quick_actions": quick_actions,
        "list_form": list_form,
        "metadata_records": metadata_records,
        "metadata_rows": metadata_rows,
        "metadata_columns": metadata_columns,
        "metadata_column_labels": metadata_column_labels,
        "metadata_table_rows": metadata_table_rows,
        "metadata_tree": metadata_tree,
        "metadata_selected_type": metadata_selected_type,
        "metadata_selected_type_label": metadata_selected_type_label,
        "metadata_result_info": metadata_result_info,
        "metadata_error": metadata_error,
        "metadata_name_filter": metadata_name_filter,
        "org_summary": org_summary,
        "custom_objects_preview": custom_objects_preview,
        "standard_objects_preview": standard_objects_preview,
        "needs_connection": False,
    }

    return render(request, "metadata/home.html", context)


@login_required
def metadata_detail_page(request, metadata_type: str, identifier: str):
    """Render a dedicated detail page for a particular metadata entry."""

    connection = getattr(request, "sf_connection", None)
    if not connection:
        messages.error(request, "Salesforce への接続が有効ではありません。")
        return render(
            request,
            "metadata/detail.html",
            {
                "metadata_type": metadata_type,
                "metadata_type_label": metadata_type,
                "detail_error": "Salesforce に接続してから詳細を確認してください。",
                "return_url": reverse("metadata:home"),
            },
        )

    client = SalesforceClient(connection)

    metadata_type = unquote(metadata_type)
    identifier = unquote(identifier)
    record_identifier = None if identifier == "lookup" else identifier
    api_name = request.GET.get("apiName")

    metadata_type_label = dict(ListMetadataForm.METADATA_TYPE_CHOICES).get(metadata_type, metadata_type)

    detail_payload = {}
    detail_error = None

    try:
        detail_payload = client.fetch_metadata_detail(
            metadata_type=metadata_type,
            record_id=record_identifier,
            api_name=api_name,
        )
    except SalesforceAPIError as exc:
        detail_error = str(exc)

    record = _serialize_value(detail_payload.get("record")) if detail_payload else {}
    object_info = _serialize_value(detail_payload.get("object")) if detail_payload else None

    record_items = []
    if isinstance(record, dict):
        record_items = [
            (key, value)
            for key, value in record.items()
            if key != "attributes"
        ]

    object_fields = []
    if object_info and isinstance(object_info, dict):
        fields = object_info.get("fields") or []
        object_fields = fields[:50]

    return_params = {}
    return_type = request.GET.get("initial_type")
    return_name = request.GET.get("initial_name")
    if return_type:
        return_params["initial_type"] = return_type
    else:
        return_params["initial_type"] = metadata_type
    if return_name:
        return_params["initial_name"] = return_name

    return_url = reverse("metadata:home")
    if return_params:
        return_url = f"{return_url}?{urlencode(return_params)}"

    context = {
        "metadata_type": metadata_type,
        "metadata_type_label": metadata_type_label,
        "identifier": record_identifier or api_name,
        "record_items": record_items,
        "record_raw": record,
        "object_info": object_info,
        "object_fields": object_fields,
        "detail_error": detail_error,
        "return_url": return_url,
        "api_name": api_name,
    }

    return render(request, "metadata/detail.html", context)

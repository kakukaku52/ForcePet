from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def is_subquery(value):
    """Check if the value is a processed subquery result"""
    return isinstance(value, dict) and value.get('_is_subquery')

@register.filter
def make_subquery_id(row_idx, col_idx):
    """Generate a unique ID string for subquery data script tag"""
    return f"subquery-{row_idx}-{col_idx}"



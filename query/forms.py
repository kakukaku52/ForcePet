from django import forms
from .models import SavedQuery


class QueryForm(forms.Form):
    """SOQL Query Form"""
    
    query = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control code-editor',
            'rows': 8,
            'placeholder': 'SELECT Id, Name FROM Account LIMIT 100',
            'data-mode': 'soql',
            'data-line-numbers': 'true'
        }),
        help_text='Enter your SOQL query here'
    )
    
    include_deleted = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Include deleted records (uses queryAll)'
    )
    
    def clean_query(self):
        query = self.cleaned_data.get('query', '').strip()

        if not query:
            raise forms.ValidationError('Query cannot be empty.')

        # Basic SOQL validation
        query_upper = query.upper()
        if not query_upper.startswith('SELECT'):
            raise forms.ValidationError('Query must start with SELECT.')

        if ' FROM ' not in query_upper:
            raise forms.ValidationError('Query must include FROM clause with proper spacing.')

        # Check for common syntax errors
        # Check if there's a comma right before FROM
        import re
        if re.search(r',\s*FROM\s', query, re.IGNORECASE):
            raise forms.ValidationError('Invalid syntax: Remove the comma before FROM keyword.')

        # Check for SELECT without any fields
        select_from_pattern = re.search(r'SELECT\s+FROM\s', query, re.IGNORECASE)
        if select_from_pattern:
            raise forms.ValidationError('You must specify at least one field to select.')

        # Check for unbalanced parentheses
        open_parens = query.count('(')
        close_parens = query.count(')')
        if open_parens != close_parens:
            raise forms.ValidationError(f'Unbalanced parentheses: {open_parens} opening, {close_parens} closing.')

        # Check for unbalanced quotes
        single_quotes = query.count("'")
        if single_quotes % 2 != 0:
            raise forms.ValidationError('Unbalanced single quotes in query.')

        return query


class SearchForm(forms.Form):
    """SOSL Search Form"""
    
    search_query = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control code-editor',
            'rows': 6,
            'placeholder': 'FIND {searchterm} IN ALL FIELDS RETURNING Account(Id, Name), Contact(Id, Name)',
            'data-mode': 'sosl',
            'data-line-numbers': 'true'
        }),
        help_text='Enter your SOSL search query here'
    )
    
    def clean_search_query(self):
        query = self.cleaned_data.get('search_query', '').strip()
        
        if not query:
            raise forms.ValidationError('Search query cannot be empty.')
        
        # Basic SOSL validation
        if not query.upper().startswith('FIND'):
            raise forms.ValidationError('Search query must start with FIND.')
        
        if 'IN ALL FIELDS' not in query.upper() and 'IN NAME FIELDS' not in query.upper() and \
           'IN EMAIL FIELDS' not in query.upper() and 'IN PHONE FIELDS' not in query.upper():
            raise forms.ValidationError('Search query must include an IN clause (ALL FIELDS, NAME FIELDS, etc.).')
        
        return query


class SavedQueryForm(forms.ModelForm):
    """Form for saving queries"""
    
    class Meta:
        model = SavedQuery
        fields = ['name', 'description', 'query_text', 'query_type', 'include_deleted', 'max_results']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter a name for this query'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional description'
            }),
            'query_text': forms.Textarea(attrs={
                'class': 'form-control code-editor',
                'rows': 6,
                'placeholder': 'Your SOQL or SOSL query'
            }),
            'query_type': forms.Select(attrs={'class': 'form-control'}),
            'include_deleted': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'max_results': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '50000'
            })
        }


class QueryBuilderForm(forms.Form):
    """Visual query builder form"""
    
    SELECT_CHOICES = [
        ('*', 'All Fields'),
        ('custom', 'Select Fields'),
    ]
    
    # Object selection
    sobject = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Account',
            'list': 'sobject-list'
        }),
        help_text='Select the object to query'
    )
    
    # Field selection
    select_type = forms.ChoiceField(
        choices=SELECT_CHOICES,
        initial='custom',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    fields = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Id, Name, CreatedDate'
        }),
        help_text='Comma-separated list of fields'
    )
    
    # WHERE clause
    where_clause = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': "Name LIKE 'A%'"
        }),
        help_text='WHERE conditions (without WHERE keyword)'
    )
    
    # ORDER BY
    order_by = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Name ASC'
        }),
        help_text='ORDER BY clause (without ORDER BY keyword)'
    )
    
    # LIMIT
    limit = forms.IntegerField(
        required=False,
        initial=100,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'max': '50000'
        }),
        help_text='Maximum number of records to return'
    )
    
    def clean_sobject(self):
        sobject = self.cleaned_data.get('sobject', '').strip()
        if not sobject:
            raise forms.ValidationError('Object name is required.')
        
        # Basic validation - should be a valid identifier
        if not sobject.replace('_', '').replace('__c', '').replace('__r', '').isalnum():
            raise forms.ValidationError('Invalid object name.')
        
        return sobject
    
    def build_soql(self):
        """Build SOQL query from form data"""
        if not self.is_valid():
            return None
        
        data = self.cleaned_data
        
        # SELECT clause
        if data['select_type'] == '*':
            select_clause = '*'
        else:
            fields = data.get('fields', '').strip()
            if not fields:
                select_clause = 'Id, Name'
            else:
                select_clause = fields
        
        # Build query
        query_parts = [f"SELECT {select_clause}"]
        query_parts.append(f"FROM {data['sobject']}")
        
        if data.get('where_clause'):
            query_parts.append(f"WHERE {data['where_clause']}")
        
        if data.get('order_by'):
            query_parts.append(f"ORDER BY {data['order_by']}")
        
        if data.get('limit'):
            query_parts.append(f"LIMIT {data['limit']}")
        
        return ' '.join(query_parts)
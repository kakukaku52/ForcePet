from django import forms
from django.conf import settings
import uuid


class LoginForm(forms.Form):
    """OAuth login form"""
    
    ENVIRONMENT_CHOICES = [
        ('production', 'Production (login.salesforce.com)'),
        ('sandbox', 'Sandbox (test.salesforce.com)'),
        ('custom', 'Custom Domain'),
    ]
    
    environment = forms.ChoiceField(
        choices=ENVIRONMENT_CHOICES,
        initial='production',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    custom_domain = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://your-domain.my.salesforce.com'
        }),
        help_text='Required only for Custom Domain'
    )
    
    api_version = forms.CharField(
        initial=settings.SALESFORCE_API_VERSION,
        max_length=10,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    # Hidden state field for OAuth security
    state = forms.CharField(
        initial=lambda: str(uuid.uuid4()),
        widget=forms.HiddenInput()
    )
    
    def clean(self):
        cleaned_data = super().clean()
        environment = cleaned_data.get('environment')
        custom_domain = cleaned_data.get('custom_domain')
        
        if environment == 'custom' and not custom_domain:
            raise forms.ValidationError('Custom domain is required when Custom Domain is selected.')
        
        return cleaned_data


class StandardLoginForm(forms.Form):
    """Username/password login form"""
    
    ENVIRONMENT_CHOICES = [
        ('production', 'Production (login.salesforce.com)'),
        ('sandbox', 'Sandbox (test.salesforce.com)'),
        ('custom', 'Custom Domain'),
    ]
    
    username = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your.email@company.com'
        })
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your Salesforce password'
        })
    )
    
    security_token = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Security token (if required)'
        }),
        help_text='Required if your IP is not in the trusted IP ranges'
    )
    
    environment = forms.ChoiceField(
        choices=ENVIRONMENT_CHOICES,
        initial='production',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    custom_domain = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://your-domain.my.salesforce.com'
        }),
        help_text='Required only for Custom Domain'
    )
    
    api_version = forms.CharField(
        initial=settings.SALESFORCE_API_VERSION,
        max_length=10,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        environment = cleaned_data.get('environment')
        custom_domain = cleaned_data.get('custom_domain')
        
        if environment == 'custom' and not custom_domain:
            raise forms.ValidationError('Custom domain is required when Custom Domain is selected.')
        
        return cleaned_data


class SettingsForm(forms.Form):
    """User settings form"""
    
    RESULT_FORMAT_CHOICES = [
        ('table', 'Table'),
        ('csv', 'CSV'),
        ('json', 'JSON'),
    ]
    
    TIMEZONE_CHOICES = [
        ('UTC', 'UTC'),
        ('America/New_York', 'Eastern Time'),
        ('America/Chicago', 'Central Time'),
        ('America/Denver', 'Mountain Time'),
        ('America/Los_Angeles', 'Pacific Time'),
        ('Europe/London', 'London Time'),
        ('Europe/Paris', 'Paris Time'),
        ('Asia/Tokyo', 'Tokyo Time'),
        ('Asia/Shanghai', 'Shanghai Time'),
        ('Australia/Sydney', 'Sydney Time'),
    ]
    
    # Query settings
    default_query_results_format = forms.ChoiceField(
        choices=RESULT_FORMAT_CHOICES,
        initial='table',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    query_timeout = forms.IntegerField(
        initial=120,
        min_value=30,
        max_value=600,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'help_text': 'Query timeout in seconds (30-600)'
        })
    )
    
    max_query_results = forms.IntegerField(
        initial=2000,
        min_value=100,
        max_value=50000,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'help_text': 'Maximum number of query results to display (100-50000)'
        })
    )
    
    # Data settings
    batch_size = forms.IntegerField(
        initial=200,
        min_value=1,
        max_value=10000,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'help_text': 'Batch size for bulk operations (1-10000)'
        })
    )
    
    enable_rollback_on_error = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    # Display settings
    timezone_preference = forms.ChoiceField(
        choices=TIMEZONE_CHOICES,
        initial='UTC',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    date_format = forms.CharField(
        initial='YYYY-MM-DD',
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'YYYY-MM-DD'
        })
    )
    
    time_format = forms.CharField(
        initial='HH:mm:ss',
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'HH:mm:ss'
        })
    )
    
    # Advanced settings
    api_timeout = forms.IntegerField(
        initial=60,
        min_value=10,
        max_value=300,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'help_text': 'API request timeout in seconds (10-300)'
        })
    )
    
    debug_mode = forms.BooleanField(
        initial=False,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Enable debug logging and additional error information'
    )
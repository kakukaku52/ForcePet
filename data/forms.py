from django import forms
from django.core.validators import FileExtensionValidator


class InsertForm(forms.Form):
    """Form for inserting records"""
    sobject = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Account, Contact, Lead'
        }),
        help_text='Salesforce object API name'
    )
    
    data = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 10,
            'placeholder': '[{"Name": "Test Account", "Type": "Customer"}]'
        }),
        help_text='JSON array of records to insert'
    )
    
    csv_file = forms.FileField(
        required=False,
        validators=[FileExtensionValidator(['csv'])],
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        help_text='Or upload a CSV file'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        data = cleaned_data.get('data')
        csv_file = cleaned_data.get('csv_file')
        
        if not data and not csv_file:
            raise forms.ValidationError('Please provide either JSON data or a CSV file')
        
        if data and csv_file:
            raise forms.ValidationError('Please provide either JSON data or a CSV file, not both')
        
        return cleaned_data


class UpdateForm(forms.Form):
    """Form for updating records"""
    sobject = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Account, Contact, Lead'
        }),
        help_text='Salesforce object API name'
    )
    
    data = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 10,
            'placeholder': '[{"Id": "001xx000003DHP0", "Name": "Updated Account"}]'
        }),
        help_text='JSON array of records to update (must include Id field)'
    )
    
    csv_file = forms.FileField(
        required=False,
        validators=[FileExtensionValidator(['csv'])],
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        help_text='Or upload a CSV file (must include Id column)'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        data = cleaned_data.get('data')
        csv_file = cleaned_data.get('csv_file')
        
        if not data and not csv_file:
            raise forms.ValidationError('Please provide either JSON data or a CSV file')
        
        if data and csv_file:
            raise forms.ValidationError('Please provide either JSON data or a CSV file, not both')
        
        return cleaned_data


class DeleteForm(forms.Form):
    """Form for deleting records"""
    sobject = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Account, Contact, Lead'
        }),
        help_text='Salesforce object API name'
    )
    
    ids = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': '001xx000003DHP0, 001xx000003DHP1, 001xx000003DHP2'
        }),
        help_text='Comma-separated list of record IDs to delete'
    )


class UpsertForm(forms.Form):
    """Form for upserting records"""
    sobject = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Account, Contact, Lead'
        }),
        help_text='Salesforce object API name'
    )
    
    external_id_field = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., External_Id__c'
        }),
        help_text='External ID field API name'
    )
    
    data = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 10,
            'placeholder': '[{"External_Id__c": "EXT001", "Name": "Account 1"}]'
        }),
        help_text='JSON array of records to upsert'
    )
    
    csv_file = forms.FileField(
        required=False,
        validators=[FileExtensionValidator(['csv'])],
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        help_text='Or upload a CSV file'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        data = cleaned_data.get('data')
        csv_file = cleaned_data.get('csv_file')
        
        if not data and not csv_file:
            raise forms.ValidationError('Please provide either JSON data or a CSV file')
        
        if data and csv_file:
            raise forms.ValidationError('Please provide either JSON data or a CSV file, not both')
        
        return cleaned_data


class UndeleteForm(forms.Form):
    """Form for undeleting records"""
    ids = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': '001xx000003DHP0, 001xx000003DHP1, 001xx000003DHP2'
        }),
        help_text='Comma-separated list of record IDs to undelete'
    )


class BulkDataForm(forms.Form):
    """Form for bulk data operations"""
    OPERATION_CHOICES = [
        ('insert', 'Insert'),
        ('update', 'Update'),
        ('upsert', 'Upsert'),
        ('delete', 'Delete'),
    ]
    
    operation = forms.ChoiceField(
        choices=OPERATION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    sobject = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Account, Contact, Lead'
        }),
        help_text='Salesforce object API name'
    )
    
    file = forms.FileField(
        validators=[FileExtensionValidator(['csv', 'json'])],
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        help_text='CSV or JSON file containing records'
    )
    
    external_id_field = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Required for upsert operation'
        }),
        help_text='External ID field (for upsert only)'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        operation = cleaned_data.get('operation')
        external_id_field = cleaned_data.get('external_id_field')
        
        if operation == 'upsert' and not external_id_field:
            raise forms.ValidationError('External ID field is required for upsert operation')
        
        return cleaned_data
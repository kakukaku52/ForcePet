from django import forms

from .constants import build_metadata_type_choices


class ListMetadataForm(forms.Form):
    """Form for listing metadata components for supported types."""

    METADATA_TYPE_CHOICES = build_metadata_type_choices()

    metadata_type = forms.ChoiceField(
        label="メタデータ種別",
        choices=METADATA_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'slds-select'}),
    )

    name_filter = forms.CharField(
        label="名前フィルター",
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'slds-input',
                'placeholder': '名前の部分一致フィルター（任意）',
            }
        ),
        help_text="名前またはラベルの部分一致で結果を絞り込みます（大文字小文字は区別されません）。",
    )

    def get_choice_label(self, value):
        for choice_value, choice_label in self.METADATA_TYPE_CHOICES:
            if choice_value == value:
                return choice_label
        return value

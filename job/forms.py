from django import forms
from .models import Job 


class UploadJobExcelForm(forms.Form):
    file = forms.FileField(
        label="Upload Jobs Excel File",
        help_text="Upload an Excel file containing job data"
    )
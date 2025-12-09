# forms.py
from django import forms
from .models import *
from main_app.models import *



# Custom widget for multiple file uploads
class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class QuestionPaperUploadForm(forms.ModelForm):
    class Meta:
        model = QuestionPaper
        fields = [
            'file',
            'title',
            'grade', 
            'term',
            'school',
            'department', 
            'subject',
            'complexity_rating',
            'topics'
        ]
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf'
            }),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter a title for this paper'
            }),
            'grade': forms.Select(attrs={'class': 'form-control'}),
            'term': forms.Select(attrs={'class': 'form-control'}),
            'school': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'subject': forms.Select(attrs={'class': 'form-control'}),
            'complexity_rating': forms.Select(attrs={'class': 'form-control'}),
            'topics': forms.SelectMultiple(attrs={'class': 'form-control'}),
        }


class BulkUploadForm(forms.Form):
    files = MultipleFileField(
        widget=MultipleFileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf'
        }),
        help_text="Select multiple PDF files"
    )
    grade = forms.ModelChoiceField(
        queryset=Grade.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    term = forms.ModelChoiceField(
        queryset=Term.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    school = forms.ModelChoiceField(
        queryset=School.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
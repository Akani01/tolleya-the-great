from django import forms
from django.forms.widgets import DateInput, TextInput
from django.forms import CheckboxSelectMultiple
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Row, Column
from college.models import CollegeAndUniversities
from bursary.models import Bursary
from .models import *
import re


class FormSettings(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(FormSettings, self).__init__(*args, **kwargs)
        # Here make some changes such as:
        for field in self.visible_fields():
            field.field.widget.attrs['class'] = 'form-control'

#custom user form
class CustomUserForm(FormSettings):
    email = forms.EmailField(required=True)
    gender = forms.ChoiceField(choices=[('M', 'Male'), ('F', 'Female')])
    first_name = forms.CharField(required=True)
    last_name = forms.CharField(required=True)
    address = forms.CharField(widget=forms.Textarea)
    password = forms.CharField(widget=forms.PasswordInput)
    widget = {
        'password': forms.PasswordInput(),
    }
    profile_pic = forms.ImageField()

    def __init__(self, *args, **kwargs):
        super(CustomUserForm, self).__init__(*args, **kwargs)

        if kwargs.get('instance'):
            instance = kwargs.get('instance').admin.__dict__
            self.fields['password'].required = False
            for field in CustomUserForm.Meta.fields:
                self.fields[field].initial = instance.get(field)
            if self.instance.pk is not None:
                self.fields['password'].widget.attrs['placeholder'] = "Fill this only if you wish to update password"

    def clean_email(self, *args, **kwargs):
        formEmail = self.cleaned_data['email'].lower()
        if self.instance.pk is None:  # Insert
            if CustomUser.objects.filter(email=formEmail).exists():
                raise forms.ValidationError(
                    "The given email is already registered")
        else:  # Update
            dbEmail = self.Meta.model.objects.get(
                id=self.instance.pk).admin.email.lower()
            if dbEmail != formEmail:  # There has been changes
                if CustomUser.objects.filter(email=formEmail).exists():
                    raise forms.ValidationError("The given email is already registered")

        return formEmail

    class Meta:
        model = CustomUser
        fields = ['first_name','last_name', 'email', 'gender',  'password','profile_pic', 'address' ]

#student form
class StudentForm(CustomUserForm):
    class Meta(CustomUserForm.Meta):
        model = Student
        fields = CustomUserForm.Meta.fields + ['school', 'grade', 'course']
        widgets = {
            'school': forms.Select(attrs={'class': 'form-control'}),
            'grade': forms.Select(attrs={'class': 'form-control'}),
            'course': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Instead of redefining the fields, just update their properties
        # Make fields required
        self.fields['school'].required = True
        self.fields['grade'].required = True
        self.fields['course'].required = False  # Not required for R-9
        
        # Update querysets and empty labels
        self.fields['school'].queryset = School.objects.all().order_by('name')
        self.fields['school'].empty_label = "Select School"
        
        self.fields['grade'].queryset = Grade.objects.all().order_by('name')
        self.fields['grade'].empty_label = "Select Grade"
        
        self.fields['course'].queryset = Course.objects.all().order_by('name')
        self.fields['course'].empty_label = "Select Course (for Grade 10-12)"
        
        # Add help text
        self.fields['grade'].help_text = "Select Grade R to Grade 12"
        self.fields['course'].help_text = "Required only for Grades 10-12"
        
        # Handle Excel/import data - convert names to IDs
        if 'grade' in self.data and self.data['grade']:
            grade_input = self.data.get('grade')
            if grade_input and not grade_input.isdigit():  # It's a name, not an ID
                grade = self.find_grade(grade_input)
                if grade:
                    # Create mutable copy of data
                    mutable_data = self.data.copy()
                    mutable_data['grade'] = str(grade.id)
                    self.data = mutable_data
        
        if 'school' in self.data and self.data['school']:
            school_input = self.data.get('school')
            if school_input and not school_input.isdigit():  # It's a name, not an ID
                school = self.find_school(school_input)
                if school:
                    mutable_data = self.data.copy()
                    mutable_data['school'] = str(school.id)
                    self.data = mutable_data
        
        if 'course' in self.data and self.data['course']:
            course_input = self.data.get('course')
            if course_input and not course_input.isdigit():
                course = self.find_course(course_input)
                if course:
                    mutable_data = self.data.copy()
                    mutable_data['course'] = str(course.id)
                    self.data = mutable_data
        
        # Toggle course field based on selected grade
        self.toggle_course_field()
        
        # Style all fields (just in case)
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control'
    
    def find_grade(self, grade_input):
        """Find grade by various naming patterns from Excel"""
        if not grade_input:
            return None
        
        grade_input = str(grade_input).strip()
        
        # Try exact match first
        grade = Grade.objects.filter(name__iexact=grade_input).first()
        if grade:
            return grade
        
        # Try with 'Grade' prefix
        if not re.match(r'^(grade|gr|grd)\s+', grade_input, re.IGNORECASE):
            grade = Grade.objects.filter(name__iexact=f"Grade {grade_input}").first()
            if grade:
                return grade
        
        # Try common variations
        variations = [
            ('^gr\s+', 'Grade '),
            ('^grd\s+', 'Grade '),
            ('^grade\s+', 'Grade '),
            ('^std\s+', 'Grade '),
            ('^class\s+', 'Grade '),
        ]
        
        for pattern, replacement in variations:
            if re.match(pattern, grade_input, re.IGNORECASE):
                normalized = re.sub(pattern, replacement, grade_input, flags=re.IGNORECASE)
                grade = Grade.objects.filter(name__iexact=normalized).first()
                if grade:
                    return grade
        
        # Try partial match
        grade = Grade.objects.filter(name__icontains=grade_input).first()
        if grade:
            return grade
        
        # Try extracting just the number
        match = re.search(r'\b(R|\d+)\b', grade_input, re.IGNORECASE)
        if match:
            grade_num = match.group(1).upper()
            # Try with Grade prefix
            grade = Grade.objects.filter(name__iexact=f"Grade {grade_num}").first()
            if grade:
                return grade
        
        return None
    
    def find_school(self, school_input):
        """Find school by name"""
        if not school_input:
            return None
        
        school_name = str(school_input).strip()
        
        # Try exact match
        school = School.objects.filter(name__iexact=school_name).first()
        if school:
            return school
        
        # Try partial match
        school = School.objects.filter(name__icontains=school_name).first()
        if school:
            return school
        
        return None
    
    def find_course(self, course_input):
        """Find course by name"""
        if not course_input:
            return None
        
        course_name = str(course_input).strip()
        
        # Try exact match
        course = Course.objects.filter(name__iexact=course_name).first()
        if course:
            return course
        
        # Try partial match
        course = Course.objects.filter(name__icontains(course_name)).first()
        if course:
            return course
        
        return None
    
    def toggle_course_field(self):
        """Show/hide course field based on selected grade"""
        if 'grade' in self.data:
            try:
                grade_id = self.data.get('grade')
                if grade_id and grade_id.isdigit():
                    grade = Grade.objects.get(id=int(grade_id))
                    if self.is_young_grade(grade.name):
                        # Hide for R-9
                        self.fields['course'].widget.attrs['style'] = 'display: none;'
                        self.fields['course'].label = ''
                        self.fields['course'].required = False
                        # Remove 'disabled' attribute if it exists
                        if 'disabled' in self.fields['course'].widget.attrs:
                            del self.fields['course'].widget.attrs['disabled']
                    else:
                        # Show for 10-12
                        if 'style' in self.fields['course'].widget.attrs:
                            del self.fields['course'].widget.attrs['style']
                        self.fields['course'].label = 'Course'
                        self.fields['course'].required = True
            except (ValueError, Grade.DoesNotExist):
                pass
    
    def is_young_grade(self, grade_name):
        """Check if grade is R-9 (no course needed)"""
        if not grade_name:
            return False
        
        grade_name = str(grade_name).strip().upper()
        
        # Clean the grade name
        grade_name = re.sub(r'^(GRADE|GR|GRD|STD|CLASS)\s+', '', grade_name, flags=re.IGNORECASE)
        
        # Young grades are R, 1-9
        young_grades = ['R', '1', '2', '3', '4', '5', '6', '7', '8', '9']
        return grade_name in young_grades
    
    def clean(self):
        """Custom validation"""
        cleaned_data = super().clean()
        
        # Get grade and check course requirement
        grade = cleaned_data.get('grade')
        course = cleaned_data.get('course')
        
        if grade:
            if not self.is_young_grade(grade.name) and not course:
                # Grade 10-12 requires course
                raise forms.ValidationError({
                    'course': f"Course is required for {grade.name}"
                })
            
            if self.is_young_grade(grade.name) and course:
                # R-9 shouldn't have course
                cleaned_data['course'] = None
        
        return cleaned_data
#educator form 
# educator form 
# educator form 
class EducatorForm(CustomUserForm):
    class Meta(CustomUserForm.Meta):
        model = Educator
        fields = CustomUserForm.Meta.fields + ['school', 'grades', 'subjects']

    def __init__(self, *args, **kwargs):
        super(EducatorForm, self).__init__(*args, **kwargs)

        self.fields['school'] = forms.ModelChoiceField(
            queryset=School.objects.all(),
            required=True,
            label="School"
        )

        self.fields['grades'] = forms.ModelMultipleChoiceField(
            queryset=Grade.objects.all(),
            required=True,
            widget=forms.CheckboxSelectMultiple,  # ✅ Changed to checkboxes
            label="Grades Taught"
        )

        self.fields['subjects'] = forms.ModelMultipleChoiceField(
            queryset=Subject.objects.all(),
            required=True,
            widget=forms.CheckboxSelectMultiple,  # ✅ Changed to checkboxes
            label="Subjects Taught"
        )

        # ✅ Bootstrap styling
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxSelectMultiple):
                field.widget.attrs['class'] = 'form-control'


#member
class MemberForm(CustomUserForm):
    def __init__(self, *args, **kwargs):
        super(MemberForm, self).__init__(*args, **kwargs)
        
        # Optional: Add Bootstrap styling
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

    class Meta(CustomUserForm.Meta):
        model = Member
        fields = CustomUserForm.Meta.fields + ['position']  # ✅ Only fields that exist


#cwa user
class CWA_AdminEditForm(forms.ModelForm):
    class Meta:
        model = CWA_Admin
        fields = ['admin', 'school', 'collegeanduniversity', 'bursary']
        widgets = {
            'admin': forms.HiddenInput(),
        }

    # Custom fields for the CustomUser
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    address = forms.CharField(widget=forms.Textarea, required=False)
    gender = forms.ChoiceField(choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')], required=False)
    position = forms.CharField(max_length=30, required=True)
    profile_pic = forms.ImageField(required=False)

    def __init__(self, *args, **kwargs):
        super(CWA_AdminEditForm, self).__init__(*args, **kwargs)
        if 'instance' in kwargs:
            instance = kwargs['instance']
            self.fields['first_name'].initial = instance.admin.first_name
            self.fields['last_name'].initial = instance.admin.last_name
            self.fields['address'].initial = instance.admin.address
            self.fields['gender'].initial = instance.admin.gender
            self.fields['profile_pic'].initial = instance.admin.profile_pic

    def save(self, commit=True):
        cwa_admin = super(CWA_AdminEditForm, self).save(commit=False)
        admin = cwa_admin.admin
        
        # Update CustomUser fields
        admin.first_name = self.cleaned_data['first_name']
        admin.last_name = self.cleaned_data['last_name']
        admin.address = self.cleaned_data['address']
        admin.gender = self.cleaned_data['gender']
        
        if self.cleaned_data['profile_pic']:
            admin.profile_pic = self.cleaned_data['profile_pic']
        
        if commit:
            admin.save()
            cwa_admin.save()
        
        return cwa_admin
        
#principal form
class PrincipalForm(CustomUserForm):
    class Meta(CustomUserForm.Meta):
        model = Principal
        fields = CustomUserForm.Meta.fields + ['school', 'grades', 'subjects']  # ✅ ManyToMany fields

    def __init__(self, *args, **kwargs):
        super(PrincipalForm, self).__init__(*args, **kwargs)
        
        self.fields['school'] = forms.ModelChoiceField(
            queryset=School.objects.all(),
            required=True,
            label="School"
        )
        
        self.fields['grades'] = forms.ModelMultipleChoiceField(  # ✅ Multiple selection
            queryset=Grade.objects.all(),
            required=True,
            widget=forms.CheckboxSelectMultiple,
            label="Grades Taught"
        )
        
        self.fields['subjects'] = forms.ModelMultipleChoiceField(  # ✅ Multiple selection
            queryset=Subject.objects.all(),
            required=True,
            widget=forms.CheckboxSelectMultiple,
            label="Subjects Taught"
        )

        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxSelectMultiple):
                field.widget.attrs['class'] = 'form-control'

#principal edit form
class PrincipalEditForm(forms.ModelForm):
    class Meta:
        model = Principal
        fields = ['school', 'grades', 'subjects']
        widgets = {
            'admin': forms.HiddenInput(),  # Keep the admin field hidden
        }

    # Custom fields for the CustomUser associated with Principal
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)
    address = forms.CharField(widget=forms.Textarea, required=False)
    gender = forms.ChoiceField(choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')], required=False)
    profile_pic = forms.ImageField(required=False)

    def __init__(self, *args, **kwargs):
        super(PrincipalEditForm, self).__init__(*args, **kwargs)
        
        # Set initial values from the associated CustomUser
        if self.instance and self.instance.pk:
            self.fields['first_name'].initial = self.instance.admin.first_name
            self.fields['last_name'].initial = self.instance.admin.last_name
            self.fields['email'].initial = self.instance.admin.email
            self.fields['address'].initial = self.instance.admin.address
            self.fields['gender'].initial = self.instance.admin.gender
            self.fields['profile_pic'].initial = self.instance.admin.profile_pic

        # Configure the ManyToMany fields with checkboxes
        self.fields['grades'] = forms.ModelMultipleChoiceField(
            queryset=Grade.objects.all(),
            required=True,
            widget=forms.CheckboxSelectMultiple,
            label="Grades Taught"
        )
        
        self.fields['subjects'] = forms.ModelMultipleChoiceField(
            queryset=Subject.objects.all(),
            required=True,
            widget=forms.CheckboxSelectMultiple,
            label="Subjects Taught"
        )

        # Bootstrap styling
        for field in self.fields.values():
            if not isinstance(field.widget, (forms.CheckboxSelectMultiple, forms.HiddenInput)):
                field.widget.attrs['class'] = 'form-control'

    def save(self, commit=True):
        principal = super(PrincipalEditForm, self).save(commit=False)
        admin = principal.admin
        
        # Update the CustomUser fields
        admin.first_name = self.cleaned_data['first_name']
        admin.last_name = self.cleaned_data['last_name']
        admin.email = self.cleaned_data['email']
        admin.address = self.cleaned_data['address']
        admin.gender = self.cleaned_data['gender']
        
        if 'profile_pic' in self.cleaned_data and self.cleaned_data['profile_pic']:
            admin.profile_pic = self.cleaned_data['profile_pic']
        
        if commit:
            admin.save()  # Save the CustomUser instance
            principal.save()  # Save the Principal instance
            # Save the many-to-many relationships
            self.save_m2m()

        return principal

#cwa_admin edit form
class CWA_AdminForm(CustomUserForm):
    def __init__(self, *args, **kwargs):
        super(CWA_AdminForm, self).__init__(*args, **kwargs)
        
        # Optional: Add Bootstrap styling
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'

    class Meta(CustomUserForm.Meta):
        model = CWA_Admin
        fields = CustomUserForm.Meta.fields + ['school', 'collegeanduniversity', 'bursary', 'session', 'term']

class CWA_AdminEditForm(forms.ModelForm):
    class Meta:
        model = CWA_Admin
        fields = ['admin', 'school', 'collegeanduniversity', 'bursary']
        widgets = {
            'admin': forms.HiddenInput(),  # Keep the admin field hidden
        }

    # Custom fields for the CustomUser associated with cwa-admin
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    address = forms.CharField(widget=forms.Textarea, required=False)
    gender = forms.ChoiceField(choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')], required=False)
    position = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    profile_pic = forms.ImageField(required=False)

    def __init__(self, *args, **kwargs):
        super(PrincipalEditForm, self).__init__(*args, **kwargs)
        if 'instance' in kwargs:
            self.fields['first_name'].initial = kwargs['instance'].admin.first_name
            self.fields['last_name'].initial = kwargs['instance'].admin.last_name
            self.fields['address'].initial = kwargs['instance'].admin.address
            self.fields['gender'].initial = kwargs['instance'].admin.gender
            self.fields['profile_pic'].initial = kwargs['instance'].admin.profile_pic

    def save(self, commit=True):
        principal = super(PrincipalEditForm, self).save(commit=False)
        admin = principal.admin
        
        # Update the CustomUser fields
        admin.first_name = self.cleaned_data['first_name']
        admin.last_name = self.cleaned_data['last_name']
        admin.address = self.cleaned_data['address']
        admin.gender = self.cleaned_data['gender']
        
        if 'profile_pic' in self.cleaned_data and self.cleaned_data['profile_pic']:
            admin.profile_pic = self.cleaned_data['profile_pic']
        
        if commit:
            admin.save()  # Save the CustomUser instance
            principal.save()  # Save the Principal instance

        return principal
    
#circuit manager
class CircuitManagerEditForm(CustomUserForm):
    def __init__(self, *args, **kwargs):
        super(CircuitManagerEditForm, self).__init__(*args, **kwargs)

    class Meta(CustomUserForm.Meta):
        model = Circuit_Manager
        fields = CustomUserForm.Meta.fields

#termform
class TermForm(forms.ModelForm):
    class Meta:
        model = Term
        fields = ['term_name', 'is_current', 'session', 'next_term_begins']
        widgets = {
            'term_name': forms.Select(attrs={'class': 'form-control'}),
            'is_current': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'session': forms.Select(attrs={'class': 'form-control'}),
            'next_term_begins': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

#admin
class AdminForm(CustomUserForm):
    def __init__(self, *args, **kwargs):
        super(AdminForm, self).__init__(*args, **kwargs)

    class Meta(CustomUserForm.Meta):
        model = Admin
        fields = CustomUserForm.Meta.fields

#edit educator profile

#staff
class StaffForm(CustomUserForm):
    def __init__(self, *args, **kwargs):
        super(StaffForm, self).__init__(*args, **kwargs)

    class Meta(CustomUserForm.Meta):
        model = Staff
        fields = CustomUserForm.Meta.fields + \
            ['school' ]


#courseform
class CourseForm(FormSettings):
    def __init__(self, *args, **kwargs):
        super(CourseForm, self).__init__(*args, **kwargs)

    class Meta:
        fields = ['name','school']
        model = Course

#gradeform
class GradeForm(FormSettings):
    def __init__(self, *args, **kwargs):
        super(GradeForm, self).__init__(*args, **kwargs)

    class Meta:
        fields = ['name']
        model = Grade

#subject
class SubjectForm(FormSettings):

    def __init__(self, *args, **kwargs):
        super(SubjectForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Subject
        fields = ['name', 'course', 'grade']


#session
class SessionForm(FormSettings):
    def __init__(self, *args, **kwargs):
        super(SessionForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Session
        fields = '__all__'
        widgets = {
            'start_year': DateInput(attrs={'type': 'date'}),
            'end_year': DateInput(attrs={'type': 'date'}),
        }


#term
class TermForm(FormSettings):
    def __init__(self, *args, **kwargs):
        super(TermForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Term
        fields = ['term_name','is_current','activity_description','session','next_term_begins']
        widgets = {
            'start_year': DateInput(attrs={'type': 'date'}),
            'end_year': DateInput(attrs={'type': 'date'}),
            'term_name': forms.Select(attrs={'class': 'form-control'}),
            'is_current': forms.TextInput(attrs={'class': 'form-control'}),
            'activity_description': forms.TextInput(attrs={'class': 'form-control'}),
            'session': forms.Select(attrs={'class': 'form-control'}),
            'next_term_begins': DateInput(attrs={'type': 'date'}),
        }

#leavereport
class LeaveReportStaffForm(FormSettings):
    def __init__(self, *args, **kwargs):
        super(LeaveReportStaffForm, self).__init__(*args, **kwargs)

    class Meta:
        model = LeaveReportStaff
        fields = ['date', 'message']
        widgets = {
            'date': DateInput(attrs={'type': 'date'}),
        }


#feedback staff
class FeedbackStaffForm(FormSettings):

    def __init__(self, *args, **kwargs):
        super(FeedbackStaffForm, self).__init__(*args, **kwargs)

    class Meta:
        model = FeedbackStaff
        fields = ['feedback']


#leavereport student
class LeaveReportStudentForm(FormSettings):
    def __init__(self, *args, **kwargs):
        super(LeaveReportStudentForm, self).__init__(*args, **kwargs)

    class Meta:
        model = LeaveReportStudent
        fields = ['date', 'message']
        widgets = {
            'date': DateInput(attrs={'type': 'date'}),
        }


#feedback
class FeedbackStudentForm(FormSettings):

    def __init__(self, *args, **kwargs):
        super(FeedbackStudentForm, self).__init__(*args, **kwargs)

    class Meta:
        model = FeedbackStudent
        fields = ['feedback']


#student edit form
class StudentEditForm(CustomUserForm):
    def __init__(self, *args, **kwargs):
        super(StudentEditForm, self).__init__(*args, **kwargs)

    class Meta(CustomUserForm.Meta):
        model = Student
        fields = CustomUserForm.Meta.fields 


#staff edit form
class StaffEditForm(CustomUserForm):
    def __init__(self, *args, **kwargs):
        super(StaffEditForm, self).__init__(*args, **kwargs)

    class Meta(CustomUserForm.Meta):
        model = Staff
        fields = CustomUserForm.Meta.fields

#circuit manager edit form
class CircuitManagerEditForm(CustomUserForm):
    def __init__(self, *args, **kwargs):
        super(StaffEditForm, self).__init__(*args, **kwargs)

    class Meta(CustomUserForm.Meta):
        model = Circuit_Manager
        fields = CustomUserForm.Meta.fields


#Edit Result form
class EditResultForm(FormSettings):
    session_list = Session.objects.all()
    session_year = forms.ModelChoiceField(
        label="Session Year", queryset=session_list, required=True)

    def __init__(self, *args, **kwargs):
        super(EditResultForm, self).__init__(*args, **kwargs)

    class Meta:
        model = StudentResult
        fields = ['session_year', 'subject', 'student', 'test', 'assignment', 'exam']

#school form
class SchoolForm(forms.ModelForm):
    class Meta:
        model = School
        fields = [
            'emis', 'name', 'contact', 'phase', 'sector', 'educators_on_db',
            'school_type', 'school_term', 'logo', 'head_principal', 'deputy',
            'filter_by', 'website_url', 'email', 'whatsapp_number', 'grade',
            'circuit', 'address', 'year', 'count'
        ]
        widgets = {
            'emis': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact': forms.TextInput(attrs={'class': 'form-control'}),
            'phase': forms.TextInput(attrs={'class': 'form-control'}),
            'sector': forms.TextInput(attrs={'class': 'form-control'}),
            'educators_on_db': forms.NumberInput(attrs={'class': 'form-control'}),

            # Correct: Model has choices
            'school_type': forms.Select(attrs={'class': 'form-control'}),
            'filter_by': forms.Select(attrs={'class': 'form-control'}),

            # Correct widget for IntegerField (no choices)
            'school_term': forms.NumberInput(attrs={'class': 'form-control'}),

            'logo': forms.FileInput(attrs={'class': 'form-control'}),
            'head_principal': forms.TextInput(attrs={'class': 'form-control'}),
            'deputy': forms.TextInput(attrs={'class': 'form-control'}),

            'website_url': forms.URLInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'whatsapp_number': forms.TextInput(attrs={'class': 'form-control'}),

            # FIXED: TextField → Textarea
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),

            'grade': forms.Select(attrs={'class': 'form-control'}),
            'circuit': forms.Select(attrs={'class': 'form-control'}),

            'year': forms.NumberInput(attrs={'class': 'form-control'}),
            'count': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        
#school dashboard phase
class SchoolEditForm(forms.ModelForm):
    class Meta:
        model = School
        fields = ['name', 'logo', 'head_principal', 'deputy', 'school_type', 'filter_by', 'website_url', 'email', 'grade', 'whatsapp_number', 'address', 'year']


# documents upload
class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['name', 'email', 'phone', 'department', 'message']
        fields = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rowas': 4}),
        }

# subscription
class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = School
        fields = ['email']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'forms-control',
                'placeholder': 'Enter your email'
            }),
        }

#timetable form
class TimetableForm(forms.ModelForm):
    class Meta:
        model = Timetable
        fields = ['day', 'grade', 'course', 'subjects', 'educators', 'start_time', 'end_time']
        widgets = {
            'subjects': forms.SelectMultiple(attrs={'size': 5}),
            'educators': forms.SelectMultiple(attrs={'size': 5}),
        }

#messages
class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['text', 'reply_to']  # 'text' for the message, media will be handled separately
        widgets = {
            'text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Type a message...'}),
            'reply_to': forms.HiddenInput(),
        }

    media_files = forms.FileField(
        widget=forms.ClearableFileInput(attrs={'allow_multiple_selected': True}),
        required=False
    )

#school perfomance

class SchoolPerformanceForm(forms.ModelForm):
    class Meta:
        model = SchoolPerformance
        fields = [
            'school_record', 'session', 'educator', 'subject', 'grade', 
            'school_principal', 'performance_score', 'comments'
        ]

#reply contact
class ReplyContactForm(forms.Form):
    subject = forms.CharField(max_length=255, widget=forms.TextInput(attrs={'class': 'form-control'}))
    message = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control'}))

class ProspectorForm(forms.ModelForm):
    class Meta:
        model = Prospectors
        fields = ['institution', 'address', 'copy', 'logo']

#custom password reset
class CustomPasswordResetForm(forms.Form):
    email = forms.EmailField(
        label="Enter your email",
        widget=forms.EmailInput(attrs={"class": "form-control"})
    )

    def clean_email(self):
        email = self.cleaned_data["email"]
        if not CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("No user with this email address found.")
        return email


class NewsAndEventsForm(forms.ModelForm):
    class Meta:
        model = NewsAndEvents
        fields = ['title', 'summary', 'posted_as', 'image']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'summary': forms.Textarea(attrs={'class': 'form-control'}),
            'posted_as': forms.Select(attrs={'class': 'form-control'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

class UploadExcelForm(forms.Form):
    file = forms.FileField(label="Upload Excel File")

#course form
class CourseExcelUploadForm(forms.Form):
    excel_file = forms.FileField(
        label='Excel File',
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )

#subject upload form
class SubjectExcelUploadForm(forms.Form):
    excel_file = forms.FileField(
        label="Upload Excel File",
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )


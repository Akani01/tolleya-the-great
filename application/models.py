# models.py (for your application automation app)
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import RegexValidator
import json
import re
from django.conf import settings

# Import for AI capabilities
import openai
import anthropic
import hashlib
import os
from datetime import datetime
from decimal import Decimal

# Get custom user model
CustomUser = get_user_model()

# Import your existing models (make sure these apps are in INSTALLED_APPS)
try:
    from college.models import CollegeAndUniversities
    HAS_COLLEGE_APP = True
except ImportError:
    HAS_COLLEGE_APP = False
    CollegeAndUniversities = None

try:
    from bursary.models import Bursary
    HAS_BURSARY_APP = True
except ImportError:
    HAS_BURSARY_APP = False
    Bursary = None


class AIService(models.Model):
    """Central AI Service Configuration"""
    class Meta:
        verbose_name = 'AI Service'
        verbose_name_plural = 'AI Services'
        ordering = ['priority']
    
    name = models.CharField(max_length=100)
    provider = models.CharField(
        max_length=20,
        choices=[
            ('openai', 'OpenAI'),
            ('anthropic', 'Anthropic'),
            ('google', 'Google Gemini'),
            ('huggingface', 'Hugging Face')
        ]
    )
    
    # API Configuration
    api_key = models.CharField(max_length=500)
    base_url = models.URLField(max_length=500, blank=True, null=True)
    
    # Model Selection
    model_name = models.CharField(
        max_length=100,
        default='gpt-4-turbo-preview',
        help_text="gpt-4-turbo-preview, claude-3-opus-20240229, etc."
    )
    
    # Capabilities
    max_tokens = models.IntegerField(default=4000)
    temperature = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=Decimal('0.1')
    )
    
    # Status & Priority
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=1, help_text="1 = highest priority")
    
    # Usage Tracking
    total_requests = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)
    last_used = models.DateTimeField(null=True, blank=True)
    
    # Rate Limits
    requests_per_minute = models.IntegerField(default=60)
    requests_per_day = models.IntegerField(default=1000)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.provider})"
    
    def get_client(self):
        """Get the appropriate API client"""
        if self.provider == 'openai':
            return openai.OpenAI(
                api_key=self.api_key,
                base_url=self.base_url if self.base_url else None
            )
        elif self.provider == 'anthropic':
            return anthropic.Anthropic(api_key=self.api_key)
        return None
    
    def can_make_request(self):
        """Check if rate limits allow a new request"""
        from django.core.cache import cache
        cache_key = f"ai_service_{self.id}_minute_count"
        minute_count = cache.get(cache_key, 0)
        
        if minute_count >= self.requests_per_minute:
            return False
        return True
    
    def record_usage(self, tokens_used=0):
        """Record API usage"""
        self.total_requests += 1
        self.total_tokens += tokens_used
        self.last_used = timezone.now()
        self.save()
        
        # Update minute counter in cache
        from django.core.cache import cache
        cache_key = f"ai_service_{self.id}_minute_count"
        current = cache.get(cache_key, 0)
        cache.set(cache_key, current + 1, 60)  # Expires in 60 seconds


class Application(models.Model):
    """Main Application Model - Integrates with your college and bursary apps"""
    
    class Meta:
        verbose_name = 'Application'
        verbose_name_plural = 'Applications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student', 'created_at']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    # ===== STATUS CHOICES =====
    class Status(models.TextChoices):
        DRAFT = 'draft', '📝 Draft'
        READY = 'ready', '✅ Ready for Automation'
        ANALYZING = 'analyzing', '🔍 Analyzing Form'
        FILLING = 'filling', '🖊️ Filling Form'
        WAITING_REVIEW = 'waiting_review', '👀 Waiting for Review'
        COMPLETED = 'completed', '🎉 Form Filled'
        SUBMITTED = 'submitted', '📤 Submitted'
        FAILED = 'failed', '❌ Failed'
    
    # ===== RELATIONSHIPS =====
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='applications',
        verbose_name="Applicant"
    )

     # Add ManyToMany for multiple university selection
    universities = models.ManyToManyField(
        CollegeAndUniversities,
        related_name='applications_multiple',
        blank=True,
        verbose_name="Selected Universities (Multiple)"
    )
    
    
    # Link to your existing College/University model
    selected_university = models.ForeignKey(
        'college.CollegeAndUniversities',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Selected University",
        help_text="Choose from existing universities"
    )
    
    # Link to your existing Bursary model (M2M for multiple selections)
    selected_bursaries = models.ManyToManyField(
        'bursary.Bursary',
        blank=True,
        verbose_name="Selected Bursaries",
        help_text="Select one or more bursaries to apply for"
    )
    
    # ===== EXACT FIELDS FROM YOUR FORM TEMPLATE =====
    
    # 1. Personal Information
    student = models.CharField(
        max_length=200,
        verbose_name="Full Names",
        help_text="Enter Full Names as they appear on ID"
    )
    
    address = models.TextField(
        max_length=1000,
        verbose_name="Full Address",
        help_text="Enter complete address with postal code"
    )
    
    disability = models.TextField(
        max_length=500,
        verbose_name="Disability Information",
        help_text="State any disabilities or 'No' if none",
        blank=True,
        null=True
    )
    
    # 2. University Information (Manual entry as fallback)
    university_manual = models.CharField(
        max_length=500,
        verbose_name="University Name (Manual Entry)",
        help_text="If not in list above, enter university name here",
        blank=True,
        null=True
    )
    
    # 3. Bursary Information (Manual entry as fallback)
    bursary_manual = models.CharField(
        max_length=200,
        verbose_name="Bursary Name (Manual Entry)",
        help_text="If not in list above, enter bursary name here",
        blank=True,
        null=True
    )
    
    # 4. Combined Details Field (for parsing)
    details = models.TextField(
        max_length=2000,
        verbose_name="Application Details",
        help_text="Courses/Faculty, Gender, Marital-status, Home Language, Citizenship, Race, Email, Phone, ID Number, Birth Date, School Name"
    )
    
    # 5. Next of Kin Information
    next_of_kin = models.TextField(
        max_length=1000,
        verbose_name="Next of Kin Details",
        help_text="Full name, address, phone numbers of next of kin",
        blank=True,
        null=True
    )
    
    # 6. Media Files
    profile_image = models.ImageField(
        upload_to="applications/profiles/%Y/%m/%d/",
        verbose_name="Profile Photo",
        null=True,
        blank=True,
        help_text="Upload a clear profile photo"
    )
    
    introduction_video = models.FileField(
        upload_to="applications/videos/%Y/%m/%d/",
        verbose_name="Introduction Video",
        null=True,
        blank=True,
        help_text="Optional: Short introduction video"
    )
    
    # ===== PARSED FIELDS (Auto-extracted from details) =====
    
    # Contact Information
    email = models.EmailField(
        verbose_name="Email Address",
        blank=True,
        null=True
    )
    
    phone = models.CharField(
        max_length=20,
        verbose_name="Phone Number",
        blank=True,
        null=True,
        validators=[RegexValidator(r'^[\d\s\+\-\(\)]+$', 'Enter a valid phone number')]
    )
    
    # Personal Details
    id_number = models.CharField(
        max_length=13,
        verbose_name="ID/Passport Number",
        blank=True,
        null=True
    )
    
    date_of_birth = models.DateField(
        verbose_name="Date of Birth",
        blank=True,
        null=True
    )
    
    gender = models.CharField(
        max_length=20,
        choices=[
            ('male', 'Male'),
            ('female', 'Female'),
            ('other', 'Other'),
            ('prefer_not_to_say', 'Prefer not to say')
        ],
        blank=True,
        null=True
    )
    
    marital_status = models.CharField(
        max_length=20,
        choices=[
            ('single', 'Single'),
            ('married', 'Married'),
            ('divorced', 'Divorced'),
            ('widowed', 'Widowed')
        ],
        blank=True,
        null=True
    )
    
    home_language = models.CharField(
        max_length=50,
        verbose_name="Home Language",
        blank=True,
        null=True
    )
    
    citizenship = models.CharField(
        max_length=50,
        verbose_name="Citizenship",
        blank=True,
        null=True
    )
    
    race = models.CharField(
        max_length=50,
        choices=[
            ('black', 'Black'),
            ('white', 'White'),
            ('coloured', 'Coloured'),
            ('indian', 'Indian/Asian'),
            ('other', 'Other')
        ],
        blank=True,
        null=True
    )
    
    # Academic Information
    course_faculty = models.CharField(
        max_length=500,
        verbose_name="Course/Faculty Choice",
        blank=True,
        null=True
    )
    
    school_name = models.CharField(
        max_length=200,
        verbose_name="High School Name",
        blank=True,
        null=True
    )
    
    matric_year = models.IntegerField(
        verbose_name="Matriculation Year",
        blank=True,
        null=True
    )
    
    # ===== AUTOMATION FIELDS =====
    
    # Target University Form
    target_form_url = models.URLField(
        verbose_name="University Application Form URL",
        max_length=2000,
        blank=True,
        null=True,
        help_text="Paste the exact URL of the university's online application form"
    )
    
    # AI Automation Settings
    preferred_ai_service = models.ForeignKey(
        AIService,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Preferred AI Service"
    )
    
    automation_status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name="Automation Status"
    )
    
    # Automation Results
    automation_log = models.JSONField(
        verbose_name="Automation Activity Log",
        default=list,
        blank=True
    )
    
    field_mapping = models.JSONField(
        verbose_name="Detected Field Mapping",
        blank=True,
        null=True
    )
    
    screenshots = models.JSONField(
        verbose_name="Automation Screenshots",
        default=list,
        blank=True
    )
    
    # Submission Tracking
    submission_reference = models.CharField(
        max_length=100,
        verbose_name="University Reference Number",
        blank=True,
        null=True
    )
    
    submission_date = models.DateTimeField(
        verbose_name="Submission Date",
        blank=True,
        null=True
    )
    
    # ===== METADATA =====
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name="Application Status"
    )
    
    notes = models.TextField(
        verbose_name="Internal Notes",
        blank=True,
        null=True
    )
    
    priority = models.IntegerField(
        verbose_name="Priority Level",
        default=1,
        help_text="Higher number = higher priority"
    )
    
    is_archived = models.BooleanField(
        verbose_name="Archived",
        default=False
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_automation_attempt = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        uni_name = self.get_university_name()
        return f"{self.student} - {uni_name} ({self.get_status_display()})"
    
    # ===== PROPERTIES =====
    
    @property
    def university_name(self):
        """Get university name from either selected or manual entry"""
        if self.selected_university:
            return self.selected_university.title
        return self.university_manual or "Not specified"
    
    @property
    def bursary_names(self):
        """Get list of bursary names"""
        names = []
        if self.selected_bursaries.exists():
            names.extend([b.title for b in self.selected_bursaries.all()])
        if self.bursary_manual:
            names.append(self.bursary_manual)
        return names if names else ["None specified"]
    
    @property
    def progress_percentage(self):
        """Calculate completion percentage"""
        required_fields = [
            'student', 'address', 'email', 'phone',
            'id_number', 'date_of_birth', 'course_faculty'
        ]
        
        completed = 0
        for field in required_fields:
            if getattr(self, field):
                completed += 1
        
        return int((completed / len(required_fields)) * 100)
    
    @property
    def is_ready_for_automation(self):
        """Check if application has all required data for automation"""
        required = [
            self.student, self.email, self.phone,
            self.id_number, self.target_form_url
        ]
        return all(required) and self.status in [self.Status.DRAFT, self.Status.READY]
    
    # ===== METHODS =====
    
    def get_university_name(self):
        """Safe method to get university name"""
        try:
            if self.selected_university:
                return self.selected_university.title
        except:
            pass
        return self.university_manual or "University not specified"
    
    def get_bursary_list(self):
        """Get formatted bursary list"""
        bursaries = []
        if HAS_BURSARY_APP and self.selected_bursaries.exists():
            bursaries.extend([b.title for b in self.selected_bursaries.all()])
        if self.bursary_manual:
            bursaries.append(self.bursary_manual)
        return ", ".join(bursaries) if bursaries else "No bursaries selected"
    
    def parse_details_field(self):
        """Intelligently parse the details field into structured data"""
        if not self.details:
            return {}
        
        parsed = {}
        text = self.details.lower()
        
        # Extract email
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', self.details)
        if email_match:
            parsed['email'] = email_match.group(0)
        
        # Extract phone (South African formats)
        phone_patterns = [
            r'(\+27|0)[\s]?\d{2}[\s]?\d{3}[\s]?\d{4}',
            r'\(\d{3}\)\s?\d{3}[\s-]?\d{4}',
            r'\d{3}[\s.-]?\d{3}[\s.-]?\d{4}'
        ]
        
        for pattern in phone_patterns:
            phone_match = re.search(pattern, self.details)
            if phone_match:
                parsed['phone'] = phone_match.group(0)
                break
        
        # Extract ID Number (South African format)
        id_match = re.search(r'\b\d{13}\b', self.details)
        if id_match:
            parsed['id_number'] = id_match.group(0)
        
        # Extract date of birth
        date_patterns = [
            r'\b(\d{2})[/-](\d{2})[/-](\d{4})\b',
            r'\b(\d{4})[/-](\d{2})[/-](\d{2})\b',
            r'\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})\b'
        ]
        
        for pattern in date_patterns:
            date_match = re.search(pattern, self.details, re.IGNORECASE)
            if date_match:
                try:
                    if '/' in date_match.group(0) or '-' in date_match.group(0):
                        parsed['date_of_birth'] = date_match.group(0)
                except:
                    pass
                break
        
        # Parse key-value pairs from details
        lines = [line.strip() for line in self.details.split('\n') if line.strip()]
        
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key_lower = key.lower().strip()
                value = value.strip()
                
                # Map keys to model fields
                field_mapping = {
                    'course': 'course_faculty',
                    'faculty': 'course_faculty',
                    'program': 'course_faculty',
                    'gender': 'gender',
                    'sex': 'gender',
                    'marital': 'marital_status',
                    'status': 'marital_status',
                    'language': 'home_language',
                    'home lang': 'home_language',
                    'citizenship': 'citizenship',
                    'nationality': 'citizenship',
                    'race': 'race',
                    'population': 'race',
                    'id': 'id_number',
                    'id number': 'id_number',
                    'passport': 'id_number',
                    'birth': 'date_of_birth',
                    'dob': 'date_of_birth',
                    'date of birth': 'date_of_birth',
                    'school': 'school_name',
                    'high school': 'school_name',
                    'matric': 'school_name',
                    'year': 'matric_year',
                    'matric year': 'matric_year',
                    'completion': 'matric_year',
                    'phone': 'phone',
                    'cell': 'phone',
                    'tel': 'phone',
                    'contact': 'phone',
                    'email': 'email',
                    'e-mail': 'email'
                }
                
                for keyword, field_name in field_mapping.items():
                    if keyword in key_lower:
                        parsed[field_name] = value
                        break
        
        return parsed
    
    def get_structured_data(self):
        """Get all application data in structured format for AI automation"""
        return {
            'application_id': self.id,
            'timestamp': timezone.now().isoformat(),
            
            'personal_information': {
                'full_name': self.student,
                'id_number': self.id_number,
                'date_of_birth': str(self.date_of_birth) if self.date_of_birth else '',
                'gender': self.gender,
                'marital_status': self.marital_status,
                'citizenship': self.citizenship,
                'race': self.race,
                'home_language': self.home_language,
                'disability': self.disability or 'None',
            },
            
            'contact_information': {
                'address': self.address,
                'email': self.email,
                'phone': self.phone,
            },
            
            'academic_information': {
                'university': self.university_name,
                'course_faculty': self.course_faculty,
                'high_school': self.school_name,
                'matric_year': self.matric_year,
                'target_form_url': self.target_form_url,
            },
            
            'financial_information': {
                'bursaries': self.bursary_names,
            },
            
            'next_of_kin': self.parse_next_of_kin(),
            
            'documents': {
                'has_profile_image': bool(self.profile_image),
                'has_introduction_video': bool(self.introduction_video),
            },
            
            'automation_data': {
                'status': self.automation_status,
                'progress': self.progress_percentage,
                'ready_for_automation': self.is_ready_for_automation,
                'last_attempt': str(self.last_automation_attempt) if self.last_automation_attempt else None,
            }
        }
    
    def parse_next_of_kin(self):
        """Parse next of kin information"""
        if not self.next_of_kin:
            return {}
        
        # Simple parsing - can be enhanced
        lines = self.next_of_kin.split(',')
        parsed = {
            'name': lines[0].strip() if len(lines) > 0 else '',
            'address': lines[1].strip() if len(lines) > 1 else '',
            'phone': lines[2].strip() if len(lines) > 2 else '',
            'relationship': lines[3].strip() if len(lines) > 3 else 'Parent',
        }
        
        return parsed
    
    def add_automation_log(self, message, level='info', data=None):
        """Add entry to automation log"""
        log_entry = {
            'timestamp': timezone.now().isoformat(),
            'level': level,
            'message': message,
            'data': data or {}
        }
        
        if not self.automation_log:
            self.automation_log = []
        
        self.automation_log.append(log_entry)
        
        # Keep only last 100 entries
        if len(self.automation_log) > 100:
            self.automation_log = self.automation_log[-100:]
        
        self.save()
    
    def update_automation_status(self, new_status, message=None):
        """Update automation status with log entry"""
        self.automation_status = new_status
        self.last_automation_attempt = timezone.now()
        
        if message:
            self.add_automation_log(
                f"Status changed to {new_status}: {message}",
                level='info'
            )
        
        self.save()
    
    def take_screenshot(self, screenshot_data, description=""):
        """Add screenshot to application"""
        if not self.screenshots:
            self.screenshots = []
        
        screenshot_entry = {
            'timestamp': timezone.now().isoformat(),
            'description': description,
            'data': screenshot_data[:500] if screenshot_data else '',  # Store first 500 chars
            'size': len(screenshot_data) if screenshot_data else 0
        }
        
        self.screenshots.append(screenshot_entry)
        self.save()
    
    def get_ai_service(self):
        """Get the appropriate AI service to use"""
        if self.preferred_ai_service and self.preferred_ai_service.is_active:
            return self.preferred_ai_service
        
        # Fallback: get first active service
        try:
            return AIService.objects.filter(is_active=True).first()
        except AIService.DoesNotExist:
            return None
    
    def prepare_for_automation(self):
        """Prepare application for automation"""
        if not self.is_ready_for_automation:
            return False
        
        # Update status
        self.update_automation_status(self.Status.READY, "Application ready for automation")
        
        # Ensure we have parsed all details
        if self.details and not self.email:
            parsed = self.parse_details_field()
            for field, value in parsed.items():
                if hasattr(self, field) and not getattr(self, field):
                    setattr(self, field, value)
        
        self.save()
        return True
    
    # ===== SAVE METHODS =====
    
    def save(self, *args, **kwargs):
        """Override save to auto-parse details and update timestamps"""
        
        # Auto-parse details field on creation or if details changed
        if self.details and (not self.pk or self.details != self._original_details):
            parsed = self.parse_details_field()
            for field, value in parsed.items():
                if hasattr(self, field) and not getattr(self, field):
                    setattr(self, field, value)
        
        # Auto-set target URL if we have university with website
        if not self.target_form_url and self.selected_university:
            if self.selected_university.website_url:
                # Try to construct application URL
                base_url = self.selected_university.website_url
                if 'apply' not in base_url and 'application' not in base_url:
                    self.target_form_url = f"{base_url.rstrip('/')}/apply"
                else:
                    self.target_form_url = base_url
        
        # Update submission date if status changes to submitted
        if self.status == self.Status.SUBMITTED and not self.submission_date:
            self.submission_date = timezone.now()
        
        super().save(*args, **kwargs)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_details = self.details


class AutomationSession(models.Model):
    """Tracks individual automation sessions"""
    
    class Meta:
        verbose_name = 'Automation Session'
        verbose_name_plural = 'Automation Sessions'
        ordering = ['-started_at']
    
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    
    session_id = models.CharField(max_length=100, unique=True)
    
    # AI Service used
    ai_service = models.ForeignKey(
        AIService,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Session Details
    target_url = models.URLField(max_length=2000)
    browser_type = models.CharField(max_length=50, default='chromium')
    
    # Progress Tracking
    total_steps = models.IntegerField(default=0)
    completed_steps = models.IntegerField(default=0)
    current_step = models.CharField(max_length=200, blank=True, null=True)
    
    # Results
    detected_fields = models.JSONField(default=list, blank=True)
    filled_fields = models.JSONField(default=list, blank=True)
    errors = models.JSONField(default=list, blank=True)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Application.Status.choices,
        default=Application.Status.DRAFT
    )
    
    # Timestamps
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Session {self.session_id} - {self.application.student}"
    
    @property
    def duration(self):
        if self.ended_at:
            return self.ended_at - self.started_at
        return timezone.now() - self.started_at
    
    @property
    def progress_percentage(self):
        if self.total_steps == 0:
            return 0
        return int((self.completed_steps / self.total_steps) * 100)


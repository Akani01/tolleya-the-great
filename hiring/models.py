from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from django.db.models import Avg, Count
import json
from datetime import timedelta
import re
from collections import Counter
from django.contrib.auth import get_user_model
import uuid
import os
from django.conf import settings

# Import models from main_app
from main_app.models import Industry, BusinessProfile, Post, JobListing, CustomUser

User = get_user_model()

# ===== APPLICANT PROFILE MODELS =====

class ApplicantProfile(models.Model):
    TITLE_CHOICES = (
        ('mr', 'Mr'), ('ms', 'Ms'), ('mrs', 'Mrs'), ('dr', 'Dr')
    )
    GENDER_CHOICES = (
        ('male', 'Male'), ('female', 'Female'), ('other', 'Other')
    )
    ETHNICITY_CHOICES = (
        ('african', 'African'), ('coloured', 'Coloured'), ('indian', 'Indian'), 
        ('white', 'White'), ('other', 'Other')
    )
    CITIZENSHIP_CHOICES = (
        ('south_african', 'South African Citizen'), 
        ('permanent_resident', 'Permanent Resident'), 
        ('work_permit', 'Work Permit'), 
        ('other', 'Other')
    )
    SALARY_RANGE_CHOICES = (
        ('0_50k', '0 - 50K Annually'), 
        ('50_100k', '50 - 100K Annually'), 
        ('100_150k', '100 - 150K Annually'), 
        ('150_200k', '150 - 200K Annually'), 
        ('200k_plus', '200K+ Annually')
    )
    
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    title = models.CharField(max_length=10, choices=TITLE_CHOICES, blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    ethnicity = models.CharField(max_length=20, choices=ETHNICITY_CHOICES, blank=True, null=True)
    disabled = models.BooleanField(default=False)
    is_citizen = models.CharField(max_length=20, choices=CITIZENSHIP_CHOICES, blank=True, null=True)
    national_id = models.CharField(max_length=20, blank=True, null=True)
    passport_number = models.CharField(max_length=20, blank=True, null=True)
    birth_date = models.DateField(null=True, blank=True)
    current_home_location = models.CharField(max_length=100, blank=True)
    has_drivers_license = models.BooleanField(default=False)
    has_own_transport = models.BooleanField(default=False)
    preferred_job_title = models.CharField(max_length=100, blank=True)
    availability = models.CharField(max_length=50, default='Immediate')
    willing_to_relocate = models.BooleanField(default=False)
    current_salary = models.CharField(max_length=20, choices=SALARY_RANGE_CHOICES, blank=True, null=True)
    desired_salary = models.CharField(max_length=20, choices=SALARY_RANGE_CHOICES, blank=True, null=True)
    introduction = models.TextField(blank=True)
    profile_completeness = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'hiring'
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class Skill(models.Model):
    PROFICIENCY_CHOICES = (
        ('beginner', 'Beginner'), 
        ('intermediate', 'Intermediate'), 
        ('good', 'Good'), 
        ('expert', 'Expert')
    )
    
    profile = models.ForeignKey(
        'ApplicantProfile', 
        on_delete=models.CASCADE, 
        related_name='skills',
        null=True,
        blank=True
    )
    skill_name = models.CharField(max_length=100)
    proficiency = models.CharField(max_length=15, choices=PROFICIENCY_CHOICES, default='good')
    
    is_business_recommended = models.BooleanField(default=False)
    recommended_by_business = models.ForeignKey(
        BusinessProfile, 
        on_delete=models.CASCADE,
        null=True, 
        blank=True,
        related_name='recommended_skills'
    )
    
    class Meta:
        app_label = 'hiring'
    
    def __str__(self):
        return f"{self.skill_name} ({self.proficiency})"
    
    def save(self, *args, **kwargs):
        if self.is_business_recommended:
            if not self.recommended_by_business:
                raise ValueError("Business recommended skills must have a business profile")
            if self.profile:
                raise ValueError("Business recommended skills should not have an applicant profile")
        else:
            if not self.profile:
                raise ValueError("Applicant skills must have an applicant profile")
            if self.recommended_by_business:
                raise ValueError("Applicant skills should not have a business profile")
        
        super().save(*args, **kwargs)

class Education(models.Model):
    profile = models.ForeignKey('ApplicantProfile', on_delete=models.CASCADE, related_name='education')
    qualification = models.CharField(max_length=200)
    institution = models.CharField(max_length=200)
    completion_year = models.IntegerField()
    major_subject = models.CharField(max_length=100, blank=True)
    grade = models.CharField(max_length=50, blank=True)
    
    class Meta:
        app_label = 'hiring'
        verbose_name_plural = 'Education'
    
    def __str__(self):
        return f"{self.qualification} - {self.institution}"

class Document(models.Model):
    DOCUMENT_TYPES = (
        ('cv', 'CV'), 
        ('id', 'ID Document'), 
        ('certificate', 'Certificate'), 
        ('transcript', 'Transcript'), 
        ('other', 'Other')
    )
    
    profile = models.ForeignKey('ApplicantProfile', on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES)
    file = models.FileField(
        upload_to='documents/%Y/%m/%d/', 
        validators=[FileExtensionValidator(['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'])]
    )
    file_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'hiring'
    
    def __str__(self):
        return f"{self.file_name} ({self.document_type})"

# ===== BUSINESS PROFILE MODELS =====

class JobCategory(models.Model):
    name = models.CharField(max_length=100)
    industry = models.ForeignKey(Industry, on_delete=models.CASCADE, related_name='job_categories')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'hiring'
        verbose_name_plural = 'Job Categories'
        ordering = ['name']
        unique_together = ['name', 'industry']
    
    def __str__(self):
        return f"{self.name} ({self.industry.name})"

class BusinessPreference(models.Model):
    PREFERENCE_TYPES = (
        ('education', 'Education'),
        ('skills', 'Skills'), 
        ('employment', 'Employment'),
        ('experience', 'Experience'),
        ('certifications', 'Certifications'),
        ('languages', 'Languages'),
        ('location', 'Location'),
        ('industry', 'Industry'),
        ('custom', 'Custom'),
    )
    
    business_profile = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, related_name='preferences')
    preference_type = models.CharField(max_length=20, choices=PREFERENCE_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    criteria = models.JSONField(default=dict, blank=True)
    positions_available = models.PositiveIntegerField(default=1)
    priority_level = models.CharField(max_length=20, choices=(
        ('low', 'Low'),
        ('medium', 'Medium'), 
        ('high', 'High'),
        ('critical', 'Critical'),
    ), default='medium')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'hiring'
        ordering = ['-priority_level', '-created_at']
    
    def __str__(self):
        return f"{self.preference_type}: {self.title} ({self.positions_available} positions)"
    
    @property
    def criteria_summary(self):
        if not self.criteria:
            return "No specific criteria"
        
        summary = []
        for key, value in self.criteria.items():
            if value:
                if isinstance(value, list):
                    summary.append(f"{key}: {', '.join(str(v) for v in value)}")
                else:
                    summary.append(f"{key}: {value}")
        
        return "; ".join(summary)

class BusinessEmploymentPreference(models.Model):
    CONTRACT_TYPE_CHOICES = (
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('freelance', 'Freelance'),
        ('internship', 'Internship'),
        ('remote', 'Remote'),
        ('hybrid', 'Hybrid'),
    )
    
    business_profile = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, related_name='employment_preferences')
    preferred_contract_type = models.CharField(max_length=20, choices=CONTRACT_TYPE_CHOICES)
    positions_available = models.PositiveIntegerField(default=1)
    job_title_keywords = models.JSONField(default=list, blank=True)
    required_experience_years = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'hiring'
        verbose_name_plural = 'Business Employment Preferences'
    
    def __str__(self):
        return f"{self.get_preferred_contract_type_display()} - {self.positions_available} positions"

class EmploymentHistory(models.Model):
    CONTRACT_TYPE_CHOICES = (
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('freelance', 'Freelance'),
        ('internship', 'Internship'),
    )
    
    profile = models.ForeignKey(ApplicantProfile, on_delete=models.CASCADE, related_name='employment_history')
    job_title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True, null=True)
    contract_type = models.CharField(max_length=20, choices=CONTRACT_TYPE_CHOICES, blank=True, null=True)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    currently_working = models.BooleanField(default=False)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'hiring'
        verbose_name_plural = 'Employment Histories'
    
    def __str__(self):
        return f"{self.job_title} at {self.company}"
    
    @property
    def experience_months(self):
        end_date = self.end_date if not self.currently_working else timezone.now().date()
        if self.start_date and end_date:
            return (end_date.year - self.start_date.year) * 12 + (end_date.month - self.start_date.month)
        return 0

# ===== JOB LISTING MODELS =====

class Application(models.Model):
    APPLICATION_STATUS = (
        ('submitted', 'Submitted'), 
        ('under_review', 'Under Review'), 
        ('shortlisted', 'Shortlisted'), 
        ('interview', 'Interview'), 
        ('successful', 'Successful'), 
        ('unsuccessful', 'Unsuccessful')
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    applicant = models.ForeignKey('ApplicantProfile', on_delete=models.CASCADE, related_name='applications')
    job_listing = models.ForeignKey(JobListing, on_delete=models.CASCADE, related_name='applications')
    status = models.CharField(max_length=20, choices=APPLICATION_STATUS, default='submitted')
    applied_date = models.DateTimeField(auto_now_add=True)
    cover_letter = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        app_label = 'hiring'
        unique_together = ['applicant', 'job_listing']
    
    def __str__(self):
        return f"{self.applicant} - {self.job_listing}"

# ===== NOTIFICATION AND ALERT MODELS =====

class NotificationPreference(models.Model):
    NOTIFICATION_TYPES = (
        ('email', 'Email'), 
        ('in_app', 'In-App'), 
        ('both', 'Both')
    )
    
    applicant = models.OneToOneField('ApplicantProfile', on_delete=models.CASCADE, related_name='notification_preferences')
    notification_type = models.CharField(max_length=10, choices=NOTIFICATION_TYPES, default='both')
    application_updates = models.BooleanField(default=True)
    job_alerts = models.BooleanField(default=True)
    profile_reminders = models.BooleanField(default=True)
    weekly_digest = models.BooleanField(default=True)
    marketing_emails = models.BooleanField(default=False)
    
    class Meta:
        app_label = 'hiring'
    
    def __str__(self):
        return f"Notification preferences for {self.applicant}"

class Alert(models.Model):
    applicant = models.ForeignKey('ApplicantProfile', on_delete=models.CASCADE, related_name='alerts')
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'hiring'
    
    def __str__(self):
        return f"Alert for {self.applicant}: {self.title}"

class EmailTemplate(models.Model):
    TEMPLATE_TYPES = (
        ('application_submitted', 'Application Submitted'), 
        ('application_status_update', 'Application Status Update'), 
        ('job_alert', 'Job Alert'), 
        ('profile_reminder', 'Profile Reminder'), 
        ('weekly_digest', 'Weekly Digest'), 
        ('welcome', 'Welcome Email')
    )
    
    name = models.CharField(max_length=100)
    template_type = models.CharField(max_length=50, choices=TEMPLATE_TYPES)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'hiring'
    
    def __str__(self):
        return f"{self.name} ({self.template_type})"

class SentNotification(models.Model):
    applicant = models.ForeignKey('ApplicantProfile', on_delete=models.CASCADE, related_name='sent_notifications')
    notification_type = models.CharField(max_length=50)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    sent_via = models.CharField(max_length=10, choices=NotificationPreference.NOTIFICATION_TYPES)
    sent_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        app_label = 'hiring'
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"{self.subject} to {self.applicant}"

class JobAlert(models.Model):
    FREQUENCY_CHOICES = (
        ('daily', 'Daily'), 
        ('weekly', 'Weekly'), 
        ('instant', 'Instant')
    )
    
    applicant = models.ForeignKey('ApplicantProfile', on_delete=models.CASCADE, related_name='job_alerts')
    keywords = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=100, blank=True)
    job_category = models.CharField(max_length=100, blank=True)
    frequency = models.CharField(max_length=10, choices=FREQUENCY_CHOICES, default='weekly')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_sent = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        app_label = 'hiring'
    
    def __str__(self):
        return f"Job alert for {self.applicant}"

class SearchHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='search_history')
    query = models.CharField(max_length=255)
    filters = models.JSONField(default=dict, blank=True)
    results_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'hiring'
        ordering = ['-created_at']
        verbose_name_plural = 'Search Histories'

    def __str__(self):
        return f"{self.user.username} - {self.query}"

# ===== BUSINESS NOTIFICATION MODELS =====

class BusinessNotificationPreference(models.Model):
    business = models.OneToOneField(BusinessProfile, on_delete=models.CASCADE, related_name='notification_preferences')
    email_notifications = models.BooleanField(default=True)
    in_app_notifications = models.BooleanField(default=True)
    new_applications = models.BooleanField(default=True)
    job_expiry_alerts = models.BooleanField(default=True)
    candidate_updates = models.BooleanField(default=True)
    system_maintenance = models.BooleanField(default=False)
    marketing_emails = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'hiring'
    
    def __str__(self):
        return f"Notifications for {self.business.company_name}"

class BusinessAlert(models.Model):
    ALERT_TYPES = (
        ('application', 'New Application'),
        ('expiry', 'Job Expiry'),
        ('custom', 'Custom Alert'),
        ('system', 'System Alert')
    )
    
    business = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, related_name='business_alerts')
    job_listing = models.ForeignKey(JobListing, on_delete=models.CASCADE, null=True, blank=True, related_name='business_alerts')
    alert_type = models.CharField(max_length=50, choices=ALERT_TYPES, default='custom')
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_active = models.BooleanField(default=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'hiring'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.business.company_name}"

class BusinessSentNotification(models.Model):
    NOTIFICATION_TYPES = (
        ('application', 'Application Update'),
        ('job', 'Job Update'),
        ('system', 'System Notification'),
        ('marketing', 'Marketing')
    )
    
    business = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, related_name='sent_notifications')
    subject = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES, default='system')
    sent_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    class Meta:
        app_label = 'hiring'
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"{self.subject} - {self.business.company_name}"

# ===== MESSAGING SYSTEM MODELS =====

class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participants = models.ManyToManyField(CustomUser, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = 'hiring'
        ordering = ['-updated_at']

    def __str__(self):
        participant_names = [user.username for user in self.participants.all()]
        return f"Conversation between {', '.join(participant_names)}"

class Message(models.Model):
    MESSAGE_TYPES = (
        ('text', 'Text'),
        ('file', 'File'),
        ('image', 'Image'),
        ('video', 'Video'),
        ('audio', 'Audio'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField(blank=True, null=True)
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='text')
    file = models.FileField(upload_to='message_files/', blank=True, null=True)
    file_name = models.CharField(max_length=255, blank=True, null=True)
    file_size = models.BigIntegerField(blank=True, null=True)
    file_mime_type = models.CharField(max_length=100, blank=True, null=True)
    
    parent_message = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies')
    
    is_forwarded = models.BooleanField(default=False)
    original_sender = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='forwarded_messages')
    
    is_read = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'hiring'
        ordering = ['created_at']

    def __str__(self):
        return f"Message from {self.sender.username} in {self.conversation.id}"

class MessageRecipient(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='recipients')
    recipient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='received_messages')
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'hiring'
        unique_together = ['message', 'recipient']

class UserStatus(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='chat_status')
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(auto_now=True)
    typing_to = models.ForeignKey(Conversation, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        app_label = 'hiring'

    def __str__(self):
        return f"{self.user.username} - {'Online' if self.is_online else 'Offline'}"

class BusinessProfileView(models.Model):
    business_profile = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, related_name='views')
    viewer = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    viewed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        db_table = 'business_profile_views'

class Rating(models.Model):
    RATING_CHOICES = [
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    ]
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='ratings')
    rating = models.IntegerField(choices=RATING_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'post']

class PostView(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='post_views')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    viewed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['post', 'ip_address']

class JobInteraction(models.Model):
    INTERACTION_TYPES = (
        ('like', 'Like'),
        ('dislike', 'Dislike'),
        ('comment', 'Comment'),
    )
    
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    job_listing = models.ForeignKey(JobListing, on_delete=models.CASCADE)
    interaction_type = models.CharField(max_length=10, choices=INTERACTION_TYPES)
    comment_text = models.TextField(blank=True, null=True)
    parent_interaction = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'job_listing', 'interaction_type']
    
    def __str__(self):
        return f"{self.user.username} {self.interaction_type} on {self.job_listing.title}"
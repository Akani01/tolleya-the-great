from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import *

class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'user_type', 'mobile_phone', 'is_staff', 'date_joined')
    list_filter = ('user_type', 'is_staff', 'is_superuser', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    readonly_fields = ('date_joined', 'last_login')
    
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('user_type', 'mobile_phone')}),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('applicantprofile')

class ApplicantProfileAdmin(admin.ModelAdmin):
    list_display = ('get_username', 'get_email', 'first_name', 'last_name', 'profile_completeness', 'created_at')
    list_filter = ('ethnicity', 'disabled', 'willing_to_relocate', 'created_at')
    search_fields = ('first_name', 'last_name', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at', 'profile_completeness')
    list_per_page = 20
    
    fieldsets = (
        ('Personal Information', {
            'fields': (
                'user', 'title', 'gender', 'first_name', 'last_name', 
                'ethnicity', 'disabled', 'birth_date'
            )
        }),
        ('Citizenship & Identification', {
            'fields': ('is_citizen', 'national_id', 'passport_number')
        }),
        ('Location & Transport', {
            'fields': ('current_home_location', 'has_drivers_license', 'has_own_transport')
        }),
        ('Career Preferences', {
            'fields': (
                'preferred_job_title', 'availability', 'willing_to_relocate',
                'current_salary', 'desired_salary', 'introduction'
            )
        }),
        ('System Information', {
            'fields': ('profile_completeness', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = 'Username'
    get_username.admin_order_field = 'user__username'
    
    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'
    get_email.admin_order_field = 'user__email'

class JobListingAdmin(admin.ModelAdmin):
    list_display = ('title', 'listing_reference', 'status', 'company_name', 'location', 'apply_by', 'created_at')
    list_filter = ('status', 'industry', 'contract_type', 'created_at')
    search_fields = ('title', 'company_name', 'listing_reference', 'location')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('status',)
    list_per_page = 25
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'listing_reference', 'title', 'status', 'apply_by', 
                'industry', 'job_category', 'location', 'contract_type'
            )
        }),
        ('Company Information', {
            'fields': ('company_name', 'company_logo', 'company_description')
        }),
        ('Position Details', {
            'fields': ('position_summary', 'job_description', 'ee_position')
        }),
        ('Requirements', {
            'fields': (
                'knowledge_requirements', 'skills_requirements', 
                'competencies_requirements', 'experience_requirements', 
                'education_requirements'
            )
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('get_applicant_name', 'get_job_title', 'status', 'applied_date', 'get_company')
    list_filter = ('status', 'applied_date', 'job_listing__company_name')
    search_fields = (
        'applicant__first_name', 'applicant__last_name', 
        'job_listing__title', 'job_listing__company_name'
    )
    readonly_fields = ('applied_date',)
    list_per_page = 30
    
    def get_applicant_name(self, obj):
        return f"{obj.applicant.first_name} {obj.applicant.last_name}"
    get_applicant_name.short_description = 'Applicant'
    get_applicant_name.admin_order_field = 'applicant__first_name'
    
    def get_job_title(self, obj):
        return obj.job_listing.title
    get_job_title.short_description = 'Job Title'
    get_job_title.admin_order_field = 'job_listing__title'
    
    def get_company(self, obj):
        return obj.job_listing.company_name
    get_company.short_description = 'Company'
    get_company.admin_order_field = 'job_listing__company_name'

class SkillAdmin(admin.ModelAdmin):
    list_display = ('get_applicant', 'skill_name', 'proficiency')
    list_filter = ('proficiency',)
    search_fields = ('skill_name', 'profile__first_name', 'profile__last_name')
    
    def get_applicant(self, obj):
        return f"{obj.profile.first_name} {obj.profile.last_name}"
    get_applicant.short_description = 'Applicant'
    get_applicant.admin_order_field = 'profile__first_name'

class EmploymentHistoryAdmin(admin.ModelAdmin):
    list_display = ('get_applicant', 'job_title', 'company', 'start_date', 'end_date', 'contract_type')
    list_filter = ('contract_type', 'start_date')
    search_fields = ('job_title', 'company', 'profile__first_name', 'profile__last_name')
    
    def get_applicant(self, obj):
        return f"{obj.profile.first_name} {obj.profile.last_name}"
    get_applicant.short_description = 'Applicant'
    get_applicant.admin_order_field = 'profile__first_name'

class EducationAdmin(admin.ModelAdmin):
    list_display = ('get_applicant', 'qualification', 'institution', 'completion_year')
    list_filter = ('completion_year',)
    search_fields = ('qualification', 'institution', 'profile__first_name', 'profile__last_name')
    
    def get_applicant(self, obj):
        return f"{obj.profile.first_name} {obj.profile.last_name}"
    get_applicant.short_description = 'Applicant'
    get_applicant.admin_order_field = 'profile__first_name'

class DocumentAdmin(admin.ModelAdmin):
    list_display = ('get_applicant', 'document_type', 'file_name', 'uploaded_at')
    list_filter = ('document_type', 'uploaded_at')
    search_fields = ('file_name', 'profile__first_name', 'profile__last_name')
    readonly_fields = ('uploaded_at',)
    
    def get_applicant(self, obj):
        return f"{obj.profile.first_name} {obj.profile.last_name}"
    get_applicant.short_description = 'Applicant'
    get_applicant.admin_order_field = 'profile__first_name'

class AlertAdmin(admin.ModelAdmin):
    list_display = ('get_applicant', 'title', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('title', 'message', 'applicant__first_name', 'applicant__last_name')
    readonly_fields = ('created_at',)
    
    def get_applicant(self, obj):
        return f"{obj.applicant.first_name} {obj.applicant.last_name}"
    get_applicant.short_description = 'Applicant'
    get_applicant.admin_order_field = 'applicant__first_name'

class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('get_applicant', 'notification_type', 'application_updates', 'job_alerts')
    list_filter = ('notification_type', 'application_updates', 'job_alerts')
    
    def get_applicant(self, obj):
        return f"{obj.applicant.first_name} {obj.applicant.last_name}"
    get_applicant.short_description = 'Applicant'
    get_applicant.admin_order_field = 'applicant__first_name'

class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'template_type', 'is_active', 'created_at')
    list_filter = ('template_type', 'is_active', 'created_at')
    search_fields = ('name', 'subject', 'template_type')
    readonly_fields = ('created_at',)
    list_editable = ('is_active',)

class SentNotificationAdmin(admin.ModelAdmin):
    list_display = ('get_applicant', 'subject', 'notification_type', 'sent_via', 'is_read', 'sent_at')
    list_filter = ('notification_type', 'sent_via', 'is_read', 'sent_at')
    search_fields = ('subject', 'applicant__first_name', 'applicant__last_name')
    readonly_fields = ('sent_at',)
    
    def get_applicant(self, obj):
        return f"{obj.applicant.first_name} {obj.applicant.last_name}"
    get_applicant.short_description = 'Applicant'
    get_applicant.admin_order_field = 'applicant__first_name'

class JobAlertAdmin(admin.ModelAdmin):
    list_display = ('get_applicant', 'keywords', 'location', 'frequency', 'is_active', 'created_at')
    list_filter = ('frequency', 'is_active', 'created_at')
    search_fields = ('keywords', 'location', 'applicant__first_name', 'applicant__last_name')
    readonly_fields = ('created_at', 'last_sent')
    
    def get_applicant(self, obj):
        return f"{obj.applicant.first_name} {obj.applicant.last_name}"
    get_applicant.short_description = 'Applicant'
    get_applicant.admin_order_field = 'applicant__first_name'

# Register all models with their custom admin classes
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(ApplicantProfile, ApplicantProfileAdmin)
admin.site.register(JobListing, JobListingAdmin)
admin.site.register(Application, ApplicationAdmin)
admin.site.register(Skill, SkillAdmin)
admin.site.register(EmploymentHistory, EmploymentHistoryAdmin)
admin.site.register(Education, EducationAdmin)
admin.site.register(Document, DocumentAdmin)
admin.site.register(Alert, AlertAdmin)
admin.site.register(NotificationPreference, NotificationPreferenceAdmin)
admin.site.register(EmailTemplate, EmailTemplateAdmin)
admin.site.register(SentNotification, SentNotificationAdmin)
admin.site.register(JobAlert, JobAlertAdmin)

# Customize admin site header and title
admin.site.site_header = "Hiring Portal Platform Administration"
admin.site.site_title = "System Admin"
admin.site.index_title = "Welcome to Hiring Portal Platform Administration"
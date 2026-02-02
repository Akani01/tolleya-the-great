# serializers.py
from rest_framework import serializers
from .models import *
import os

# Define the choices that are missing
SKILL_PROFICIENCY_LEVELS = [
    ('beginner', 'Beginner'),
    ('intermediate', 'Intermediate'), 
    ('good', 'Good'),
    ('expert', 'Expert')
]


def has_business_access(user):
    """
    Check if user has business access.
    Returns True if user is in Business group or has business profile.
    """
    # Option 1: Check by group name
    if user.groups.filter(name='Business').exists():
        return True
    
    # Option 2: Check if user has a business profile
    from .models import BusinessProfile
    if BusinessProfile.objects.filter(user=user).exists():
        return True
    
    # Option 3: Check custom user field if you have one
    if hasattr(user, 'is_business_user') and user.is_business_user:
        return True
        
    return False
# ==================== USER SERIALIZERS ====================

class CustomUserSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'user_type', 
                 'mobile_phone', 'display_name', 'is_online']
    
    def get_display_name(self, obj):
        """Get display name from ApplicantProfile if available"""
        if hasattr(obj, 'applicantprofile') and obj.applicantprofile:
            profile = obj.applicantprofile
            full_name = f"{profile.first_name} {profile.last_name}".strip()
            if full_name:
                return full_name
        return obj.username
    
    def get_is_online(self, obj):
        """Get online status from UserProfile"""
        if hasattr(obj, 'profile'):
            return obj.profile.is_online
        return False

class SimpleUserSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'display_name', 'is_online']
    
    def get_display_name(self, obj):
        """Get display name from ApplicantProfile if available"""
        if hasattr(obj, 'applicantprofile') and obj.applicantprofile:
            profile = obj.applicantprofile
            full_name = f"{profile.first_name} {profile.last_name}".strip()
            if full_name:
                return full_name
        return obj.username
    
    def get_is_online(self, obj):
        """Get online status from UserProfile"""
        if hasattr(obj, 'profile'):
            return obj.profile.is_online
        return False

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'email', 'user_type', 'mobile_phone', 'first_name', 'last_name')
        read_only_fields = ('id', 'user_type')


# ==================== AUTHENTICATION SERIALIZERS ====================

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, 
        required=True,
        min_length=8,
        error_messages={
            'min_length': 'Password must be at least 8 characters long.',
            'required': 'Password is required.'
        }
    )
    password_confirm = serializers.CharField(
        write_only=True, 
        required=True,
        min_length=8,
        error_messages={
            'min_length': 'Password must be at least 8 characters long.',
            'required': 'Please confirm your password.'
        }
    )
    mobile_phone = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    
    username = serializers.CharField(
        required=True,
        min_length=2,
        max_length=150,
        error_messages={
            'min_length': 'Username must be at least 2 characters long.',
            'max_length': 'Username cannot be longer than 150 characters.',
            'required': 'Username is required.'
        }
    )

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'mobile_phone', 'password', 'password_confirm', 'first_name', 'last_name')

    def validate_username(self, value):
        if CustomUser.objects.filter(username=value).exists():
            raise serializers.ValidationError("This username is already taken. Please choose a different one.")
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Password fields didn't match."})
        
        if CustomUser.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({"email": "This email is already registered."})
        
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = CustomUser.objects.create_user(**validated_data)
        user.set_password(password)
        user.user_type = 'applicant'
        user.save()
        return user


# ==================== PROFILE SERIALIZERS ====================

class ApplicantProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = ApplicantProfile
        fields = '__all__'
        read_only_fields = ('user', 'profile_completeness', 'created_at', 'updated_at')

class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicantProfile
        fields = [
            'title', 'gender', 'first_name', 'last_name', 'ethnicity', 'disabled',
            'is_citizen', 'national_id', 'passport_number', 'birth_date',
            'current_home_location', 'has_drivers_license', 'has_own_transport',
            'preferred_job_title', 'availability', 'willing_to_relocate',
            'current_salary', 'desired_salary', 'introduction'
        ]
        extra_kwargs = {
            'first_name': {'required': False, 'allow_blank': True},
            'last_name': {'required': False, 'allow_blank': True},
            'title': {'required': False, 'allow_null': True},
            'gender': {'required': False, 'allow_null': True},
            'ethnicity': {'required': False, 'allow_null': True},
            'is_citizen': {'required': False, 'allow_null': True},
            'birth_date': {'required': False, 'allow_null': True},
            'current_home_location': {'required': False, 'allow_blank': True},
            'preferred_job_title': {'required': False, 'allow_blank': True},
            'availability': {'required': False, 'allow_blank': True},
            'current_salary': {'required': False, 'allow_null': True},
            'desired_salary': {'required': False, 'allow_null': True},
            'introduction': {'required': False, 'allow_blank': True},
        }


# ==================== SKILLS SERIALIZERS ====================
class SkillSerializer(serializers.ModelSerializer):
    recommended_by_company = serializers.SerializerMethodField()
    recommended_by_business_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Skill
        fields = '__all__'
        read_only_fields = ('profile',)
    
    def get_recommended_by_company(self, obj):
        """Get company name if this is a business-recommended skill"""
        if obj.is_business_recommended and obj.recommended_by_business:
            return obj.recommended_by_business.company_name
        return None
    
    def get_recommended_by_business_info(self, obj):
        """Get business info if this is a business-recommended skill"""
        if obj.is_business_recommended and obj.recommended_by_business:
            return {
                'company_name': obj.recommended_by_business.company_name,
                'company_id': obj.recommended_by_business.id
            }
        return None

class SkillCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['skill_name', 'proficiency']

class BusinessSkillCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    proficiency_level = serializers.ChoiceField(
        choices=SKILL_PROFICIENCY_LEVELS, 
        required=False, 
        default='intermediate'
    )
    years_of_experience = serializers.IntegerField(required=False, default=0, min_value=0)
    description = serializers.CharField(required=False, allow_blank=True)
    category = serializers.CharField(required=False, allow_blank=True)
    
    def validate_name(self, value):
        # Ensure skill name is not empty
        if not value.strip():
            raise serializers.ValidationError("Skill name cannot be empty")
        return value.strip()

# ==================== EMPLOYMENT SERIALIZERS ====================

# serializers.py
class BusinessEmploymentPreferenceSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='business_profile.company_name', read_only=True)
    
    class Meta:
        model = BusinessEmploymentPreference
        fields = [
            'id', 'preferred_contract_type', 'positions_available', 
            'job_title_keywords', 'required_experience_years', 'is_active',
            'company_name', 'created_at'
        ]
        read_only_fields = ('business_profile',)

class BusinessEmploymentPreferenceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessEmploymentPreference
        fields = [
            'preferred_contract_type', 'positions_available', 
            'job_title_keywords', 'required_experience_years', 'is_active'
        ]
    
    def validate_job_title_keywords(self, value):
        """Ensure job_title_keywords is a list of strings"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Job title keywords must be a list.")
        return [keyword.strip().lower() for keyword in value if keyword.strip()]

class EmploymentHistorySerializer(serializers.ModelSerializer):
    experience_months = serializers.ReadOnlyField()
    
    class Meta:
        model = EmploymentHistory
        exclude = ['created_at', 'updated_at']
        read_only_fields = ('profile',)

class EmploymentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmploymentHistory
        fields = [
            'job_title', 'company', 'location', 'contract_type',
            'start_date', 'end_date', 'currently_working', 'description'
        ]
    
    def validate_contract_type(self, value):
        """Allow None/empty values for contract_type"""
        if value == '' or value is None:
            return None
        return value
    
    def validate_location(self, value):
        """Allow None/empty values for location"""
        if value == '':
            return None
        return value
    
    def validate_description(self, value):
        """Allow None/empty values for description"""
        if value == '':
            return None
        return value
    
    def validate(self, data):
        """Validate employment dates and logic"""
        if not data.get('start_date'):
            raise serializers.ValidationError({"start_date": "Start date is required."})
        
        if data.get('end_date') and data['start_date'] > data['end_date']:
            raise serializers.ValidationError({"end_date": "End date cannot be before start date."})
        
        if data.get('currently_working') and data.get('end_date'):
            raise serializers.ValidationError({"end_date": "Cannot have end date when currently working."})
        
        return data
    
# ==================== EDUCATION SERIALIZERS ====================

class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = '__all__'
        read_only_fields = ('profile',)

class EducationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = ['qualification', 'institution', 'completion_year', 'major_subject', 'grade']
    
    def validate_completion_year(self, value):
        """Validate completion year"""
        from django.utils import timezone
        current_year = timezone.now().year
        if value < 1900 or value > current_year + 5:
            raise serializers.ValidationError("Invalid completion year.")
        return value


# serializers.py
class BusinessPreferenceSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='business_profile.company_name', read_only=True)
    criteria_summary = serializers.ReadOnlyField()
    
    class Meta:
        model = BusinessPreference
        fields = [
            'id', 'preference_type', 'title', 'description', 'criteria',
            'positions_available', 'priority_level', 'is_active',
            'company_name', 'criteria_summary', 'created_at'
        ]
        read_only_fields = ('business_profile',)

class BusinessPreferenceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessPreference
        fields = [
            'preference_type', 'title', 'description', 'criteria',
            'positions_available', 'priority_level', 'is_active'
        ]
    
    def validate_criteria(self, value):
        """Ensure criteria is a dictionary"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Criteria must be a dictionary.")
        return value
    

# ==================== DOCUMENTS SERIALIZERS ====================

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = '__all__'
        read_only_fields = ('profile', 'file_name', 'uploaded_at')

class DocumentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['document_type', 'file']
    
    def validate_file(self, value):
        """Validate file size and type"""
        max_size = 5 * 1024 * 1024  # 5MB
        if value.size > max_size:
            raise serializers.ValidationError("File size cannot exceed 5MB.")
        
        allowed_types = ['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png']
        file_extension = value.name.split('.')[-1].lower()
        if file_extension not in allowed_types:
            raise serializers.ValidationError(f"File type not allowed. Allowed types: {', '.join(allowed_types)}")
        
        return value


# ==================== JOB & APPLICATION SERIALIZERS ====================

class JobListingSerializer(serializers.ModelSerializer):
    company_logo_url = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    
    class Meta:
        model = JobListing
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def get_company_logo_url(self, obj):
        request = self.context.get('request')
        if obj.company_logo:
            if request:
                return request.build_absolute_uri(obj.company_logo.url)
            return obj.company_logo.url
        if request:
            return request.build_absolute_uri('/static/hiring/images/default-company-logo.png')
        return '/static/hiring/images/default-company-logo.png'
    
    def get_is_expired(self, obj):
        from django.utils import timezone
        return obj.apply_by < timezone.now().date()

class ApplicationSerializer(serializers.ModelSerializer):
    job_listing = JobListingSerializer(read_only=True)
    applicant = ApplicantProfileSerializer(read_only=True)
    reference_number = serializers.SerializerMethodField()
    
    class Meta:
        model = Application
        fields = '__all__'
        read_only_fields = ('applicant', 'applied_date', 'job_listing')
    
    def get_reference_number(self, obj):
        return f"APP-{obj.id.hex[:8].upper()}"

class ApplicationCreateSerializer(serializers.ModelSerializer):
    cover_letter = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    
    class Meta:
        model = Application
        fields = ['cover_letter']
    
    def validate_cover_letter(self, value):
        if value and len(value.strip()) < 10:
            raise serializers.ValidationError("Cover letter should be at least 10 characters long if provided.")
        if value and len(value) > 2000:
            raise serializers.ValidationError("Cover letter cannot exceed 2000 characters.")
        return value.strip() if value else ""


# ==================== NOTIFICATION SERIALIZERS ====================

class AlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = '__all__'
        read_only_fields = ('applicant', 'created_at')

class SentNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SentNotification
        fields = '__all__'
        read_only_fields = ('applicant', 'sent_at')

class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = '__all__'
        read_only_fields = ('applicant',)

class JobAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobAlert
        fields = '__all__'
        read_only_fields = ('applicant', 'created_at', 'last_sent')

class EmailTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailTemplate
        fields = '__all__'


# ==================== BUSINESS SERIALIZERS ====================

class IndustrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Industry
        fields = ['id', 'name', 'description']

class CompanySizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanySize
        fields = ['id', 'size_range', 'description', 'min_employees', 'max_employees']

class JobCategorySerializer(serializers.ModelSerializer):
    industry_name = serializers.CharField(source='industry.name', read_only=True)
    
    class Meta:
        model = JobCategory
        fields = ['id', 'name', 'industry', 'industry_name', 'description', 'is_active']

class BusinessProfileSerializer(serializers.ModelSerializer):
    industry_name = serializers.CharField(source='industry.name', read_only=True)
    company_size_name = serializers.CharField(source='company_size.size_range', read_only=True)
    
    class Meta:
        model = BusinessProfile
        fields = [
            'id', 'company_name', 'company_description', 'company_size', 'company_size_name',
            'industry', 'industry_name', 'website', 'phone_number', 'address', 'city',
            'country', 'postal_code', 'company_logo', 'is_verified',
            'receive_applicant_notifications', 'receive_newsletter',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'is_verified', 'created_at', 'updated_at']

class BusinessSignupSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150, required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, min_length=8, required=True)
    password_confirm = serializers.CharField(write_only=True, required=True)
    first_name = serializers.CharField(max_length=30, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=30, required=False, allow_blank=True)
    mobile_phone = serializers.CharField(max_length=15, required=False, allow_blank=True)
    
    # Business fields
    company_name = serializers.CharField(max_length=200, required=True)
    company_description = serializers.CharField(required=False, allow_blank=True)
    company_size = serializers.PrimaryKeyRelatedField(
        queryset=CompanySize.objects.filter(is_active=True), 
        required=False, 
        allow_null=True
    )
    industry = serializers.PrimaryKeyRelatedField(
        queryset=Industry.objects.filter(is_active=True), 
        required=False, 
        allow_null=True
    )
    website = serializers.URLField(required=False, allow_blank=True)
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    company_logo = serializers.ImageField(required=False, allow_null=True)

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match"})
        
        if CustomUser.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError({"username": "Username already exists"})
        
        if CustomUser.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({"email": "Email already exists"})
        
        return data

    def create(self, validated_data):
        # Extract user data
        user_data = {
            'username': validated_data['username'],
            'email': validated_data['email'],
            'password': validated_data['password'],
            'first_name': validated_data.get('first_name', ''),
            'last_name': validated_data.get('last_name', ''),
            'mobile_phone': validated_data.get('mobile_phone', ''),
            'user_type': 'admin'
        }
        
        # Create user
        user = CustomUser.objects.create_user(**user_data)
        
        # Create business profile
        business_profile_data = {
            'user': user,
            'company_name': validated_data['company_name'],
            'company_description': validated_data.get('company_description', ''),
            'company_size': validated_data.get('company_size'),
            'industry': validated_data.get('industry'),
            'website': validated_data.get('website', ''),
            'phone_number': validated_data.get('phone_number', '')
        }
        
        business_profile = BusinessProfile.objects.create(**business_profile_data)
        
        return user


# ==================== ADMIN SERIALIZERS ====================
class AdminJobCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating jobs in admin with all model fields"""
    
    class Meta:
        model = JobListing
        fields = [
            'listing_reference', 'title', 'status', 'apply_by', 'position_summary',
            'industry', 'job_category', 'location', 'contract_type', 'ee_position',
            'company_name', 'company_logo', 'company_description', 'job_description',
            'knowledge_requirements', 'skills_requirements', 'competencies_requirements',
            'experience_requirements', 'education_requirements'
        ]
        extra_kwargs = {
            'listing_reference': {'required': False},
            'company_name': {'required': False, 'default': 'Benta Group'},
            'ee_position': {'required': False, 'default': True},
            # Make these fields optional with default values
            'industry': {'required': False, 'allow_blank': True, 'default': ''},
            'job_category': {'required': False, 'allow_blank': True, 'default': ''},
            'contract_type': {'required': False, 'allow_blank': True, 'default': ''},
            'company_description': {'required': False, 'allow_blank': True, 'default': ''},
            'knowledge_requirements': {'required': False, 'allow_blank': True, 'default': ''},
            'skills_requirements': {'required': False, 'allow_blank': True, 'default': ''},
            'competencies_requirements': {'required': False, 'allow_blank': True, 'default': ''},
            'experience_requirements': {'required': False, 'allow_blank': True, 'default': ''},
            'education_requirements': {'required': False, 'allow_blank': True, 'default': ''}
        }

    def validate_apply_by(self, value):
        """Validate apply_by date - allow past dates for testing"""
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user if request else None
        
        # Define has_business_access locally if not imported
        def has_business_access(user):
            if user and user.groups.filter(name='Business').exists():
                return True
            # Check for business profile
            try:
                from .models import BusinessProfile
                if BusinessProfile.objects.filter(user=user).exists():
                    return True
            except:
                pass
            return False
        
        # BUSINESS USER: Force company name and logo from business profile
        if user and has_business_access(user) and not user.is_superuser:
            try:
                from .models import BusinessProfile
                business_profile = BusinessProfile.objects.get(user=user)
                # Force company name from business profile
                validated_data['company_name'] = business_profile.company_name
                
                # Auto-populate company logo from business profile if not provided
                if 'company_logo' not in validated_data or not validated_data.get('company_logo'):
                    if business_profile.company_logo:
                        validated_data['company_logo'] = business_profile.company_logo
                    else:
                        validated_data['company_logo'] = None
            except BusinessProfile.DoesNotExist:
                raise serializers.ValidationError({
                    'company_name': 'Business profile not found. Please complete your business profile first.'
                })
        
        # Generate listing reference if not provided
        if not validated_data.get('listing_reference'):
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            validated_data['listing_reference'] = f"JOB-{timestamp}"
        
        # Set default values for optional fields
        optional_fields = [
            'industry', 'job_category', 'contract_type', 'company_description',
            'knowledge_requirements', 'skills_requirements', 'competencies_requirements',
            'experience_requirements', 'education_requirements'
        ]
        
        for field in optional_fields:
            if field not in validated_data or validated_data[field] is None:
                validated_data[field] = ''
        
        return super().create(validated_data)

    def update(self, instance, validated_data):
        request = self.context.get('request')
        user = request.user if request else None
        
        # Define has_business_access locally if not imported
        def has_business_access(user):
            if user and user.groups.filter(name='Business').exists():
                return True
            # Check for business profile
            try:
                from .models import BusinessProfile
                if BusinessProfile.objects.filter(user=user).exists():
                    return True
            except:
                pass
            return False
        
        # BUSINESS USER: Prevent changing company name and handle logo properly
        if user and has_business_access(user) and not user.is_superuser:
            # Remove company_name from validated_data to prevent changes
            validated_data.pop('company_name', None)
            
            # Handle company logo: if being removed, use business profile logo
            if 'company_logo' in validated_data and validated_data['company_logo'] is None:
                try:
                    from .models import BusinessProfile
                    business_profile = BusinessProfile.objects.get(user=user)
                    if business_profile.company_logo:
                        validated_data['company_logo'] = business_profile.company_logo
                except BusinessProfile.DoesNotExist:
                    validated_data['company_logo'] = None
        
        return super().update(instance, validated_data)

        
class AdminApplicationStatusSerializer(serializers.Serializer):
    """Serializer for updating application status"""
    status = serializers.ChoiceField(choices=Application.APPLICATION_STATUS)

    def validate_status(self, value):
        """Validate status value"""
        valid_statuses = [choice[0] for choice in Application.APPLICATION_STATUS]
        if value not in valid_statuses:
            raise serializers.ValidationError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        return value


# ==================== MESSAGING SERIALIZERS ====================

class MessagingUserSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()
    profile_pic = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'display_name', 'is_online', 'profile_pic']
        read_only_fields = fields

    def get_display_name(self, obj):
        if obj.first_name and obj.last_name:
            return f"{obj.first_name} {obj.last_name}"
        return obj.username

    def get_is_online(self, obj):
        try:
            return obj.chat_status.is_online
        except UserStatus.DoesNotExist:
            return False

    def get_profile_pic(self, obj):
        return None

class ConversationSerializer(serializers.ModelSerializer):
    participants = MessagingUserSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    other_user = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'participants', 'created_at', 'updated_at', 'last_message', 'unread_count', 'other_user']

    def get_last_message(self, obj):
        last_message = obj.messages.last()
        if last_message:
            return MessagePreviewSerializer(last_message).data
        return None

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.messages.filter(is_read=False).exclude(sender=request.user).count()
        return 0

    def get_other_user(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            other_users = obj.participants.exclude(id=request.user.id)
            if other_users.exists():
                return MessagingUserSerializer(other_users.first(), context=self.context).data
        return None

class MessagePreviewSerializer(serializers.ModelSerializer):
    sender = MessagingUserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'sender', 'content', 'message_type', 'file_name', 'created_at']

class MessageSerializer(serializers.ModelSerializer):
    sender = MessagingUserSerializer(read_only=True)
    parent_message = MessagePreviewSerializer(read_only=True)
    original_sender = MessagingUserSerializer(read_only=True)
    file_url = serializers.SerializerMethodField()
    file_download_url = serializers.SerializerMethodField()
    is_image = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender', 'content', 'message_type', 
            'file', 'file_name', 'file_size', 'file_mime_type', 'file_url',
            'file_download_url', 'parent_message', 'is_forwarded', 
            'original_sender', 'is_read', 'delivered_at', 'read_at', 
            'created_at', 'is_image'
        ]
        read_only_fields = ['id', 'sender', 'created_at', 'updated_at']

    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None

    def get_file_download_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return f"{request.build_absolute_uri(obj.file.url)}?download=true"
            return f"{obj.file.url}?download=true"
        return None

    def get_is_image(self, obj):
        """Check if the file is an image for frontend preview"""
        if obj.message_type == 'image':
            return True
        
        # Additional check based on file extension
        if obj.file_name:
            image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.jfif']
            file_extension = os.path.splitext(obj.file_name)[1].lower()
            return file_extension in image_extensions
        
        return False

class MessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['content', 'message_type', 'parent_message', 'is_forwarded']

class FileUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    message_type = serializers.ChoiceField(choices=Message.MESSAGE_TYPES, default='file')

    def validate_file(self, value):
        # Validate file size (10MB limit)
        max_size = 10 * 1024 * 1024  # 10MB
        if value.size > max_size:
            raise serializers.ValidationError(f"File size must be less than 10MB. Current size: {value.size}")
        return value

class UserStatusSerializer(serializers.ModelSerializer):
    user = MessagingUserSerializer(read_only=True)

    class Meta:
        model = UserStatus
        fields = ['user', 'is_online', 'last_seen', 'typing_to']



#====================== Post Comment Serializers ======================

class PostAuthorSerializer(serializers.ModelSerializer):
    """Serializer for author information in posts"""
    profile_picture = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'first_name', 'last_name', 'user_type', 'profile_picture']
    
    def get_profile_picture(self, obj):
        # You can implement profile pictures later
        return None

class PostCompanySerializer(serializers.ModelSerializer):
    """Serializer for company information in posts"""
    logo_url = serializers.SerializerMethodField()
    
    class Meta:
        model = BusinessProfile
        fields = ['id', 'company_name', 'logo_url']
    
    def get_logo_url(self, obj):
        if obj.company_logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.company_logo.url)
            return obj.company_logo.url
        return None

class PostSerializer(serializers.ModelSerializer):
    author = PostAuthorSerializer(read_only=True)
    company = PostCompanySerializer(read_only=True)
    likes_count = serializers.SerializerMethodField()
    dislikes_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    user_has_liked = serializers.SerializerMethodField()
    user_has_disliked = serializers.SerializerMethodField()
    user_rating = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    video_url = serializers.SerializerMethodField()
    tags_list = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()
    time_since = serializers.SerializerMethodField()
    
    class Meta:
        model = Post
        fields = [
            'id', 'author', 'company', 'post_type', 'title', 'content',
            'image', 'video', 'video_url', 'tags', 'tags_list',
            'views', 'likes_count', 'dislikes_count', 'comments_count',
            'shares', 'average_rating', 'rating_count', 'visibility',
            'created_at', 'updated_at', 'is_published', 'is_edited', 'edited_at',
            'user_has_liked', 'user_has_disliked', 'user_rating',
            'image_url', 'video_url', 'can_edit', 'can_delete', 'time_since'
        ]
        read_only_fields = [
            'views', 'likes', 'dislikes', 'shares', 'average_rating', 
            'rating_count', 'created_at', 'updated_at'
        ]
    
    def get_likes_count(self, obj):
        return obj.likes.count()
    
    def get_dislikes_count(self, obj):
        return obj.dislikes.count()
    
    def get_comments_count(self, obj):
        return obj.comments.count()
    
    def get_user_has_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(id=request.user.id).exists()
        return False
    
    def get_user_has_disliked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.dislikes.filter(id=request.user.id).exists()
        return False
    
    def get_user_rating(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            rating = Rating.objects.filter(post=obj, user=request.user).first()
            return rating.rating if rating else None
        return None
    
    def get_image_url(self, obj):
        if obj.image and hasattr(obj.image, 'url'):
            request = self.context.get('request')
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None
    
    def get_video_url(self, obj):
        if obj.video and hasattr(obj.video, 'url'):
            request = self.context.get('request')
            return request.build_absolute_uri(obj.video.url) if request else obj.video.url
        return None
    
    def get_tags_list(self, obj):
        """Convert comma-separated tags to list"""
        if not obj.tags:
            return []
        return [tag.strip() for tag in obj.tags.split(',') if tag.strip()]

    def get_can_edit(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return request.user == obj.author or request.user.is_staff
        return False
    
    def get_can_delete(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return request.user == obj.author or request.user.is_staff
        return False
    
    def get_time_since(self, obj):
        from django.utils import timezone
        from django.utils.timesince import timesince
        
        now = timezone.now()
        if obj.created_at:
            return timesince(obj.created_at, now).split(',')[0] + ' ago'
        return ''


#post create serializer
class PostCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating posts - ULTRA FLEXIBLE VERSION"""
    
    class Meta:
        model = Post
        fields = [
            'post_type', 'title', 'content', 'image', 'video', 
            'video_url', 'tags', 'visibility', 'is_published'
        ]
        extra_kwargs = {
            'title': {'required': True},  # But we handle this in the view
            'content': {'required': True},
            'image': {'required': False, 'allow_null': True},
            'video': {'required': False, 'allow_null': True},
            'video_url': {'required': False, 'allow_blank': True},
            'tags': {'required': False, 'allow_blank': True},
            'visibility': {'required': False, 'default': 'public'},
            'is_published': {'required': False, 'default': True},
            'post_type': {'required': False, 'default': 'general'}
        }
    
    def validate(self, data):
        """ULTRA SIMPLE validation - ALL users can post ANYTHING"""
        
        # Auto-generate title if somehow missing (should be handled in view)
        if 'title' not in data or not data['title']:
            content = data.get('content', '')
            if content:
                words = content.strip().split()[:5]
                data['title'] = ' '.join(words) + '...'
            else:
                data['title'] = 'New Post'
        
        # Ensure content is not empty
        if 'content' not in data or not data['content']:
            raise serializers.ValidationError({
                'content': 'Post content cannot be empty'
            })
        
        # Don't allow both video and video_url
        if data.get('video') and data.get('video_url'):
            raise serializers.ValidationError({
                'video': 'Please upload a video file OR provide a video URL, not both.'
            })
        
        return data
    
    def create(self, validated_data):
        """Create post - SIMPLE AND WORKS"""
        request = self.context['request']
        user = request.user
        
        print(f"Creating post for user: {user.username}")
        print(f"Title: {validated_data.get('title', 'No title')}")
        print(f"Content length: {len(validated_data.get('content', ''))}")
        
        # 1. Set the author
        validated_data['author'] = user
        
        # 2. Auto-set company if user has business profile
        if hasattr(user, 'business_profile'):
            validated_data['company'] = user.business_profile
            print(f"Auto-set company: {user.business_profile.company_name}")
        
        # 3. Create the post
        try:
            post = Post.objects.create(**validated_data)
            print(f"✓ Post created successfully! ID: {post.id}")
            return post
        except Exception as e:
            print(f"✗ Error creating post: {str(e)}")
            raise serializers.ValidationError({
                'non_field_errors': [f"Failed to save post: {str(e)}"]
            })
        

class PostUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating posts"""
    class Meta:
        model = Post
        fields = [
            'title', 'content', 'image', 'video', 
            'video_url', 'tags', 'visibility', 'is_published'
        ]
        extra_kwargs = {
            'title': {'required': False},
            'content': {'required': False},
            'image': {'required': False, 'allow_null': True},
            'video': {'required': False, 'allow_null': True},
            'video_url': {'required': False, 'allow_blank': True},
            'tags': {'required': False, 'allow_blank': True},
        }
    
    def validate(self, data):
        # Validate file sizes
        request = self.context['request']
        
        if 'image' in request.FILES:
            image = request.FILES['image']
            if image.size > 314572800:  # 300MB
                raise serializers.ValidationError({
                    'image': 'Image file size cannot exceed 300MB'
                })
        
        if 'video' in request.FILES:
            video = request.FILES['video']
            if video.size > 314572800:  # 300MB
                raise serializers.ValidationError({
                    'video': 'Video file size cannot exceed 300MB'
                })
        
        # Don't allow both video file and video URL
        if data.get('video') and data.get('video_url'):
            raise serializers.ValidationError(
                "Please upload a video file OR provide a video URL, not both."
            )
        
        return data
    
    def update(self, instance, validated_data):
        # Handle file uploads/removal
        request = self.context['request']
        
        # Handle image
        if 'image' in request.FILES:
            validated_data['image'] = request.FILES['image']
        elif 'image' in validated_data and validated_data['image'] is None:
            # Remove image if explicitly set to null
            validated_data['image'] = None
            if instance.image:
                instance.image.delete(save=False)
        
        # Handle video
        if 'video' in request.FILES:
            validated_data['video'] = request.FILES['video']
        elif 'video' in validated_data and validated_data['video'] is None:
            # Remove video if explicitly set to null
            validated_data['video'] = None
            if instance.video:
                instance.video.delete(save=False)
        
        # Mark as edited
        validated_data['is_edited'] = True
        validated_data['edited_at'] = timezone.now()
        
        return super().update(instance, validated_data)

class CommentSerializer(serializers.ModelSerializer):
    author = PostAuthorSerializer(read_only=True)
    likes_count = serializers.SerializerMethodField()
    replies_count = serializers.SerializerMethodField()
    user_has_liked = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()
    time_since = serializers.SerializerMethodField()
    
    class Meta:
        model = Comment
        fields = [
            'id', 'post', 'author', 'content', 'likes_count',
            'replies_count', 'parent_comment', 'created_at',
            'updated_at', 'is_edited', 'user_has_liked',
            'can_edit', 'can_delete', 'time_since'
        ]
    
    def get_likes_count(self, obj):
        return obj.likes.count()
    
    def get_replies_count(self, obj):
        return obj.replies.count()
    
    def get_user_has_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(id=request.user.id).exists()
        return False
    
    def get_can_edit(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return request.user == obj.author or request.user.is_staff
        return False
    
    def get_can_delete(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return request.user == obj.author or request.user.is_staff
        return False
    
    def get_time_since(self, obj):
        from django.utils import timezone
        from django.utils.timesince import timesince
        
        now = timezone.now()
        if obj.created_at:
            return timesince(obj.created_at, now).split(',')[0] + ' ago'
        return ''

class CommentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating comments"""
    class Meta:
        model = Comment
        fields = ['content', 'parent_comment']
        extra_kwargs = {
            'content': {'required': True},
            'parent_comment': {'required': False, 'allow_null': True}
        }
    
    def validate(self, data):
        # Validate parent comment belongs to same post
        parent_comment = data.get('parent_comment')
        post_id = self.context.get('post_id')
        
        if parent_comment and parent_comment.post_id != post_id:
            raise serializers.ValidationError({
                'parent_comment': 'Parent comment must belong to the same post'
            })
        
        return data
    
    def create(self, validated_data):
        user = self.context['request'].user
        post_id = self.context['post_id']
        post = Post.objects.get(id=post_id)
        
        validated_data['author'] = user
        validated_data['post'] = post
        
        return super().create(validated_data)

class RatingSerializer(serializers.ModelSerializer):
    """Serializer for post ratings"""
    class Meta:
        model = Rating
        fields = ['id', 'post', 'rating', 'created_at']
        read_only_fields = ['user']
    
    def validate(self, data):
        rating = data.get('rating')
        
        if rating < 1 or rating > 5:
            raise serializers.ValidationError({
                'rating': 'Rating must be between 1 and 5'
            })
        
        return data
    
    def create(self, validated_data):
        user = self.context['request'].user
        post = validated_data['post']
        
        # Check if user already rated this post
        existing_rating = Rating.objects.filter(user=user, post=post).first()
        if existing_rating:
            # Update existing rating
            existing_rating.rating = validated_data['rating']
            existing_rating.save()
            
            # Update post average rating
            post.update_rating(validated_data['rating'])
            
            return existing_rating
        else:
            # Create new rating
            validated_data['user'] = user
            rating = Rating.objects.create(**validated_data)
            
            # Update post average rating
            post.update_rating(validated_data['rating'])
            
            return rating

class LikeDislikeSerializer(serializers.Serializer):
    """Serializer for like/dislike actions"""
    action = serializers.ChoiceField(choices=['like', 'dislike', 'remove'])
    
    def validate(self, data):
        return data

class JobInteractionSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    user_avatar = serializers.SerializerMethodField()
    
    class Meta:
        model = JobInteraction
        fields = [
            'id', 'user', 'user_name', 'user_avatar', 
            'job_listing', 'interaction_type', 'comment_text',
            'parent_interaction', 'created_at'
        ]
        read_only_fields = ['user', 'created_at']
    
    def get_user_avatar(self, obj):
        # You can customize this to return user avatar URL
        return f"/static/images/avatars/{obj.user.username[:1].upper()}.png"

class JobListingInteractionSerializer(serializers.ModelSerializer):
    """Extended serializer for JobListing with interaction counts"""
    likes_count = serializers.SerializerMethodField()
    dislikes_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    user_has_liked = serializers.SerializerMethodField()
    user_has_disliked = serializers.SerializerMethodField()
    company_logo_url = serializers.SerializerMethodField()
    
    def get_likes_count(self, obj):
        return JobInteraction.objects.filter(
            job_listing=obj, 
            interaction_type='like'
        ).count()
    
    def get_dislikes_count(self, obj):
        return JobInteraction.objects.filter(
            job_listing=obj, 
            interaction_type='dislike'
        ).count()
    
    def get_comments_count(self, obj):
        return JobInteraction.objects.filter(
            job_listing=obj, 
            interaction_type='comment',
            parent_interaction__isnull=True  # Only count parent comments
        ).count()
    
    def get_user_has_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return JobInteraction.objects.filter(
                job_listing=obj,
                user=request.user,
                interaction_type='like'
            ).exists()
        return False
    
    def get_user_has_disliked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return JobInteraction.objects.filter(
                job_listing=obj,
                user=request.user,
                interaction_type='dislike'
            ).exists()
        return False
    
    def get_company_logo_url(self, obj):
        if obj.company_logo:
            return obj.company_logo.url
        return '/static/hiring/images/default-company-logo.png'
    
    class Meta:
        model = JobListing
        fields = [
            'id', 'listing_reference', 'title', 'status', 'apply_by',
            'position_summary', 'industry', 'job_category', 'location',
            'contract_type', 'ee_position', 'company_name', 'company_logo_url',
            'company_description', 'likes_count', 'dislikes_count', 
            'comments_count', 'user_has_liked', 'user_has_disliked',
            'created_at', 'updated_at'
        ]


class RatingSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    
    def validate(self, data):
        return data
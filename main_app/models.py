from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import UserManager
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.db import models
from datetime import datetime
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.urls import reverse
from datetime import date
from django.db.models import Q
from ckeditor.fields import RichTextField
from django.contrib.auth.models import AbstractUser, UserManager
from django.contrib.auth.models import BaseUserManager
from django.conf import settings
from django.core.files import File
from io import BytesIO
from PIL import Image, ImageDraw
from django.core.validators import MaxValueValidator
from django.utils import timezone
from django.db.models import Sum
from django.contrib.auth.hashers import make_password
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.core.exceptions import ValidationError
from college.models import CollegeAndUniversities
from bursary.models import Bursary
#from moviepy.editor import VideoFileClip
import uuid
import os

NEWS = "News"
EVENTS = "Event"

POST = (
    (NEWS, "News"),
    (EVENTS, "Event"),
)


# School Type
DEPENDENT_SCHOOL = "Dependent School"
INDEPENDENT_SCHOOL = "Independent School"
SPECIAL_NEEDS = "Special Needs"

SCHOOL_TYPE = (
    (DEPENDENT_SCHOOL, "Dependent School"),
    (INDEPENDENT_SCHOOL, "Independent School"),
    (SPECIAL_NEEDS, "Special Needs"),
)

# Filter By
HIGH_SCHOOL = "High School"
PRIMARY_SCHOOL = "Primary School"
COMBINED_SCHOOL = "Combined School"
HOME_SCHOOL = "Home School"

FILTER_BY = (
    (HIGH_SCHOOL, "High School"),
    (PRIMARY_SCHOOL, "Primary School"),
    (COMBINED_SCHOOL, "Combined School"),
    (HOME_SCHOOL, "Home School"),  # Fixed redundancy
)



DISTINCTION_RESULTS = "Distinction"
BACHELOR_RESULTS = "Bachelor"
DIPLOMA_RESULTS = "Diploma"
FAILED_RESULTS = "Fail"

LEVEL = (
    (DISTINCTION_RESULTS, "Distinction RESULTS"),
    (BACHELOR_RESULTS, "Bachelor RESULTS"),
    (DIPLOMA_RESULTS, "Diploma RESULTS"),
    (FAILED_RESULTS, "Failed RESULTS"),
)


# QuerySet for NewsAndEvents
class NewsAndEventsQuerySet(models.query.QuerySet):
    def search(self, query):
        lookups = Q(title__icontains=query) | Q(summary__icontains=query) | Q(posted_as__icontains=query)
        return self.filter(lookups).distinct()

# Manager for NewsAndEvents
class NewsAndEventsManager(models.Manager):
    def get_queryset(self):
        return NewsAndEventsQuerySet(self.model, using=self._db)

    def search(self, query):
        return self.get_queryset().search(query)

# NewsAndEvents model
class NewsAndEvents(models.Model):
    title = models.CharField(max_length=200, null=True)
    summary = models.TextField(max_length=2000, blank=True, null=True)
    posted_as = models.CharField(choices=[('News', 'News'), ('Event', 'Event')], max_length=10)
    updated_date = models.DateTimeField(auto_now=True)
    upload_time = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to="news_images/%y/%m/%d/", default="default.png", null=True)


    def __str__(self):
        return self.title

    def get_image(self):
        try:
            return self.image.url
        except:
            return settings.MEDIA_URL + "default.png"
#End

#Custom User
class CustomUserManager(UserManager):
    def _create_user(self, email, password, **extra_fields):
        email = self.normalize_email(email)
        user = CustomUser(email=email, **extra_fields)
        user.password = make_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        assert extra_fields["is_staff"]
        assert extra_fields["is_superuser"]
        return self._create_user(email, password, **extra_fields)


#Session
class Session(models.Model):
    start_year = models.DateField()
    end_year = models.DateField()

    def __str__(self):
        return "From " + str(self.start_year) + " to " + str(self.end_year)

#Custom UserSettings
class CustomUser(AbstractUser):
    USER_TYPE = ((1, "HOD"), (2, "Staff"), (3, "Student"), (4,"Principal"), (5,"Educator"), (6,"Circuit_Manager"), (7, "Parent"), (8, "Member"), (9, "CWA_Admin"))
    GENDER = [("M", "Male"), ("F", "Female")]
    username = None  # Removed username, using email instead
    email = models.EmailField(unique=True)
    user_type = models.CharField(default=1, choices=USER_TYPE, max_length=1)
    gender = models.CharField(max_length=1, choices=GENDER)
    profile_pic = models.ImageField()
    address = models.TextField()
    fcm_token = models.TextField(default="")  # For firebase notifications
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = CustomUserManager()

    def __str__(self):
        return self.last_name + ", " + self.first_name



#grade
class Grade(models.Model):
    name = models.CharField(max_length=120)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    

    def __str__(self):
        return self.name
    
#Term
class Term(models.Model):
    TERM_CHOICES = [
        ('Term 1', 'Term 1'),
        ('Term 2', 'Term 2'),
        ('Term 3', 'Term 3'),
        ('Term 4', 'Term 4'),
    ]
    
    term_name = models.CharField(max_length=10, choices=TERM_CHOICES, blank=True)
    is_current = models.BooleanField(default=False)  # Removed null=True for clarity
    activity_description = models.CharField(max_length=120, blank=True)  # Renamed for clarity
    session = models.ForeignKey(
        'Session', on_delete=models.CASCADE, blank=True, null=True
    )
    next_term_begins = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.term_name


# CIRCUIT MODEL
class Circuit(models.Model):
    name = models.CharField(max_length=255, unique=True)
    contact = models.CharField(max_length=255)
    email = models.CharField(max_length=255)
    whatsapp_number = models.CharField(max_length=255)
    address = models.TextField(null=True, blank=True)
    

    def __str__(self):
        return self.name  


# SCHOOL MODEL
class School(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='school', 
        null=True, 
        blank=True
    )
    emis = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    grade = models.ForeignKey('Grade', on_delete=models.DO_NOTHING, null=True, blank=False)
    circuit = models.ForeignKey('Circuit', on_delete=models.DO_NOTHING, null=True, blank=False)
    contact = models.CharField(max_length=255)
    phase = models.CharField(max_length=255, null=True, blank=True)
    sector = models.CharField(max_length=255, null=True, blank=True)
    educators_on_db = models.IntegerField(default=0)
    school_type = models.CharField(max_length=255, choices=[('Public', 'Public'), ('Private', 'Private')], default='Public')
    school_term = models.IntegerField(default=0)
    filter_by = models.CharField(max_length=255, choices=[('Region', 'Region'), ('Phase', 'Phase')], default='Region')
    website_url = models.URLField(null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    whatsapp_number = models.CharField(max_length=15, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    year = models.IntegerField(default=2025)
    count = models.IntegerField(default=0)
    logo = models.ImageField(upload_to='logos/', null=True, blank=True)
    head_principal = models.CharField(max_length=255, null=True, blank=True)
    deputy = models.CharField(max_length=255, null=True, blank=True)
    
    def __str__(self):
        return self.name  
   

#Course
class Course(models.Model):
    name = models.CharField(max_length=120)
    school = models.ForeignKey(School, on_delete=models.DO_NOTHING, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name



#Custom User 2
class Staff(models.Model):
    course = models.ForeignKey(Course, on_delete=models.DO_NOTHING, null=True, blank=False)
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)

    def __str__(self):
        return self.admin.last_name + " " + self.admin.first_name



#Subject
class Subject(models.Model):
    name = models.CharField(max_length=120)
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='subjects')  # Added related_name
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

#EDUCATOR
# EDUCATOR MODEL
class Educator(models.Model):
    admin = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    circuit = models.ForeignKey(Circuit, on_delete=models.DO_NOTHING, null=True, blank=False)
    school = models.ForeignKey(School, on_delete=models.DO_NOTHING, null=True, blank=False)
    grade = models.ForeignKey('Grade', on_delete=models.DO_NOTHING, null=True)
    subjects = models.ManyToManyField('Subject')
    session = models.ForeignKey('Session', on_delete=models.DO_NOTHING, null=True)
    term = models.ForeignKey('Term', on_delete=models.DO_NOTHING, null=True)
    course = models.ForeignKey('Course', on_delete=models.DO_NOTHING, null=True, blank=False)

    def __str__(self):
        return f"{self.admin.last_name}, {self.admin.first_name}"
    
#Admin
class Admin(models.Model):
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)



# STUDENT MODEL
class Student(models.Model):
    admin = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    course = models.ForeignKey('Course', on_delete=models.DO_NOTHING, null=True, blank=False)
    session = models.ForeignKey('Session', on_delete=models.DO_NOTHING, null=True)
    circuit = models.ForeignKey(Circuit, on_delete=models.DO_NOTHING, null=True, blank=False)
    school = models.ForeignKey(School, on_delete=models.DO_NOTHING, null=True, blank=False)
    grade = models.ForeignKey('Grade', on_delete=models.DO_NOTHING, null=True, blank=False)

    def __str__(self):
        return f"{self.admin.last_name}, {self.admin.first_name}"
    

#informal student result
class InformalStudentResult(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    informaltest = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

#Attendance
class Attendance(models.Model):
    session = models.ForeignKey(Session, on_delete=models.DO_NOTHING)
    subject = models.ForeignKey(Subject, on_delete=models.DO_NOTHING)
    grade = models.ForeignKey(Grade, on_delete=models.DO_NOTHING)
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

#attendance report
class AttendanceReport(models.Model):
    student = models.ForeignKey(Student, on_delete=models.DO_NOTHING)
    attendance = models.ForeignKey(Attendance, on_delete=models.CASCADE)
    status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

#leavereport student
class LeaveReportStudent(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    date = models.CharField(max_length=60)
    message = models.TextField()
    status = models.SmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


#leavereport staff
class LeaveReportStaff(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    date = models.CharField(max_length=60)
    message = models.TextField()
    status = models.SmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


#feedback student
class FeedbackStudent(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    feedback = models.TextField()
    reply = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


#feedback staff
class FeedbackStaff(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    feedback = models.TextField()
    reply = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


#notifications
class NotificationStaff(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


#notification student
class NotificationStudent(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

#STUDENTRESULTS
class StudentResult(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    assignment = models.FloatField(default=0)
    test = models.FloatField(default=0)
    exam = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)



#MEMBER
class Member(models.Model):
   admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
   school = models.ForeignKey(School, on_delete=models.DO_NOTHING, null=True, blank=False)
   position = models.CharField(max_length=20, null=True, blank=True)
   #report
   session = models.ForeignKey(Session, on_delete=models.DO_NOTHING, null=True)
   term = models.ForeignKey(Term, on_delete=models.DO_NOTHING, null=True)

   def __str__(self):
        return self.admin.last_name + ", " + self.admin.first_name

#CWA admin
class CWA_Admin(models.Model):
   admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
   collegeanduniversity = models.ForeignKey(CollegeAndUniversities, on_delete=models.DO_NOTHING, null=True)
   bursary = models.ForeignKey(Bursary, on_delete=models.DO_NOTHING, null=True)
   school = models.ForeignKey(School, on_delete=models.DO_NOTHING, null=True, blank=False)
   position = models.CharField(max_length=20, null=True, blank=True)
   #report
   session = models.ForeignKey(Session, on_delete=models.DO_NOTHING, null=True)
   term = models.ForeignKey(Term, on_delete=models.DO_NOTHING, null=True)

   def __str__(self):
        return self.admin.last_name + ", " + self.admin.first_name

#parent
class Parent(models.Model):
    EMPLOYMENT_STATUS = [
        ('employed', 'Employed'),
        ('unemployed', 'Unemployed'),
        ('self_employed', 'Self-employed'),
        ('retired', 'Retired'),
        ('other', 'Other'),
    ]

    EDUCATION_LEVELS = [
        ('none', 'No formal education'),
        ('primary', 'Primary education'),
        ('secondary', 'Secondary education'),
        ('tertiary', 'Tertiary education'),
        ('postgraduate', 'Postgraduate education'),
    ]

    RELATIONSHIP_CHOICES = [
        ('mother', 'Mother'),
        ('father', 'Father'),
        ('guardian', 'Guardian'),
        ('other', 'Other'),
    ]

    # Required link to user
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)

    # Optional school connection
    school = models.ForeignKey(School, on_delete=models.DO_NOTHING, null=True, blank=True)

    # Relationship to student(s)
    student = models.ManyToManyField(Student, related_name='parents')
    relationship = models.CharField(max_length=10, choices=RELATIONSHIP_CHOICES, default='other')

    # Parent background
    employment_status = models.CharField(max_length=20, choices=EMPLOYMENT_STATUS, null=True, blank=True)
    occupation = models.CharField(max_length=100, null=True, blank=True)
    education_level = models.CharField(max_length=20, choices=EDUCATION_LEVELS, null=True, blank=True)

    # Optional report-related fields
    session = models.ForeignKey(Session, on_delete=models.DO_NOTHING, null=True, blank=True)
    term = models.ForeignKey(Term, on_delete=models.DO_NOTHING, null=True, blank=True)

    def __str__(self):
        return f"{self.admin.last_name}, {self.admin.first_name}"

#Custom User 4
class Principal(models.Model):
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    circuit = models.ForeignKey(Circuit, on_delete=models.DO_NOTHING, null=True, blank=False)
    school = models.ForeignKey(School, on_delete=models.DO_NOTHING, null=True, blank=False)
    grade = models.ForeignKey(Grade, on_delete=models.DO_NOTHING, null=True)
    #report
    subject = models.ForeignKey(Subject, on_delete=models.DO_NOTHING, null=True)
    term = models.ForeignKey(Term, on_delete=models.DO_NOTHING, null=True)
    course = models.ForeignKey(Course, on_delete=models.DO_NOTHING, null=True, blank=False)
    #attendancereport, subject, course, session, term, student, studentresult, educator, parent, member

    def __str__(self):
        return self.admin.last_name + ", " + self.admin.first_name

#Circuit manager
class Circuit_Manager(models.Model):
    admin = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    circuit = models.ForeignKey(Circuit, on_delete=models.DO_NOTHING, null=True, blank=False)

    def __str__(self):
        return self.admin.last_name + ", " + self.admin.first_name


#DOWNLOAD QUESTION PAPERS
class QuestionPaperQuerySet(models.query.QuerySet):
    def search(self, query):
        lookups = Q(filename__icontains=query) | Q(subject__name__icontains=query)
        return self.filter(lookups).distinct()

class QuestionPaperManager(models.Manager):
    def get_queryset(self):
        return QuestionPaperQuerySet(self.model, using=self._db)

    def search(self, query):
        return self.get_queryset().search(query)


@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if instance.user_type == 1:
            Admin.objects.create(admin=instance)
        if instance.user_type == 2:
            Staff.objects.create(admin=instance)
        if instance.user_type == 3:
            Student.objects.create(admin=instance)
        if instance.user_type == 4:
            Principal.objects.create(admin=instance)
        if instance.user_type == 5:
            Educator.objects.create(admin=instance)
        if instance.user_type == 6:
            Circuit_Manager.objects.create(admin=instance)
        if instance.user_type == 7:
            Parent.objects.create(admin=instance)
        if instance.user_type == 8:
            Member.objects.create(admin=instance)
        if instance.user_type == 9:
            CWA_Admin.objects.create(admin=instance)


@receiver(post_save, sender=CustomUser)
def save_user_profile(sender, instance, **kwargs):
    if instance.user_type == 1:
        instance.admin.save()
    if instance.user_type == 2:
        instance.staff.save()
    if instance.user_type == 3:
        instance.student.save()
    if instance.user_type == 4:
        instance.principal.save()
    if instance.user_type == 5:
        instance.educator.save()
    if instance.user_type == 6:
        instance.circuit_manager.save()
    if instance.user_type == 7:
        instance.parent.save()
    if instance.user_type == 8:
        instance.member.save()
    if instance.user_type == 9:
        instance.cwa_admin.save()


#Documents

#submits
class Textbook(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    grade = models.ForeignKey('Grade', on_delete=models.CASCADE)
    file = models.FileField(upload_to='textbooks/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

#appointments
class Appointment(models.Model):
    DEPARTMENT_CHOICES = [
        ('Admissions', 'Admissions'),
        ('Finance', 'Finance'),
        ('HR', 'Human Resources'),
        ('Academics', 'Academics'),
        ('Advertisement', 'Advertisements'),
        ('Sponsor', 'Sponsors'),
        ('Project', 'Projects'),
        ('Other', 'Others')
    ]

    name= models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=15)
    department = models.CharField(max_length=50, choices=DEPARTMENT_CHOICES)
    message = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.department}"

#contacts
class Contact(models.Model): 
    full_names = models.CharField(max_length=255)
    gmail = models.EmailField()
    phone_number = models.CharField(max_length=15)
    message_box = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.full_names} - {self.gmail}"

#subscription
class Subscription(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email

#files
class Files(models.Model):
    filename = models.CharField(max_length=100)
    owner = models.CharField(max_length=100)
    pdf = models.FileField(upload_to='store/pdfs/')
    cover = models.ImageField(upload_to='store/pdfs/')

    def __str__(self):
        return self.filename

    def delete(self, *args, **kwargs):
        self.pdf.delete()
        self.cover.delete()
        super().delete(*args, **kwargs)

        
    
#timetable
class Timetable(models.Model):
    DAY_CHOICES = [
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
        ('Saturday', 'Saturday'),
    ]

    day = models.CharField(max_length=20, choices=DAY_CHOICES)
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, null=True, blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True)
    subjects = models.ManyToManyField(Subject)  # Subjects for the timetable
    educators = models.ManyToManyField(Educator)  # Add educators here
    start_time = models.TimeField()
    end_time = models.TimeField()
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='created_timetables')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def save(self, *args, **kwargs):
        if not self.created_by_id:
            raise ValueError("The 'created_by' field must be set before saving.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.day} - {self.grade.name} ({self.course.name})"


#testimonial
class Message(models.Model):
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    reply_to = models.ForeignKey('self', null=True, blank=True, related_name='replies', on_delete=models.SET_NULL)  # This field allows replies to other messages

    def __str__(self):
        return self.text[:50]

class MessageMedia(models.Model):
    message = models.ForeignKey(Message, related_name='media', on_delete=models.CASCADE)
    media = models.FileField(upload_to='message_media/')

    def __str__(self):
        return self.media.name


#School Perfomance
class SchoolPerformance(models.Model):
    school_record = models.ForeignKey(School, on_delete=models.CASCADE)
    session = models.ForeignKey(Session, on_delete=models.CASCADE)  # New ForeignKey to Session
    educator = models.ForeignKey(Educator, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    grade = models.ForeignKey(Grade, on_delete=models.DO_NOTHING, null=True, blank=False)
    school_principal = models.ForeignKey(Principal, on_delete=models.CASCADE)
    performance_score = models.DecimalField(max_digits=5, decimal_places=2)
    total_score = models.DecimalField(max_digits=7, decimal_places=2, default=0.00)
    overall_performance = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    num_evaluations = models.IntegerField(default=1)
    improvement = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    comments = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('school_record', 'session', 'subject', 'grade')  # Updated to include session

    def __str__(self):
        return f"{self.school_record.name} - {self.subject} ({self.grade}) Performance ({self.school_record.year})"

    def calculate_total_score(self):
        total = SchoolPerformance.objects.filter(
            school_record=self.school_record,
            session=self.session,
            grade=self.grade,
            subject=self.subject
        ).aggregate(total=Sum('performance_score'))['total']
        self.total_score = total or 0.00
        self.save()

    def calculate_overall_performance(self):
        if self.num_evaluations > 0:
            self.overall_performance = self.total_score / self.num_evaluations
        else:
            self.overall_performance = 0.00
        self.save()

    def calculate_improvement(self, previous_score):
        if previous_score:
            self.improvement = self.performance_score - previous_score
        else:
            self.improvement = self.performance_score
        self.save()

    def save(self, *args, **kwargs):
        self.calculate_total_score()
        self.calculate_overall_performance()
        super(SchoolPerformance, self).save(*args, **kwargs)

#school of specialisation assessment dates

#Jobs model
#Category model
class SosCategory(models.Model):
    class Meta:
        verbose_name = 'SosCategory'
        verbose_name_plural = 'SosCategories'

    user = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=100, null=False, blank=False)

    def __str__(self):
        return self.name


#sos
class Sos(models.Model):
    class Meta:
        verbose_name = 'Sos'
        verbose_name_plural = 'soss'
    
    
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    image = models.ImageField(null=False, blank=False)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    grade = models.ForeignKey(Grade, on_delete=models.DO_NOTHING, null=True, blank=False)
    date = models.CharField(max_length=20, null=True, blank=True)
    assessment = models.CharField(max_length=20, null=True, blank=True)
    description = models.TextField()
   
    def __str__(self):
        return self.description

#members advertisements

def validate_video_size(video):
    # Define maximum size in bytes (50 MB)
    max_size = 50 * 1024 * 1024
    if video.size > max_size:
        raise ValidationError(f"Maximum file size is 50MB. Uploaded file size: {video.size / (1024 * 1024):.2f}MB")

def validate_video_duration(video):
    from moviepy.editor import VideoFileClip  # Import within the function to avoid issues when not using videos
    try:
        clip = VideoFileClip(video.temporary_file_path())  # Get video path for duration check
        duration = clip.duration
        if duration > 60:  # 1 minute is 60 seconds
            raise ValidationError("Maximum duration is 1 minute.")
    except Exception as e:
        raise ValidationError(f"Unable to verify video duration: {e}")

class CustomAd(models.Model):
    title = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='Ads/')
    video = models.FileField(upload_to='Ads/videos/', blank=True, null=True, validators=[validate_video_size])
    web_url = models.URLField()
    whatsapp_number = models.CharField(max_length=20, null=True, blank=True)
    facebook_url = models.CharField(max_length=300, null=True, blank=True)
    tiktok_url = models.CharField(max_length=300, null=True, blank=True)
    zoom_url = models.CharField(max_length=900, null=True, blank=True)
    microsoftTeam_url = models.CharField(max_length=900, null=True, blank=True)
    location = models.CharField(max_length=900, blank=True, null=True)
    twitter_url = models.CharField(max_length=900, null=True, blank=True)
    playstore_url = models.CharField(max_length=900, null=True, blank=True)
    linkedin_url = models.CharField(max_length=900, null=True, blank=True)
    instagram_url = models.CharField(max_length=900, null=True, blank=True)
    pinterest_url = models.CharField(max_length=900, null=True, blank=True)
    youtube_url = models.CharField(max_length=1000, null=True, blank=True)
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    share_id = models.UUIDField(default=uuid.uuid4, editable=False)

    def __str__(self):
        return self.web_url
    
#models for privacy and terms of use
class TermsOfUse(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    last_updated = models.DateTimeField(auto_now=True)

class PrivacyPolicy(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    last_updated = models.DateTimeField(auto_now=True)

#Prospectors
#Prospectors
class Prospectors(models.Model):
    institution = models.CharField(max_length=100)
    address = models.CharField(max_length=100)
    copy = models.FileField(upload_to='store/prospectors/')
    logo = models.ImageField(upload_to='store/prospectors/')

    class Meta:
        managed = False  # Prevent Django from creating a new table in MA
        db_table = 'main_app_prospectors'  # Ensure it maps to the correct CMS table

    def __str__(self):
        return self.institution

#models
class Comment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  # Best practice
    # OR explicitly (if you prefer):
    # user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    likes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='comment_likes', blank=True)
    
    def __str__(self):
        return f"Comment by {self.user.username}"
    
    @property
    def like_count(self):
        return self.likes.count()
    
    @property
    def reply_count(self):
        return self.replies.count()
    

class Document(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='documents/')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False)
    
    def __str__(self):
        return self.title

class PaperRequest(models.Model):
    REQUEST_TYPES = [
        ('QP', 'Question Paper'),
        ('RM', 'Research Material'),
        ('HL', 'Homework Help'),
    ]
    
    request_type = models.CharField(max_length=2, choices=REQUEST_TYPES)
    description = models.TextField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    guest_email = models.EmailField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    fulfilled = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.get_request_type_display()} Request"
    
#deepseek
class AIChatLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    ip_address = models.GenericIPAddressField()
    question_type = models.CharField(max_length=50, choices=[
        ('career', 'Career Guidance'),
        ('school', 'School Management'),
        ('prospector', 'Undergraduate Prospector'),
        ('bursary', 'Bursaries/Financial Aid'),
        ('assessment', 'Assessments/Homework'),
        ('memorandum', 'Memorandums/Answer Keys'),
        ('general', 'General Question')
    ])
    question = models.TextField()
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.get_question_type_display()} - {self.created_at}"

#video comment
class VideoCategory(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

#video
class Video(models.Model):
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    category = models.ForeignKey(VideoCategory, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    video_file = models.FileField(upload_to='videos/', null=True, blank=True)  # ✅ Add this line
    thumbnail = models.ImageField(upload_to='video_thumbnails/', null=True, blank=True)
    date_posted = models.DateTimeField(default=timezone.now)


    # Social links
    website_url = models.CharField(max_length=2000, null=True, blank=True)
    gmail_url = models.CharField(max_length=2000, null=True, blank=True)
    whatsapp_number = models.CharField(max_length=20, null=True, blank=True)
    facebook_url = models.CharField(max_length=300, null=True, blank=True)
    tiktok_url = models.CharField(max_length=300, null=True, blank=True)
    zoom_url = models.CharField(max_length=900, null=True, blank=True)
    microsoftTeam_url = models.CharField(max_length=900, null=True, blank=True)
    location = models.CharField(max_length=900, blank=True, null=True)
    twitter_url = models.CharField(max_length=900, null=True, blank=True)
    playstore_url = models.CharField(max_length=900, null=True, blank=True)
    linkedin_url = models.CharField(max_length=900, null=True, blank=True)
    instagram_url = models.CharField(max_length=900, null=True, blank=True)
    pinterest_url = models.CharField(max_length=900, null=True, blank=True)
    youtube_url = models.CharField(max_length=1000, null=True, blank=True)

    def __str__(self):
        return self.title

#video comment
class VideoComment(models.Model):
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name="replies")
    text = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Comment by {self.user} on {self.video}"


class VideoLike(models.Model):
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('video', 'user')

    def __str__(self):
        return f"{self.user} likes {self.video}"
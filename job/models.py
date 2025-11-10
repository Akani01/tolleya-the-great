from django.db import models
from main_app.models import CustomUser
from django.utils import timezone
from django.conf import settings


# Create your models here.
EMPLOYED = "EMPLOYED"
UNEMPLOYED = "UNEMPLOYED"
PART_TIME_JOB = "PART_TIME_JOB"
LEARNERSHIP = "LEARNERSHIP"
INTERNSHIP = "INTERNSHIP"

SINGLE = "SINGLE"
MARRIED = "MARRIED"
UNKNOWN = "UNKNOWN"
OTHER = "OTHER"

STATUS = (
    (EMPLOYED, "EMPLOYED"),
    (UNEMPLOYED, "UNEMPLOYED"),
    (PART_TIME_JOB, "PART_TIME_JOB"),
    (LEARNERSHIP, "LEARNERSHIP"),
    (INTERNSHIP, "INTERNSHIP"),
    
)

MARITAL_STATUS = (
    (SINGLE, "SINGLE"),
    (MARRIED, "MARRIED"),
    (UNKNOWN, "UNKNOWN"),
    (OTHER, "OTHER"),
)

#Category model
class Category(models.Model):
    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'

    user = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=100, null=False, blank=False)

    def __str__(self):
        return self.name

#Jobs model
class Job(models.Model):
    class Meta:
        verbose_name = 'Job'
        verbose_name_plural = 'Jobs'
    
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True)
    author = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    image = models.ImageField(null=False, blank=False)
    video = models.FileField(upload_to="videos/", null=True, blank=True)
    website_url = models.CharField(max_length=2000, null=True, blank=True)
    whatsapp_number = models.CharField(max_length=20, null=True, blank=True)
    facebook_url = models.CharField(max_length=300, null=True, blank=True)
    zoom_url = models.CharField(max_length=900, null=True, blank=True)
    microsoftTeam_url = models.CharField(max_length=900, null=True, blank=True)
    location = models.CharField(max_length=900, blank=True, null=True)
    twitter_url = models.CharField(max_length=900, null=True, blank=True)
    playstore_url = models.CharField(max_length=900, null=True, blank=True)
    linkedin_url = models.CharField(max_length=900, null=True, blank=True)
    instagram_url = models.CharField(max_length=900, null=True, blank=True)
    pinterest_url = models.CharField(max_length=900, null=True, blank=True)
    youtube_url = models.CharField(max_length=1000, null=True, blank=True)
    upload_date = models.DateTimeField(auto_now_add=True)
    description = models.TextField()
   
    def __str__(self):
        return self.description


#apply jobs
class ApplyJob(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # links to your custom user model
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    full_names = models.CharField(max_length=2000, null=True, blank=True)
    age = models.CharField(max_length=2000, null=True, blank=True)
    address = models.CharField(max_length=2000, null=True, blank=True)
    qualifications = models.CharField(max_length=2000, null=True, blank=True)
    motivation = models.TextField()
    recent_jobs = models.CharField(max_length=2000, null=True, blank=True)
    position = models.CharField(max_length=2000, null=True, blank=True)
    marital_status = models.CharField(max_length=50, choices=MARITAL_STATUS)
    experience = models.CharField(max_length=2000, null=True, blank=True)
    contacts = models.CharField(max_length=2000, null=True, blank=True)
    whatsapp_no = models.CharField(max_length=2000, null=True, blank=True)
    image = models.ImageField(upload_to="jobs/img/%y/%m/%d/", default="default.png", null=True)
    cv = models.FileField(upload_to='jobs/cv/%y/%m/%d/')
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.full_names
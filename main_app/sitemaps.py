# sitemaps.py
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta
from .models import *
from job.models import *
from bursary.models import *
from college.models import *
from questpaper.models import *
# ========== DYNAMIC CONTENT SITEMAPS ==========

class JobSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8
    protocol = "https"

    def items(self):
        # Return only active/approved jobs
        return Job.objects.filter(is_active=True, is_approved=True).order_by('-created_date')

    def lastmod(self, obj):
        return obj.updated_date or obj.created_date
    
    def location(self, obj):
        # Assuming you have a job_detail view
        return reverse('job_detail', args=[obj.slug])

class BursarySitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.7
    protocol = "https"

    def items(self):
        # Return bursaries that are still open for applications
        today = timezone.now().date()
        return Bursary.objects.filter(
            application_deadline__gte=today
        ).order_by('-upload_time')

    def lastmod(self, obj):
        return obj.upload_time
    
    def priority(self, obj):
        # Higher priority for bursaries closing soon
        days_remaining = (obj.application_deadline - timezone.now().date()).days
        if days_remaining <= 7:
            return 0.9
        elif days_remaining <= 30:
            return 0.7
        return 0.6

class CollegeSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.7
    protocol = "https"

    def items(self):
        return College.objects.filter(is_active=True).order_by('-upload_time')

    def lastmod(self, obj):
        return obj.upload_time

class NewsSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.9
    protocol = "https"

    def items(self):
        # Return recent news items (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        return News.objects.filter(
            updated_date__gte=thirty_days_ago,
            is_published=True
        ).order_by('-updated_date')

    def lastmod(self, obj):
        return obj.updated_date
    
    def priority(self, obj):
        # Higher priority for recent news
        days_old = (timezone.now().date() - obj.updated_date.date()).days
        if days_old <= 1:
            return 1.0  # Breaking news
        elif days_old <= 7:
            return 0.9
        elif days_old <= 30:
            return 0.8
        return 0.5

class VideoSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6
    protocol = "https"

    def items(self):
        return Video.objects.filter(is_public=True).order_by('-date_posted')

    def lastmod(self, obj):
        return obj.date_posted

class QuestionPaperSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.7
    protocol = "https"

    def items(self):
        # Group by grade and school
        return QuestionPaper.objects.all().select_related(
            'grade', 'school', 'subject'
        ).order_by('-upload_date')

    def lastmod(self, obj):
        return obj.upload_date
    
    def priority(self, obj):
        # Higher priority for matric (Grade 12) papers
        if obj.grade and obj.grade.name == "12":
            return 0.9
        return 0.6

class SchoolSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.6
    protocol = "https"

    def items(self):
        return School.objects.filter(is_active=True).order_by('name')

    def lastmod(self, obj):
        # Use the latest update time from school dashboard
        return obj.updated_at

class PhotoSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.5
    protocol = "https"

    def items(self):
        # Photos from slider section
        return Photo.objects.filter(is_active=True).order_by('-upload_date')

    def lastmod(self, obj):
        return obj.upload_date

class ProspectorSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.6
    protocol = "https"

    def items(self):
        return Prospector.objects.filter(is_active=True).order_by('-created_date')

    def lastmod(self, obj):
        return obj.created_date

class SOSSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8
    protocol = "https"

    def items(self):
        # Assessment dates - future dates only
        today = timezone.now().date()
        return SOS.objects.filter(
            assessment_date__gte=today
        ).order_by('assessment_date')

    def lastmod(self, obj):
        return obj.created_date

# ========== STATIC PAGES SITEMAPS ==========

class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = "monthly"
    protocol = "https"

    def items(self):
        # List all your important static URLs
        return [
            'index',
            'about',
            'services',
            'contact_form',
            'faq',
            'help',
            'circuitmanager',
            'school_dashboard',
            'schoolupload',
            'login_page',
            'register_selection',
            'terms_of_use',
            'privacy_policy',
            'consulting',
            'message',
            'cases',
            'questionpaperlist',
            'prospectors_list',
            'college_list',
            'bursary_list',
            'soslistview',
            'video_add',
            'videos',
            'jobgallery',
        ]

    def location(self, item):
        return reverse(item)

class HighPriorityStaticSitemap(Sitemap):
    priority = 0.9
    changefreq = "weekly"
    protocol = "https"

    def items(self):
        return [
            'index',  # Homepage
            'college_list',  # Top priority section
            'bursary_list',  # Top priority section
            'school_dashboard',  # Main dashboard
        ]

    def location(self, item):
        return reverse(item)

# ========== SECTION PAGES SITEMAP ==========

class SectionSitemap(Sitemap):
    priority = 0.7
    changefreq = "weekly"
    protocol = "https"

    def items(self):
        # Important section anchors from your navigation
        return [
            '#college-section',
            '#bursary-section', 
            '#school-section',
            '#appointment-section',
            '#contact-section',
        ]

    def location(self, item):
        # These are page anchors, so they go to homepage with anchor
        return reverse('index') + item

# ========== USER PROFILE SITEMAPS ==========

class UserProfileSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.3
    protocol = "https"
    
    def items(self):
        # Only include public profiles
        return UserProfile.objects.filter(
            is_public=True,
            user__is_active=True
        )

    def lastmod(self, obj):
        return obj.updated_at
    
    def location(self, obj):
        return reverse('user_profile', args=[obj.user.username])

# ========== FEED SITEMAPS ==========

class RSSFeedSitemap(Sitemap):
    priority = 0.4
    changefreq = "daily"
    protocol = "https"

    def items(self):
        return ['news_feed', 'jobs_feed', 'bursaries_feed']

    def location(self, item):
        if item == 'news_feed':
            return '/feeds/news/'
        elif item == 'jobs_feed':
            return '/feeds/jobs/'
        elif item == 'bursaries_feed':
            return '/feeds/bursaries/'
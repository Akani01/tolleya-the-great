from django.db import models
from django.shortcuts import render
import json
import requests
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import (HttpResponse, HttpResponseRedirect,
                              get_object_or_404, redirect, render)
from django.templatetags.static import static
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from main_app.models import School, Grade, Term, Subject, Educator
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db import models
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.contrib.auth import get_user_model
import PyPDF2
import re
import threading

User = get_user_model()

class Department(models.Model):
    name = models.CharField(max_length=255)
    
    class Meta:
        ordering = ['name']
        
    def __str__(self):
        return self.name

class Grade(models.Model):
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=10, blank=True, null=True)
    
    class Meta:
        ordering = ['name']
        
    def __str__(self):
        return self.name

class Term(models.Model):
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=10, blank=True, null=True)
    
    class Meta:
        ordering = ['name']
        
    def __str__(self):
        return self.name

class School(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=20, blank=True, null=True)
    
    class Meta:
        ordering = ['name']
        
    def __str__(self):
        return self.name

class Subject(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=20, blank=True, null=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['name']
        
    def __str__(self):
        return self.name

class ExtractionPatternManager(models.Manager):
    def get_active_patterns(self):
        """Get all active patterns ordered by priority"""
        return self.filter(is_active=True).order_by('priority')
    
    def get_patterns_by_type(self, field_type):
        """Get active patterns for specific field type"""
        return self.filter(field_type=field_type, is_active=True).order_by('priority')
    
    def get_high_priority_patterns(self, threshold=5):
        """Get high priority patterns"""
        return self.filter(is_active=True, priority__lte=threshold).order_by('priority')

class ExtractionPattern(models.Model):
    """Store patterns for extracting different types of information from PDFs"""
    
    FIELD_TYPE_CHOICES = [
        ('topic', 'Topic'),
        ('question_count', 'Question Count'),
        ('subject', 'Subject'),
        ('grade', 'Grade'),
        ('complexity', 'Complexity'),
        ('term', 'Term'),
        ('school', 'School'),
    ]
    
    name = models.CharField(max_length=255)
    field_type = models.CharField(max_length=100, choices=FIELD_TYPE_CHOICES)
    pattern = models.TextField(help_text="Regex pattern for extraction")
    priority = models.IntegerField(default=1, help_text="Lower numbers = higher priority")
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True, help_text="Pattern description and usage")
    
    objects = ExtractionPatternManager()
    
    class Meta:
        ordering = ['field_type', 'priority']
        verbose_name = 'Extraction Pattern'
        verbose_name_plural = 'Extraction Patterns'
    
    def __str__(self):
        return f"{self.name} ({self.field_type}) - Priority {self.priority}"
    
    def clean(self):
        """Validate regex pattern"""
        try:
            re.compile(self.pattern)
        except re.error as e:
            raise ValidationError(f"Invalid regex pattern: {e}")

class Topic(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    
    class Meta:
        ordering = ['name']
        
    def __str__(self):
        return self.name

class QuestionPaperManager(models.Manager):
    def high_confidence(self, threshold=0.7):
        """Get question papers with high extraction confidence"""
        return self.filter(extraction_confidence__gte=threshold)
    
    def needs_review(self):
        """Get question papers that need manual review"""
        return self.filter(extraction_confidence__lt=0.3)
    
    def by_subject(self, subject_name):
        """Get question papers by subject name"""
        return self.filter(subject__name__icontains=subject_name)
    
    def by_grade_and_term(self, grade_name, term_name):
        """Get question papers by grade and term"""
        return self.filter(grade__name__icontains=grade_name, term__name__icontains=term_name)
    
    def by_uploader(self, user):
        """Get question papers uploaded by specific user"""
        return self.filter(uploaded_by=user)

class QuestionPaper(models.Model):
    # Core relationships
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, null=True, blank=True)
    term = models.ForeignKey(Term, on_delete=models.CASCADE, null=True, blank=True)
    school = models.ForeignKey(School, on_delete=models.CASCADE, null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, blank=True)
    
    # Upload information
    uploaded_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='uploaded_question_papers'
    )
    file = models.FileField(upload_to='question_papers/%Y/%m/%d/')
    
    # Complexity rating
    COMPLEXITY_CHOICES = [(i, f"Level {i}") for i in range(1, 6)]
    complexity_rating = models.IntegerField(choices=COMPLEXITY_CHOICES, default=3)
    
    # Content management
    topics = models.ManyToManyField(Topic, related_name="question_papers", blank=True)
    number_of_questions = models.IntegerField(default=0)
    
    # Auto-extracted fields
    extracted_text = models.TextField(blank=True, null=True)
    extraction_confidence = models.FloatField(default=0.0)
    auto_detected_data = models.JSONField(default=dict, blank=True)
    
    # Status tracking
    is_processed = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True, null=True)
    
    objects = QuestionPaperManager()
    
    class Meta:
        ordering = ['-id']
        verbose_name = 'Question Paper'
        verbose_name_plural = 'Question Papers'
    
    def __str__(self):
        components = []
        if self.grade:
            components.append(str(self.grade))
        if self.term:
            components.append(str(self.term))
        if self.subject:
            components.append(self.subject.name)
        if components:
            return " - ".join(components)
        return f"Question Paper - {self.file.name}"
    
    def clean(self):
        """Django model validation"""
        errors = {}
        
        # Validate file type
        if self.file and not self.file.name.lower().endswith('.pdf'):
            errors['file'] = "Only PDF files are allowed"
        
        # Validate confidence score
        if self.extraction_confidence < 0 or self.extraction_confidence > 1:
            errors['extraction_confidence'] = "Confidence score must be between 0 and 1"
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Override save to include validation and auto-processing"""
        self.clean()
        is_new = self.pk is None
        
        super().save(*args, **kwargs)
        
        # Auto-process new question papers
        if is_new and self.file:
            self.schedule_auto_processing()
    
    def schedule_auto_processing(self):
        """Schedule PDF processing in background thread"""
        try:
            thread = threading.Thread(target=self.process_pdf_automatically)
            thread.daemon = True
            thread.start()
        except Exception as e:
            print(f"Error scheduling processing: {e}")
            self.processing_error = str(e)
            self.save()
    
    def extract_text_from_pdf(self):
        """Enhanced PDF text extraction with better error handling"""
        try:
            if not self.file.name.lower().endswith('.pdf'):
                self.processing_error = "File is not a PDF"
                return ""
            
            text = ""
            with self.file.open('rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                
                if len(pdf_reader.pages) == 0:
                    self.processing_error = "PDF has no pages"
                    return ""
                
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        # Clean up common PDF extraction issues
                        page_text = re.sub(r'\s+', ' ', page_text)  # Normalize whitespace
                        page_text = re.sub(r'(\w+)-\s+(\w+)', r'\1\2', page_text)  # Fix hyphenated words
                        text += f"--- Page {page_num + 1} ---\n{page_text}\n\n"
            
            self.extracted_text = text.strip()
            return self.extracted_text
            
        except Exception as e:
            error_msg = f"Error extracting text from PDF: {e}"
            print(error_msg)
            self.processing_error = error_msg
            return ""
    
    def clean_extracted_value(self, value):
        """Clean and normalize extracted values"""
        if not value or value in ["", "—", None, "nan", "null", "undefined"]:
            return None
            
        value = str(value).strip()
        
        # Remove common noise characters but keep essential punctuation
        noise_chars = ['≈', '~', '+', '$', '€', '£', '—', '•', '·', '"', "'", '\\', '/']
        for ch in noise_chars:
            value = value.replace(ch, '')
            
        # Handle number ranges (take first value)
        if '-' in value and not value.startswith('-'):
            try:
                parts = value.split('-')
                if len(parts) == 2 and parts[0].strip().isdigit():
                    return parts[0].strip()
            except:
                pass
                
        # Remove extra whitespace
        value = re.sub(r'\s+', ' ', value).strip()
        
        return value if value else None

    def extract_with_patterns(self, text):
        """Extract information using configured patterns with improved matching"""
        extracted_data = {}
        patterns_matched = 0
        total_attempted = 0
        
        # Get active patterns ordered by priority
        patterns = ExtractionPattern.objects.get_active_patterns()
        total_patterns = patterns.count()
        
        for pattern in patterns:
            total_attempted += 1
            try:
                # Compile pattern for better performance
                compiled_pattern = re.compile(pattern.pattern, re.IGNORECASE | re.MULTILINE)
                matches = compiled_pattern.findall(text)
                
                if matches:
                    # Handle different match types (groups vs simple matches)
                    if isinstance(matches[0], tuple):
                        # Take first non-empty group
                        match_value = next((group for group in matches[0] if group.strip()), '')
                    else:
                        match_value = matches[0]
                    
                    cleaned_value = self.clean_extracted_value(match_value)
                    if cleaned_value:
                        # Only overwrite if higher priority or not set
                        if pattern.field_type not in extracted_data or pattern.priority < 3:
                            extracted_data[pattern.field_type] = cleaned_value
                            patterns_matched += 1
                            print(f"✅ Matched {pattern.field_type}: {cleaned_value} (Pattern: {pattern.name})")
            except Exception as e:
                print(f"❌ Pattern error {pattern.name}: {e}")
                continue
        
        # Calculate confidence based on patterns matched vs attempted
        confidence_score = patterns_matched / total_attempted if total_attempted > 0 else 0.0
        
        return extracted_data, confidence_score

    def auto_detect_topics(self, text):
        """Smart topic detection from PDF content with improved patterns"""
        detected_topics = []
        
        # Enhanced topic indicators
        topic_indicators = [
            r'section\s*[a-z]\s*[:\-]\s*([^\n]{5,100})',
            r'topic\s*[:\-]\s*([^\n]{5,100})',
            r'part\s*[a-z]\s*[:\-]\s*([^\n]{5,100})',
            r'answer\s*(?:questions?|all)\s*from\s*([^\n]{5,100})',
            r'chapter\s*[:\-]\s*([^\n]{5,100})',
            r'unit\s*[:\-]\s*([^\n]{5,100})',
            r'\[topic\s*[:\-]\s*([^\]]+)\]',
            r'topic\s*name\s*[:\-]\s*([^\n]{5,100})',
        ]
        
        for pattern_str in topic_indicators:
            try:
                pattern = re.compile(pattern_str, re.IGNORECASE)
                matches = pattern.findall(text)
                for match in matches:
                    # Enhanced cleaning
                    topic_name = re.sub(r'[^a-zA-Z0-9\s\-\.]', '', match).strip()
                    topic_name = re.sub(r'\s+', ' ', topic_name)  # Normalize spaces
                    
                    if 3 <= len(topic_name) <= 100 and not topic_name.isdigit():
                        # Title case for consistency
                        topic_name = topic_name.title()
                        topic, created = Topic.objects.get_or_create(
                            name=topic_name,
                            defaults={'name': topic_name}
                        )
                        if topic not in detected_topics:
                            detected_topics.append(topic)
                            print(f"📚 Detected topic: {topic_name}")
            except Exception as e:
                print(f"Topic detection error with pattern {pattern_str}: {e}")
                continue
        
        return detected_topics

    def count_questions_advanced(self, text):
        """Advanced question counting with multiple patterns and validation"""
        question_numbers = set()
        
        # Pre-compiled patterns for better performance
        question_patterns = [
            re.compile(r'question\s*(\d+)', re.IGNORECASE),
            re.compile(r'q\.?\s*(\d+)', re.IGNORECASE),
            re.compile(r'^\s*(\d+)\.', re.MULTILINE),
            re.compile(r'\(\s*(\d+)\s*\)'),
            re.compile(r'\[(\d+)\]'),
            re.compile(r'^\s*(\d+)\s+[a-zA-Z]', re.MULTILINE),
        ]
        
        for pattern in question_patterns:
            matches = pattern.findall(text)
            for match in matches:
                if match.isdigit():
                    q_num = int(match)
                    # Validate reasonable question numbers
                    if 1 <= q_num <= 100:
                        question_numbers.add(q_num)
        
        # Enhanced range detection
        range_patterns = [
            re.compile(r'questions?\s*(\d+)\s*to\s*(\d+)', re.IGNORECASE),
            re.compile(r'questions?\s*(\d+)\s*-\s*(\d+)', re.IGNORECASE),
            re.compile(r'q\.?\s*(\d+)\s*to\s*(\d+)', re.IGNORECASE),
        ]
        
        for pattern in range_patterns:
            matches = pattern.findall(text)
            for start, end in matches:
                if start.isdigit() and end.isdigit():
                    start_num, end_num = int(start), int(end)
                    if 1 <= start_num <= end_num <= 100:
                        question_numbers.update(range(start_num, end_num + 1))
        
        count = len(question_numbers)
        print(f"🔢 Detected {count} unique questions")
        return count

    def find_related_objects(self, extracted_data):
        """Find and assign related objects based on extracted data"""
        # Find subject
        if 'subject' in extracted_data and not self.subject:
            subject_name = extracted_data['subject']
            try:
                subject = Subject.objects.filter(
                    name__icontains=subject_name
                ).first()
                if not subject:
                    subject = Subject.objects.create(name=subject_name.title())
                self.subject = subject
                print(f"📖 Assigned subject: {subject.name}")
            except Exception as e:
                print(f"Error finding subject: {e}")
        
        # Find grade
        if 'grade' in extracted_data and not self.grade:
            grade_name = extracted_data['grade']
            try:
                grade = Grade.objects.filter(
                    name__icontains=grade_name
                ).first()
                if not grade:
                    grade = Grade.objects.create(name=grade_name.title())
                self.grade = grade
                print(f"🎓 Assigned grade: {grade.name}")
            except Exception as e:
                print(f"Error finding grade: {e}")
        
        # Find term
        if 'term' in extracted_data and not self.term:
            term_name = extracted_data['term']
            try:
                term = Term.objects.filter(
                    name__icontains=term_name
                ).first()
                if not term:
                    term = Term.objects.create(name=term_name.title())
                self.term = term
                print(f"📅 Assigned term: {term.name}")
            except Exception as e:
                print(f"Error finding term: {e}")
        
        # Find school
        if 'school' in extracted_data and not self.school:
            school_name = extracted_data['school']
            try:
                school = School.objects.filter(
                    name__icontains=school_name
                ).first()
                if not school:
                    school = School.objects.create(name=school_name.title())
                self.school = school
                print(f"🏫 Assigned school: {school.name}")
            except Exception as e:
                print(f"Error finding school: {e}")

    def process_pdf_automatically(self):
        """Main method to process PDF and auto-fill fields with enhanced error handling"""
        try:
            print(f"🔄 Starting automatic processing for: {self.file.name}")
            
            # Extract text from PDF
            text = self.extract_text_from_pdf()
            if not text:
                self.is_processed = True
                self.processing_error = "No text extracted from PDF"
                self.save()
                return False
            
            # Extract data using patterns
            extracted_data, confidence = self.extract_with_patterns(text)
            
            # Auto-detect topics
            detected_topics = self.auto_detect_topics(text)
            
            # Count questions if not detected by patterns
            if 'question_count' not in extracted_data:
                question_count = self.count_questions_advanced(text)
                if question_count > 0:
                    extracted_data['question_count'] = question_count
                    self.number_of_questions = question_count
            else:
                try:
                    self.number_of_questions = int(extracted_data['question_count'])
                except (ValueError, TypeError):
                    pass
            
            # Find and assign related objects
            self.find_related_objects(extracted_data)
            
            # Save extracted data and update status
            self.auto_detected_data = extracted_data
            self.extraction_confidence = confidence
            self.is_processed = True
            self.processing_error = ""  # Clear any previous errors
            
            # Save the instance
            self.save()
            
            # Add detected topics
            if detected_topics:
                self.topics.add(*detected_topics)
                print(f"✅ Added {len(detected_topics)} topics")
            
            print(f"✅ Successfully processed {self.file.name} (Confidence: {confidence:.2f})")
            return True
            
        except Exception as e:
            error_msg = f"Error processing PDF: {e}"
            print(f"❌ {error_msg}")
            self.is_processed = True
            self.processing_error = error_msg
            self.save()
            return False

    # Utility methods
    def get_extracted_field(self, field_name):
        """Safely get extracted field value"""
        return self.auto_detected_data.get(field_name)
    
    def get_topic_names(self):
        """Get list of topic names"""
        return list(self.topics.values_list('name', flat=True))
    
    def get_processing_status(self):
        """Get human-readable processing status"""
        if not self.is_processed:
            return "Pending"
        elif self.processing_error:
            return f"Error: {self.processing_error[:50]}..."
        elif self.extraction_confidence > 0.7:
            return "High confidence"
        elif self.extraction_confidence > 0.4:
            return "Medium confidence"
        else:
            return "Low confidence - needs review"
    
    def reprocess(self):
        """Force reprocessing of the question paper"""
        self.is_processed = False
        self.processing_error = None
        self.extraction_confidence = 0.0
        self.auto_detected_data = {}
        self.save()
        return self.process_pdf_automatically()

# Signal handlers
@receiver(post_save, sender=QuestionPaper)
def handle_new_question_paper(sender, instance, created, **kwargs):
    """Auto-process new question papers if not already processed"""
    if created and instance.file and not instance.is_processed:
        # Small delay to ensure save is complete
        import time
        time.sleep(1)
        instance.schedule_auto_processing()

#Prospectors
class Prospectors(models.Model):
    institution = models.CharField(max_length=100)
    address = models.CharField(max_length=100)
    copy = models.FileField(upload_to='store/prospectors/')
    logo = models.ImageField(upload_to='store/prospectors/')

    def __str__(self):
        return self.filename

    def delete(self, *args, **kwargs):
        self.copy.delete()
        self.logo.delete()
        super().delete(*args, **kwargs)
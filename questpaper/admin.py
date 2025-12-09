from django.contrib import admin
from .models import *

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']
    
@admin.register(ExtractionPattern)
class ExtractionPatternAdmin(admin.ModelAdmin):
    list_display = ['name', 'field_type', 'priority', 'is_active']
    list_filter = ['field_type', 'is_active']
    list_editable = ['priority', 'is_active']
    search_fields = ['name', 'pattern']
    ordering = ['field_type', 'priority']


@admin.register(QuestionPaper)
class QuestionPaperAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'title', 'subject', 'grade', 'term', 
        'number_of_questions', 'extraction_confidence', 
        'get_processing_status_display'
    ]
    list_filter = [
        'grade', 'term', 'subject', 'department',
        'is_processed', 'complexity_rating'
    ]
    search_fields = [
        'title', 'extracted_text', 'subject__name', 
        'grade__name', 'term__name'
    ]
    readonly_fields = [
        'extraction_confidence', 'auto_detected_data', 
        'extracted_text', 'is_processed', 'processing_error'
        # Remove 'created_at', 'updated_at' if they don't exist
    ]
    filter_horizontal = ['topics']
    actions = ['reprocess_selected', 'mark_high_confidence']
    
    def get_processing_status_display(self, obj):
        return obj.get_processing_status()
    get_processing_status_display.short_description = 'Status'
    
    def reprocess_selected(self, request, queryset):
        for qp in queryset:
            qp.reprocess()
        self.message_user(request, f"Scheduled reprocessing for {queryset.count()} question papers")
    reprocess_selected.short_description = "Reprocess selected question papers"
    
    def mark_high_confidence(self, request, queryset):
        updated = queryset.update(extraction_confidence=0.9)
        self.message_user(request, f"Marked {updated} question papers as high confidence")
    mark_high_confidence.short_description = "Mark as high confidence"

from main_app.models import Subject, Grade, Term, School
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from questpaper.models import QuestionPaper
from main_app.models import School, Grade, Term, Subject, Educator
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.http import FileResponse, Http404
import os
import mimetypes
from django.conf import settings
from questpaper.forms import QuestionPaperUploadForm
from django.http import HttpResponse, FileResponse
from django.core.exceptions import ObjectDoesNotExist
from .models import *
from .forms import *
from django.contrib import messages

# =========================
# FUNCTION-BASED VIEWS
# =========================

def upload_question_paper(request):
    """Handle single and bulk uploads"""
    if request.method == 'POST':
        if 'files' in request.FILES:
            return handle_bulk_upload(request)
        else:
            return handle_single_upload(request)
    
    single_form = QuestionPaperUploadForm()
    bulk_form = BulkUploadForm()
    
    context = {
        'single_form': single_form,
        'bulk_form': bulk_form,
        'grades': Grade.objects.all(),
        'terms': Term.objects.all(),
        'schools': School.objects.all(),
        'departments': Department.objects.all(),
        'subjects': Subject.objects.all(),
    }
    return render(request, 'questpaper/upload.html', context)

def handle_single_upload(request):
    """Process single file upload"""
    form = QuestionPaperUploadForm(request.POST, request.FILES)
    if form.is_valid():
        paper = form.save(commit=False)
        paper.uploaded_by = request.user
        
        if not paper.name and paper.file:
            filename = os.path.splitext(paper.file.name)[0]
            clean_name = filename.replace('_', ' ').replace('-', ' ').title()
            paper.name = clean_name
        
        paper.save()
        form.save_m2m()
        messages.success(request, f"Question paper '{paper.name}' uploaded successfully!")
        return redirect('questpaper_list')
    else:
        messages.error(request, "Please correct the errors below.")
        return render(request, 'questpaper/upload.html', {
            'single_form': form,
            'bulk_form': BulkUploadForm(),
            'grades': Grade.objects.all(),
            'terms': Term.objects.all(),
            'schools': School.objects.all(),
            'departments': Department.objects.all(),
            'subjects': Subject.objects.all(),
        })

def handle_bulk_upload(request):
    """Process multiple file upload"""
    form = BulkUploadForm(request.POST, request.FILES)
    if form.is_valid():
        files = request.FILES.getlist('files')
        successful = 0
        
        for file in files:
            try:
                filename = os.path.splitext(file.name)[0]
                clean_name = filename.replace('_', ' ').replace('-', ' ').title()
                
                paper = QuestionPaper(
                    name=clean_name,
                    file=file,
                    uploaded_by=request.user,
                    grade=form.cleaned_data.get('grade'),
                    term=form.cleaned_data.get('term'),
                    school=form.cleaned_data.get('school'),
                )
                paper.save()
                successful += 1
            except Exception as e:
                print(f"Error uploading {file.name}: {e}")
                messages.warning(request, f"Failed to upload {file.name}: {str(e)}")
                continue
        
        if successful > 0:
            messages.success(request, f"Successfully uploaded {successful} question papers.")
        else:
            messages.error(request, "No files were uploaded.")
        
        return redirect('questpaper_list')
    else:
        messages.error(request, "Please select valid PDF files.")
        return render(request, 'questpaper/upload.html', {
            'single_form': QuestionPaperUploadForm(),
            'bulk_form': form,
            'grades': Grade.objects.all(),
            'terms': Term.objects.all(),
            'schools': School.objects.all(),
            'departments': Department.objects.all(),
            'subjects': Subject.objects.all(),
        })

def view_question_paper(request, pk):
    """View a question paper PDF in browser"""
    question_paper = get_object_or_404(QuestionPaper, pk=pk)
    
    try:
        file = question_paper.file.open('rb')
        file_name = question_paper.file.name
        content_type, encoding = mimetypes.guess_type(file_name)
        if content_type is None:
            content_type = 'application/pdf'
        
        response = FileResponse(file, content_type=content_type)
        filename = os.path.basename(file_name)
        if not filename.endswith('.pdf'):
            filename += '.pdf'
            
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response
    except Exception as e:
        return HttpResponse(f"Error opening file: {str(e)}", status=500)


def download_question_paper(request, pk):
    """Download question paper file"""
    paper = get_object_or_404(QuestionPaper, pk=pk)

    if not paper.file:
        raise Http404("File not found")

    try:
        # Open the file using Django's storage API
        file = paper.file.open('rb')
        
        # Get the filename
        filename = paper.name or os.path.basename(paper.file.name)
        if not filename.endswith('.pdf'):
            filename += '.pdf'
        
        # Create response
        response = FileResponse(file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Add Content-Length header if possible
        try:
            response['Content-Length'] = paper.file.size
        except (AttributeError, NotImplementedError):
            pass
            
        return response
        
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error downloading file {paper.file.name}: {str(e)}")
        
        raise Http404(f"File could not be opened: {str(e)}")

        
def filter_by_grade(question_papers, grade):
    """
    Filter question papers by grade.
    Usage in template: {{ question_papers|filter_by_grade:grade }}
    """
    if hasattr(question_papers, 'filter'):
        return question_papers.filter(grade=grade)
    elif isinstance(question_papers, (list, tuple)):
        return [paper for paper in question_papers 
                if hasattr(paper, 'grade') and paper.grade.id == grade.id]
    return question_papers.none() if hasattr(question_papers, 'none') else []

def question_paper_list(request):
    """List all question papers"""
    papers = QuestionPaper.objects.all()
    
    grade_filter = request.GET.get('grade')
    term_filter = request.GET.get('term')
    status_filter = request.GET.get('status')
    
    if grade_filter:
        papers = papers.filter(grade_id=grade_filter)
    if term_filter:
        papers = papers.filter(term_id=term_filter)
    if status_filter == 'processed':
        papers = papers.filter(is_processed=True)
    elif status_filter == 'pending':
        papers = papers.filter(is_processed=False)
    
    context = {
        'papers': papers,
        'grades': Grade.objects.all(),
        'terms': Term.objects.all(),
        'total_count': papers.count(),
        'processed_count': QuestionPaper.objects.filter(is_processed=True).count(),
        'pending_count': QuestionPaper.objects.filter(is_processed=False).count(),
    }
    return render(request, 'questpaper/list.html', context)

def question_paper_detail(request, pk):
    """View question paper details"""
    paper = get_object_or_404(QuestionPaper, pk=pk)
    context = {
        'paper': paper,
    }
    return render(request, 'questpaper/detail.html', context)

def delete_question_paper(request, pk):
    """Delete a question paper"""
    if request.method == 'POST':
        paper = get_object_or_404(QuestionPaper, pk=pk, uploaded_by=request.user)
        paper_name = paper.name or paper.file.name
        paper.delete()
        messages.success(request, f"'{paper_name}' has been deleted.")
        return redirect('questpaper_list')

def reprocess_paper(request, pk):
    """Reprocess a question paper"""
    if request.method == 'POST':
        paper = get_object_or_404(QuestionPaper, pk=pk, uploaded_by=request.user)
        paper.is_processed = False
        paper.processing_error = None
        paper.save()
        messages.success(request, "Question paper is being reprocessed.")
        return redirect('questpaper_detail', pk=pk)

def filter_question_papers(request):
    """Filter Question Papers"""
    question_papers = QuestionPaper.objects.all().select_related(
        'grade', 'term', 'school', 'department', 'subject'
    ).prefetch_related('topics')
    
    grade_filter = request.GET.get('grade')
    term_filter = request.GET.get('term')
    subject_filter = request.GET.get('subject')
    department_filter = request.GET.get('department')
    school_filter = request.GET.get('school')
    
    if grade_filter:
        question_papers = question_papers.filter(grade_id=grade_filter)
    if term_filter:
        question_papers = question_papers.filter(term_id=term_filter)
    if subject_filter:
        question_papers = question_papers.filter(subject_id=subject_filter)
    if department_filter:
        question_papers = question_papers.filter(department_id=department_filter)
    if school_filter:
        question_papers = question_papers.filter(school_id=school_filter)
    
    departments = Department.objects.all()
    grades = Grade.objects.all()
    terms = Term.objects.all()
    schools = School.objects.all()
    subjects = Subject.objects.all()

    context = {
        'question_papers': question_papers.order_by('grade__name', 'subject__name'),
        'departments': departments,
        'grades': grades,
        'terms': terms,
        'schools': schools,
        'subjects': subjects,
        'total_count': question_papers.count(),
    }
    return render(request, 'question_papers/questionpaperlist.html', context)

# =========================
# CLASS-BASED VIEWS
# =========================

class QuestionPaperListView(ListView):
    model = QuestionPaper
    template_name = 'question_papers/question_paper_list.html'
    context_object_name = 'question_papers'
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            'grade', 'term', 'school', 'department', 'subject'
        ).order_by('grade__name', 'subject__name')
        
        filters = {}
        
        if self.request.GET.get('grade'):
            filters['grade_id'] = self.request.GET.get('grade')
        if self.request.GET.get('term'):
            filters['term_id'] = self.request.GET.get('term')
        if self.request.GET.get('subject'):
            filters['subject_id'] = self.request.GET.get('subject')
        if self.request.GET.get('department'):
            filters['department_id'] = self.request.GET.get('department')
        if self.request.GET.get('school'):
            filters['school_id'] = self.request.GET.get('school')
        if self.request.GET.get('status') == 'processed':
            filters['is_processed'] = True
        elif self.request.GET.get('status') == 'pending':
            filters['is_processed'] = False
            
        if filters:
            queryset = queryset.filter(**filters)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['grades'] = Grade.objects.all().order_by('name')
        context['terms'] = Term.objects.all().order_by('name')
        context['subjects'] = Subject.objects.all().order_by('name')
        context['departments'] = Department.objects.all().order_by('name')
        context['schools'] = School.objects.all().order_by('name')
        context['total_count'] = self.get_queryset().count()
        context['processed_count'] = QuestionPaper.objects.filter(is_processed=True).count()
        context['pending_count'] = QuestionPaper.objects.filter(is_processed=False).count()
        return context

class TopicListView(ListView):
    model = Topic
    template_name = 'topics/topic_list.html'
    context_object_name = 'topics'
    paginate_by = 20

    def get_queryset(self):
        queryset = Topic.objects.all().order_by('name')
        subject = self.request.GET.get('subject')
        grade = self.request.GET.get('grade')

        if subject:
            queryset = queryset.filter(subject_id=subject)
        if grade:
            queryset = queryset.filter(grade_id=grade)

        return queryset

class TopicCreateView(CreateView):
    model = Topic
    fields = ['name']
    template_name = 'topic_form.html'
    success_url = reverse_lazy('topic_list')

class TopicDetailView(DetailView):
    model = Topic
    template_name = 'topic_detail.html'
    context_object_name = 'topic'

class TopicUpdateView(UpdateView):
    model = Topic
    fields = ['name']
    template_name = 'topic_form.html'
    success_url = reverse_lazy('topic_list')

class TopicDeleteView(DeleteView):
    model = Topic
    template_name = 'topic_confirm_delete.html'
    success_url = reverse_lazy('topic_list')

class DepartmentListView(ListView):
    model = Department
    template_name = 'department_list.html'
    context_object_name = 'departments'

class DepartmentCreateView(CreateView):
    model = Department
    fields = ['name']
    template_name = 'department_form.html'
    success_url = reverse_lazy('department_list')

class DepartmentDetailView(DetailView):
    model = Department
    template_name = 'department_detail.html'
    context_object_name = 'department'

class DepartmentUpdateView(UpdateView):
    model = Department
    fields = ['name']
    template_name = 'department_form.html'
    success_url = reverse_lazy('department_list')

class DepartmentDeleteView(DeleteView):
    model = Department
    template_name = 'department_confirm_delete.html'
    success_url = reverse_lazy('department_list')
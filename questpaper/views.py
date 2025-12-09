from main_app.models import Subject, Grade, Term, School
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from questpaper.models import QuestionPaper
from main_app.models import School, Grade, Term, Subject, Educator
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView
from django.urls import reverse_lazy
import os
from django.conf import settings
from questpaper.forms import QuestionPaperUploadForm
from django.http import HttpResponse, FileResponse
from django.core.exceptions import ObjectDoesNotExist
from .models import *
from .forms import *
from django.contrib import messages

#upload questionpapers


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
        paper.save()
        form.save_m2m()  # Save many-to-many relationships
        messages.success(request, "Question paper uploaded and is being processed!")
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
                paper = QuestionPaper(
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
                continue
        
        if successful > 0:
            messages.success(request, f"Successfully uploaded {successful} files. They are being processed.")
        else:
            messages.error(request, "No files were uploaded. Please check if they are valid PDFs.")
        
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
    
    # Get the file path
    file_path = question_paper.file.path
    
    # Check if file exists
    if not os.path.exists(file_path):
        return HttpResponse("File not found", status=404)
    
    try:
        # Open file in binary mode
        file = open(file_path, 'rb')
        
        # Get content type
        content_type, encoding = mimetypes.guess_type(file_path)
        if content_type is None:
            content_type = 'application/pdf'
        
        # Create response
        response = FileResponse(file, content_type=content_type)
        response['Content-Disposition'] = f'inline; filename="{os.path.basename(file_path)}"'
        
        return response
    except Exception as e:
        return HttpResponse(f"Error opening file: {str(e)}", status=500)


def download_question_paper(request, pk):
    """Download a question paper"""
    question_paper = get_object_or_404(QuestionPaper, pk=pk)
    
    # Get the file path
    file_path = question_paper.file.path
    
    # Check if file exists
    if not os.path.exists(file_path):
        return HttpResponse("File not found", status=404)
    
    try:
        # Open file in binary mode
        file = open(file_path, 'rb')
        
        # Get content type
        content_type, encoding = mimetypes.guess_type(file_path)
        if content_type is None:
            content_type = 'application/octet-stream'
        
        # Create response for download
        response = FileResponse(file, content_type=content_type)
        filename = question_paper.title or os.path.basename(file_path)
        response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
        
        return response
    except Exception as e:
        return HttpResponse(f"Error downloading file: {str(e)}", status=500)


def question_paper_list(request):
    """List all question papers"""
    papers = QuestionPaper.objects.all()
    
    # Filtering
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

def download_question_paper(request, pk):
    """Download question paper file"""
    paper = get_object_or_404(QuestionPaper, pk=pk)
    
    try:
        response = HttpResponse(paper.file, content_type='application/pdf')
        filename = paper.title or paper.file.name.split('/')[-1]
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        messages.error(request, "File not found or cannot be downloaded.")
        return redirect('questpaper_detail', pk=pk)


def delete_question_paper(request, pk):
    """Delete a question paper"""
    if request.method == 'POST':
        paper = get_object_or_404(QuestionPaper, pk=pk, uploaded_by=request.user)
        paper_name = paper.title or paper.file.name
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
        paper.schedule_auto_processing()
        messages.success(request, "Question paper is being reprocessed.")
        return redirect('questpaper_detail', pk=pk)

#question papers
class QuestionPaperListView(ListView):
    model = QuestionPaper
    template_name = 'question_papers/question_paper_list.html'
    context_object_name = 'question_papers'
    
    def get_queryset(self):
        """Get filtered queryset"""
        queryset = super().get_queryset().select_related(
            'grade', 'term', 'school', 'department', 'subject'
        ).order_by('grade__name', 'subject__name')
        
        # Apply filters from GET parameters
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
        """Add additional context data"""
        context = super().get_context_data(**kwargs)
        
        # Add filter options to context
        context['grades'] = Grade.objects.all().order_by('name')
        context['terms'] = Term.objects.all().order_by('name')
        context['subjects'] = Subject.objects.all().order_by('name')
        context['departments'] = Department.objects.all().order_by('name')
        context['schools'] = School.objects.all().order_by('name')
        
        # Add counts
        context['total_count'] = self.get_queryset().count()
        context['processed_count'] = QuestionPaper.objects.filter(is_processed=True).count()
        context['pending_count'] = QuestionPaper.objects.filter(is_processed=False).count()
        
        return context

#question_paper_detail
def question_paper_detail(request, paper_id):
    paper = get_object_or_404(QuestionPaper, id=paper_id)
    
    # Check if the file is a PDF
    is_pdf = paper.file.url.lower().endswith('.pdf')

    return render(request, 'question_paper_detail.html', {'paper': paper, 'is_pdf': is_pdf})

# Filter Question Papers
def filter_question_papers(request):
    # Get all question papers with related data
    question_papers = QuestionPaper.objects.all().select_related(
        'grade', 'term', 'school', 'department', 'subject'
    ).prefetch_related('topics')
    
    # Apply filters from GET parameters
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
    
    # Get all filter options
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


# Download Question Paper
def download_question_paper(request, pk):
    try:
        question_paper = QuestionPaper.objects.get(pk=pk)
        response = FileResponse(open(question_paper.file.path, 'rb'))
        return response
    except ObjectDoesNotExist:
        return HttpResponse("Question paper not found", status=404)
        

# View the Question Paper (instead of download)
def view_question_paper(request, pk):
    question_paper = get_object_or_404(QuestionPaper, pk=pk)

    # If the file is a PDF, render it in the browser
    file_path = question_paper.file.path

    if file_path.endswith('.pdf'):
        return FileResponse(open(file_path, 'rb'), content_type='application/pdf')
    else:
        return HttpResponse("This file format is not supported for viewing.", status=400)

# Topic Views
class TopicListView(ListView):
    model = Topic
    template_name = 'topic_list.html'  # Template to use
    context_object_name = 'topics'    # Context name in template

class TopicCreateView(CreateView):
    model = Topic
    fields = ['name']
    template_name = 'topic_form.html'  # Template for the form
    success_url = reverse_lazy('topic_list')  # Redirect after success

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
    template_name = 'topic_confirm_delete.html'  # Confirmation template
    success_url = reverse_lazy('topic_list')

# Department Views
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